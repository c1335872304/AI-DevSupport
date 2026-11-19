<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { approvalApi, approvalLabel } from '@/service/api/support-approval';
import type { ApprovalReview } from '@/service/api/support-approval';

const enabled = ref(false);
const loading = ref(false);
const saving = ref(false);
const selected = ref<ApprovalReview | null>(null);
const rows = ref<ApprovalReview[]>([]);
const note = ref('');
const hasMore = ref(false);

async function refresh(append = false) {
  loading.value = true;
  try {
    const { data } = await approvalApi.queue(append ? rows.value.length : 0);
    if (data) {
      rows.value = append ? [...rows.value, ...data] : data;
      hasMore.value = data.length === 50;
    }
  } finally {
    loading.value = false;
  }
}

async function decide(decision: 'approve' | 'reject') {
  const item = selected.value;
  const comment = note.value.trim();
  if (!item || (!item.decision && !comment)) return;
  saving.value = true;
  try {
    const { data } = item.decision
      ? await approvalApi.resume(item.requestId)
      : await approvalApi.decide(item.requestId, decision, comment);
    if (data) {
      selected.value = null;
      await refresh();
    }
  } finally {
    saving.value = false;
  }
}

function open(item: ApprovalReview) {
  selected.value = item;
  note.value = item.decisionNote || '';
}

onMounted(async () => {
  const { data } = await approvalApi.capabilities();
  enabled.value = Boolean(data?.enabled);
  if (enabled.value) await refresh();
});
</script>

<template>
  <NCard v-if="enabled" title="业务审批" size="small" :bordered="false">
    <template #header-extra>
      <NButton size="small" :loading="loading" @click="refresh()">刷新审批队列</NButton>
    </template>
    <NEmpty v-if="!rows.length && !loading" description="暂无审批申请" />
    <div v-else class="max-h-64 overflow-y-auto">
      <div
        v-for="item in rows"
        :key="item.requestId"
        class="flex items-center justify-between gap-3 border-b border-stone-200 py-2 last:border-0"
      >
        <div class="min-w-0">
          <div>{{ item.handoffId ? '关闭工单' : '申请退款' }} · {{ approvalLabel(item.status) }}</div>
          <div class="break-all text-xs text-stone-500">
            {{ item.handoffId || item.invoiceId }} · 用户 {{ item.userId }}
          </div>
          <div v-if="item.executionStatus === 'NEEDS_REVIEW'" class="text-amber-700">自动重试已暂停，请核查后恢复</div>
          <div v-else-if="['PENDING', 'RUNNING'].includes(item.executionStatus || '')" class="text-stone-500">
            自动恢复处理中 · 已尝试 {{ item.executionAttempts || 0 }} 次
          </div>
          <div v-if="item.receipt" class="break-all text-xs">退款编号 {{ item.receipt.refundId }}</div>
        </div>
        <NButton size="small" @click="open(item)">{{ item.decision ? '查看' : '审阅' }}</NButton>
      </div>
    </div>
    <NButton v-if="hasMore" :loading="loading" @click="refresh(true)">加载更多申请</NButton>
    <NModal
      :show="!!selected"
      preset="card"
      title="审阅业务申请"
      class="w-[min(92vw,510px)]"
      @update:show="
        value => {
          if (!value && !saving) selected = null;
        }
      "
    >
      <div v-if="selected" class="flex flex-col gap-3">
        <NDescriptions :column="1" bordered size="small">
          <NDescriptionsItem label="操作">{{ selected.handoffId ? '关闭工单' : '申请退款' }}</NDescriptionsItem>
          <NDescriptionsItem label="申请人">{{ selected.userId }}</NDescriptionsItem>
          <NDescriptionsItem label="目标">{{ selected.handoffId || selected.invoiceId }}</NDescriptionsItem>
          <NDescriptionsItem v-if="selected.amountMinor !== undefined" label="退款金额">
            {{ (selected.amountMinor / 100).toFixed(2) }} {{ selected.currency }}
          </NDescriptionsItem>
          <NDescriptionsItem label="原因">{{ selected.reason }}</NDescriptionsItem>
          <NDescriptionsItem label="当前状态">{{ approvalLabel(selected.status) }}</NDescriptionsItem>
        </NDescriptions>
        <NInput
          v-model:value="note"
          type="textarea"
          placeholder="审批说明"
          :maxlength="500"
          :readonly="!!selected.decision || saving"
        />
        <div v-if="!selected.decision" class="flex justify-end gap-2">
          <NButton :loading="saving" :disabled="!note.trim()" @click="decide('reject')">拒绝</NButton>
          <NButton type="primary" :loading="saving" :disabled="!note.trim()" @click="decide('approve')">
            批准执行
          </NButton>
        </div>
        <NButton
          v-else-if="
            selected.decision === 'approve' && ['REFUND_RECONCILING', 'APPROVED_PREVIEW'].includes(selected.status)
          "
          :loading="saving"
          @click="decide('approve')"
        >
          重试恢复或核对
        </NButton>
      </div>
    </NModal>
  </NCard>
</template>
