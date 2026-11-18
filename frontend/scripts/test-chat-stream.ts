import assert from 'node:assert/strict';
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
console.log('PASS: generation isolation, initial binding, append, correction, missed-event reconciliation and terminal protection');
