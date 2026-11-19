<script setup lang="tsx">
import { computed, onMounted, reactive, ref } from 'vue';
import type { DataTableColumns, PaginationProps } from 'naive-ui';
import { NButton, NEllipsis, NTag } from 'naive-ui';
import { request } from '@/service/request';
import ApprovalQueue from './approval-queue.vue';

const appStore = useAppStore();
const authStore = useAuthStore();

const loading = ref(false);
const saving = ref(false);
const detailLoading = ref(false);
const drawerVisible = ref(false);
const selected = ref<Api.Support.HandoffDetail | null>(null);
const rows = ref<Api.Support.HandoffListItem[]>([]);
type TicketAudit = {
  id: number;
  actorId: string;
  createdAt: string;
  before: { status?: string };
  after: { status?: string; resolutionNote?: string | null };
};
const audit = ref<TicketAudit[]>([]);
async function loadTicketAudit(handoffId: string) {
  const { data, error } = await request<TicketAudit[]>({ url: `/support/admin/handoffs/${handoffId}/audit` });
  audit.value = !error && data ? data : [];
}

const statistics = ref<Api.Support.HandoffStatistics>({ status: {}, priority: {} });

const filters = reactive<Pick<Api.Support.SearchParams, 'status' | 'priority' | 'category' | 'keyword' | 'userId'>>({
  status: null,
  priority: null,
  category: null,
  keyword: null,
  userId: null
});

const pagination = reactive<PaginationProps>({
  page: 1,
  pageSize: 10,
  itemCount: 0,
  showSizePicker: true,
  pageSizes: [10, 20, 30, 50],
  prefix: page => `共 ${page.itemCount || 0} 条`,
  onUpdatePage: async page => {
    pagination.page = page;
    await getData();
  },
  onUpdatePageSize: async pageSize => {
    pagination.pageSize = pageSize;
    pagination.page = 1;
    await getData();
  }
});

const statusOptions = [
  { label: '待处理', value: 'OPEN' },
  { label: '处理中', value: 'IN_PROGRESS' },
  { label: '已解决', value: 'RESOLVED' },
  { label: '已关闭', value: 'CLOSED' }
];

const allowedEditStatuses = computed(() => {
  const current = selected.value?.status || 'OPEN';
  const next: Record<string, string[]> = {
    OPEN: ['IN_PROGRESS'],
    IN_PROGRESS: ['OPEN', 'RESOLVED'],
    RESOLVED: ['IN_PROGRESS', 'CLOSED'],
    CLOSED: []
  };
  return statusOptions.filter(option => option.value === current || next[current].includes(option.value));
});
const priorityOptions = [
  { label: '低', value: 'LOW' },
  { label: '普通', value: 'NORMAL' },
  { label: '高', value: 'HIGH' },
  { label: '紧急', value: 'URGENT' }
];

const summary = computed(() => ({
  open: statistics.value.status.OPEN || 0,
  inProgress: statistics.value.status.IN_PROGRESS || 0,
  highPriority: (statistics.value.priority.HIGH || 0) + (statistics.value.priority.URGENT || 0),
  total: pagination.itemCount || 0
}));

const editForm = reactive({
  status: 'OPEN' as Api.Support.HandoffStatus,
  assignedTo: '',
  resolutionNote: ''
});

function statusLabel(status: Api.Support.HandoffStatus) {
  return statusOptions.find(item => item.value === status)?.label || status;
}

function statusType(status: Api.Support.HandoffStatus) {
  return {
    OPEN: 'warning',
    IN_PROGRESS: 'info',
    RESOLVED: 'success',
    CLOSED: 'default'
  }[status] as 'warning' | 'info' | 'success' | 'default';
}

function priorityLabel(priority: Api.Support.HandoffPriority) {
  return priorityOptions.find(item => item.value === priority)?.label || priority;
}

