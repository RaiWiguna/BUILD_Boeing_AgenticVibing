import { Dialog as DialogPrimitive } from 'radix-ui';
import { X } from 'lucide-react';
import * as React from 'react';
import { cn } from '@/lib/utils';

export const Sheet = DialogPrimitive.Root;
export const SheetTrigger = DialogPrimitive.Trigger;

/** Right-side panel for secondary tasks (e.g. export) that should not take page space. */
export function SheetContent({ title, description, className, children, ...props }: React.ComponentPropsWithoutRef<typeof DialogPrimitive.Content> & { title: React.ReactNode; description?: React.ReactNode }) {
  return (
    <DialogPrimitive.Portal>
      <DialogPrimitive.Overlay className="fixed inset-0 z-50 bg-[rgba(25,27,32,0.24)] data-[state=open]:animate-in data-[state=open]:fade-in-0" />
      <DialogPrimitive.Content
        className={cn('fixed inset-y-0 right-0 z-50 flex w-[min(460px,100vw)] flex-col border-l border-hairline-soft bg-surface shadow-pop outline-none data-[state=open]:animate-in data-[state=open]:slide-in-from-right motion-reduce:animate-none', className)}
        {...props}
      >
        <div className="flex items-start justify-between gap-3 border-b border-hairline-soft px-6 py-5">
          <div className="min-w-0">
            <DialogPrimitive.Title className="text-[22px] font-semibold tracking-[-0.025em] text-ink">{title}</DialogPrimitive.Title>
            {description ? <DialogPrimitive.Description className="mt-1 text-[14px] text-ink-2">{description}</DialogPrimitive.Description> : <DialogPrimitive.Description className="sr-only">{typeof title === 'string' ? title : 'Panel'}</DialogPrimitive.Description>}
          </div>
          <DialogPrimitive.Close aria-label="Close" className="inline-flex size-9 shrink-0 items-center justify-center rounded-full text-ink-2 transition-colors hover:bg-track hover:text-ink">
            <X className="size-[18px]" />
          </DialogPrimitive.Close>
        </div>
        <div className="flex-1 overflow-y-auto overscroll-contain px-6 py-5 scrollbar-thin">{children}</div>
      </DialogPrimitive.Content>
    </DialogPrimitive.Portal>
  );
}
