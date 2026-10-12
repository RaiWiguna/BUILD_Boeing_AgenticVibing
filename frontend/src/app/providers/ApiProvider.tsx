import type { ReactNode } from 'react';
import { demoPort, hybridApi } from '@/api/adapters/demo';
import { mockStream } from '@/api/adapters/mock';
import { ApiContext } from '@/hooks/useApi';

// MOCK track: the in-process adapter, plus demo backend workspaces (DEMO track, ADR 0003).
// After G-BE, swap for the HTTP adapter here.
const value = { api: hybridApi, stream: mockStream, demo: demoPort };

export function ApiProvider({ children }: { children: ReactNode }) {
  return <ApiContext.Provider value={value}>{children}</ApiContext.Provider>;
}
