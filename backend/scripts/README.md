# 脚本入口与边界

从 `backend/` 执行，使用应用环境解释器。脚本默认读取 `.env`；写入或真实 Provider 调用前核对目标数据库、存储、索引和用户。不要把验收账号、测试 URL 或示例代理当成部署配置。

## 常用命令

| 命令 | 用途 | 影响 |
| --- | --- | --- |
| `python -m alembic upgrade head` | 数据库升级，先备份 | 修改 schema；无需另写迁移脚本 |
| `python scripts/check_docs.py` | 检查当前与历史文档的本地链接、代码围栏 | 只读；不校验远端 URL 和页内锚点 |
| `python scripts/seed_demo_knowledge.py --validate-only` | 校验当前官方语料、解析与分块 | 不建库、不编码 |
| `python scripts/seed_demo_knowledge.py --username admin` | 按默认官方清单导入/更新 | 写存储、数据库和索引，可能产生编码费用 |
| `python scripts/evaluate_rag.py eval/vendor_full_rag.jsonl --username admin -k 6` | 当前官方语料检索评测 | 查询编码有费用；结果须记录检索后端和过滤条件 |
| `python scripts/cache_docling_models.py` | 固定模型预下载 | 网络与本地模型缓存；代理按实际环境设置 |
| `python scripts/verify_docling.py` | 验证 Docling 真实样本 | 独立解析进程及本地报告 |
| `python scripts/privacy_maintenance.py --help` | 隐私维护参数 | 执行前检查参数与目标数据 |

`seed_demo_knowledge.py` 为兼容原调用保留名字，默认清单已是 `vendor_knowledge/manifest.json`。普通导入优先不加 `--reset`；`--reset`/`--reindex` 用于保留身份的强制重建，可能重复付费。

## 开发、验收与历史工具

| 类别 | 脚本 | 使用条件 |
| --- | --- | --- |
| 语料采集 | `collect_vendor_knowledge.py` | 更新快照须复核来源、清单和评测，不自动覆盖现有库 |
| 显式重建/旧语料退出 | `rebuild_qwen_knowledge.py`、`remove_legacy_demo_knowledge.py` | 仅有明确迁移需求时使用，不放启动钩子 |
| 业务与隔离夹具 | `seed_support_demo.py`、`seed_advanced_rag_fixtures.py`、`generate_docling_fixtures.py` | 模拟数据；优先专用测试库 |
| 离线评测 | `evaluate_*.py`、`validate_blind_dataset.py` | 数据集可能属于历史语料，先核对适用范围 |
| 真实模型观察 | `inspect_live_agent_run.py`、`run_live_refund_retest.py` | 显式授权、限制调用量并记录费用 |
| 第一阶段专用验收 | `phase1_acceptance_server.py`、`prepare_phase1_ui_fixture.py`、`verify_phase1_api.py`、`verify_kafka_indexing.py`、`verify_crossformat_rag.py` | 独立本地 MySQL/ES/Kafka 与测试账号；不是正式服务启动命令 |
| 第一阶段迁移工具 | `upgrade_phase1_application.py`、`verify_phase1_migration.py` | 前者修改应用库并备份；后者在副本演练，不在重启时重复升级 |
| 冻结基线与回放 | `run_phase1_baseline.py`、`verify_phase1_retrieval.py`、`verify_final_retrieval.py`、`benchmark_rag_checkpoint.py` | 参数与快照绑定当轮证据，不作为通用在线健康检查 |

专用脚本保留原位置，避免破坏报告、测试和人工运维引用。复用能力放入 `app/`；应用不导入这些验收脚本。

