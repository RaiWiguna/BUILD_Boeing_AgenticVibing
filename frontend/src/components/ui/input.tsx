import * as React from 'react';
import { cn } from '@/lib/utils';

export const Input = React.forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement>>(({ className, ...props }, ref) => (
  <input
    ref={ref}
    className={cn(
      'h-11 w-full rounded-control border border-hairline-strong bg-surface px-3.5 text-[15px] text-ink shadow-[inset_0_1px_1px_rgba(25,27,32,0.02)] placeholder:text-ink-3 transition-colors duration-[140ms] hover:border-[#c6ccd4] focus-visible:border-data focus-visible:outline-none focus-visible:ring-[3px] focus-visible:ring-data/15 disabled:bg-sunken disabled:text-ink-3 aria-[invalid=true]:border-discrepancy',
      className,
    )}
    {...props}
  />
));
Input.displayName = 'Input';

export const Textarea = React.forwardRef<HTMLTextAreaElement, React.TextareaHTMLAttributes<HTMLTextAreaElement>>(({ className, ...props }, ref) => (
  <textarea
    ref={ref}
    className={cn(
      'min-h-[92px] w-full resize-y rounded-control border border-hairline-strong bg-surface px-3.5 py-3 text-[15px] leading-relaxed text-ink placeholder:text-ink-3 transition-colors duration-[140ms] hover:border-[#c6ccd4] focus-visible:border-data focus-visible:outline-none focus-visible:ring-[3px] focus-visible:ring-data/15 disabled:bg-sunken disabled:text-ink-3 aria-[invalid=true]:border-discrepancy',
      className,
    )}
    {...props}
  />
));
Textarea.displayName = 'Textarea';

export function Label({ className, ...props }: React.LabelHTMLAttributes<HTMLLabelElement>) {
  return <label className={cn('text-[14px] font-medium text-ink', className)} {...props} />;
}

export function Kbd({ className, ...props }: React.HTMLAttributes<HTMLElement>) {
  return <kbd className={cn('inline-flex h-6 min-w-6 items-center justify-center rounded-[7px] bg-track px-1.5 font-sans text-[12px] font-medium text-ink-2', className)} {...props} />;
}
