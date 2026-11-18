# 管理员工单台测试计划

> 历史记录：本文保留当时的语料、实现和执行结果，不代表当前系统状态。当前结论见 [第一阶段验收](../reports/RAG_PHASE_ONE_ACCEPTANCE.md)，历史导航见 [历史索引](../README.md#legacy)。


> 状态：已执行。执行结果见 [ADMIN_TICKET_CONSOLE_TEST_REPORT.md](ADMIN_TICKET_CONSOLE_TEST_REPORT.md)；本文仍是用例基线，不代表所有用例均已通过。

## 1. 目标

验证管理员能在“工单管理”页面完成查看、筛选、打开详情与处理工单；同时验证普通用户和未登录者不能读取或修改其他客户的工单。

验收对象：

- 前端路由 `/support-handoff` 与页面 `frontend/src/views/support-handoff/index.vue`；
- 管理员 API：`/api/v1/support/admin/handoffs`；
- 用户 API：`/api/v1/support/handoffs`；
- 工单数据表 `support_handoffs`。

不在本轮范围：客服专属角色、状态机强约束、操作审计时间线、客户侧工单页面、Agent Trace 展示。

## 2. 前置条件

1. Docker 服务已启动，`http://localhost:8000/health` 返回 `200`，前端可访问 `http://localhost:9527`。
2. 准备两个现有账号：

   | 身份 | 用途 |
   |---|---|
   | 管理员 | 登录后台、查看和更新工单 |
   | 普通用户 | 权限拒绝与“仅自己的工单”验证 |

   不在测试记录中写入密码、JWT、API Key 或完整客户敏感内容。

3. 至少存在两张测试工单：一张属于普通用户 A，另一张属于不同用户或管理员。优先复用此前 Agent 显式转人工流程创建的本地演示工单。
4. 开始更新测试前，记录目标工单的 `handoffId`、`status`、`assignedTo`、`resolutionNote` 和 `updatedAt`，以便测试结束后恢复。

## 3. 测试数据与清理规则

| 数据 | 规则 |
|---|---|
| 工单 | 仅使用本地 Demo 或明确标注的测试工单；不得用生产客户数据 |
| 更新用例 | 处理说明使用唯一标记，例如 `ticket-e2e-YYYYMMDD` |
| 恢复 | 用例完成后将状态、处理人和处理说明恢复为执行前快照 |
| 创建工单 | 若需新建，通过客户对话中明确“请转人工”触发；记录真实 `handoffId`，不伪造 |
| 凭据 | 不写入 Markdown、截图、终端输出或浏览器控制台 |

## 4. 分层执行顺序

```text
部署健康
  → 类型检查与生产构建
  → API 权限与契约
  → 管理员页面操作
  → 普通用户隔离
  → 数据恢复与测试报告
```

若 API 权限与契约失败，不继续页面测试；若更新后无法恢复测试数据，立即停止并记录为阻断。

## 5. API 功能与权限用例

所有接口请求均使用实际 Access Token。除无登录用例外，不允许用前端隐藏菜单代替 API 权限验证。

| ID | 身份 | 操作 | 预期 |
|---|---|---|---|
| API-01 | 未登录 | `GET /support/admin/handoffs?page=1&size=10` | `401` |
| API-02 | 普通用户 | 同 API-01 | `403` |
| API-03 | 管理员 | 列表第 1 页，`size=10` | `200`；返回 `data`、`content`、`number`、`size`、`totalElements`、`statistics` |
| API-04 | 管理员 | `status=OPEN` 筛选 | 每条记录状态为 `OPEN`；统计中的 `OPEN` 与总数一致 |
| API-05 | 管理员 | `priority=HIGH`、`category=BILLING`、`userId`、关键词分别筛选 | 返回记录均满足对应条件；无结果时返回空数组与 `totalElements=0` |
| API-06 | 管理员 | 读取 `/support/admin/handoffs/{handoffId}` | `200`；详情工单号正确，包含 `reason`、完整 `summary`、处理字段 |
| API-07 | 管理员 | 读取不存在的工单 | `404` |
| API-08 | 管理员 | 以记录的有效状态、处理人、说明更新目标工单 | `200`；返回字段与请求一致，重新读取后仍一致 |
| API-09 | 管理员 | `status=INVALID` 更新 | `422`，原工单字段不变 |
| API-10 | 普通用户 A | `GET /support/handoffs` | `200`；只返回 A 的工单 |
| API-11 | 普通用户 A | `GET /support/handoffs/{B 的 handoffId}` | `404`，不泄露工单存在性 |
| API-12 | 普通用户 A | `PATCH /support/admin/handoffs/{handoffId}` | `403` |

### 列表脱敏断言

在 API-03 的任意一条列表记录上断言：

- 不含 `reason` 与 `resolutionNote`；
- `summary` 长度不超过 500 个字符；
- 不含 `trace`、`tools`、`arguments`、`apiKey`、`token`、`password` 等敏感或内部运行字段；
- 管理员详情 API 可以按授权返回 `reason` 和完整摘要。

## 6. 管理员页面功能用例

| ID | 操作 | 预期 |
|---|---|---|
| UI-01 | 以管理员登录 | 左侧出现“工单管理”，进入 `/support-handoff` 无 `403` 页面 |
| UI-02 | 首次打开页面 | 显示四张统计卡、筛选栏、表格与分页；加载态结束后无控制台异常 |
| UI-03 | 切换页码和页大小 | 发送带正确 `page` / `size` 的请求，表格和总数同步变化 |
| UI-04 | 分别按关键词、客户 ID、状态、优先级、分类筛选 | 点击“筛选”后表格和统计卡按服务端结果刷新；“重置”恢复默认列表 |
| UI-05 | 点击“查看” | 打开详情抽屉，工单号、客户、转人工原因、Agent 摘要、会话/生成记录与列表记录一致 |
| UI-06 | 修改状态、处理人与处理说明并保存 | 成功提示出现；关闭并重开详情后字段仍存在；列表状态/处理人同步更新 |
| UI-07 | 提交无效状态（使用 API 或临时请求构造） | 页面给出失败反馈，原数据保持不变 |
| UI-08 | 工单为空 | 表格展示空状态，统计为 0，不出现异常 |

UI-06 完成后必须执行“恢复”步骤，将目标工单写回执行前的字段快照。

## 7. 普通用户页面隔离用例

| ID | 操作 | 预期 |
|---|---|---|
| AUTH-01 | 以普通用户登录 | 菜单不显示“工单管理” |
| AUTH-02 | 手动访问 `http://localhost:9527/support-handoff` | 路由守卫拒绝访问或跳转到权限页；不得显示工单数据 |
| AUTH-03 | 浏览器开发工具或 HTTP 客户端调用管理员列表 | 后端返回 `403`，即使前端路由逻辑被绕过也是如此 |
| AUTH-04 | 调用自己的 `/support/handoffs` | 仅能获得自己的工单，不含其他用户记录 |

## 8. 自动化建议

首轮以浏览器手工验收与 API 请求为准，避免测试脚本在 Docker 重建期间误判服务启动状态。稳定后新增：

1. 后端 API 集成测试：覆盖 API-01～API-12，使用隔离数据库和固定 JWT 夹具；
2. Playwright E2E：覆盖 UI-01、UI-03～UI-06 与 AUTH-01～AUTH-02；
3. 契约测试：锁定分页结构和列表脱敏字段，防止 API 恢复成无分页数组或意外暴露工单正文。

自动化测试必须使用独立测试工单，不能更新 Demo 之外的真实记录。

## 9. 通过标准与报告模板

模块只有在下列条件同时满足时才标记“功能通过”：

- API-01～API-12 全部通过；
- UI-01～UI-08 全部通过；
- AUTH-01～AUTH-04 全部通过；
- 更新测试数据已恢复；
- `pnpm typecheck`、`pnpm build` 与相关后端测试通过；
- 测试报告记录环境、工单 ID（可部分脱敏）、结果、失败证据与恢复结果。

执行报告应写入 `docs/04-testing/history/ADMIN_TICKET_CONSOLE_TEST_REPORT.md`，并使用以下摘要：

```text
执行时间：
环境与镜像：
管理员/普通用户身份：已验证，凭据未记录
测试工单：
API：通过 X / 12
UI：通过 X / 8
权限：通过 X / 4
数据恢复：通过 / 失败
结论：通过 / 失败 / 阻断
```
