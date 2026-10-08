import { useQuery } from '@tanstack/react-query';
import { Check, FlaskConical, LogOut, MoreHorizontal, UserRound } from 'lucide-react';
import { useNavigate } from 'react-router';
import { toast } from 'sonner';
import { DEMO_ACCOUNT_PASSWORD as DEMO_PASSWORD } from '@/app/devtools/demo';
import { ROLE_LABEL } from '@/lib/roles';
import { useAuth } from '@/app/providers/AuthProvider';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuTrigger } from '@/components/ui/menu';
import { useApi } from '@/hooks/useApi';
import { cn } from '@/lib/utils';

export function Avatar({ name, className }: { name: string; className?: string }) {
  const initials = name.split(' ').map((p) => p[0]).slice(0, 2).join('');
  return (
    <span aria-hidden className={cn('relative inline-flex size-10 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-[#dfe9ff] to-[#f6d9e8] text-[14px] font-semibold text-[#2a3150] ring-2 ring-white shadow-[0_0_0_1px_rgba(25,27,32,0.08)]', className)}>
      {initials}
    </span>
  );
}

export function UserMenu({ collapsed }: { collapsed: boolean }) {
  const { session, login, logout } = useAuth();
  const api = useApi();
  const navigate = useNavigate();
  const demo = useQuery({ queryKey: ['demo-accounts'], queryFn: () => api.demoAccounts(), staleTime: Infinity });
  if (!session) return null;
  const { account } = session;
  const switchTo = async (email: string) => {
    try {
      const next = await login(email, DEMO_PASSWORD);
      toast.success(`Signed in as ${ROLE_LABEL[next.account.role]}`, { description: 'Cached session data was cleared for the new account.' });
      navigate('/sessions');
    } catch (e) {
      toast.error('Could not switch account', { description: e instanceof Error ? e.message : undefined });
    }
  };
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <button type="button" aria-label="Account menu" className={cn('flex w-full items-center gap-3 rounded-[14px] p-1.5 text-left transition-colors hover:bg-[#eceef1] data-[state=open]:bg-[#eceef1]', collapsed && 'justify-center')}>
          <Avatar name={account.name} />
          {!collapsed && (
            <>
              <span className="min-w-0 flex-1">
                <span className="block truncate text-[15px] font-semibold text-ink">{account.name}</span>
                <span className="block truncate text-[13px] text-ink-2">{ROLE_LABEL[account.role]} · Research workspace</span>
              </span>
              <MoreHorizontal aria-hidden className="size-[18px] shrink-0 text-ink-2" />
            </>
          )}
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent side="right" align="end" sideOffset={14} className="w-[280px]">
        <div className="px-3 pb-2 pt-2.5">
          <p className="text-[14px] font-semibold text-ink">{account.name}</p>
          <p className="text-[13px] text-ink-2">{account.email}</p>
        </div>
        <DropdownMenuSeparator />
        <DropdownMenuLabel className="flex items-center gap-1.5">
          <FlaskConical className="size-3" /> Switch role · MOCK demo
        </DropdownMenuLabel>
        {(demo.data ?? []).map((d) => (
          <DropdownMenuItem key={d.email} onSelect={() => d.email !== account.email && switchTo(d.email)}>
            <UserRound />
            <span className="flex-1">
              {ROLE_LABEL[d.role]}
              <span className="block text-[12px] text-ink-3">{d.name}</span>
            </span>
            {d.email === account.email && <Check className="!text-data" />}
          </DropdownMenuItem>
        ))}
        <DropdownMenuSeparator />
        <DropdownMenuItem
          onSelect={async () => {
            await logout();
            navigate('/login');
          }}
        >
          <LogOut /> Sign out
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
