<script setup lang="ts">
import type { NScrollbar } from 'naive-ui';
import { VueMarkdownItProvider } from '@/vendor/vue-markdown-shiki';
import ChatMessage from '../chat/modules/chat-message.vue';

defineOptions({
  name: 'ChatHistory'
});

const scrollbarRef = ref<InstanceType<typeof NScrollbar>>();

const list = ref<Api.Chat.Message[]>([]);
const loading = ref(false);

watch(() => [...list.value], scrollToBottom);

function scrollToBottom() {
  setTimeout(() => {
    scrollbarRef.value?.scrollBy({
      top: 999999999999999,
      behavior: 'auto'
    });
  }, 100);
}

const range = ref<[number, number] | null>(null);
const userId = ref<number | null>(null);

const params = computed(() => {
  const query: {
    userid?: number;
    start_date?: string;
    end_date?: string;
  } = {};

  // Remote selects can briefly emit undefined or an empty string while their
  // options are loading/clearing. Never pass those transient values to the
  // FastAPI integer query parameter.
  const selectedUserId = Number(userId.value);
  if (Number.isInteger(selectedUserId) && selectedUserId > 0) {
    query.userid = selectedUserId;
  }

  // A date-range picker can be in a half-selected state. Send date filters
  // only after both timestamps are valid, instead of emitting Invalid Date.
  const [start, end] = range.value || [];
  if (Number.isFinite(start) && Number.isFinite(end)) {
    query.start_date = dayjs(start).format('YYYY-MM-DD');
    query.end_date = dayjs(end).format('YYYY-MM-DD');
  }

  return query;
});

let latestRequest = 0;

watch([userId, range], () => {
  void getList();
}, { immediate: true, deep: true });

async function getList() {
  const requestId = ++latestRequest;
  loading.value = true;
  const { error, data } = await request<Api.Chat.Message[]>({
    url: 'admin/conversation',
    params: params.value
  });
  if (!error && requestId === latestRequest) {
    list.value = data;
    scrollToBottom();
  }
  if (requestId === latestRequest) {
    loading.value = false;
  }
}
</script>

<template>
  <div class="h-full">
    <Teleport defer to="#header-extra">
      <div class="px-10">
        <NForm label-placement="left" :show-feedback="false" inline>
          <NFormItem label="用户">
            <TheSelect
              v-model:value="userId"
              url="admin/users/list"
              :params="{ page: 1, size: 200 }"
              key-field="content"
              value-field="userId"
              label-field="username"
              class="clear w-200px!"
              placeholder="全部用户"
            />
          </NFormItem>
          <NFormItem label="时间">
            <NDatePicker v-model:value="range" type="daterange" class="clear" clearable />
          </NFormItem>
        </NForm>
      </div>
    </Teleport>
    <NScrollbar ref="scrollbarRef">
      <NSpin :show="loading" class="h-full">
        <VueMarkdownItProvider>
          <ChatMessage v-for="(item, index) in list" :key="index" :msg="item" />
        </VueMarkdownItProvider>
        <NEmpty v-if="!list.length" description="暂无数据" class="mt-60" />
      </NSpin>
    </NScrollbar>
  </div>
</template>

<style scoped lang="scss"></style>
