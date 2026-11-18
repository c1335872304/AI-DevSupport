<script setup lang="ts">
import { computed, onUnmounted, ref, watch } from 'vue';
import { request } from '@/service/request';

const props = defineProps<{ diagnosisId?: string; snapshot?: Api.Chat.Diagnosis }>();
const diagnosis = ref<Api.Chat.Diagnosis>();
const unavailable = ref(false);
const clock = ref(Date.now());
const recheckRequest = ref('');
const recheckKey = ref('');
const submitting = ref(false);
const pollUntil = ref(0);
const latestExecution = computed(() => diagnosis.value?.executions?.[0]);
const running = computed(() =>
  ['PENDING', 'RUNNING', 'READY', 'HANDOFF_PENDING'].includes(latestExecution.value?.status || '')
);
const canRecheck = computed(
  () => ['WAITING_USER_ACTION', 'WAITING_RECHECK'].includes(diagnosis.value?.status || '') && !running.value
);
const causeLabels = { SUPPORTED: '观测支持', EXCLUDED: '已排除', UNDETERMINED: '尚无法判断' };
const stateLabels: Record<string, string> = {
  COLLECTING: '待补信息',
  VERIFYING: '核查中',
  WAITING_USER_ACTION: '待用户操作',
  WAITING_RECHECK: '待复查',
  RESOLVED: '已解决',
  CLOSED_UNRESOLVED: '未解决结束',
  HANDED_OFF: '已转人工'
};
const sourceLabels = {
  USER_REPORT: '用户描述 · 尚未核验',
  BUSINESS_QUERY: '业务工具查询',
  DOCUMENT_RULE: '文档规则 · 通用说明'
};
const fieldLabels: Record<string, string> = {
  valid_request_id: '可查询的请求号',
  request_id_or_incident_time: '请求号或故障时间',
  confirm_app_id: '核对应用归属',
  confirm_http_status: '核对请求状态码',
  confirm_error_code: '核对错误码',
  confirm_endpoint: '核对接口路径',
  business_evidence_unavailable: '补齐未成功的业务核查',
  RECHECK_NOT_FOUND: '提供可查询的新请求号',
  RECHECK_SCOPE_MISMATCH: '核对新请求的应用和接口',
  RECHECK_TIME_MISMATCH: '提供修正后五分钟内的新请求',
  RECHECK_TIME_UNKNOWN: '核对新请求时间',
  RECHECK_CONFLICT: '核对复查描述与日志冲突'
};
const records = computed(() => (diagnosis.value?.evidence || []).slice(-8));
function validity(e: Api.Chat.DiagnosisEvidence) {
  if (e.freshness === 'CURRENT' && (!e.validUntil || Date.parse(e.validUntil) < clock.value))
    return '已过期，需重新查询';
  return (
    (
      {
        CURRENT: '查询时有效',
        HISTORICAL_ONLY: '仅说明历史事件或窗口',
        REPORTED_ONLY: '尚未核验',
        UNVERIFIED: '没有可核验结果',
        REQUIRES_DOCUMENT_REVALIDATION: '通用规则，使用时需核对版本',
        AUTHORIZED_ACTIVE_DOCUMENT: '当前有权访问的文档版本',
        DOCUMENT_UNAVAILABLE: '来源已失效或无权访问',
        EXPIRED: '已过期，需重新查询'
      } as Record<string, string>
    )[e.freshness] || '需要进一步核查'
  );
}
function summary(e: Api.Chat.DiagnosisEvidence) {
  if (e.sourceType === 'USER_REPORT') return e.summary;
  if (e.sourceType === 'BUSINESS_QUERY' && !e.verified) return '本次查询未完成核验，不能据此确认业务状态';
  const fact = e.facts?.[0];
  if (e.tool === 'query_call_log')
    return fact?.found ? `请求 ${e.requestId || ''}，历史 HTTP ${fact.httpStatus}` : '未找到该请求记录';
  if (e.tool === 'query_recent_call_stats')
    return `窗口内 ${fact?.total ?? 0} 次调用；429 ${fact?.rateLimitedCount ?? 0} 次`;
  if (e.tool === 'query_api_key_status') return '已查询脱敏 Key 状态；不能据此断言历史请求的具体根因';
  if (e.tool === 'query_request_observation') return '请求时的脱敏观测，用于核对该服务版本的候选原因';
  if (e.sourceType === 'DOCUMENT_RULE') return '规则依据不等同于本次故障已经确认';
  return '业务核查记录';
}
async function refresh() {
  const id = props.diagnosisId || props.snapshot?.diagnosisId;
  if (!id) return;
  const { data, error } = await request<Api.Chat.Diagnosis>({ url: `diagnoses/${id}` });
  if (id !== (props.diagnosisId || props.snapshot?.diagnosisId)) return;
  unavailable.value = Boolean(error);
  if (error) diagnosis.value = undefined;
  else if (
    data &&
    (!diagnosis.value || data.diagnosisId !== diagnosis.value.diagnosisId || data.revision >= diagnosis.value.revision)
  )
    diagnosis.value = data;
}
watch(recheckRequest, () => {
  recheckKey.value = '';
});
async function submitRecheck() {
  if (!diagnosis.value || !recheckRequest.value.trim() || submitting.value) return;
  recheckKey.value ||= crypto.randomUUID();
  submitting.value = true;
  try {
    const { error } = await request({
      url: `diagnoses/${diagnosis.value.diagnosisId}/rechecks`,
      method: 'POST',
      data: {
        requestId: recheckRequest.value.trim(),
        expectedRevision: diagnosis.value.revision,
        idempotencyKey: recheckKey.value
      }
    });
    if (!error) {
      window.$message?.success('已提交复查，结果以核查状态为准');
      pollUntil.value = Date.now() + 60000;
    }
    await refresh();
  } finally {
    submitting.value = false;
  }
}
async function resume() {
  if (!diagnosis.value || !latestExecution.value) return;
  const { error } = await request({
    url: `diagnoses/${diagnosis.value.diagnosisId}/resume`,
    method: 'POST',
    data: { generationId: latestExecution.value.generationId }
  });
  if (!error) pollUntil.value = Date.now() + 60000;
  await refresh();
}
function recheckStatusLabel(status: string) {
  const labels: Record<string, string> = {
    SUCCEEDED: '新请求已成功',
    STILL_FAILING: '仍失败',
    REJECTED: '关联校验未通过'
  };
  return labels[status] || '待核查';
}
watch(
  () => props.snapshot,
  value => {
    if (
      value &&
      (!diagnosis.value ||
        value.diagnosisId !== diagnosis.value.diagnosisId ||
        value.revision >= diagnosis.value.revision)
    )
      diagnosis.value = value;
  },
  { immediate: true }
);
watch(
  () => props.diagnosisId || props.snapshot?.diagnosisId,
  () => {
    refresh().catch(console.error);
  },
  { immediate: true }
);
const timer = setInterval(() => {
  clock.value = Date.now();
  if (pollUntil.value > Date.now()) refresh().catch(console.error);
}, 3000);
onUnmounted(() => clearInterval(timer));
</script>

