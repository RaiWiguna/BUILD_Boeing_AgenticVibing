/**
 * MOCK control state — simulates server/provider/network conditions for demos and tests.
 * Only the dev Mock Control panel (src/app/devtools) and the mock adapter read this.
 */
import { createStore } from 'zustand/vanilla';

export interface MockScenarioFlags {
  providerOutage: boolean;
  connectionLost: boolean;
  versionConflictNext: boolean;
  audioAccessDenied: boolean;
  emptyCatalogue: boolean;
  diskHighWater: boolean;
  staleTracks: boolean;
  sessionExpired: boolean;
}

export interface MockControlState extends MockScenarioFlags {
  latencyMs: [number, number];
  set: (patch: Partial<MockControlState>) => void;
  reset: () => void;
  resetDataNonce: number;
}

const DEFAULT_FLAGS: MockScenarioFlags = {
  providerOutage: false,
  connectionLost: false,
  versionConflictNext: false,
  audioAccessDenied: false,
  emptyCatalogue: false,
  diskHighWater: false,
  staleTracks: false,
  sessionExpired: false,
};

export const mockControl = createStore<MockControlState>((set) => ({
  ...DEFAULT_FLAGS,
  latencyMs: [120, 420],
  resetDataNonce: 0,
  set: (patch) => set(patch),
  reset: () => set((s) => ({ ...DEFAULT_FLAGS, latencyMs: [120, 420], resetDataNonce: s.resetDataNonce + 1 })),
}));

export function delay() {
  const [min, max] = mockControl.getState().latencyMs;
  const ms = min + Math.random() * Math.max(0, max - min);
  return new Promise<void>((resolve) => setTimeout(resolve, ms));
}
