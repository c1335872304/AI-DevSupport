---
name: knowledge
description: 企业知识库检索与引用专业工作流；适用于政策、产品说明、错误码、API 文档和使用方法，不能代替账户事实查询。
triggers: ["知识库", "文档", "说明", "政策", "规则", "如何使用", "怎么用", "是什么", "API 文档", "错误码", "产品说明", "使用方法"]
negative_triggers: ["已经解决", "不用查文档"]
allowed_tools: ["search_knowledge", "list_documents", "get_document", "read_skill_reference", "run_skill_script"]
references: ["references/retrieval-and-citation.md", "references/knowledge-boundary.md"]
scripts: ["rewrite_knowledge_query", "audit_knowledge_answer"]
evals: ["eval/routing.jsonl", "eval/behavior.jsonl", "eval/answer.jsonl"]
quality_gate: audit_knowledge_answer
priority: 70
---
# Knowledge

## 目标
从企业知识库中找出与当前问题最相关的证据，并用可追溯来源回答。知识库只提供通用资料，不能推断某个客户的订单、支付、退款到账或账户状态。

## 工作流
1. 先理解问题，再结合历史实体和当前上下文改写检索词；不要把整段无关历史直接塞进查询。
2. 政策、产品说明、错误码、API 文档和使用方法优先调用 `search_knowledge`；需要浏览文件目录或取完整文档时再使用 `list_documents` / `get_document`。
3. 已知产品、错误码、渠道、类别或月份时尽量使用 Metadata Filter；Filter 是检索约束，不是权限替代。
4. 只使用实际返回的结果，引用来源编号、文件名和页码（如有）。没有命中时明确说明资料不足，不用模型常识补齐企业规则。
5. 如果问题要求查询个人账户事实，停止用知识库猜测，交回 `customer-support` 或对应业务 Tool；如果是退款申请等高风险操作，交给 `billing + escalation`。

需要选择检索词和过滤器时读取 [references/retrieval-and-citation.md](references/retrieval-and-citation.md)；需要判断知识库边界时读取 [references/knowledge-boundary.md](references/knowledge-boundary.md)。最终输出前运行 `audit_knowledge_answer`。

## 输出契约
- 先回答问题，再给最少必要依据和下一步。
- 每个企业事实都应能追溯到本轮真实检索结果。
- 不把知识库政策写成个人账户状态，不伪造不存在的文档或引用。
- 只展示当前用户有权限看到的资料。
