/** Correlate live events without attaching an unknown generation to another answer. */
export function findStreamMessage(
  messages: Api.Chat.Message[], generationId?: string, allowUnboundStart = false
): Api.Chat.Message | null {
  if (generationId) {
    const found = [...messages].reverse().find(item => item.role === 'assistant' && item.generationId === generationId);
    if (found) return found;
    if (!allowUnboundStart) return null;
  }
  const latest = messages[messages.length - 1];
  return latest?.role === 'assistant' && (!generationId || !latest.generationId) ? latest : null;
}

/** Replacements and authoritative completions are assignments, never appends. */
export function applyStreamContent(message: Api.Chat.Message, payload: Record<string, unknown>): void {
  if (payload.type === 'chunk') {
    if (message.status === 'finished' || message.status === 'error') return;
    if (typeof payload.chunk === 'string') message.content += payload.chunk;
    message.status = 'loading';
  } else if (payload.type === 'answer_replace' || payload.type === 'completion') {
    if (typeof payload.content === 'string') message.content = payload.content;
  }
}
