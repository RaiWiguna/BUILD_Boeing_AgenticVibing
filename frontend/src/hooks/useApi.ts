import { createContext, useContext } from 'react';
import type { ApiClient, StreamClient } from '@/api/client';
import type { DemoPort } from '@/api/demo';

export const ApiContext = createContext<{ api: ApiClient; stream: StreamClient; demo: DemoPort } | null>(null);

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

/** DEMO track port (ADR 0003): named workspaces on the local demo backend. */
export function useDemo() {
  const ctx = useContext(ApiContext);
  if (!ctx) throw new Error('ApiContext missing');
  return ctx.demo;
}
