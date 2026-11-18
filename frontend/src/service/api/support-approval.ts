import { request } from '@/service/request';

export interface ApprovalItem {
  requestId: string;
  invoiceId: string | null;
  conversationId?: string;
  handoffId?: string;
  status: string;
  amountMinor?: number;
  currency?: string;
  receipt?: { refundId: string; amountMinor: number; currency: string };
}

export interface ApprovalReview extends ApprovalItem {
  userId: string;
  reason: string;
  decision: 'approve' | 'reject' | null;
  decidedBy: string | null;
  decisionNote: string | null;
}

export interface ApprovalOptions {
  invoices: { id: string; month: string; amount: number }[];
  tickets: { id: string; summary: string }[];
}

export function approvalLabel(status: string) {
  const labels: Record<string, string> = {
    PENDING_APPROVAL: '等待人工审批',
    REJECTED: '申请已拒绝',
    APPROVED_PREVIEW: '已批准，等待执行确认',
    SANDBOX_REFUNDED: '沙箱退款已确认',
    SANDBOX_REJECTED: '沙箱拒绝退款',
    REFUND_RECONCILING: '退款待核对',
    TICKET_CLOSED: '工单已关闭',
    TICKET_UNAVAILABLE: '工单已关闭或不可用'
  };
  return labels[status] || status;
}

export const approvalApi = {
  capabilities: () => request<{ enabled: boolean }>({ url: '/support/approval-capabilities' }),
  options: (conversationId: string) =>
    request<ApprovalOptions>({ url: '/support/refund-options', params: { conversationId } }),
  list: (conversationId: string) =>
    request<ApprovalItem[]>({ url: '/support/refund-requests', params: { conversationId } }),
  submit: (data: {
    conversationId: string;
    requestKey: string;
    reason: string;
    invoiceId?: string;
    handoffId?: string;
  }) => request<ApprovalItem>({ url: '/support/refund-requests', method: 'post', data }),
  queue: () => request<ApprovalReview[]>({ url: '/support/admin/refund-requests' }),
  decide: (id: string, decision: 'approve' | 'reject', note: string) =>
    request<ApprovalItem>({ url: `/support/admin/refund-requests/${id}/decision`, method: 'post', data: { decision, note } })
};