function priorityType(priority: Api.Support.HandoffPriority) {
  return {
    LOW: 'default',
    NORMAL: 'info',
    HIGH: 'warning',
    URGENT: 'error'
  }[priority] as 'default' | 'info' | 'warning' | 'error';
}

function formatDate(value: string) {
  return dayjs(value).format('YYYY-MM-DD HH:mm:ss');
}

const columns = computed<DataTableColumns<Api.Support.HandoffListItem>>(() => [
  {
    key: 'handoffId',
    title: '工单号',
    width: 210,
    ellipsis: { tooltip: true }
  },
  {
    key: 'requester',
    title: '客户',
    width: 150,
    render: row => (
      <div class="flex flex-col gap-1">
        <span>{row.username || `用户 ${row.userId}`}</span>
        {row.username ? <span class="text-xs text-stone-400">ID: {row.userId}</span> : null}
      </div>
    )
  },
  {
    key: 'category',
    title: '分类',
    width: 110,
    render: row => <NTag size="small">{row.category}</NTag>
  },
  {
    key: 'priority',
    title: '优先级',
    width: 95,
    render: row => (
      <NTag size="small" type={priorityType(row.priority)}>
        {priorityLabel(row.priority)}
      </NTag>
    )
  },
  {
    key: 'status',
    title: '状态',
    width: 100,
    render: row => (
      <NTag size="small" type={statusType(row.status)}>
        {statusLabel(row.status)}
      </NTag>
    )
  },
  {
    key: 'summary',
    title: '工单摘要',
    minWidth: 260,
    ellipsis: { tooltip: true },
    render: row => (
      <div class="ticket-summary-cell">
        <NEllipsis line-clamp={2} tooltip>
          {row.summary}
        </NEllipsis>
      </div>
    )
  },
  {
    key: 'assignedTo',
    title: '处理人',
    width: 130,
    render: row => row.assignedTo || '未指派'
  },
  {
    key: 'createdAt',
    title: '创建时间',
    width: 170,
    render: row => formatDate(row.createdAt)
  },
  {
    key: 'actions',
    title: '操作',
    fixed: 'right',
    width: 90,
    render: row => (
      <NButton size="small" type="primary" ghost onClick={() => openDetail(row.handoffId)}>
        查看
      </NButton>
    )
  }
]);

function buildParams(): Api.Support.SearchParams {
  return {
    page: pagination.page || 1,
    size: pagination.pageSize || 10,
    status: filters.status,
    priority: filters.priority,
    category: filters.category,
    keyword: filters.keyword?.trim() || null,
    userId: filters.userId?.trim() || null
  };
}

async function getData() {
  loading.value = true;
  try {
    const { error, data } = await request<Api.Support.HandoffList>({
      url: '/support/admin/handoffs',
      params: buildParams()
    });
    if (!error && data) {
      rows.value = data.data || data.content || [];
      pagination.itemCount = data.totalElements || 0;
      statistics.value = data.statistics || { status: {}, priority: {} };
    }
  } finally {
    loading.value = false;
  }
}

async function openDetail(handoffId: string) {
  drawerVisible.value = true;
  detailLoading.value = true;
  selected.value = null;
  try {
    const { error, data } = await request<Api.Support.HandoffDetail>({ url: `/support/admin/handoffs/${handoffId}` });
    if (!error && data) {
      selected.value = data;
      await loadTicketAudit(handoffId);
      editForm.status = data.status;
      editForm.assignedTo = data.assignedTo || '';
      editForm.resolutionNote = data.resolutionNote || '';
    }
  } finally {
    detailLoading.value = false;
  }
}

