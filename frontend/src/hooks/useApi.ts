import { createContext, useContext } from 'react';
import type { ApiClient, StreamClient } from '@/api/client';

export const ApiContext = createContext<{ api: ApiClient; stream: StreamClient } | null>(null);

export function useApi() {
  const ctx = useContext(ApiContext);
  if (!ctx) throw new Error('ApiContext missing');
  return ctx.api;
}

export function useStreamClient() {
  const ctx = useContext(ApiContext);
  if (!ctx) throw new Error('ApiContext missing');
  return ctx.stream;
}
