import type { DemoPort } from '../../demo';
import { mockApi } from '../mock';
import { demoApi } from './client';
import { createHybridClient, registerDemoWorkspace } from './hybrid';

/** MOCK engine + demo backend workspaces (DEMO track, ADR 0003). */
export const hybridApi = createHybridClient(mockApi);

export const demoPort: DemoPort = {
  health: demoApi.health,
  scenarios: demoApi.scenarios,
  listWorkspaces: demoApi.listWorkspaces,
  getWorkspace: demoApi.getWorkspace,
  createWorkspace: demoApi.createWorkspace,
  savePlayback: demoApi.savePlayback,
  registerWorkspace: async (id) => {
    await registerDemoWorkspace(mockApi, id);
  },
  rememberPlayback: (id, cursorMs) => mockApi.setExternalCursor(id, cursorMs),
};
