import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render } from '@testing-library/react';
import { createMemoryRouter, RouterProvider } from 'react-router';
import { mockApi, mockControl, DEMO_PASSWORD } from '@/api/adapters/mock';
import { mid } from '@/api/adapters/mock/ids';
import { ApiProvider } from '@/app/providers/ApiProvider';
import { AuthProvider } from '@/app/providers/AuthProvider';
import { routes } from '@/app/routing/routes';
import { TooltipProvider } from '@/components/ui/tooltip';

export const S1 = mid('session:runway27');
export const F03 = mid('runway27:finding:F-03');

/** Mounts the real routes on the in-process MOCK adapter, signed in as a demo account. */
export async function renderApp(path: string, email = 'evaluator@flowlens.test') {
  mockControl.getState().set({ latencyMs: [0, 0] });
  await mockApi.login(email, DEMO_PASSWORD);
  return renderRoutes(path);
}

/** Mounts the real routes on the MOCK adapter with whatever session is current (none after logout). */
export function renderRoutes(path: string) {
  mockControl.getState().set({ latencyMs: [0, 0] });
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false, staleTime: Infinity } } });
  const router = createMemoryRouter(routes, { initialEntries: [path] });
  const utils = render(
    <QueryClientProvider client={qc}>
      <ApiProvider>
        <AuthProvider>
          <TooltipProvider delayDuration={0}>
            <RouterProvider router={router} />
          </TooltipProvider>
        </AuthProvider>
      </ApiProvider>
    </QueryClientProvider>,
  );
  return { ...utils, router };
}
