import process from 'node:process';
import assert from 'node:assert/strict';
import { applyWorkflowProgress, progressLabels } from '../src/utils/chat-progress';
import { applyStreamContent, findStreamMessage } from '../src/utils/chat-stream';

const a = { role: 'assistant', content: '', status: 'loading', generationId: 'a' } as Api.Chat.Message;
const b = { role: 'assistant', content: '', status: 'pending', generationId: 'b' } as Api.Chat.Message;
const list = [a, b];
assert.equal(findStreamMessage(list, 'a'), a);
assert.equal(findStreamMessage(list, 'unknown'), null);
assert.equal(findStreamMessage(list, 'unknown', true), null);
const pending = { role: 'assistant', content: '', status: 'pending' } as Api.Chat.Message;
assert.equal(findStreamMessage([pending], 'new', true), pending);

applyStreamContent(a, { type: 'chunk', chunk: 'first' });
applyStreamContent(a, { type: 'chunk', chunk: ' second' });
assert.equal(a.content, 'first second');
assert.equal(b.content, '');
applyStreamContent(a, { type: 'answer_replace', content: 'corrected' });
assert.equal(a.content, 'corrected');
// Final content also repairs a missed live event; it is not appended twice.
applyStreamContent(a, { type: 'completion', content: 'authoritative final' });
assert.equal(a.content, 'authoritative final');
a.status = 'finished';
applyStreamContent(a, { type: 'chunk', chunk: 'late' });
assert.equal(a.content, 'authoritative final');
a.status = 'error';
applyStreamContent(a, { type: 'chunk', chunk: 'late' });
assert.equal(a.content, 'authoritative final');
process.stdout.write(
  'PASS: generation isolation, initial binding, append, correction, missed-event reconciliation and terminal protection\n'
);

const replay: Api.Chat.Message = { ...a, status: 'loading', content: 'A' };
applyStreamContent(replay, { type: 'chunk', chunk: 'B', content: 'AB' });
applyStreamContent(replay, { type: 'chunk', chunk: 'B', content: 'AB' });
assert.equal(replay.content, 'AB');

const progress: Api.Chat.Message = { ...a, status: 'loading', workflowProgress: undefined };
applyWorkflowProgress(progress, { generationId: 'b', phase: 'checking_billing', timestamp: 20 });
assert.equal(progress.workflowProgress, undefined);
applyWorkflowProgress(progress, {
  generationId: 'a',
  phase: 'checking_billing',
  timestamp: 20,
  text: 'private reasoning'
});
assert.equal(progressLabels[progress.workflowProgress || ''], '正在核对套餐和账单');
applyWorkflowProgress(progress, { generationId: 'a', phase: 'checking_request', timestamp: 19 });
assert.equal(progress.workflowProgress, 'checking_billing');
applyWorkflowProgress(progress, { generationId: 'a', phase: 'private reasoning', timestamp: 21 });
assert.equal(progress.workflowProgress, 'checking_billing');
applyWorkflowProgress(progress, { generationId: 'a', phase: '__proto__', timestamp: 21 });
assert.equal(progress.workflowProgress, 'checking_billing');
progress.status = 'finished';
applyWorkflowProgress(progress, { generationId: 'a', phase: 'checking_request', timestamp: 22 });
assert.equal(progress.workflowProgress, 'checking_billing');
