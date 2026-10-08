import { Dialog as DialogPrimitive } from 'radix-ui';
import { restoreEvidenceFocus, useEvidence } from '@/hooks/useEvidence';
import { EvidencePanel } from './EvidencePanel';

/**
 * Evidence drawer driven by ?evidence=. Opening it never moves the replay clock;
 * closing returns focus to the control that opened it.
 */
export function EvidenceDrawer() {
  const { evidenceId, close } = useEvidence();
  return (
    <DialogPrimitive.Root open={!!evidenceId} onOpenChange={(o) => !o && close()}>
      <DialogPrimitive.Portal>
        <DialogPrimitive.Overlay className="fixed inset-0 z-40 bg-[rgba(25,27,32,0.18)] data-[state=open]:animate-in data-[state=open]:fade-in-0 data-[state=closed]:animate-out data-[state=closed]:fade-out-0" />
        <DialogPrimitive.Content
          aria-labelledby="drawer-evidence-title"
          aria-describedby={undefined}
          onCloseAutoFocus={(e) => {
            e.preventDefault();
            restoreEvidenceFocus();
          }}
          className="fixed inset-y-2 right-2 z-50 flex w-[min(600px,calc(100vw-16px))] flex-col overflow-hidden rounded-[26px] border border-hairline-soft bg-surface shadow-pop outline-none data-[state=open]:animate-in data-[state=open]:slide-in-from-right-8 data-[state=open]:fade-in-0 data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=closed]:slide-out-to-right-8 sm:inset-y-3 sm:right-3"
        >
          <DialogPrimitive.Title className="sr-only">Evidence</DialogPrimitive.Title>
          <div className="scrollbar-thin min-h-0 flex-1 overflow-y-auto p-5 sm:p-6">{evidenceId && <EvidencePanel id={evidenceId} onClose={close} headingId="drawer-evidence-title" />}</div>
        </DialogPrimitive.Content>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  );
}
