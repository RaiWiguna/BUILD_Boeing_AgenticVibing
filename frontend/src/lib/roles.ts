import type { Role } from '@/api/types';

export const ROLE_LABEL: Record<Role, string> = {
  EVALUATOR: 'Evaluator',
  CONTROLLER_REVIEW: 'Controller review',
  OBSERVER: 'Observer',
  ADMIN: 'Administrator',
};
