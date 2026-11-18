<script setup lang="ts">
// eslint-disable-next-line @typescript-eslint/no-unused-vars
import { nextTick } from 'vue';
import { router } from '@/router';
import { request } from '@/service/request';
import { formatDate } from '@/utils/common';
import { VueMarkdownIt } from '@/vendor/vue-markdown-shiki';
import DiagnosisPanel from './diagnosis-panel.vue';
defineOptions({ name: 'ChatMessage' });

const props = defineProps<{
  msg: Api.Chat.Message,
  sessionId?: string,
  retrievalQueryFallback?: string
}>();

const authStore = useAuthStore();
const progressNow = ref(Date.now());
let progressTimer: ReturnType<typeof setInterval> | undefined;
onMounted(() => { progressTimer = setInterval(() => { progressNow.value = Date.now(); }, 1000); });
onUnmounted(() => { if (progressTimer) clearInterval(progressTimer); });
const running = computed(() => ['pending', 'loading'].includes(props.msg.status || ''));
const progressText = computed(() => ({
  load_context: '正在读取会话上下文', extract_entities: '正在理解你的问题',
  routing_policy: '正在选择处理流程', target_specialist_dispatch: '正在核查处理步骤',
  target_execute_tools: '正在查询资料或业务记录', target_evidence_join: '正在汇总查询证据',
  target_handoff_decision: '正在确认后续处理方式', target_create_handoff: '正在创建人工工单',
  target_generate_response: props.msg.content ? '正在继续生成回答' : '正在根据证据生成回答',
  safety: '正在完成最终检查', emit_final: '正在整理最终引用', persist_trace: '正在保存结果'
} as Record<string, string>)[props.msg.workflowStage || ''] || '正在处理你的问题');
const stageSeconds = computed(() => Math.max(0, Math.floor(
  (progressNow.value - (props.msg.workflowStageStartedAt || progressNow.value)) / 1000
)));

function handleCopy(content: string) {
  navigator.clipboard.writeText(content);
  window.$message?.success('已复制');
}

const chatStore = useChatStore();
const feedbackSubmitting = ref<Record<string, boolean>>({});

function getMessageFeedbackKey(message: Api.Chat.Message) {
  return message.generationId || `${message.conversationId || 'unknown'}:${message.timestamp || ''}`;
}

async function handleFeedback(message: Api.Chat.Message, rating: 'good' | 'bad') {
  if (message.role !== 'assistant') {
    return;
  }

  const key = getMessageFeedbackKey(message);
  if (feedbackSubmitting.value[key]) {
    return;
  }

  feedbackSubmitting.value = {
    ...feedbackSubmitting.value,
    [key]: true
  };

  const { error } = await request({
    url: 'chat/feedback',
    method: 'POST',
    data: {
      rating,
      reason: rating === 'good' ? '用户点击点赞，表示认可本次回答' : '用户点击点踩，表示不满意本次回答',
      conversationId: message.conversationId || props.sessionId,
      generationId: message.generationId
    }
  });

  feedbackSubmitting.value = {
    ...feedbackSubmitting.value,
    [key]: false
  };

  if (error) {
    window.$message?.error('反馈记录失败');
    return;
  }

  message.feedbackRating = rating;
  window.$message?.success(rating === 'good' ? '已记录点赞反馈' : '已记录点踩反馈');
}

