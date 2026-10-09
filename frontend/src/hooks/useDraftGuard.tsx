import { useEffect } from 'react';
import { useBlocker, type Location } from 'react-router';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogFooter } from '@/components/ui/dialog';

/** Params that change what is being edited; replay `t` writes never count as leaving. */
const FOCUS = ['finding', 'segment', 'option', 'run', 'mode'];
const leaving = (a: Location, b: Location) => {
  if (a.pathname !== b.pathname) return true;
  const pa = new URLSearchParams(a.search);
  const pb = new URLSearchParams(b.search);
  return FOCUS.some((k) => pa.get(k) !== pb.get(k));
};

/**
 * Keeps an unsaved review, rating or correction from being lost: in-app navigation asks
 * "Discard draft?", and closing or reloading the tab triggers the browser's own prompt.
 */
export function useDraftGuard(dirty: boolean) {
  const blocker = useBlocker(({ currentLocation, nextLocation }) => dirty && leaving(currentLocation, nextLocation));
  useEffect(() => {
    if (!dirty) return;
    const onUnload = (e: BeforeUnloadEvent) => {
      e.preventDefault();
      e.returnValue = '';
    };
    window.addEventListener('beforeunload', onUnload);
    return () => window.removeEventListener('beforeunload', onUnload);
  }, [dirty]);
  return blocker;
}

export function DraftGuard({ dirty, what = 'draft' }: { dirty: boolean; what?: string }) {
  const blocker = useDraftGuard(dirty);
  const open = blocker.state === 'blocked';
  return (
    <Dialog open={open} onOpenChange={(v) => !v && blocker.reset?.()}>
      {open && (
        <DialogContent title="Discard draft?" description={`Your unsaved ${what} will be lost. Saved revisions are not affected.`} hideClose>
          <DialogFooter>
            <Button variant="secondary" onClick={() => blocker.reset?.()}>
              Keep editing
            </Button>
            <Button variant="danger" onClick={() => blocker.proceed?.()}>
              Discard draft
            </Button>
          </DialogFooter>
        </DialogContent>
      )}
    </Dialog>
  );
}
