import type { ReactNode } from 'react';
import { mockApi, mockStream } from '@/api/adapters/mock';
import { ApiContext } from '@/hooks/useApi';

// MOCK track: the in-process adapter. After G-BE, swap for the HTTP adapter here.
const value = { api: mockApi, stream: mockStream };

export function ApiProvider({ children }: { children: ReactNode }) {
  return <ApiContext.Provider value={value}>{children}</ApiContext.Provider>;
}
