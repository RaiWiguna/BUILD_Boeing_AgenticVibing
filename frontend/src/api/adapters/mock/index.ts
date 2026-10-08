import { MockApiClient } from './engine';

/** Singleton MOCK backend for the frontend-only track. */
export const mockApi = new MockApiClient();
export const mockStream = mockApi.stream;
export { mockControl } from './control';
export { DEMO_PASSWORD } from './seed/accounts';
