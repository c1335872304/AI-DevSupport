# 三条可复现演示与交付启动

适用：第四阶段交付源码、迁移0015。普通启动见[本地启动](../01-getting-started/GETTING_STARTED.md)；诊断恢复见[运行手册](DIAGNOSIS_OPERATIONS.md)。本页命令均在 backend 执行。

## 独立演示环境

```powershell
.\.venv\Scripts\python.exe scripts/phase4_demo_server.py
```

API 仅监听127.0.0.1:18046，独立 SQLite `data/phase4-demo.sqlite` 与存储目录；禁用模型和编码，每次生成新会话，不导入或清空正式知识。测试账号 loopaccept / LoopAccept123 只属于这个独立环境。首次准备包含结构化模拟日志与请求时观测，不能用于证明三家厂商账户。

另一个终端执行：

```powershell
.\.venv\Scripts\python.exe scripts/verify_phase4_demos.py
```

应得到3条通过记录；报告和诊断 ID 写入 `data/checkpoints/phase4/demos-report.json`。夹具新请求必须在五分钟内复查，超时重新启动生成新会话；不要把旧请求时间改成现在。

| 演示 | 输入与实际路径 | 预期结果 |
| --- | --- | --- |
| 401修正后恢复 | 过期 Key 请求及当时观测；模拟拥有者修正后提交新200请求 | 同用户/应用/接口校验后 RESOLVED，仅确认新请求范围 |
| 429修正仍失败 | 原请求频率观测；新请求429配额观测 | STILL_FAILING，原因改为配额，WAITING_USER_ACTION；不假称已恢复 |
| 人工交接 | 用户明确要求人工；程序汇总事实并创建真实测试工单 | HANDED_OFF；重复“继续”不重复建单 |

面板演示可单独启动前端：进程级设置 VITE_SERVICE_BASE_URL=http://127.0.0.1:18046/api/v1，VITE_OTHER_SERVICE_BASE_URL 的 api 指向该地址、ws 指向 ws://127.0.0.1:18046，再运行 `pnpm exec vite --host 127.0.0.1 --port 19547 --strictPort`。不要改已有 `.env`；登录后选择对应会话，输入 `demos-fixture.json` 中的新请求号。

## 新开发环境

1. Python3.12、Node20、pnpm按锁文件安装；后端 `pip install -r requirements-dev.txt`，前端 `pnpm install --frozen-lockfile`。若从无实际配置的源码归档恢复，首次将前端 `.env.example` 复制为 `.env.development`；生产模式单独设置相对API和WS地址，不覆盖已有文件。
2. 首次创建 `.env` 时使用示例；已有配置不覆盖。SQLite或MySQL先备份，再执行 `python -m alembic upgrade head`。
3. 普通服务使用现有启动入口；Docling需要独立解析环境及固定模型缓存，扫描OCR未纳入本轮。
4. 知识检索必须有真实千问 Key；可导入官方快照，也可恢复受保护数据库与对象存储。不要为了演示全库重编。上面三条模拟诊断无需任何 Provider Key。
5. 真实模型验收使用显式临时参数。当前配置 deepseek-chat 未出现在本轮官方模型列表；本轮实际验收使用 deepseek-flash，不自动替用户修改配置或推断旧别名可用。

生产多实例、滚动部署和大负载属于独立部署验收。现有 Docker Demo 未重建，不能用这三条独立本地演示证明已有生产容器已更新。
