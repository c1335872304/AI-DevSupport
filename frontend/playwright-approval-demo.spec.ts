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