<template>
  <section
    class="diagnosis-panel min-w-0 border border-gray-200 rounded-lg border-solid p-3 text-sm"
    aria-label="诊断进度"
  >
    <div class="flex items-center justify-between gap-3">
      <strong>诊断进度 · {{ stateLabels[diagnosis?.status || ''] || '读取中' }}</strong>
      <NButton size="tiny" @click="refresh">刷新状态</NButton>
    </div>
    <p v-if="unavailable">诊断记录暂时不可读取，请刷新重试。</p>
    <template v-if="diagnosis">
      <p v-if="diagnosis.appId">应用：{{ diagnosis.appId }}</p>
      <p v-if="diagnosis.missingFields.length">
        待补信息：{{ diagnosis.missingFields.map(f => fieldLabels[f] || f).join('、') }}
      </p>
      <p>下一步：{{ diagnosis.nextAction }}</p>
      <p v-if="diagnosis.workflow?.decision?.ruleVersion">
        规则范围：独立 Demo API · {{ diagnosis.workflow.decision.ruleVersion }}
      </p>
      <ul v-if="diagnosis.candidates?.length" class="my-2 pl-4 space-y-1" aria-label="候选原因">
        <li v-for="candidate in diagnosis.candidates" :key="candidate.cause">
          {{ candidate.title }} · {{ causeLabels[candidate.status] }}
        </li>
      </ul>
      <p v-for="action in diagnosis.workflow?.actions || []" :key="action.cause">建议：{{ action.instruction }}</p>
      <div v-for="result in (diagnosis.workflow?.rechecks || []).slice(-3)" :key="result.requestId">
        复查 {{ result.requestId }}：{{ recheckStatusLabel(result.status) }}
        <template v-if="result.httpStatus">· HTTP {{ result.httpStatus }}</template>
      </div>
      <div v-if="canRecheck" class="my-2 flex flex-col gap-2">
        <NInput
          v-model:value="recheckRequest"
          placeholder="修正后的新请求号，不要输入密钥"
          :maxlength="64"
          aria-label="复查请求号"
        />
        <NButton size="small" :loading="submitting" :disabled="!recheckRequest.trim()" @click="submitRecheck">
          提交复查
        </NButton>
      </div>
      <div v-if="running" class="my-2">
        <span>核查任务执行或恢复中</span>
        <NButton size="tiny" @click="resume">继续核查</NButton>
      </div>
      <details class="mt-2">
        <summary>证据与时间范围（最近 {{ records.length }} 条）</summary>
        <ul class="mt-2 pl-4 space-y-2">
          <li v-for="item in records" :key="item.evidenceId">
            <strong>{{ sourceLabels[item.sourceType] }}</strong>
            · {{ validity(item) }}
            <p>{{ summary(item) }}</p>
            <p v-if="item.eventAt">事件时间：{{ item.eventAt }}</p>
            <p v-if="item.windowStart">统计范围：{{ item.windowStart }} ～ {{ item.windowEnd }}</p>
            <p v-if="item.queriedAt">记录时间：{{ item.queriedAt }}</p>
          </li>
        </ul>
      </details>
      <p class="mt-2 opacity-60">
        更新：{{ diagnosis.updatedAt }} ·
        {{ diagnosis.status === 'RESOLVED' ? '恢复结论仅覆盖已核验的新请求' : '历史事件不代表当前已恢复' }}
      </p>
    </template>
  </section>
</template>

<style scoped>
.diagnosis-panel {
  overflow-wrap: anywhere;
}
</style>
