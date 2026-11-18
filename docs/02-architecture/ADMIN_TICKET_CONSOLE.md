# 管理员工单台

> 状态：当前实现基线（2026-09-10）。管理员页面和 API 的执行结果见 [ADMIN_TICKET_CONSOLE_TEST_REPORT.md](../04-testing/history/ADMIN_TICKET_CONSOLE_TEST_REPORT.md)。

## 1. 目标与范围

工单台用于让管理员处理 Agent 创建的人工交接（`SupportHandoff`）。它不是新的工单创建渠道：工单仍只能由客服工作流在证据汇总和人工交接决策后，经 `create_support_handoff` 创建。

本模块提供以下闭环：

```text
客户请求人工 / 高风险操作 / 无法安全解决
  → Agent 证据汇总
  → 创建 SupportHandoff
  → 管理员在“工单管理”筛选、查看与处理
  → 更新状态、处理人、处理说明
```

第一版不向客户前端展示管理员处理说明，也不提供客服专属角色。当前项目只有 `ADMIN` 与 `USER` 两个角色，因此所有工单管理操作均属于管理员权限。

## 2. 前端入口与界面

管理员登录后可在左侧菜单进入 **工单管理**（路由 `/support-handoff`）。路由元数据为 `roles: ['ADMIN']`，普通用户不会看到该入口；真正的访问控制仍由 API 端校验。

页面由以下部分组成：

| 区域 | 内容 |
|---|---|
| 汇总卡片 | 当前筛选结果下的待处理、处理中、高优先级与工单总数 |
| 筛选栏 | 关键词、客户 ID、状态、优先级、分类 |
| 远程表格 | 工单号、客户、分类、优先级、状态、摘要、处理人、创建时间 |
| 详情抽屉 | 转人工原因、Agent 摘要、关联会话/生成记录，以及处理表单 |
| 处理表单 | 状态、处理人、处理说明；保存后刷新当前列表 |

页面布局约束：侧栏菜单内容独立滚动，底部收起按钮不覆盖菜单项；筛选栏使用响应式网格，宽屏单行、中等宽度换行、小屏单列；列表摘要只展示受控省略，完整内容在详情抽屉中查看。当前产品品牌显示为“API 助手”。

“关键词”在服务端匹配工单号、客户 ID、摘要和转人工原因。筛选须点击“筛选”提交，避免每次键入都产生请求。

## 3. 数据与状态

工单表为 `support_handoffs`，核心字段如下：

| 字段 | 说明 |
|---|---|
| `handoff_id` | 工单号，例如 `CS_xxx` |
| `user_id` | 请求人工的客户；管理员列表会关联显示用户名 |
| `conversation_id` / `generation_id` | 关联会话和 Agent 生成记录 |
| `category` / `priority` | 分类和优先级 |
| `reason` / `summary` | 转人工依据与 Agent 整理摘要 |
| `assigned_to` / `resolution_note` | 处理人和管理员内部处理说明 |
| `status` | `OPEN`、`IN_PROGRESS`、`RESOLVED`、`CLOSED` |

当前接口允许管理员在上述四种状态间更新。状态机强约束、处理审计时间线和专属客服角色尚未实现；在这些需求确定前，不应假定系统会自动分派或自动关闭工单。

## 4. 权限与数据边界

| 调用方 | 可做事项 |
|---|---|
| 未登录者 | 不能访问管理员工单接口，返回 `401` |
| 普通用户 | 只能通过 `/api/v1/support/handoffs` 查看自己的工单；不能访问管理员列表和更新接口，返回 `403` |
| 管理员 | 可查看全部工单、查看详情并更新处理字段 |

管理员接口统一使用 `admin_user` 依赖校验，前端菜单隐藏不是权限措施。

列表接口遵循最小暴露原则：不返回 `reason`、`resolutionNote`，`summary` 最多 500 个字符。完整工单正文仅在管理员详情接口返回。所有文本在前端按普通文本渲染，不执行 HTML。原始 Tool 参数、Token、API Key、完整 Agent Trace 不进入本模块的列表或详情响应。

## 5. API 契约

所有路径均以 `/api/v1` 为前缀，并要求 Bearer Access Token。

### 管理员分页列表

```text
GET /support/admin/handoffs?page=1&size=10
  &status=OPEN
  &priority=HIGH
  &category=BILLING
  &keyword=429
  &userId=2
```

只有 `page` 与 `size` 必填默认值（分别为 `1` 与 `10`）；其余筛选条件可省略。`size` 范围为 1–100。

返回遵循项目统一表格结构：

```json
{
  "code": 200,
  "data": {
    "data": [{ "handoffId": "CS_xxx", "username": "demo_user" }],
    "content": [{ "handoffId": "CS_xxx", "username": "demo_user" }],
    "number": 1,
    "size": 10,
    "totalElements": 1,
    "statistics": {
      "status": { "OPEN": 1 },
      "priority": { "HIGH": 1 }
    }
  }
}
```

此前该接口返回无分页数组；前端模块启用时已改为上述统一分页结构。若存在项目外部调用方，需同步迁移其解析逻辑。

### 管理员详情与更新

```text
GET   /support/admin/handoffs/{handoffId}
PATCH /support/admin/handoffs/{handoffId}
```

更新请求体：

```json
{
  "status": "IN_PROGRESS",
  "assignedTo": "admin",
  "resolutionNote": "已联系客户，等待补充 request_id。"
}
```

`status` 只能取 `OPEN`、`IN_PROGRESS`、`RESOLVED`、`CLOSED`；无效值返回 `422`。

### 用户侧读取

```text
GET /support/handoffs
GET /support/handoffs/{handoffId}
```

普通用户仅能读取自己的工单；访问他人工单时返回 `404`，避免泄露工单存在性。

## 6. 代码位置

| 内容 | 位置 |
|---|---|
| 管理员工单页面 | `frontend/src/views/support-handoff/index.vue` |
| 路由、菜单权限 | `frontend/src/router/elegant/routes.ts` |
| 前端 API 类型 | `frontend/src/typings/api.d.ts` |
| 工单 API | `backend/app/api/v1/support.py` |
| 序列化与状态校验 | `backend/app/support/handoff.py` |
| 工单模型 | `backend/app/db/models.py` 的 `SupportHandoff` |

## 7. 验收与当前验证状态

本模块的 API、管理员浏览器页面、分页筛选、详情保存、列表脱敏、普通用户接口隔离和 Docker 前端构建均已有执行记录。当前仍保留两个测试夹具缺口：

1. 需要第二个用户的现存工单，才能闭环验证管理员访问“其他用户工单”的真实数据场景；
2. 需要可用的普通用户浏览器账号，才能完成普通用户菜单隐藏和手动访问管理员路由的页面级验证。

详细通过项、未闭环项、数据恢复说明和本轮 UI 修复记录，以 [ADMIN_TICKET_CONSOLE_TEST_REPORT.md](../04-testing/history/ADMIN_TICKET_CONSOLE_TEST_REPORT.md) 为准；本架构文档不重复维护测试数字。
