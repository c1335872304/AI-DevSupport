import { defineConfig } from '@soybeanjs/eslint-config';

export default defineConfig(
  { vue: true, unocss: true },
  { ignores: ['test-results/**', 'playwright-report/**'] },
  {
    rules: {
      'vue/multi-word-component-names': [
        'warn',
        {
          ignores: ['index', 'App', 'Register', '[id]', '[url]']
        }
      ],
      'vue/component-name-in-template-casing': [
        'warn',
        'PascalCase',
        {
          registeredComponentsOnly: false,
          ignores: ['/^icon-/']
        }
      ],
      'unocss/order-attributify': 'off',
      'no-warning-comments': 'off',
      'no-console': ['warn', { allow: ['warn', 'error'] }],
      'vue/no-v-html': 'off'
    }
  }
);
