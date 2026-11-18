<script setup lang="tsx">
import { onMounted, ref } from 'vue';
import { NButton, NCard, NEmpty } from 'naive-ui';

const modelProvidersLoading = ref(false);
const modelProviders = ref<Api.Admin.ModelProviderSettings | null>(null);

function cloneProviderItem(item: Api.Admin.ModelProviderItem): Api.Admin.ModelProviderItem {
  return {
    provider: item.provider,
    displayName: item.displayName,
    apiStyle: item.apiStyle,
    apiBaseUrl: item.apiBaseUrl,
    model: item.model,
    dimension: item.dimension ?? null,
    enabled: Boolean(item.enabled),
    active: Boolean(item.active),
    hasApiKey: Boolean(item.hasApiKey),
    maskedApiKey: item.maskedApiKey || '',
    apiKeyInput: ''
  };
}

function cloneModelProviderScope(payload: Api.Admin.ModelProviderScopeSettings): Api.Admin.ModelProviderScopeSettings {
  return {
    scope: payload.scope,
    activeProvider: payload.activeProvider,
    providers: (payload.providers || []).map(cloneProviderItem)
  };
}

function cloneModelProviderSettings(
  payload?: Api.Admin.ModelProviderSettings | null
): Api.Admin.ModelProviderSettings | null {
  if (!payload) {
    return null;
  }
  return {
    llm: cloneModelProviderScope(payload.llm),
    embedding: cloneModelProviderScope(payload.embedding)
  };
}

async function getModelProviders() {
  modelProvidersLoading.value = true;
  const { error, data } = await request<Api.Admin.ModelProviderSettings>({
    url: '/admin/model-providers'
  });

  if (!error && data) {
    modelProviders.value = cloneModelProviderSettings(data);
  }
  modelProvidersLoading.value = false;
}

async function testModelProvider(scopeKey: 'llm' | 'embedding', provider: Api.Admin.ModelProviderItem) {
  const { error, data } = await request<Api.Admin.ConnectivityTestResult>({
    url: `/admin/model-providers/${scopeKey}/test`,
    method: 'post',
    data: {
      provider: provider.provider,
      apiBaseUrl: provider.apiBaseUrl,
      model: provider.model,
      apiKey: provider.apiKeyInput?.trim() || '',
      dimension: scopeKey === 'embedding' ? provider.dimension : null
    }
  });

  if (!error && data) {
    if (data.success) {
      window.$message?.success(`${provider.displayName} 连接成功，耗时 ${data.latencyMs}ms`);
    } else {
      window.$message?.error(`${provider.displayName} 连接失败：${data.message}`);
    }
  }
}

onMounted(() => {
  getModelProviders();
});
</script>

