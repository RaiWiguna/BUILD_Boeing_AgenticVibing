import { MutationCache, QueryCache, QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { Toaster } from 'sonner';
import { hasCode } from '@/api/errors';
import { qk } from '@/api/queryKeys';
import { TooltipProvider } from '@/components/ui/tooltip';
import { ApiProvider } from './ApiProvider';
import { AuthProvider } from './AuthProvider';

function onAuthError(error: unknown) {
  if (hasCode(error, 'AUTH_REQUIRED')) queryClient.setQueryData(qk.auth, null);
}

export const queryClient = new QueryClient({
  queryCache: new QueryCache({ onError: onAuthError }),
  mutationCache: new MutationCache({ onError: onAuthError }),
  defaultOptions: {
    queries: {
      staleTime: 15_000,
      refetchOnWindowFocus: false,
      // Typed denials/not-found are final answers; never retry them into an empty success.
      retry: (count, error) => !hasCode(error, 'ACCESS_DENIED', 'NOT_FOUND', 'AUTH_REQUIRED', 'EVIDENCE_UNAVAILABLE') && count < 1,
    },
  },
});

export function AppProviders({ children }: { children: ReactNode }) {
  return (
    <QueryClientProvider client={queryClient}>
      <ApiProvider>
        <AuthProvider>
          <TooltipProvider delayDuration={250}>
            {children}
            <Toaster
              position="bottom-right"
              offset={20}
              toastOptions={{
                classNames: {
                  toast: '!rounded-[16px] !border !border-hairline-soft !bg-surface !shadow-pop !font-sans !text-[14px] !text-ink',
                  description: '!text-ink-2',
                },
              }}
            />
          </TooltipProvider>
        </AuthProvider>
      </ApiProvider>
    </QueryClientProvider>
  );
}
