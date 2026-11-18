<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import { approvalApi, approvalLabel } from '@/service/api/support-approval';
import type { ApprovalItem, ApprovalOptions } from '@/service/api/support-approval';
import { useChatStore } from '@/store/modules/chat';

const chat = useChatStore();
const enabled = ref(false);
const visible = ref(false);
const loading = ref(false);
const items = ref<ApprovalItem[]>([]);
const options = ref<ApprovalOptions>({ invoices: [], tickets: [] });
const action = ref<'refund' | 'close'>('refund');
const target = ref<string | null>(null);
const reason = ref('');
let draftKey = '';
let draftPayload = '';
let revision = 0;

const targets = computed(() =>
  action.value === 'refund'
    ? options.value.invoices.map(item => ({ label: `${item.month} · ${item.id} · ${item.amount.toFixed(2)}`, value: item.id }))
    : options.value.tickets.map(item => ({ label: `${item.id} · ${item.summary}`, value: item.id }))
);

async function refresh() {
  if (!enabled.value || !chat.conversationId) return;
  const conversationId = chat.conversationId;
  const requestRevision = ++revision;
  const { data } = await approvalApi.list(conversationId);
  if (!data || requestRevision !== revision) return;
  if (requestRevision === revision && chat.conversationId === conversationId) {
    items.value = data;
  }
}

async function open() {
  if (!chat.conversationId) await chat.createNewSession();
  const conversationId = chat.conversationId;
  if (!conversationId) return;
  const { data } = await approvalApi.options(conversationId);
  if (data && conversationId === chat.conversationId) {
    options.value = data;
    visible.value = true;
  }
}

async function submit() {
  if (!target.value || !reason.value.trim() || !chat.conversationId) return;
  const conversationId = chat.conversationId;
  const fields = {
    conversationId,
    reason: reason.value.trim(),
    ...(action.value === 'refund' ? { invoiceId: target.value } : { handoffId: target.value })
  };
  const fingerprint = JSON.stringify(fields);
  if (fingerprint !== draftPayload) {
    draftPayload = fingerprint;
    draftKey = Array.from(crypto.getRandomValues(new Uint8Array(16)), value => value.toString(16).padStart(2, '0')).join('');
  }
  loading.value = true;
  try {
    const { data } = await approvalApi.submit({ ...fields, requestKey: draftKey });
    if (data && conversationId === chat.conversationId) {
      visible.value = false;
      reason.value = '';
      target.value = null;
      draftPayload = '';
      await refresh();
    }
  } finally {
    loading.value = false;
  }
}

watch(action, () => { target.value = null; });
watch(() => chat.conversationId, () => {
  revision += 1;
  items.value = [];
  visible.value = false;
  target.value = null;
  reason.value = '';
  void refresh();
});
onMounted(async () => {
  window.addEventListener('focus', refresh);
  const { data } = await approvalApi.capabilities();
  enabled.value = Boolean(data?.enabled);
  await refresh();
});
onBeforeUnmount(() => {
  revision += 1;
  window.removeEventListener('focus', refresh);
});
</script>

<template>
  <section v-if="enabled" class="mx-4 mb-2 flex flex-col gap-2" aria-label="会话业务申请">
    <div class="flex gap-2">
      <NButton size="small" @click="open">发起业务申请</NButton>
      <NButton v-if="items.length" text size="small" @click="refresh">刷新申请状态</NButton>
    </div>
    <div v-if="items.length" class="max-h-36 overflow-y-auto">
      <div v-for="item in items" :key="item.requestId" class="my-1 rounded-lg border border-stone-200 px-3 py-2 text-sm">
        <span class="font-medium">{{ item.handoffId ? '关闭工单' : '申请退款' }} · {{ approvalLabel(item.status) }}</span>
        <div v-if="item.receipt" class="break-all">
          退款编号 {{ item.receipt.refundId }} · {{ (item.receipt.amountMinor / 100).toFixed(2) }} {{ item.receipt.currency }}
        </div>
        <div v-else-if="item.handoffId">工单 {{ item.handoffId }}</div>
      </div>
    </div>
    <NModal v-model:show="visible" preset="card" title="发起业务申请" class="w-[min(92vw,480px)]">
      <NForm label-placement="top">
        <NFormItem label="业务动作">
          <NRadioGroup v-model:value="action">
            <NRadio value="refund">申请退款</NRadio>
            <NRadio value="close">关闭工单</NRadio>
          </NRadioGroup>
        </NFormItem>
        <NFormItem :label="action === 'refund' ? '已支付账单' : '本会话工单'">
          <NSelect v-model:value="target" :options="targets" placeholder="请选择" />
        </NFormItem>
        <NFormItem label="申请原因">
          <NInput v-model:value="reason" type="textarea" :maxlength="500" :disabled="loading" />
        </NFormItem>
        <NButton type="primary" :disabled="!target || !reason.trim()" :loading="loading" @click="submit">
          提交人工审批
        </NButton>
      </NForm>
    </NModal>
  </section>
</template>
