<script setup lang="ts">
import { $t } from '@/locales';

defineOptions({ name: 'Register' });

const { toggleLoginModule } = useRouterPush();
const { formRef, validate } = useNaiveForm();
const model = reactive({ username: '', password: '', confirmPassword: '' });
const loading = ref(false);

const rules = computed<Record<keyof typeof model, App.Global.FormRule[]>>(() => {
  const { formRules, createConfirmPwdRule } = useFormRules();

  return {
    username: formRules.userName,
    password: formRules.pwd,
    confirmPassword: createConfirmPwdRule(model.password)
  };
});

async function handleSubmit() {
  if (loading.value) return;
  await validate();
  if (loading.value) return;

  loading.value = true;
  try {
    const { error } = await fetchRegister(model.username.trim(), model.password);
    if (!error) {
      window.$message?.success($t('page.login.register.success'));
      toggleLoginModule('pwd-login');
    }
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <NForm
    ref="formRef"
    :model="model"
    :rules="rules"
    size="large"
    :show-label="false"
    @keyup.enter="handleSubmit"
  >
    <NFormItem path="username">
      <NInput v-model:value="model.username" :placeholder="$t('page.login.common.userNamePlaceholder')">
        <template #prefix>
          <icon-ant-design:user-outlined />
        </template>
      </NInput>
    </NFormItem>
    <NFormItem path="password">
      <NInput
        v-model:value="model.password"
        type="password"
        show-password-on="click"
        :placeholder="$t('page.login.common.passwordPlaceholder')"
      >
        <template #prefix>
          <icon-ant-design:key-outlined />
        </template>
      </NInput>
    </NFormItem>
    <NFormItem path="confirmPassword">
      <NInput
        v-model:value="model.confirmPassword"
        type="password"
        show-password-on="click"
        :placeholder="$t('page.login.common.confirmPasswordPlaceholder')"
      >
        <template #prefix>
          <icon-ant-design:key-outlined />
        </template>
      </NInput>
    </NFormItem>
    <NSpace vertical :size="18" class="w-full">
      <NButton type="primary" size="large" round block :loading="loading" @click="handleSubmit">
        {{ $t('page.login.common.register') }}
      </NButton>
      <NButton block @click="toggleLoginModule('pwd-login')">
        {{ $t('page.login.common.back') }}
      </NButton>
    </NSpace>

    <div class="mt-4 text-center">
      {{ $t('page.login.register.agreement') }}
      <NButton text type="primary">{{ $t('page.login.register.protocol') }}</NButton>
      {{ $t('page.login.register.and') }}
      <NButton text type="primary">{{ $t('page.login.register.policy') }}</NButton>
    </div>
  </NForm>
</template>
