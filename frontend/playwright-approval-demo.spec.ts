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
    await requestAction(page, '申请退款', /sandbox-paid-1/);
    const reviewer = await admin.newPage();
    await login(reviewer, 'refund-reviewer');
    await reviewer.goto('/support-handoff');
    await approve(reviewer, '申请退款');
    const adminReceipt = reviewer.getByText(/退款编号 rf_demo_/);
    await expect(adminReceipt).toBeVisible();
    const refundId = (await adminReceipt.innerText()).match(/rf_demo_[a-f0-9]+/)?.[0];
    expect(refundId).toBeTruthy();
    await page.getByRole('button', { name: '刷新申请状态' }).click();
    await expect(page.getByText(new RegExp(refundId!))).toBeVisible();
    await page.reload();
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