async function saveTicket() {
  if (!selected.value) return;
  saving.value = true;
  try {
    const { error, data } = await request<Api.Support.HandoffDetail>({
      url: `/support/admin/handoffs/${selected.value.handoffId}`,
      method: 'patch',
      data: {
        status: editForm.status,
        expectedStatus: selected.value.status,
        assignedTo: editForm.assignedTo,
        resolutionNote: editForm.resolutionNote
      }
    });
    if (!error && data) {
      selected.value = {
        ...data,
        // The PATCH response is the shared serializer and may omit the
        // list-only username. Preserve the detail's already loaded identity.
        username: data.username ?? selected.value.username
      };
      await loadTicketAudit(selected.value.handoffId);
      window.$message?.success('工单已更新');
      await getData();
    }
  } finally {
    saving.value = false;
  }
}

async function applyFilters() {
  pagination.page = 1;
  await getData();
}

async function resetFilters() {
  filters.status = null;
  filters.priority = null;
  filters.category = null;
  filters.keyword = null;
  filters.userId = null;
  await applyFilters();
}

onMounted(getData);
</script>

<template>
  <div class="support-handoff-page min-h-500px flex-col-stretch gap-16px overflow-x-hidden overflow-y-auto">
    <div class="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <NCard :bordered="false" size="small" class="summary-card">
        <div class="summary-label">待处理</div>
        <div class="summary-value text-amber-500">{{ summary.open }}</div>
      </NCard>
      <NCard :bordered="false" size="small" class="summary-card">
        <div class="summary-label">处理中</div>
        <div class="summary-value text-sky-500">{{ summary.inProgress }}</div>
      </NCard>
      <NCard :bordered="false" size="small" class="summary-card">
        <div class="summary-label">高优先级</div>
        <div class="summary-value text-red-500">{{ summary.highPriority }}</div>
      </NCard>
      <NCard :bordered="false" size="small" class="summary-card">
        <div class="summary-label">工单总数</div>
        <div class="summary-value">{{ summary.total }}</div>
      </NCard>
    </div>

    <ApprovalQueue v-if="authStore.isAdmin" />
    <NCard title="工单管理" :bordered="false" size="small" class="ticket-card card-wrapper">
      <template #header-extra>
        <NButton :loading="loading" @click="getData">刷新</NButton>
      </template>

      <NForm :model="filters" inline label-placement="left" :show-feedback="false" class="ticket-filter-form mb-4">
        <NFormItem label="关键词">
          <NInput
            v-model:value="filters.keyword"
            clearable
            placeholder="工单号、客户、摘要或原因"
            class="ticket-filter-control"
          />
        </NFormItem>
        <NFormItem label="客户 ID">
          <NInput v-model:value="filters.userId" clearable placeholder="请输入用户 ID" class="ticket-filter-control" />
        </NFormItem>
        <NFormItem label="状态">
          <NSelect v-model:value="filters.status" :options="statusOptions" clearable class="ticket-filter-control" />
        </NFormItem>
        <NFormItem label="优先级">
          <NSelect
            v-model:value="filters.priority"
            :options="priorityOptions"
            clearable
            class="ticket-filter-control"
          />
        </NFormItem>
        <NFormItem label="分类">
          <NInput v-model:value="filters.category" clearable placeholder="如 BILLING" class="ticket-filter-control" />
        </NFormItem>
        <div class="ticket-filter-actions">
          <NButton type="primary" @click="applyFilters">筛选</NButton>
          <NButton @click="resetFilters">重置</NButton>
        </div>
      </NForm>

      <NDataTable
        remote
        :columns="columns"
        :data="rows"
        :loading="loading"
        :pagination="pagination"
        :flex-height="!appStore.isMobile"
        :scroll-x="1400"
        :row-key="row => row.handoffId"
        class="ticket-table sm:h-full"
      />
    </NCard>

    <NDrawer v-model:show="drawerVisible" :width="appStore.isMobile ? '100%' : 680" placement="right">
      <NDrawerContent title="工单详情" closable>
        <NSpin :show="detailLoading">
          <template v-if="selected">
            <NDescriptions label-placement="left" :column="1" bordered size="small">
              <NDescriptionsItem label="工单号">{{ selected.handoffId }}</NDescriptionsItem>
              <NDescriptionsItem label="客户">{{ selected.username || `用户 ${selected.userId}` }}</NDescriptionsItem>
              <NDescriptionsItem label="客户 ID">{{ selected.userId }}</NDescriptionsItem>
              <NDescriptionsItem label="分类">{{ selected.category }}</NDescriptionsItem>
              <NDescriptionsItem label="创建时间">{{ formatDate(selected.createdAt) }}</NDescriptionsItem>
              <NDescriptionsItem label="关联会话">{{ selected.conversationId || '无' }}</NDescriptionsItem>
              <NDescriptionsItem label="关联生成记录">{{ selected.generationId || '无' }}</NDescriptionsItem>
              <NDescriptionsItem label="转人工原因">{{ selected.reason }}</NDescriptionsItem>
              <NDescriptionsItem label="Agent 摘要">{{ selected.summary }}</NDescriptionsItem>
            </NDescriptions>

            <NDivider>处理历史</NDivider>
            <NEmpty v-if="!audit.length" description="暂无处理记录" />
            <div v-for="entry in audit" :key="entry.id" class="mb-3 text-sm">
              <div>
                {{ formatDate(entry.createdAt) }} · {{ entry.actorId }} · {{ entry.before.status || '新建' }} →
                {{ entry.after.status }}
              </div>
              <div v-if="entry.after.resolutionNote" class="text-stone-500">{{ entry.after.resolutionNote }}</div>
            </div>
            <NDivider>处理工单</NDivider>
            <NForm label-placement="top">
              <div class="grid gap-4 sm:grid-cols-2">
                <NFormItem label="处理状态">
                  <NSelect v-model:value="editForm.status" :options="allowedEditStatuses" />
                </NFormItem>
                <NFormItem label="处理人">
                  <NInput v-model:value="editForm.assignedTo" placeholder="管理员用户名或标识" clearable />
                </NFormItem>
              </div>
              <NFormItem label="处理说明">
                <NInput
                  v-model:value="editForm.resolutionNote"
                  type="textarea"
                  :rows="5"
                  maxlength="6000"
                  show-count
                  placeholder="记录处理结论；客户不会自动看到这段说明。"
                />
              </NFormItem>
              <div class="flex justify-end">
                <NButton type="primary" :loading="saving" :disabled="selected.status === 'CLOSED'" @click="saveTicket">
                  保存处理结果
                </NButton>
              </div>
            </NForm>
          </template>
          <NEmpty v-else-if="!detailLoading" description="未找到工单" />
        </NSpin>
      </NDrawerContent>
    </NDrawer>
  </div>
</template>

<style scoped>
.summary-card {
  min-height: 94px;
}

.summary-label {
  color: rgb(120 113 108);
  font-size: 13px;
}

.summary-value {
  margin-top: 8px;
  font-size: 28px;
  font-weight: 700;
  line-height: 1;
}

.ticket-filter-form {
  display: grid;
  grid-template-columns: minmax(260px, 2fr) repeat(4, minmax(132px, 1fr)) auto;
  gap: 12px 16px;
  align-items: end;
}

.ticket-filter-form :deep(.n-form-item) {
  min-width: 0;
  margin-right: 0;
}

.ticket-filter-form :deep(.n-form-item-blank) {
  min-width: 0;
}

.ticket-filter-control {
  width: 100%;
}

.ticket-filter-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}

.ticket-summary-cell {
  min-width: 0;
  line-height: 1.5;
  white-space: normal;
}

@media (max-width: 1400px) {
  .ticket-filter-form {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .ticket-filter-actions {
    grid-column: 1 / -1;
    justify-content: flex-end;
  }
}

@media (max-width: 720px) {
  .ticket-filter-form {
    grid-template-columns: 1fr;
  }

  .ticket-filter-actions {
    grid-column: auto;
    justify-content: flex-start;
  }
}
</style>
