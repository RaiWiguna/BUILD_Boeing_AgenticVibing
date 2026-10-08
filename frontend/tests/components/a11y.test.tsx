import { screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { axe } from 'vitest-axe';
import { renderApp, S1 } from './harness';

// jsdom does not lay out or paint: contrast and landmark rules are checked by token review and in the browser.
const AXE = { rules: { 'color-contrast': { enabled: false }, region: { enabled: false } } };
const BLOCKING = new Set(['serious', 'critical']);

const EVALUATOR_ROUTES = [
  '/sessions',
  '/sessions/import',
  `/s/${S1}/workspace?t=322000`,
  `/s/${S1}/memory?mode=debrief&t=400000`,
  `/s/${S1}/memory/runway?t=322000`,
  `/s/${S1}/review/transcript?mode=debrief&t=322000`,
  `/s/${S1}/review/findings?mode=debrief&t=322000`,
  `/s/${S1}/review/options?mode=debrief&t=322000`,
  `/s/${S1}/debrief`,
  `/s/${S1}/metrics?t=322000`,
  `/s/${S1}/ask?t=322000`,
  '/settings/account',
  '/help',
];
const ADMIN_ROUTES = ['/settings/users', '/settings/access', '/settings/providers', '/settings/jobs', '/settings/storage', '/settings/audit', '/settings/retention'];

async function expectNoBlockingViolations(path: string, email?: string) {
  const { container } = await renderApp(path, email);
  await screen.findByRole('heading', { level: 1 }, { timeout: 5000 });
  // Let lazy panels and queries settle before scanning.
  await new Promise((r) => setTimeout(r, 400));
  const results = await axe(container, AXE);
  const blocking = results.violations.filter((v) => BLOCKING.has(v.impact ?? ''));
  expect(blocking.map((v) => `${v.id}: ${v.nodes.map((n) => n.target.join(' ')).join(', ')}`)).toEqual([]);
}

describe('accessibility · no serious/critical axe violations per route (MOCK)', () => {
  it.each(EVALUATOR_ROUTES)('evaluator %s', async (path) => {
    await expectNoBlockingViolations(path);
  });

  it.each(ADMIN_ROUTES)('admin %s', async (path) => {
    await expectNoBlockingViolations(path, 'admin@flowlens.test');
  });
});
