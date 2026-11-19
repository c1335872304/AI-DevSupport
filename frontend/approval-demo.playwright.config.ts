import process from 'node:process';
import { defineConfig } from '@playwright/test';

const apiPort = 18789;
const webPort = 18790;
const api = `http://127.0.0.1:${apiPort}`;
const web = `http://127.0.0.1:${webPort}`;
const python = process.env.REFUND_DEMO_PYTHON || 'python';
process.env.REFUND_DEMO_PASSWORD ||= 'DemoApproval2026';

export default defineConfig({
  testMatch: 'playwright-approval-demo.spec.ts',
  timeout: 90_000,
  workers: 1,
  expect: { timeout: 15_000 },
  use: {
    baseURL: web,
    actionTimeout: 15_000,
    trace: 'retain-on-failure',
    launchOptions: process.env.REFUND_DEMO_BROWSER ? { executablePath: process.env.REFUND_DEMO_BROWSER } : {}
  },
  webServer: [
    {
      command: `"${python}" -X utf8 scripts/run_refund_sandbox_demo.py --serve ${apiPort}`,
      cwd: '../backend',
      env: { REFUND_DEMO_PASSWORD: process.env.REFUND_DEMO_PASSWORD },
      url: `${api}/health`,
      timeout: 40_000
    },
    {
      command: `node node_modules/vite/bin/vite.js --mode development --host 127.0.0.1 --port ${webPort} --strictPort`,
      env: {
        VITE_SERVICE_BASE_URL: `${api}/api/v1`,
        VITE_OTHER_SERVICE_BASE_URL: JSON.stringify({ api: `${api}/api/v1`, ws: `ws://127.0.0.1:${apiPort}` }),
        VITE_HTTP_PROXY: 'Y'
      },
      url: web,
      timeout: 60_000
    }
  ]
});
