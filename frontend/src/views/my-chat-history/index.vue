<script setup lang="ts">
import { router } from '@/router';
import { useChatStore } from '@/store/modules/chat';

defineOptions({ name: 'MyChatHistory' });

const chatStore = useChatStore();
const { sessions, sessionsLoading } = storeToRefs(chatStore);

const orderedSessions = computed(() => {
  return [...sessions.value].sort((left, right) => {
    return new Date(right.updatedAt).getTime() - new Date(left.updatedAt).getTime();
  });
});

async function openConversation(conversationId: string) {
  await chatStore.switchSession(conversationId);
  await router.push('/chat');
}

onMounted(() => {
  void chatStore.loadSessions();
});
</script>

<template>
  <div class="h-full p-4 md:p-6">
    <NCard title="我的聊天记录" :bordered="false" class="h-full rounded-16px shadow-sm">
      <template #header-extra>
        <NButton secondary size="small" :loading="sessionsLoading" @click="chatStore.loadSessions()">
          刷新
        </NButton>
      </template>
      <NSpin :show="sessionsLoading">
        <NList bordered hoverable>
          <NListItem v-for="session in orderedSessions" :key="session.conversationId">
            <div class="min-w-0 flex items-center gap-3">
              <div class="min-w-0 flex-1">
                <div class="truncate font-medium">{{ session.title || '未命名对话' }}</div>
                <div class="mt-1 text-12px text-gray-500">
                  {{ session.updatedAt }} · {{ session.status === 'ARCHIVED' ? '已归档' : '进行中' }}
                </div>
              </div>
              <NButton size="small" type="primary" secondary @click="openConversation(session.conversationId)">
                查看
              </NButton>
            </div>
          </NListItem>
        </NList>
        <NEmpty v-if="!sessionsLoading && !orderedSessions.length" description="暂无聊天记录" class="mt-16" />
      </NSpin>
    </NCard>
  </div>
</template>
