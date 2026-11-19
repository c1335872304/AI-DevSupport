import process from 'node:process';
import { expect, test } from '@playwright/test';
import type { Page } from '@playwright/test';

async function login(page: Page, name: string) {
  await page.goto('/login');
  await page.getByPlaceholder('请输入用户名').fill(name);
  const password = page.getByPlaceholder('请输入密码');
  await password.fill(process.env.REFUND_DEMO_PASSWORD!);
  await password.press('Enter');
  await expect(page.getByRole('button', { name, exact: true })).toBeVisible({ timeout: 25_000 });
}

async function requestAction(page: Page, action: '申请退款' | '关闭工单', target: RegExp) {
  await page.getByRole('button', { name: '发起业务申请' }).click();
  const form = page.locator('.n-modal').filter({ hasText: '发起业务申请' });
  await form.locator(`input[type="radio"][value="${action === '申请退款' ? 'refund' : 'close'}"]`).check();
  await form.locator('.n-base-selection').click();
  await page.getByText(target).last().click();
  await form.locator('textarea').fill(`浏览器验收：${action}`);
  await form.getByRole('button', { name: '提交人工审批' }).click();
  await expect(page.getByText(`${action} · 等待人工审批`)).toBeVisible();
}

async function approve(page: Page, action: '申请退款' | '关闭工单') {
  await page.getByRole('button', { name: '刷新审批队列' }).click();
  await expect(page.getByText(`${action} · 等待人工审批`)).toBeVisible();
  await page.getByRole('button', { name: '审阅', exact: true }).click();
  await page.getByPlaceholder('审批说明').fill('批准浏览器演示');
  await page.getByRole('button', { name: '批准执行' }).click();
}

test('客服会话与后台完成退款回执及工单关闭', async ({ page, browser, baseURL }) => {
  const admin = await browser.newContext({ baseURL });
  try {
    await login(page, 'refund-customer');
    await page.getByText('客服演示', { exact: true }).click();
    await requestAction(page, '申请退款', /sandbox-paid-1/);
    const reviewer = await admin.newPage();
    await login(reviewer, 'refund-reviewer');
    await reviewer.goto('/support-handoff');
    await approve(reviewer, '申请退款');
    const adminReceipt = reviewer.getByText(/退款编号 rf_demo_/);
    await expect(adminReceipt).toBeVisible();
    const refundId = ((await adminReceipt.textContent()) || '').match(/rf_demo_[a-f0-9]+/)?.[0];
    expect(refundId).toBeTruthy();
    await page.getByRole('button', { name: '刷新申请状态' }).click();
    await expect(page.getByText(new RegExp(refundId!))).toBeVisible();
    await page.reload();
    await page.getByText('客服演示', { exact: true }).click();
    await expect(page.getByText(new RegExp(refundId!))).toBeVisible();

    await requestAction(page, '关闭工单', /demo-support-ticket.*待确认关闭/);
    await approve(reviewer, '关闭工单');
    await expect(reviewer.getByText('关闭工单 · 工单已关闭')).toBeVisible();
    await page.getByRole('button', { name: '刷新申请状态' }).click();
    await expect(page.getByText('关闭工单 · 工单已关闭')).toBeVisible();
  } finally {
    await admin.close();
  }
});

test('support operator handles ticket transitions with history and no approval permissions', async ({ page }) => {
  await login(page, 'support-agent');
  await page.goto('/support-handoff');
  await expect(page.getByText('业务审批', { exact: true })).toHaveCount(0);
  const row = page.getByRole('row').filter({ hasText: 'demo-support-staff-ticket' });
  await expect(row).toBeVisible();
  await row.getByRole('button', { name: '查看', exact: true }).click();
  const drawer = page.locator('.n-drawer');
  const select = drawer.locator('.n-select').first();
  await select.click();
  await expect(page.locator('.n-base-select-option').filter({ hasText: /^已关闭$/ })).toHaveCount(0);
  await page
    .locator('.n-base-select-option')
    .filter({ hasText: /^处理中$/ })
    .click();
  await drawer.getByRole('button', { name: '保存处理结果' }).click();
  await expect(drawer.getByText(/OPEN → IN_PROGRESS/)).toBeVisible();
  await drawer.getByPlaceholder('记录处理结论；客户不会自动看到这段说明。').fill('已核对并修复');
  await select.click();
  await page
    .locator('.n-base-select-option')
    .filter({ hasText: /^已解决$/ })
    .click();
  await drawer.getByRole('button', { name: '保存处理结果' }).click();
  await expect(drawer.getByText(/IN_PROGRESS → RESOLVED/)).toBeVisible();
});

test('business progress stays with its generation and retains the requested next step', async ({ page }) => {
  let push: ((payload: Record<string, unknown>) => void) | undefined;
  await page.routeWebSocket(/\/chat(?:\?|$)/, socket => {
    socket.onMessage(raw => {
      if (raw === '__chat_ping__') {
        socket.send('__chat_pong__');
        return;
      }
      const payload = JSON.parse(String(raw));
      if (payload.type === 'auth') socket.send(JSON.stringify({ type: 'connection', sessionId: 'progress-demo' }));
      if (payload.type === 'message') {
        socket.send(
          JSON.stringify({ type: 'start', generationId: 'progress-one', conversationId: payload.conversationId })
        );
        push = event => socket.send(JSON.stringify(event));
      }
    });
  });
  await login(page, 'refund-customer');
  await page.getByText('客服演示', { exact: true }).click();
  const input = page.getByPlaceholder('给 API 助手 发送消息，Enter 发送，Shift+Enter 换行');
  await input.fill('请核对账单和请求记录');
  await input.press('Enter');
  await expect.poll(() => Boolean(push)).toBe(true);
  await expect(page.getByText('正在处理你的问题', { exact: true })).toBeVisible();
  push!({
    type: 'workflow_progress',
    generationId: 'progress-one',
    phase: 'checking_billing',
    timestamp: 10,
    text: 'PRIVATE_REASONING'
  });
  await expect(page.getByText('正在核对套餐和账单', { exact: true })).toBeVisible();
  push!({ type: 'workflow_progress', generationId: 'another-generation', phase: 'checking_request', timestamp: 11 });
  await expect(page.getByText('正在核对套餐和账单', { exact: true })).toBeVisible();
  await expect(page.getByText('PRIVATE_REASONING')).toHaveCount(0);
  push!({ type: 'workflow_progress', generationId: 'progress-one', phase: 'supplementing', timestamp: 12 });
  await expect(page.getByText('正在补查缺少的证据', { exact: true })).toBeVisible();
  push!({ type: 'workflow_progress', generationId: 'progress-one', phase: 'waiting_for_user', timestamp: 13 });
  await expect(page.getByText('等待你补充信息', { exact: true })).toBeVisible();
  push!({ type: 'completion', generationId: 'progress-one', status: 'finished', content: '请补充请求号。' });
  await expect(page.getByText('请补充请求号。', { exact: true })).toBeVisible();
  await expect(page.getByText('等待你补充信息', { exact: true })).toBeVisible();
});
