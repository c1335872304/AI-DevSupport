# 质量门禁与 CI

更新：2026-10-20。当前目录没有 Git 仓库；工作流已实现并在本地验证对应命令，尚无 GitHub 执行记录。推送后才会触发远端 CI。

| 层级 | 实现 | 范围与边界 |
| --- | --- | --- |
| Fast | `.github/workflows/ci-fast.yml` | 全后端离线回归、冻结输入校验、实际 AgentRuntime 合成轨迹、前端类型/构建、文档与 Compose |
| Integration | `.github/workflows/ci-integration.yml` | 手动或相关 PR 路径触发；专用 MySQL8.4/ES8.17；文档并发、独立进程领取、清理、诊断恢复、防重；保存 JUnit |
| Live | `scripts/evaluate_phase4_diagnosis.py --live --model deepseek-flash` | 独立手动 CLI，不参与默认 CI；合成业务数据、官方 Provider、跨次累计预算 |

Fast 不读模型密钥，不启动外部基础设施。真实模型调用通过显式命令启用，缺密钥和预算耗尽均停止。运行时没有本地哈希编码或空 Key 假向量降级；索引集成测试只通过显式测试替身验证工程行为。

## 门禁

- `python scripts/check_phase4_inputs.py`：冻结数据集 SHA、24个机制任务、开发/保留划分；修改标注必须说明原因并重新冻结。
- `python scripts/evaluate_phase4_diagnosis.py --mode final`：执行真实工作流与模拟业务，禁止外部 Provider；保存逐步证据、参数、候选、复查和真实测试工单。
- `python -m pytest tests -q`：离线全回归。外部条件导致的跳过单独报告，不能计作集成成功。
- Integration 的关键索引/诊断场景不允许跳过；JUnit 的 failures/errors/skipped 均为0。
- 检索与性能对照复用本地冻结源码/知识/真实千问向量，执行脚本见[最终验收](../04-testing/FINAL_PROJECT_ACCEPTANCE.md)。这些较大本地快照不假装由普通 CI 自动拥有。

真实 Provider 的网络失败不会阻断默认离线 CI。LLM 模型/价格、预算、用量未知与失败记录单独审计。当前费用记录见最终验收；不沿用旧虚构语料、旧哈希或其他模型的指标。

CI 安装 `requirements-dev.txt`，Ruff 阻断 E9/F63/F7/F82。前端全量 ESLint 的存量风格债务未纳入本轮，类型与生产构建为当前门禁。远端工作流服务编排仍需 GitHub 首跑确认，不能以本地命令通过声称远端已绿。
