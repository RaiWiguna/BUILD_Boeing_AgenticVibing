import type { Account, Capability, Role } from '../../../types';
import { mid } from '../ids';

export const ROLE_CAPABILITIES: Record<Role, Capability[]> = {
  EVALUATOR: ['session.read', 'session.import', 'analysis.create', 'audio.play', 'review.write', 'export.create'],
  CONTROLLER_REVIEW: ['session.read', 'audio.play', 'review.write'],
  OBSERVER: ['session.read'],
  ADMIN: ['session.read', 'session.import', 'analysis.create', 'audio.play', 'export.create', 'admin.manage'],
};

export const ROLE_LABEL: Record<Role, string> = {
  EVALUATOR: 'Evaluator',
  CONTROLLER_REVIEW: 'Controller review',
  OBSERVER: 'Observer',
  ADMIN: 'Administrator',
};

/** MOCK demo accounts. Password for every demo account is shown on the login screen (MOCK only). */
export const DEMO_PASSWORD = 'flowlens-demo';

export const ACCOUNTS: Account[] = [
  { id: mid('acct:dana'), name: 'Dana Whitfield', email: 'evaluator@flowlens.test', role: 'EVALUATOR', active: true, last_login_at: '2026-10-08T13:40:00Z', must_change_password: false },
  { id: mid('acct:sam'), name: 'Sam Ortiz', email: 'controller@flowlens.test', role: 'CONTROLLER_REVIEW', active: true, last_login_at: '2026-10-07T09:12:00Z', must_change_password: false },
  { id: mid('acct:ira'), name: 'Ira Santoso', email: 'observer@flowlens.test', role: 'OBSERVER', active: true, last_login_at: '2026-10-06T16:30:00Z', must_change_password: false },
  { id: mid('acct:nizam'), name: 'Nizam Rahman', email: 'admin@flowlens.test', role: 'ADMIN', active: true, last_login_at: '2026-10-08T08:02:00Z', must_change_password: false },
  { id: mid('acct:tyler'), name: 'Tyler Brooks', email: 'tyler@flowlens.test', role: 'EVALUATOR', active: false, last_login_at: '2026-09-21T11:00:00Z', must_change_password: true },
];