<template>
  <div class="min-h-500px flex-col-stretch gap-16px overflow-auto">
    <NCard :bordered="false" size="small" class="card-wrapper">
      <template #header>模型 Provider 配置</template>
      <template #header-extra>
        <div class="flex items-center gap-2">
          <span class="text-xs text-stone-400">当前运行环境配置（只读）</span>
        </div>
      </template>

      <NSpin :show="modelProvidersLoading">
        <div class="mb-4 border border-stone-200 rounded-2xl bg-stone-50 px-4 py-3 text-xs text-stone-500">
          当前值来自后端运行环境，不会回显 API Key 明文。请在
          <code>backend/.env</code>
          修改模型地址、模型名或密钥后重建 API/Worker 容器；Embedding 模型或维度变更后必须重新索引知识库。
        </div>

        <div v-if="modelProviders" class="grid gap-4">
          <div class="provider-scope">
            <div class="provider-scope-header">
              <div>
                <div class="provider-scope-title">LLM Provider</div>
                <div class="provider-scope-sub">聊天请求使用当前运行环境中的 active provider</div>
              </div>
              <div class="text-xs text-stone-400">{{ modelProviders.llm.activeProvider }}</div>
            </div>

            <div class="provider-grid">
              <div v-for="item in modelProviders.llm.providers" :key="`llm-${item.provider}`" class="provider-card">
                <div class="provider-card-header">
                  <div>
                    <div class="provider-name">{{ item.displayName }}</div>
                    <div class="provider-code">{{ item.provider }} · {{ item.apiStyle }}</div>
                  </div>
                  <NSwitch :value="item.enabled" size="small" disabled />
                </div>
                <div class="limit-grid">
                  <div>
                    <div class="limit-label">API 地址</div>
                    <NInput :value="item.apiBaseUrl" readonly />
                  </div>
                  <div>
                    <div class="limit-label">模型</div>
                    <NInput :value="item.model" readonly />
                  </div>
                  <div>
                    <div class="limit-label">现有密钥</div>
                    <div class="provider-mask">{{ item.hasApiKey ? item.maskedApiKey : '未配置' }}</div>
                  </div>
                </div>
                <div class="mt-3 flex justify-end">
                  <NButton size="small" secondary @click="testModelProvider('llm', item)">测试连接</NButton>
                </div>
              </div>
            </div>
          </div>

          <div class="provider-scope">
            <div class="provider-scope-header">
              <div>
                <div class="provider-scope-title">Embedding Provider</div>
                <div class="provider-scope-sub">Embedding 地址、模型和维度在运行期间只读</div>
              </div>
              <div class="text-xs text-stone-400">{{ modelProviders.embedding.activeProvider }}</div>
            </div>

            <div class="provider-grid">
              <div
                v-for="item in modelProviders.embedding.providers"
                :key="`embedding-${item.provider}`"
                class="provider-card"
              >
                <div class="provider-card-header">
                  <div>
                    <div class="provider-name">{{ item.displayName }}</div>
                    <div class="provider-code">{{ item.provider }} · {{ item.apiStyle }}</div>
                  </div>
                  <NSwitch :value="item.enabled" size="small" disabled />
                </div>
                <div class="limit-grid">
                  <div>
                    <div class="limit-label">API 地址</div>
                    <NInput :value="item.apiBaseUrl" readonly />
                  </div>
                  <div>
                    <div class="limit-label">模型</div>
                    <NInput :value="item.model" readonly />
                  </div>
                  <div>
                    <div class="limit-label">维度</div>
                    <NInputNumber :value="item.dimension" :min="1" class="w-full" readonly />
                  </div>
                  <div>
                    <div class="limit-label">现有密钥</div>
                    <div class="provider-mask">{{ item.hasApiKey ? item.maskedApiKey : '未配置' }}</div>
                  </div>
                </div>
                <div class="mt-3 flex justify-end">
                  <NButton size="small" secondary @click="testModelProvider('embedding', item)">测试连接</NButton>
                </div>
              </div>
            </div>
          </div>
        </div>
        <NEmpty v-else size="small" description="暂未加载到模型配置" />
      </NSpin>
    </NCard>
  </div>
</template>

<style scoped lang="scss">
.provider-scope {
  @apply rounded-3xl border border-stone-200 bg-[linear-gradient(180deg,_rgba(255,255,255,0.98),_rgba(248,250,252,0.94))] p-5 shadow-sm;
}

.provider-scope-header {
  @apply mb-4 flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between;
}

.provider-scope-title {
  @apply text-sm font-semibold text-stone-700;
}

.provider-scope-sub {
  @apply mt-1 text-xs text-stone-500;
}

.provider-grid {
  @apply grid gap-4 xl:grid-cols-2;
}

.provider-card {
  @apply rounded-2xl border border-stone-200 bg-white p-4 shadow-sm;
}

.provider-card-header {
  @apply mb-4 flex items-start justify-between gap-3;
}

.provider-name {
  @apply text-sm font-semibold text-stone-700;
}

.provider-code {
  @apply mt-1 text-xs uppercase tracking-0.08em text-stone-400;
}

.provider-mask {
  @apply rounded-xl border border-dashed border-stone-200 bg-stone-50 px-3 py-2 text-sm text-stone-500;
}

.limit-grid {
  @apply grid gap-3 sm:grid-cols-2;
}

.limit-label {
  @apply mb-2 text-xs font-semibold uppercase tracking-0.08em text-stone-400;
}
</style>
