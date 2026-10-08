import { DropdownMenu as M, Popover as P } from 'radix-ui';
import * as React from 'react';
import { cn } from '@/lib/utils';

export const DropdownMenu = M.Root;
export const DropdownMenuTrigger = M.Trigger;
export const DropdownMenuGroup = M.Group;

export function DropdownMenuContent({ className, align = 'end', sideOffset = 8, ...props }: React.ComponentPropsWithoutRef<typeof M.Content>) {
  return (
    <M.Portal>
      <M.Content align={align} sideOffset={sideOffset} className={cn('z-50 min-w-[220px] rounded-[16px] border border-hairline-soft bg-surface p-1.5 shadow-pop data-[state=open]:animate-in data-[state=open]:fade-in-0 data-[state=open]:zoom-in-[0.98]', className)} {...props} />
    </M.Portal>
  );
}

export function DropdownMenuItem({ className, ...props }: React.ComponentPropsWithoutRef<typeof M.Item>) {
  return <M.Item className={cn('flex h-10 cursor-pointer select-none items-center gap-2.5 rounded-[10px] px-3 text-[14px] text-ink outline-none data-[disabled]:cursor-not-allowed data-[disabled]:text-ink-3 data-[highlighted]:bg-track [&_svg]:size-4 [&_svg]:text-ink-2', className)} {...props} />;
}

export function DropdownMenuLabel({ className, ...props }: React.ComponentPropsWithoutRef<typeof M.Label>) {
  return <M.Label className={cn('px-3 pb-1 pt-2 text-[12px] font-medium uppercase tracking-[0.04em] text-ink-3', className)} {...props} />;
}

export function DropdownMenuSeparator() {
  return <M.Separator className="mx-1.5 my-1.5 h-px bg-hairline" />;
}

export const DropdownMenuRadioGroup = M.RadioGroup;
export function DropdownMenuRadioItem({ className, children, ...props }: React.ComponentPropsWithoutRef<typeof M.RadioItem>) {
  return (
    <M.RadioItem className={cn('flex h-10 cursor-pointer select-none items-center gap-2.5 rounded-[10px] px-3 text-[14px] text-ink outline-none data-[highlighted]:bg-track', className)} {...props}>
      <span className="flex size-4 items-center justify-center rounded-full border border-boundary">
        <M.ItemIndicator className="size-2 rounded-full bg-data" />
      </span>
      {children}
    </M.RadioItem>
  );
}

export const Popover = P.Root;
export const PopoverTrigger = P.Trigger;
export const PopoverAnchor = P.Anchor;
export function PopoverContent({ className, align = 'end', sideOffset = 8, ...props }: React.ComponentPropsWithoutRef<typeof P.Content>) {
  return (
    <P.Portal>
      <P.Content align={align} sideOffset={sideOffset} className={cn('z-50 rounded-[20px] border border-hairline-soft bg-surface shadow-pop outline-none data-[state=open]:animate-in data-[state=open]:fade-in-0 data-[state=open]:zoom-in-[0.98]', className)} {...props} />
    </P.Portal>
  );
}
