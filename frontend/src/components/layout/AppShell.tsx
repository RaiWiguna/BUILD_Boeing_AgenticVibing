import { Menu, Search } from 'lucide-react';
import { Dialog as DialogPrimitive } from 'radix-ui';
import { useEffect, useState, type ReactNode } from 'react';
import { Link, Outlet, useLocation } from 'react-router';
import { cn } from '@/lib/utils';
import { CommandPalette } from './CommandPalette';
import { Wordmark } from './Logo';
import { Sidebar } from './Sidebar';

/** Below md: compact top bar + slide-in navigation sheet (the sidebar is hidden). */
function MobileBar({ onSearch }: { onSearch: () => void }) {
  const [open, setOpen] = useState(false);
  const { pathname } = useLocation();
  const [lastPath, setLastPath] = useState(pathname);
  if (lastPath !== pathname) {
    setLastPath(pathname);
    if (open) setOpen(false);
  }
  return (
    <div className="sticky top-0 z-40 flex h-14 items-center justify-between border-b border-hairline-soft bg-canvas/90 px-4 backdrop-blur md:hidden">
      <Link to="/sessions" aria-label="FlowLens home" className="rounded-[10px]">
        <Wordmark />
      </Link>
      <div className="flex items-center gap-1">
        <button type="button" onClick={onSearch} aria-label="Search" className="inline-flex size-10 items-center justify-center rounded-full text-ink-2 hover:bg-track">
          <Search className="size-5" />
        </button>
        <DialogPrimitive.Root open={open} onOpenChange={setOpen}>
          <DialogPrimitive.Trigger aria-label="Open navigation" className="inline-flex size-10 items-center justify-center rounded-full text-ink hover:bg-track">
            <Menu className="size-5" />
          </DialogPrimitive.Trigger>
          <DialogPrimitive.Portal>
            <DialogPrimitive.Overlay className="fixed inset-0 z-50 bg-[rgba(25,27,32,0.28)] data-[state=open]:animate-in data-[state=open]:fade-in-0" />
            <DialogPrimitive.Content aria-describedby={undefined} tabIndex={-1} onOpenAutoFocus={(e) => { e.preventDefault(); (e.currentTarget as HTMLElement).focus(); }} className="outline-none fixed inset-y-0 left-0 z-50 overflow-y-auto bg-canvas shadow-pop data-[state=open]:animate-in data-[state=open]:slide-in-from-left">
              <DialogPrimitive.Title className="sr-only">Navigation</DialogPrimitive.Title>
              <Sidebar collapsed={false} onToggle={() => setOpen(false)} onSearch={() => { setOpen(false); onSearch(); }} />
            </DialogPrimitive.Content>
          </DialogPrimitive.Portal>
        </DialogPrimitive.Root>
      </div>
    </div>
  );
}

const COLLAPSE_KEY = 'flowlens.sidebarCollapsed';

function readCollapsed() {
  try {
    const v = localStorage.getItem(COLLAPSE_KEY);
    if (v != null) return v === '1';
  } catch {
    /* preference only */
  }
  return typeof window !== 'undefined' && window.innerWidth < 1360;
}

export function AppShell({ devtools }: { devtools?: ReactNode }) {
  const [collapsed, setCollapsed] = useState(readCollapsed);
  const [search, setSearch] = useState(false);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        setSearch((v) => !v);
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  const toggle = () =>
    setCollapsed((v) => {
      try {
        localStorage.setItem(COLLAPSE_KEY, v ? '0' : '1');
      } catch {
        /* ignore */
      }
      return !v;
    });

  return (
    <div className="min-h-dvh bg-canvas">
      <a href="#main" className="sr-only z-50 rounded-[10px] bg-action px-4 py-2 text-on-action focus:not-sr-only focus:fixed focus:left-4 focus:top-4">
        Skip to content
      </a>
      <MobileBar onSearch={() => setSearch(true)} />
      <div className="flex">
        <div className="hidden md:block">
          <Sidebar collapsed={collapsed} onToggle={toggle} onSearch={() => setSearch(true)} />
        </div>
        <main id="main" tabIndex={-1} className={cn('min-w-0 flex-1 px-4 pb-8 pt-5 outline-none md:px-[var(--main-padding)] md:pt-7')}>
          <Outlet />
        </main>
      </div>
      <CommandPalette open={search} onOpenChange={setSearch} />
      {devtools}
    </div>
  );
}
