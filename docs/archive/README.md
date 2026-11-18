# 验收与必要追溯

日常使用[七份手册](../README.md)。这里保留七份有代表性的最终测试报告，覆盖不同验证范围，另保留一条未关闭问题的原始证据。

| 最终报告 | 保留依据 |
| --- | --- |
| [源码候选验收](reports/RELEASE_CANDIDATE_ACCEPTANCE_2026-11-19.md) | 当前代码、三个 P1 修复、完整回归和 CI |
| [真实模型与性能验收](reports/ERP_CANDIDATE_RELEASE_ACCEPTANCE_2026-11-18.md) | 真实模型、Token、性能与本机预发布对照 |
| [四阶段核心验收](reports/FINAL_PROJECT_ACCEPTANCE.md) | RAG 召回、索引可靠性和诊断轨迹的机制基线 |
| [RAG 最终验收](reports/RAG_PHASE_ONE_ACCEPTANCE.md) | Docling 样本、跨格式检索、构建及权限的集成结果 |
| [诊断闭环验收](reports/DIAGNOSIS_LOOP_ACCEPTANCE.md) | 正式 HTTP 诊断、修正复查、恢复和幂等交接 |
| [流式交付验收](reports/LIVE_STREAMING_ACCEPTANCE_2026-10-20.md) | 模型结束前交付正文、质量门和权威正文校准的实测 |
| [回答质量修复验收](reports/ANSWER_QUALITY_FIX_2026-10-20.md) | 原题及新题复测，包含仍需追踪的地域与计费范围问题 |

[N12 原始失败证据](evidence/N12_SCOPE_FAILURE_2026-10-20.md)保留原问法、审阅、原回答和结果哈希。现行待办见[维护台账](../MAINTENANCE.md)。

正式题集位于 `backend/eval`，回归用例位于 `backend/tests`。旧文档中的 60 条问法已提取为[待复核候选题库](../../backend/eval/customer_service/manual_question_candidates.json)，保留原 ID、问法、预期边界和来源提交，状态为尚未执行的候选输入。

已完成或过时的计划、进度、框架介绍快照、重复报告及大体积答卷导出直接删除。原始运行数据按报告所列路径核对，历史版本可从 Git 追溯。