// 存储文件名和对应的事件处理
const sourceFiles = ref<Array<{fileName: string, id: string, referenceNumber: number, fileMd5?: string, pageNumber?: number}>>([]);
const bareUrlPattern = /https?:\/\/[A-Za-z0-9\-._~:/?#\[\]@!$&'()*+,;=%]+/g;
const toolNameLabels: Record<string, string> = {
  search_knowledge: '查询客服知识库',
  list_documents: '读取文档列表',
  get_document: '读取文档内容',
  read_skill_reference: '读取 Skill Reference',
  run_skill_script: '执行 Skill Script',
  generate_summary: '生成知识摘要',
  submit_feedback: '记录反馈',
  knowledge_stats: '读取知识库统计',
  create_support_handoff: '创建人工客服工单',
  get_support_handoff: '查询人工客服工单'
};
const toolStatusLabels: Record<Api.Chat.AgentToolEvent['status'], string> = {
  executing: '执行中',
  success: '已完成',
  failed: '失败'
};

const toolEvents = computed(() => props.msg.toolEvents || []);
const activeSkills = computed(() => props.msg.activeSkills || []);
const skillTrace = computed(() => props.msg.skillTrace);
const skillNameLabels: Record<string, string> = {
  'customer-support': '客服应答',
  'troubleshooting': '故障排查',
  'escalation': '人工升级'
};
const intentLabels: Record<string, string> = {
  refund_request: '退款申请',
  refund_policy: '退款政策咨询',
  payment_dispute: '支付争议',
  api_diagnostic: 'API 故障',
  authentication_error: '认证错误',
  network_error: '网络错误',
  upload_error: '上传错误',
  billing: '账单咨询',
  order: '订单咨询',
  product_usage: '产品使用',
  general: '一般咨询',
  keyword_fallback: '关键词兜底'
};
const specialistLabels: Record<string, string> = {
  api_diagnostic: 'API诊断 Agent',
  billing: '账单 Agent',
  doc_rag: '知识库 Agent'
};

function getSkillLabel(skill: string) {
  return skillNameLabels[skill] || skill;
}

function getIntentLabel(intent: string) {
  return intentLabels[intent] || intent;
}

function getSpecialistLabel(agent: string) {
  return specialistLabels[agent] || agent;
}

function getToolLabel(tool: string) {
  return toolNameLabels[tool] || tool;
}

function getToolStatusLabel(status: Api.Chat.AgentToolEvent['status']) {
  return toolStatusLabels[status] || status;
}

function splitTrailingUrlPunctuation(rawUrl: string) {
  let url = rawUrl;
  let trailing = '';

  while (url) {
    const lastChar = url.at(-1);
    if (!lastChar) break;

    if (/[，。！？；：、,.!?;:]/.test(lastChar)) {
      trailing = `${lastChar}${trailing}`;
      url = url.slice(0, -1);
      continue;
    }

    if (lastChar === ')' || lastChar === '）') {
      const openingChar = lastChar === ')' ? '(' : '（';
      const closingChar = lastChar;
      const openingCount = (url.match(new RegExp(`\\${openingChar}`, 'g')) || []).length;
      const closingCount = (url.match(new RegExp(`\\${closingChar}`, 'g')) || []).length;

      if (closingCount > openingCount) {
        trailing = `${lastChar}${trailing}`;
        url = url.slice(0, -1);
        continue;
      }
    }

    break;
  }

  return { url, trailing };
}

function normalizeBareUrls(text: string) {
  return text.replace(bareUrlPattern, (match, offset: number, source: string) => {
    const previousChar = source[offset - 1] || '';
    const previousTwoChars = source.slice(Math.max(0, offset - 2), offset);
    const previousTenChars = source.slice(Math.max(0, offset - 10), offset).toLowerCase();

    if (previousChar === '<' || previousTwoChars === '](' || /(?:href|src)=["']?$/.test(previousTenChars)) {
      return match;
    }

    const { url, trailing } = splitTrailingUrlPunctuation(match);
    return url ? `<${url}>${trailing}` : match;
  });
}

function createSourceLink(
  sourceNum: string,
  fileName: string,
  extras?: { fileMd5?: string; pageNumber?: number; displayName?: string }
): string {
  const linkClass = 'source-file-link';
  const trimmedFileName = fileName.trim();
  const fileId = `source-file-${sourceFiles.value.length}`;
  const referenceNumber = parseInt(sourceNum, 10);

  sourceFiles.value.push({
    fileName: trimmedFileName,
    id: fileId,
    referenceNumber,
    fileMd5: extras?.fileMd5,
    pageNumber: extras?.pageNumber
  });

  return `来源#${sourceNum}: <span class="${linkClass}" data-file-id="${fileId}">${extras?.displayName || trimmedFileName}</span>`;
}

// 处理来源文件链接的函数
function processSourceLinks(text: string): string {
  // 重置来源文件列表，避免重复
  sourceFiles.value = [];

  // 支持单个来源，也支持一个括号里包含多个来源：
  // (来源#1: test.pdf | 第5页; 来源#2: other.pdf | 第8页)
  const entryBoundary = '(?=\\s*(?:[;；,，、。！？!?\\)）]|$))';
  const pagePattern = new RegExp(
    `来源#(\\d+):\\s*([^|;；,，、。！？!?\\n\\r]+?)\\s*\\|\\s*第(\\d+)页${entryBoundary}`,
    'g'
  );
  const md5Pattern = new RegExp(
    `来源#(\\d+):\\s*([^|;；,，、。！？!?\\n\\r]+?)\\s*\\|\\s*MD5:\\s*([a-fA-F0-9]+)${entryBoundary}`,
    'g'
  );
  const simplePattern = new RegExp(
    `来源#(\\d+):\\s*([^<>\\n\\r|;；,，、。！？!?]+?)${entryBoundary}`,
    'g'
  );

  let processedText = text.replace(pagePattern, (_match, sourceNum, fileName, pageNum) => {
    return createSourceLink(sourceNum, fileName, {
      pageNumber: parseInt(pageNum, 10),
      displayName: `${fileName.trim()} (第${pageNum}页)`
    });
  });

  processedText = processedText.replace(md5Pattern, (_match, sourceNum, fileName, fileMd5) => {
    return createSourceLink(sourceNum, fileName, {
      fileMd5: fileMd5.trim()
    });
  });

  processedText = processedText.replace(simplePattern, (_match, sourceNum, fileName) => {
    return createSourceLink(sourceNum, fileName);
  });

  return processedText;
}

const content = computed(() => {
  chatStore.scrollToBottom?.();
  const rawContent = props.msg.content ?? '';

  // 只对助手消息处理来源链接
  if (props.msg.role === 'assistant') {
    return normalizeBareUrls(processSourceLinks(rawContent));
  }

  return rawContent;
});

function extractContextAnchorText(target: HTMLElement) {
  const scope = target.closest('li, p, blockquote, td, th');
  const rawText = scope?.textContent?.replace(/\s+/g, ' ').trim() || '';
  if (!rawText) return '';

  const beforeCitation = rawText.split(/(?:\(|（)?来源#\d+:/)[0] || rawText;
  return beforeCitation
    .replace(/^\s*\d+\.\s*/, '')
    .replace(/[（(]\s*$/, '')
    .replace(/\s+/g, ' ')
    .trim();
}

function openReferencePreviewPage(payload: {
  citationId?: string | null;
  indexVersion?: string | null;
  retrievalMode?: Api.Chat.ReferenceEvidence['retrievalMode'];
  retrievalLabel?: string | null;
  retrievalQuery?: string | null;
  evidenceSnippet?: string | null;
  matchedChunkText?: string | null;
  score?: number | null;
  chunkId?: number | null;
  fileName: string;
  fileMd5?: string | null;
  pageNumber?: number | null;
  anchorText?: string | null;
  sessionId?: string;
  referenceNumber: number;
}) {
  const previewKey = `reference-preview:${Date.now()}:${Math.random().toString(36).slice(2, 8)}`;
  localStorage.setItem(previewKey, JSON.stringify(payload));

  const routeLocation = router.resolve({
    path: '/chat',
    query: {
      preview: 'reference',
      previewKey
    }
  });

  window.open(routeLocation.href, '_blank', 'noopener,noreferrer');
}

// 处理内容点击事件（事件委托）
function handleContentClick(event: MouseEvent) {
  const target = event.target as HTMLElement;

  // 检查点击的是否是文件链接
  if (target.classList.contains('source-file-link')) {
    const fileId = target.getAttribute('data-file-id');
    if (fileId) {
      const file = sourceFiles.value.find(f => f.id === fileId);
      if (file) {
        const contextAnchorText = extractContextAnchorText(target);
        handleSourceFileClick({
          fileName: file.fileName,
          referenceNumber: file.referenceNumber,
          fileMd5: file.fileMd5,
          anchorText: contextAnchorText
        });
      }
    }
  }
}

// 处理来源文件点击事件
async function handleSourceFileClick(fileInfo: {
  fileName: string;
  referenceNumber: number;
  fileMd5?: string;
  anchorText?: string;
}) {
  const { fileName, referenceNumber, fileMd5: extractedMd5, anchorText: clickedAnchorText } = fileInfo;
  const persistedDetail = props.msg.referenceMappings?.[String(referenceNumber)] || props.msg.referenceMappings?.[referenceNumber];
  const referenceSessionId = props.msg.generationId || props.msg.conversationId || props.sessionId;
  console.log('点击了来源文件:', fileName, '引用编号:', referenceNumber, '提取的MD5:', extractedMd5, '会话ID:', referenceSessionId);

  try {
    let detail: Api.Document.ReferenceDetailResponse | null = null;
    const fallbackRetrievalQuery = props.retrievalQueryFallback || '';

    if (referenceSessionId && (!persistedDetail?.retrievalQuery || !persistedDetail?.matchedChunkText || !persistedDetail?.evidenceSnippet)) {
      try {
        const { error: detailError, data: detailData } = await request<Api.Document.ReferenceDetailResponse>({
          url: 'documents/reference-detail',
          params: {
            sessionId: referenceSessionId,
            referenceNumber: referenceNumber.toString()
          }
        });

        if (!detailError && detailData?.fileMd5) {
          detail = detailData;
        }
      } catch (detailErr) {
        console.warn('通过API查询引用详情失败:', detailErr);
      }
    }

    if (persistedDetail?.fileMd5 && !detail) {
      openReferencePreviewPage({
        citationId: persistedDetail.citationId,
        indexVersion: persistedDetail.indexVersion,
        fileName: persistedDetail.fileName || fileName,
        fileMd5: persistedDetail.fileMd5,
        pageNumber: persistedDetail.pageNumber,
        anchorText: clickedAnchorText || persistedDetail.anchorText || '',
        retrievalMode: persistedDetail.retrievalMode,
        retrievalLabel: persistedDetail.retrievalLabel,
        retrievalQuery: persistedDetail.retrievalQuery || fallbackRetrievalQuery,
        evidenceSnippet: persistedDetail.evidenceSnippet,
        matchedChunkText: persistedDetail.matchedChunkText,
        score: persistedDetail.score,
        chunkId: persistedDetail.chunkId,
        sessionId: referenceSessionId,
        referenceNumber
      });
      return;
    }

    const targetMd5 = detail?.fileMd5 || extractedMd5 || null;
    openReferencePreviewPage({
      citationId: detail?.citationId,
      indexVersion: detail?.indexVersion,
      fileName: detail?.fileName || fileName,
      fileMd5: targetMd5,
      pageNumber: detail?.pageNumber,
      anchorText: clickedAnchorText || detail?.anchorText || '',
      retrievalMode: detail?.retrievalMode,
      retrievalLabel: detail?.retrievalLabel,
      retrievalQuery: detail?.retrievalQuery || fallbackRetrievalQuery,
      evidenceSnippet: detail?.evidenceSnippet,
      matchedChunkText: detail?.matchedChunkText,
      score: detail?.score,
      chunkId: detail?.chunkId,
      sessionId: referenceSessionId,
      referenceNumber
    });
  } catch (err) {
    console.error('文件下载失败:', err);
    window.$message?.error(`文件下载失败: ${fileName}`);
  }
}
</script>

<template>
  <div class="mb-8 flex-col gap-2">
    <div v-if="msg.role === 'user'" class="flex items-center gap-4">
      <NAvatar class="bg-success">
        <SvgIcon icon="ph:user-circle" class="text-icon-large color-white" />
      </NAvatar>
      <div class="flex-col gap-1">
        <NText class="text-4 font-bold">{{ msg.username || authStore.userInfo.username }}</NText>
        <NText class="text-3 color-gray-500">{{ formatDate(msg.timestamp) }}</NText>
      </div>
    </div>
    <div v-else class="flex items-center gap-4">
      <NAvatar class="bg-primary">
        <span class="text-10px text-white font-bold">API</span>
      </NAvatar>
      <div class="flex-col gap-1">
        <NText class="text-4 font-bold">{{ $t('system.title') }}</NText>
        <NText class="text-3 color-gray-500">{{ formatDate(msg.timestamp) }}</NText>
      </div>
    </div>
    <div v-if="msg.role === 'assistant' && running" class="ml-12 mt-3 flex items-center gap-2 text-12px color-gray-500" aria-live="polite">
      <icon-eos-icons:three-dots-loading class="text-4" />
      <span>{{ progressText }}</span><span v-if="stageSeconds > 0">· {{ stageSeconds }} 秒</span>
    </div>
    <DiagnosisPanel v-if="msg.role === 'assistant' && (msg.diagnosisId || msg.diagnosis)" class="mt-3 sm:ml-12"
      :diagnosis-id="msg.diagnosisId || msg.diagnosis?.diagnosisId" :snapshot="msg.diagnosis" />
    <div v-if="msg.role === 'assistant' && activeSkills.length > 0" class="ml-12 mt-3 flex flex-wrap gap-2">
      <span v-for="skill in activeSkills" :key="skill" class="skill-chip">
        Skill · {{ getSkillLabel(skill) }}
      </span>
    </div>
    <div v-if="msg.role === 'assistant' && msg.intent" class="ml-12 mt-2 flex flex-wrap gap-2">
      <span class="skill-trace-chip">
        意图 · {{ getIntentLabel(msg.intent) }}
        <template v-if="msg.intentConfidence !== undefined"> · {{ Math.round(msg.intentConfidence * 100) }}%</template>
      </span>
      <span v-if="msg.needsHuman" class="skill-trace-chip">需人工核验</span>
      <span v-for="(value, key) in (msg.entities || {})" :key="`entity-${key}`" class="skill-trace-chip">
        {{ key }} · {{ value }}<template v-if="msg.entitySources?.[key] === 'history'">（历史）</template>
      </span>
      <span v-for="agent in (msg.specialistAgents || [])" :key="`agent-${agent}`" class="skill-trace-chip">
        {{ getSpecialistLabel(agent) }}
      </span>
    </div>
    <div v-if="msg.role === 'assistant' && skillTrace" class="ml-12 mt-2 flex flex-wrap gap-2">
      <span class="skill-trace-chip">
        Trace · {{ skillTrace.stepsUsed || 0 }} steps · {{ skillTrace.totalToolCalls || 0 }} tools
        <template v-if="(skillTrace.maxParallelWidth || 0) > 1"> · parallel {{ skillTrace.maxParallelWidth }}</template>
      </span>
      <span v-if="(skillTrace.scriptsUsed || []).length > 0" class="skill-trace-chip">
        scripts · {{ (skillTrace.scriptsUsed || []).join(', ') }}
      </span>
      <span v-if="(skillTrace.qualityGatesRecommended || []).length > 0" class="skill-trace-chip">
        gate · {{ Math.round((skillTrace.qualityGateCoverage || 0) * 100) }}%
      </span>
      <span v-if="(skillTrace.qualityGatesFailed || []).length > 0" class="skill-trace-chip skill-trace-chip-danger">
        gate warning · {{ (skillTrace.qualityGatesFailed || []).length }}
      </span>
      <span v-if="skillTrace.workflowEngine" class="skill-trace-chip">
        LangGraph · {{ (skillTrace.graphPath || []).join(' → ') }}
      </span>
      <span v-if="(skillTrace.dependencyBatches || []).length" class="skill-trace-chip">
        依赖调度 · {{ (skillTrace.dependencyBatches || []).length }} 批
      </span>
      <span v-if="(skillTrace.specialistDecisions || []).length" class="skill-trace-chip">
        专业决策 · {{ (skillTrace.specialistDecisions || []).length }} 次
      </span>
    </div>
    <div v-if="msg.role === 'assistant' && toolEvents.length > 0" class="ml-12 mt-3 flex flex-col gap-2">
      <div
        v-for="event in toolEvents"
        :key="event.id || event.tool"
        class="tool-event"
        :class="`tool-event--${event.status}`"
      >
        <icon-eos-icons:three-dots-loading v-if="event.status === 'executing'" class="text-4" />
        <icon-material-symbols:check-circle-rounded v-else-if="event.status === 'success'" class="text-4" />
        <icon-material-symbols:error-rounded v-else class="text-4" />
        <span class="tool-event__name">{{ getToolLabel(event.tool) }}</span>
        <span v-if="event.agent" class="tool-event__status">{{ event.agent }}</span>
        <span class="tool-event__status">{{ getToolStatusLabel(event.status) }}</span>
        <span v-if="event.durationMs !== undefined" class="tool-event__status">{{ event.durationMs }} ms</span>
        <span v-if="event.error" class="tool-event__status" :title="event.error">{{ event.resultStatus || 'ERROR' }}</span>
      </div>
    </div>
    <NText v-if="msg.status === 'error'" class="ml-12 mt-2 italic color-#d03050">
      {{ msg.errorMessage || msg.content || '服务器繁忙，请稍后再试' }}
    </NText>
    <div v-if="msg.role === 'assistant' && msg.content && (msg.status !== 'error' || msg.errorMessage)" class="mt-2 pl-12" @click="handleContentClick">
      <VueMarkdownIt :content="content" />
    </div>
    <NText v-else-if="msg.role === 'user'" class="ml-12 mt-2 text-4">{{ content }}</NText>
    <NDivider class="ml-12 w-[calc(100%-3rem)] mb-0! mt-2!" />
    <div class="ml-12 flex gap-2">
      <NButton quaternary title="复制回答" aria-label="复制回答" @click="handleCopy(msg.content)">
        <template #icon>
          <icon-mynaui:copy />
        </template>
      </NButton>
      <NButton
        v-if="msg.role === 'assistant'"
        quaternary
        title="点赞"
        aria-label="点赞"
        :type="msg.feedbackRating === 'good' ? 'primary' : 'default'"
        :loading="feedbackSubmitting[getMessageFeedbackKey(msg)]"
        @click="handleFeedback(msg, 'good')"
      >
        <template #icon>
          <icon-material-symbols:thumb-up-outline-rounded />
        </template>
      </NButton>
      <NButton
        v-if="msg.role === 'assistant'"
        quaternary
        title="点踩"
        aria-label="点踩"
        :type="msg.feedbackRating === 'bad' ? 'error' : 'default'"
        :loading="feedbackSubmitting[getMessageFeedbackKey(msg)]"
        @click="handleFeedback(msg, 'bad')"
      >
        <template #icon>
          <icon-material-symbols:thumb-down-outline-rounded />
        </template>
      </NButton>
    </div>
  </div>
</template>

<style scoped lang="scss">
:deep(.source-file-link) {
  color: #1890ff;
  cursor: pointer;
  text-decoration: underline;
  transition: color 0.2s;

  &:hover {
    color: #40a9ff;
    text-decoration: none;
  }

  &:active {
    color: #096dd9;
  }
}

.skill-chip {
  display: inline-flex;
  width: fit-content;
  align-items: center;
  border: 1px solid rgb(32 128 240 / 0.22);
  border-radius: 999px;
  background: rgb(32 128 240 / 0.06);
  padding: 3px 9px;
  font-size: 12px;
  line-height: 18px;
  color: #2080f0;
}

.skill-trace-chip {
  display: inline-flex;
  width: fit-content;
  align-items: center;
  border-radius: 999px;
  background: rgb(var(--card-color));
  padding: 2px 8px;
  font-size: 11px;
  line-height: 18px;
  color: rgb(var(--text-color-3));
}

.tool-event {
  display: inline-flex;
  width: fit-content;
  max-width: 100%;
  align-items: center;
  gap: 8px;
  border: 1px solid rgb(var(--border-color) / 0.18);
  border-radius: 6px;
  background: rgb(var(--card-color));
  padding: 5px 9px;
  font-size: 12px;
  line-height: 18px;
  color: rgb(var(--text-color-2));
}

.tool-event__name {
  font-weight: 500;
  color: rgb(var(--text-color));
}

.tool-event__status {
  color: rgb(var(--text-color-3));
}

.tool-event--success {
  border-color: rgb(24 160 88 / 0.25);
  color: #18a058;
}

.tool-event--failed {
  border-color: rgb(208 48 80 / 0.25);
  color: #d03050;
}
</style>
