import { screen, waitFor } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { axe } from 'vitest-axe';
import { mockApi } from '@/api/adapters/mock';
import { LOGIN_PATH } from '@/lib/links';
import { renderApp, renderRoutes } from './harness';

const AXE = { rules: { 'color-contrast': { enabled: false }, region: { enabled: false } } };

describe('public landing page and sign-in route', () => {
  it('renders the product introduction at / with no link into the sign-in flow', async () => {
    const { container } = await renderApp('/');
    expect(await screen.findByRole('heading', { level: 1, name: /said, heard, observed/i })).toBeInTheDocument();
    const hrefs = [...container.querySelectorAll('a')].map((a) => a.getAttribute('href') ?? '');
    expect(hrefs.length).toBeGreaterThan(0);
    expect(hrefs.every((h) => h.startsWith('#'))).toBe(true);
    expect(screen.queryByRole('link', { name: /sign in|log in|login/i })).toBeNull();
    expect(screen.queryByRole('button', { name: /sign in|log in|login/i })).toBeNull();
  });

  it('has no serious or critical axe violations', async () => {
    const { container } = await renderApp('/');
    await screen.findByRole('heading', { level: 1 });
    const results = await axe(container, AXE);
    const blocking = results.violations.filter((v) => v.impact === 'serious' || v.impact === 'critical');
    expect(blocking.map((v) => v.id)).toEqual([]);
  });

  it('sends signed-out visitors of app routes to /login-flow with next', async () => {
    await mockApi.logout();
    const { router } = renderRoutes('/help');
    await waitFor(() => expect(router.state.location.pathname).toBe(LOGIN_PATH));
    expect(router.state.location.search).toBe('?next=%2Fhelp');
    expect(await screen.findByRole('heading', { level: 1, name: 'Sign in' })).toBeInTheDocument();
  });

  it('redirects the old /login URL to /login-flow and keeps the query', async () => {
    await mockApi.logout();
    const { router } = renderRoutes('/login?next=%2Fhelp');
    await waitFor(() => expect(router.state.location.pathname).toBe(LOGIN_PATH));
    expect(router.state.location.search).toBe('?next=%2Fhelp');
  });
});
