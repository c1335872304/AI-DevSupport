# 脚本入口

从 `backend` 的应用环境执行。参数和默认目标以各脚本为准，涉及写入、迁移或真实 Provider 时核对实际数据库、存储、索引和调用范围。

| 用途 | 入口 |
| --- | --- |
| 文档与冻结校验 | `check_docs.py`、`check_phase4_inputs.py` |
| 数据库迁移 | `python -m alembic upgrade head` |
| 官方知识导入 | `seed_demo_knowledge.py --validate-only` 校验，`--username <user>` 导入，`--reindex` 强制重建 |
| 解析环境 | `cache_docling_models.py`、`verify_docling.py` |
| 当前客服演示 | `run_customer_service_demo.py` |
| 退款与关单演示 | `run_refund_sandbox_demo.py` |
| 诊断演示 | `phase4_demo_server.py`、`verify_phase4_demos.py` |
| 轨迹评分 | `evaluate_phase4_diagnosis.py --mode final`，真实模型通过显式 `--live` 入口 |
| 检索评测 | `evaluate_rag.py eval/vendor_full_rag.jsonl --username <user> -k 6` |
| 发布探测 | `observe_rollout.py` |
| 隐私维护 | `privacy_maintenance.py` |

日常命令与配置见[测试](../../docs/TESTING.md)、[运维](../../docs/OPERATIONS.md)和[发布](../../docs/RELEASING.md)。保留的最终结果见[验收索引](../../docs/archive/README.md)。

## 历史数据工具

阶段专用迁移、夹具和独立验收脚本保留各自的输入及环境条件，操作前阅读其目标和影响。普通应用升级统一使用 Alembic，知识导入默认按稳定身份更新，真实编码和检索会产生 Provider 调用。

`report_complexity_chain.py`、`report_evidence_budget.py`、`report_stable_prefix.py` 和 `summarize_independent_answers.py` 根据已有原始结果和审阅复算。默认导出到 `backend/data/reports/2026-10-20`。这些导出按需生成，完整答卷不进入日常文档目录。

正式题集、人工审阅与冻结清单保存在 `backend/eval`。手工候选问法单独保存为 `customer_service/manual_question_candidates.json`，复核后才能纳入冻结评测。真实模型复跑使用独立输出目录并记录预算、版本、失败和实际用量。
