import { beforeEach, describe, expect, it } from 'vitest';
import { mockControl } from '@/api/adapters/mock/control';
import { MockApiClient } from '@/api/adapters/mock/engine';
import { at, mid } from '@/api/adapters/mock/ids';
import { DEMO_PASSWORD } from '@/api/adapters/mock/seed/accounts';

const S1 = mid('session:runway27');
const RUN03 = mid('runway27:run:#03');
const scope = { sessionId: S1, runId: RUN03 };
const F03 = mid('runway27:finding:F-03');

async function client(email = 'evaluator@flowlens.test') {
  const api = new MockApiClient();
  await api.login(email, DEMO_PASSWORD);
  return api;
}

describe('MOCK server behaviour (simulates backend contract)', () => {
  beforeEach(() => {
    mockControl.getState().reset();
    mockControl.getState().set({ latencyMs: [0, 0] });
  });

  it('AS_KNOWN hides information that was not yet available; DEBRIEF shows it', async () => {
    const api = await client();
    const asKnown = await api.listFindings(scope, { mode: 'AS_KNOWN', asOfMs: at('05:21') });
    expect(asKnown.map((f) => f.label)).not.toContain('F-03'); // event 05:19, available 05:22
    const later = await api.listFindings(scope, { mode: 'AS_KNOWN', asOfMs: at('05:22') });
    expect(later.map((f) => f.label)).toContain('F-03');
    const debrief = await api.listFindings(scope, { mode: 'DEBRIEF', asOfMs: at('05:21') });
    expect(debrief.map((f) => f.label)).toContain('F-03');
  });

  it('keeps the correction out of as-known memory at 05:22', async () => {
    const api = await client();
    const snap = await api.getSnapshot(scope, { mode: 'AS_KNOWN', asOfMs: at('05:22') });
    const fln214 = snap.entities.find((e) => e.entity_id === mid('runway27:entity:FLN214'))!;
    expect(fln214.readback.state).toBe('MISMATCH');
    expect(fln214.movement.state).toBe('NOT_EVALUABLE');
    const after = await api.getSnapshot(scope, { mode: 'AS_KNOWN', asOfMs: at('05:40') });
    expect(after.entities.find((e) => e.entity_id === fln214.entity_id)!.readback.state).toBe('CORRECTED');
  });

  it('does not leak future findings into as-known timeline markers', async () => {
    const api = await client();
    const snap = await api.getSnapshot(scope, { mode: 'AS_KNOWN', asOfMs: at('05:22') });
    const labels = snap.event_markers.map((m) => m.label.split(' ')[0]);
    expect(labels).toContain('F-03');
    expect(labels).not.toContain('F-07');
    const debrief = await api.getSnapshot(scope, { mode: 'DEBRIEF', asOfMs: at('05:22') });
    expect(debrief.event_markers.map((m) => m.label.split(' ')[0])).toContain('F-07');
  });

  it('denies review mutations to an observer and audio to evidence', async () => {
    const api = await client('observer@flowlens.test');
    await expect(api.reviewFinding(scope, F03, { decision: 'CONFIRMED', reason: 'Checked audio' }, { idempotencyKey: 'k1' })).rejects.toMatchObject({ code: 'ACCESS_DENIED' });
    const ev = await api.getEvidence(scope, F03, { mode: 'DEBRIEF', asOfMs: at('18:40') });
    expect(ev.audio_access).toBe('DENIED');
  });

  it('is idempotent per key and rejects a reused key with a different payload', async () => {
    const api = await client();
    const a = await api.reviewFinding(scope, F03, { decision: 'UNRESOLVED', reason: 'Clipped audio' }, { idempotencyKey: 'same' });
    const b = await api.reviewFinding(scope, F03, { decision: 'UNRESOLVED', reason: 'Clipped audio' }, { idempotencyKey: 'same' });
    expect(b.id).toBe(a.id);
    const list = await api.listFindings(scope, { mode: 'DEBRIEF', asOfMs: at('18:40') });
    expect(list.find((f) => f.label === 'F-03')!.reviews).toHaveLength(1);
    await expect(api.reviewFinding(scope, F03, { decision: 'CONFIRMED', reason: 'Different' }, { idempotencyKey: 'same' })).rejects.toMatchObject({ code: 'IDEMPOTENCY_CONFLICT' });
  });

  it('rejects stale expectedVersion and keeps reviews append-only', async () => {
    const api = await client();
    await api.reviewFinding(scope, F03, { decision: 'UNRESOLVED', reason: 'First pass' }, { idempotencyKey: 'r1', expectedVersion: 1 });
    await expect(api.reviewFinding(scope, F03, { decision: 'CONFIRMED', reason: 'Second' }, { idempotencyKey: 'r2', expectedVersion: 1 })).rejects.toMatchObject({ code: 'VERSION_CONFLICT' });
    await api.reviewFinding(scope, F03, { decision: 'CONFIRMED', reason: 'Second' }, { idempotencyKey: 'r3', expectedVersion: 2 });
    const f = (await api.listFindings(scope, { mode: 'DEBRIEF', asOfMs: at('18:40') })).find((x) => x.label === 'F-03')!;
    expect(f.reviews.map((r) => r.decision)).toEqual(['UNRESOLVED', 'CONFIRMED']);
    expect(f.reviews[1]!.supersedes_id).toBe(f.reviews[0]!.id);
  });

  it('never edits the original STT hypothesis and marks dependents stale', async () => {
    const api = await client();
    const seg = mid('runway27:seg:T-10');
    const view = await api.correctTranscript(scope, seg, { text: 'Holding short runway two seven, Flow lens two one four.', reason: 'Listened to audio' }, { idempotencyKey: 'c1', expectedVersion: 1 });
    const row = view.rows.find((r) => r.segment.id !== r.original.id)!;
    expect(row.original.text).toContain('zero nine');
    expect(row.segment.origin).toBe('HUMAN_CORRECTION');
    expect(row.stale_dependents).toBeGreaterThan(0);
    const findings = await api.listFindings(scope, { mode: 'DEBRIEF', asOfMs: at('18:40') });
    expect(findings.every((f) => f.finding.stale)).toBe(true);
  });

  it('accepts a second correction on the original segment id and numbers re-analysis after the latest run', async () => {
    const api = await client();
    const seg = mid('runway27:seg:T-10');
    await api.correctTranscript(scope, seg, { text: 'Holding short runway two seven.', reason: 'First pass' }, { idempotencyKey: 'c2a', expectedVersion: 1 });
    const view = await api.correctTranscript(scope, seg, { text: 'Holding short runway two seven, Flow lens two one four.', reason: 'Second pass' }, { idempotencyKey: 'c2b', expectedVersion: 2 });
    const row = view.rows.find((r) => r.original.id === seg)!;
    expect(row.revisions).toHaveLength(2);
    expect(row.original.text).toContain('zero nine');
    // Seed runs are #02 and #03; a new run must not reuse #03.
    const run = await api.reanalyze(scope, { idempotencyKey: 'r1' });
    expect(run.label).toBe('#04');
  });

  it('pauses mutations while the connection is lost and nothing is queued', async () => {
    const api = await client();
    mockControl.getState().set({ connectionLost: true });
    await expect(api.reviewFinding(scope, F03, { decision: 'CONFIRMED', reason: 'x y z' }, { idempotencyKey: 'n1' })).rejects.toMatchObject({ code: 'CONNECTION_LOST' });
    mockControl.getState().set({ connectionLost: false });
    const f = (await api.listFindings(scope, { mode: 'DEBRIEF', asOfMs: at('18:40') })).find((x) => x.label === 'F-03')!;
    expect(f.reviews).toHaveLength(0);
  });

  it('keeps cached results readable during a provider outage but blocks new briefs', async () => {
    const api = await client();
    mockControl.getState().set({ providerOutage: true });
    await expect(api.listFindings(scope, { mode: 'DEBRIEF', asOfMs: at('18:40') })).resolves.not.toHaveLength(0);
    await expect(api.createBrief(scope, at('18:40'), { idempotencyKey: 'b1' })).rejects.toMatchObject({ code: 'PROVIDER_UNAVAILABLE' });
  });

  it('options carry no command payload and insufficient context yields zero options', async () => {
    const api = await client();
    const set = await api.listOptions(scope, { mode: 'DEBRIEF', asOfMs: at('18:40') });
    for (const o of set.options) expect(Object.keys(o.option)).not.toEqual(expect.arrayContaining(['command', 'payload', 'execute']));
    expect(set.insufficient.map((i) => i.entity_label)).toContain('VEH03');
  });
  it('brief revisions append; earlier revisions stay readable', async () => {
    const api = await client();
    const before = await api.listBriefs(scope);
    const b = await api.createBrief(scope, at('18:40'), { idempotencyKey: 'brief-append' });
    const after = await api.listBriefs(scope);
    expect(after).toHaveLength(before.length + 1);
    expect(b.brief.revision).toBe(before.length + 1);
    expect(after.map((x) => x.brief.id)).toEqual(expect.arrayContaining(before.map((x) => x.brief.id)));
  });

  it('exports always carry provenance and CSV cells are formula-safe', async () => {
    const api = await client();
    const job = await api.createExport(scope, { format: 'CSV', briefId: null, includeJournal: true, redacted: true }, { idempotencyKey: 'csv-1' });
    expect(job.status).toBe('PREPARING');
    await new Promise((r) => setTimeout(r, 2300));
    const file = await api.downloadExport(job.id);
    expect(file.content.split('\n')[0]).toMatch(/"source_kind":"SYNTHETIC"/);
    expect(file.content).not.toMatch(/^"[=+\-@]/m);
  });

  it('runway clear/safe questions return Unknown with no evidence', async () => {
    const api = await client();
    const r = await api.ask(scope, { mode: 'AS_KNOWN', asOfMs: at('05:22') }, 'Is runway 27 clear for departure?', { idempotencyKey: 'ask-clear' });
    expect(r.status).toBe('INSUFFICIENT_CONTEXT');
    expect(r.items).toHaveLength(0);
    expect(r.note).toMatch(/does not indicate whether the runway is clear/);
  });
});
