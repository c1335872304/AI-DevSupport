# 验收产物索引

本目录收录逐题回答和截图。验收结论在[报告索引](../archive/README.md)，日常验证命令见[测试](../TESTING.md)。

## 逐题记录

| 产物 | 生成入口 |
| --- | --- |
| [ANSWER_QUALITY_FINAL_CASES_2026-10-20.md](2026-10-20/ANSWER_QUALITY_FINAL_CASES_2026-10-20.md) | 对应报告保留原执行记录 |
| [ANSWER_QUALITY_FIRST_CASES_2026-10-20.md](2026-10-20/ANSWER_QUALITY_FIRST_CASES_2026-10-20.md) | 对应报告保留原执行记录 |
| [COMPLEXITY_CHAIN_BASELINE_CASES_2026-10-20.md](2026-10-20/COMPLEXITY_CHAIN_BASELINE_CASES_2026-10-20.md) | [report_complexity_chain.py](../../backend/scripts/report_complexity_chain.py) |
| [COMPLEXITY_CHAIN_FINAL_CASES_2026-10-20.md](2026-10-20/COMPLEXITY_CHAIN_FINAL_CASES_2026-10-20.md) | [report_complexity_chain.py](../../backend/scripts/report_complexity_chain.py) |
| [EVIDENCE_BUDGET_BASELINE_CASES_2026-10-20.md](2026-10-20/EVIDENCE_BUDGET_BASELINE_CASES_2026-10-20.md) | [report_evidence_budget.py](../../backend/scripts/report_evidence_budget.py) |
| [EVIDENCE_BUDGET_FINAL_CASES_2026-10-20.md](2026-10-20/EVIDENCE_BUDGET_FINAL_CASES_2026-10-20.md) | [report_evidence_budget.py](../../backend/scripts/report_evidence_budget.py) |
| [INDEPENDENT_ANSWER_CASES_2026-10-20.md](2026-10-20/INDEPENDENT_ANSWER_CASES_2026-10-20.md) | [summarize_independent_answers.py](../../backend/scripts/summarize_independent_answers.py) |
| [STABLE_PREFIX_BASELINE_CASES_2026-10-20.md](2026-10-20/STABLE_PREFIX_BASELINE_CASES_2026-10-20.md) | [report_stable_prefix.py](../../backend/scripts/report_stable_prefix.py) |
| [STABLE_PREFIX_CACHE_PROBE_CASES_2026-10-20.md](2026-10-20/STABLE_PREFIX_CACHE_PROBE_CASES_2026-10-20.md) | [report_stable_prefix.py](../../backend/scripts/report_stable_prefix.py) |
| [STABLE_PREFIX_FINAL_CASES_2026-10-20.md](2026-10-20/STABLE_PREFIX_FINAL_CASES_2026-10-20.md) | [report_stable_prefix.py](../../backend/scripts/report_stable_prefix.py) |

这些汇总脚本读取已有运行数据。其原始输入路径和判分条件见相应验收报告，缺少本地运行数据时保留原产物，真实模型复跑另按受控预算执行。

## 截图

- [docker-demo-upgrade.png](assets/docker-demo-upgrade.png)
- [docker-vendor-gpt.png](assets/docker-vendor-gpt.png)
- [docker-vendor-knowledge.png](assets/docker-vendor-knowledge.png)
- [phase3-ui-resolved.png](assets/phase3-ui-resolved.png)
- [vendor-scope-fix.png](assets/vendor-scope-fix.png)

截图记录原执行日期的界面。数据库、供应商流水、模型缓存及其他大体量产物继续由报告指向原 `backend/data` 位置。