[文档导航](../../docs/README.md) · [RAG 运行手册](../../docs/OPERATIONS.md#knowledge) · [第一阶段验收](../../docs/archive/reports/RAG_PHASE_ONE_ACCEPTANCE.md)

## 第二阶段验收

- `verify_phase2_migration.py`：应用 SQLite 副本升级/回退演练；`--apply` 才备份并升级应用库。
- `phase2_acceptance_server.py`：独立 SQLite 与模拟诊断页面，禁用模型/编码，API 18026；不是正式启动命令。
- `verify_phase2_api.py`：仅访问上述本地夹具，验证登录、诊断读取、历史/generation 关联及未授权拒绝。
- 诊断测试支持 `PHASE2_TEST_MYSQL_URL` 指向专用验收库，禁止指向已有应用库。

设计与验证见 [诊断架构](../../docs/ARCHITECTURE.md#diagnosis) 和 [第二阶段验收](../../docs/archive/reports/DIAGNOSIS_STATE_ACCEPTANCE.md)。

## 第三阶段验收

- `verify_phase3_migration.py`：应用 SQLite 副本升级/回退演练，`--apply` 才备份并升级实际应用库。
- `phase3_acceptance_server.py`：独立 SQLite、测试账号与新旧请求，禁用真实模型/编码，API 18036；每次生成新验收会话，不替代正式启动。
- `verify_phase3_api.py`：仅访问上述夹具，验证候选原因、新请求复查、revision 和幂等键。
- `PHASE3_TEST_MYSQL_URL`：只允许专用测试库，用于 `tests/agent/test_diagnosis_loop.py`。
- `verify_phase3_delivery.py`：比较起点知识/配置指纹，保存交付源码与数据库副本，排除实际 `.env` 和依赖目录。

步骤与限制见[诊断运行手册](../../docs/OPERATIONS.md#diagnosis)和[第三阶段验收](../../docs/archive/reports/DIAGNOSIS_LOOP_ACCEPTANCE.md)。

## 第四阶段评测与交付

| 脚本 | 范围 |
| --- | --- |
| `check_phase4_inputs.py` | 只读校验冻结输入，不调用模型 |
| `evaluate_phase4_retrieval.py --system plain/baseline/final` | 各运行一次，独立 DB 副本、120条冻结真实千问向量；不重新编码 |
| `evaluate_phase4_diagnosis.py --mode preopt/final` | 优化前后工作流的24个实际 AgentRuntime 合成任务；逐轨迹评分 |
| 同上 `--live --model deepseek-flash` | 显式付费验收；最多6请求/100,000字节/每次512输出Token，2元预算，跨次账本不自动重置 |
| `compare_phase4_cleanup.py` | 冻结旧索引器的两连接清理交错；仅临时 SQLite/显式替身 |
| `summarize_phase4.py` | 重评保存轨迹，合并三组检索、真实服务JUnit与Live；缺失/失败不放绿 |
| `phase4_demo_server.py`、`verify_phase4_demos.py` | 独立端口18046、三条HTTP演示，实际配置不变 |
| `verify_phase4_delivery.py` | 比较第四阶段起点知识/配置指纹，保存最终源码和数据库副本，排除实际 `.env` |

对照脚本依赖本机 checkpoints 中受保护的起点源码、知识副本与查询向量；缺失即失败，不能伪造基线。普通CI只跑无需这些大快照的最终轨迹门禁。结果和费用口径见[最终验收](../../docs/archive/reports/FINAL_PROJECT_ACCEPTANCE.md)，演示见[启动材料](../../docs/TESTING.md#demos)。

## Docker 原地升级验收

- `bootstrap_demo.py`：空库初始化；已有业务和知识则跳过各自的导入，不重编码旧库。
- `docker_demo_probe.py`：兼容0006/0015的只读知识摘要，不输出密钥，不调用Provider。
- `repair_legacy_embedding_metadata.py`：先逐条核对活动DB记录、ES身份/正文/向量，再补齐旧ES缺失的模型名和维度。默认只读，`--apply`才更新；有冲突即停止，使用ES并发条件，无编码/DB写入。
- `docker_demo_fixture.py prepare/cleanup`：仅创建、清理带唯一前缀且ID匹配的临时验收账号及其资料；凭据留在容器`/tmp/docker_demo_acceptance.json`，不可公开。`grant-upload-quota`仅补充该测试账号的DOCX字节数预检额度。
- `verify_docker_demo.py`：通过9527的真实HTTP/WS验证诊断、Billing MCP与文档生命周期；使用检查点private夹具，不可用真实客户账号。成功的WS轨迹可复用以控制付费调用，失败不记为通过。

本次执行与回滚说明见 [Docker升级验收](../../docs/archive/reports/DOCKER_DEMO_UPGRADE_2026-10-20.md)。

官方语料替换使用`export_vendor_vectors.py`只读导出清单内60份原文和现有Qwen向量，`migrate_vendor_vectors.py`核对包摘要及精确旧文档清单，完整暂存后发布、定向清理。两者不调用编码，不复制用户/配置/计费台账；要求停写及备份，默认预检，`--apply`才迁移。见[迁移验收](../../docs/archive/reports/DOCKER_VENDOR_KNOWLEDGE_MIGRATION_2026-10-20.md)。`verify_docker_demo.py`可用`DOCKER_DEMO_ACCEPTANCE_DIR`选择独立检查点，`DOCKER_DEMO_BILLING_QUESTION`指定有界重测问题；原失败轨迹必须保留。

## 独立回答评测（有真实 Provider 费用）

- `evaluate_independent_answers.py`：2026-10-20冻结的12题首次执行客户端；真实会话、检索、生成和引用检查。已有逐题产物保留首轮，不自动重跑；入口固定本机18870，账号来自检查点private目录。
- `answer_eval_observer.py`：同镜像临时ASGI入口，旁路观测httpx返回的用量；不改写请求和回答。默认预算上限10元、144次Provider请求，按frozen-inputs.json设定；本次两轮为10元/300次。重启从既有流水恢复累计预算，禁止与主API重复执行启动恢复/维护。它不是替代生产入口。
- `answer_eval_identity.py prepare/cleanup`：仅创建临时USER、不写知识及厂商账户事实；清理前核对账号ID/前缀、无自有文档、无运行生成或未结算预留，定向移除该账号及其轨迹。
- `summarize_independent_answers.py`：只读原始结果和用量，核对冻结摘要，汇总延迟/公开价费用与引用映射，生成逐题证据；不调用模型、不自动冒充事实裁判。

本批账号和容器已清理。复测须另建有预算、独立冻结输入和检查点的运行，不覆盖本批证据。private配置、登录凭据不得进入源码包。结果、运行步骤及边界见[评测报告](../../docs/archive/reports/INDEPENDENT_ANSWER_EVALUATION_2026-10-20.md)。

修复重验通过`--checkpoint`与`--dataset`选择新的冻结组合；汇总器支持`--review`、`--report`，按每题起止时间隔离同一流水中的多轮用量。首轮与最终结果分目录保留。`replay_vendor_retrieval.py`在容器`/evaluation`读取现有query-vectors.json，只读重放120条ES检索，不重新编码，不将其当作回答生成评测。见[本次修复验收](../../docs/archive/reports/ANSWER_QUALITY_FIX_2026-10-20.md)。
# 复杂度调用链评测（2026-10-20）

`probe_stable_prefix.py`：从自然验收已授权证据冻结固定选材，使用真实Provider对照“问题在前”和“稳定证据在前”；独立固定实验标记仅用于测试，不写生产配置。与ASGI observer共用累计预算文件时必须串行，格式实验后重启observer再做任何Provider调用，避免独立进程请求编号冲突。完整映射、来源和旧编号在private/原始证据内，报告不公开签名。

`report_stable_prefix.py`：离线复算自然题与独立格式实验的Token加权缓存命中率、耗时及费用，要求已有审阅和原始答复哈希，禁止自动给修改后的答复判通过。参见 [STABLE_PREFIX_OPTIMIZATION_2026-10-20.md](../../docs/archive/reports/STABLE_PREFIX_OPTIMIZATION_2026-10-20.md)。

`report_evidence_budget.py` 离线复算后续上下文压缩评测；人工review必须存在且绑定回答产物哈希，脚本不自动给新答案判分。原始失败及全部usage保留，实测缓存成本与全部未命中的归一化成本分列，详见 [EVIDENCE_BUDGET_OPTIMIZATION_2026-10-20.md](../../docs/archive/reports/EVIDENCE_BUDGET_OPTIMIZATION_2026-10-20.md)。

`report_complexity_chain.py` 从已冻结的本地证据复算旧链路/优化后质量、调用量、耗时与费用，无模型调用。`complexity_eval_fixture.py` 仅为临时评测用户准备Demo请求和诊断后新建的复查请求；`eval_route_cache.py` 仅备份、重置、恢复冻结题目的缓存键。必须保留失败尝试及费用，评测结束恢复缓存并清理临时身份。详见 [COMPLEXITY_CHAIN_OPTIMIZATION_2026-10-20.md](../../docs/archive/reports/COMPLEXITY_CHAIN_OPTIMIZATION_2026-10-20.md)。


历史逐题回答的汇总默认输出到 `docs/artifacts/2026-10-20`，索引见[验收产物](../../docs/artifacts/README.md)。日常文档与历史报告分别从[文档入口](../../docs/README.md)和[归档索引](../../docs/archive/README.md)查阅。
