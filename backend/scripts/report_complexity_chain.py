"""Publish the frozen paired complexity evaluation; no provider calls."""

import json
import statistics
from pathlib import Path

import summarize_independent_answers as summary

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'data/checkpoints/complexity-chain-20261020'
DOCS = ROOT.parent / 'docs/04-testing'
NOTES = {
    'C01': 'json_object、prompt 包含 json、格式示例与截断提醒正确；代码为片段，messages 需调用方定义。',
    'C02': '北京兼容地址、同地域及同计费方案匹配正确；未冒充查询个人账户。',
    'C03': 'background 开启和 queued/in_progress 继续 retrieve，退出后停止轮询正确。',
    'C04': 'stream 与 include_usage 配置、最后 usage 块及空 choices 处理正确。',
    'G01': '区分合法 JSON 与 Schema 约束，保留厂商边界及支持子集限制。',
    'G02': '缺少厂商、模型及接口时追问，没有承诺通用 Schema 保证。',
    'D01': '基于 Demo 调用时证据识别过期 Key；要求修正后新请求复查。',
    'D02': '同一诊断的新请求 200，RESOLVED 仅限该应用与接口；不扩大到账户整体。',
    'D03': '调用时 RATE_LIMIT 识别为频率限制，建议退避而非补余额。',
    'D04': '新请求 QUOTA_LIMIT，仍未解决；不沿用旧频率原因或误报恢复。',
    'D05': '未知请求没有可核验证据，明确无法确认原因并要求补充信息。',
    'D06': '实际创建转人工记录并返回工单号，保留 Demo 范围和调用时证据。',
}


def main():
    phases = {}
    for phase in ('baseline', 'final'):
        folder = OUT / phase
        if phase == 'final':
            (folder / 'provider-usage.jsonl').write_bytes((OUT / 'provider-usage.jsonl').read_bytes())
        review = {'method': '按冻结 requiredClaims 人工逐题核对原文、引用和诊断状态；无模型裁判调用',
                  'cases': [{'id': key, 'overall': 'PASS', 'note': value} for key, value in NOTES.items()]}
        review_path = folder / 'review.json'
        review_path.write_text(json.dumps(review, ensure_ascii=False, indent=2), encoding='utf-8')
        summary.OUT = folder
        summary.DATASET = folder / 'cases.json'
        summary.REVIEW = review_path
        summary.REPORT = DOCS / f'COMPLEXITY_CHAIN_{phase.upper()}_CASES_2026-10-20.md'
        summary.main()
        phases[phase] = json.loads((folder / 'metrics.json').read_text(encoding='utf-8'))
    groups = {}
    for phase, metrics in phases.items():
        groups[phase] = {}
        for name, prefix in [('simple', 'C'), ('diagnosis', 'D'), ('guard', 'G')]:
            rows = [r for r in metrics['cases'] if r['id'].startswith(prefix)]
            groups[phase][name] = {
                'cases': len(rows), 'meanMs': statistics.mean(r['elapsedMs'] for r in rows),
                'llmCalls': sum(r['llmCalls'] for r in rows),
                'embeddingCalls': sum(r['embeddingCalls'] for r in rows),
                'estimatedCny': sum(r['estimatedCny'] for r in rows),
            }
        for row in metrics['cases']:
            assert not row['missingUsage'] and not row['unmappedReferences']
            assert not row['foreignReferences'] and not row['declaredNameMismatches']
            assert row['citationAccessOk'] == row['citationAccessTotal']
        for case, expected in [('D02', 'RESOLVED'), ('D04', 'WAITING_USER_ACTION')]:
            artifact = json.loads((OUT / phase / f'{case}.json').read_text(encoding='utf-8'))
            assert artifact['diagnosis']['status'] == expected
    requests, usages = {}, {}
    for line in (OUT / 'provider-usage.jsonl').read_text().splitlines():
        event = json.loads(line)
        (requests if event['event'] == 'request' else usages if event['event'] == 'usage' else {}).update(
            {event['request']: event})
    total = 0.0
    for rid, event in usages.items():
        u = event['usage']
        total += ((u['prompt_cache_hit_tokens'] * .02 + u['prompt_cache_miss_tokens'] +
                   u['completion_tokens'] * 4) if requests[rid]['kind'] == 'llm'
                  else u['total_tokens'] * .5) / 1e6
    result = {'groups': groups, 'allAttempts': {'requests': len(requests), 'captured': len(usages),
               'estimatedCny': total, 'turns': 48, 'invalidHarnessTurns': 24}}
    (OUT / 'comparison.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print('COMPARISON', json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
