import { useCallback } from 'react';
import { useSearchParams } from 'react-router';

let returnFocus: HTMLElement | null = null;

/** Evidence drawer state lives in the URL (?evidence=) so replay position is untouched. */
export function useEvidence() {
  const [params, setParams] = useSearchParams();
  const evidenceId = params.get('evidence');
  const open = useCallback(
    (id: string) => {
      returnFocus = document.activeElement instanceof HTMLElement ? document.activeElement : null;
      setParams((p) => {
        const next = new URLSearchParams(p);
        next.set('evidence', id);
        return next;
      });
    },
    [setParams],
  );
  const close = useCallback(() => {
    setParams((p) => {
      const next = new URLSearchParams(p);
      next.delete('evidence');
      return next;
    });
  }, [setParams]);
  return { evidenceId, open, close };
}

/**
 * Returns focus to the control that opened the drawer. Called from the dialog's close-auto-focus,
 * after the focus trap is released (focusing earlier is pulled back into the closing dialog).
 */
export function restoreEvidenceFocus() {
  const target = returnFocus;
  returnFocus = null;
  if (target?.isConnected) target.focus();
  return !!target?.isConnected;
}
