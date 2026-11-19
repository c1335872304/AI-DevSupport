/** Public phases are an allowlist, never server-supplied reasoning or tool arguments. */
export const progressLabels: Record<string, string> = {
  understanding: '正在理解你的问题',
  checking: '正在核对相关信息',
  searching_documents: '正在查找相关文档',
  checking_request: '正在核查请求记录',
  checking_billing: '正在核对套餐和账单',
  supplementing: '正在补查缺少的证据',
  reviewing: '正在核对查询结果',
  creating_handoff: '正在提交人工工单',
  answering: '正在整理回答',
  waiting_for_user: '等待你补充信息',
  handed_off: '已转交人工处理'
};

export function applyWorkflowProgress(message: Api.Chat.Message, payload: Record<string, unknown>): void {
  if (!['pending', 'loading'].includes(message.status || '')) return;
  if (!message.generationId || payload.generationId !== message.generationId) return;
  if (typeof payload.phase !== 'string' || !Object.hasOwn(progressLabels, payload.phase)) return;
  const timestamp = Number(payload.timestamp);
  if (!Number.isFinite(timestamp) || timestamp <= 0 || timestamp < (message.workflowProgressAt || 0)) return;
  if (message.workflowProgress !== payload.phase) message.workflowStageStartedAt = Date.now();
  message.workflowProgress = payload.phase;
  message.workflowProgressAt = timestamp;
}
