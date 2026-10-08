import { Tabs as TabsPrimitive } from 'radix-ui';
import * as React from 'react';
import { cn } from '@/lib/utils';

export const Tabs = TabsPrimitive.Root;
export const TabsContent = React.forwardRef<HTMLDivElement, React.ComponentPropsWithoutRef<typeof TabsPrimitive.Content>>(({ className, ...props }, ref) => (
  <TabsPrimitive.Content ref={ref} className={cn('focus-visible:outline-none', className)} {...props} />
));
TabsContent.displayName = 'TabsContent';

/** Underline tabs (Transcript / Findings / Options). */
export const TabsList = React.forwardRef<HTMLDivElement, React.ComponentPropsWithoutRef<typeof TabsPrimitive.List>>(({ className, ...props }, ref) => (
  <TabsPrimitive.List ref={ref} className={cn('flex items-center gap-1 border-b border-hairline', className)} {...props} />
));
TabsList.displayName = 'TabsList';

export const TabsTrigger = React.forwardRef<HTMLButtonElement, React.ComponentPropsWithoutRef<typeof TabsPrimitive.Trigger>>(({ className, ...props }, ref) => (
  <TabsPrimitive.Trigger
    ref={ref}
    className={cn(
      'relative -mb-px inline-flex h-11 items-center gap-2 px-4 text-[15px] font-medium text-ink-2 transition-colors duration-[140ms] hover:text-ink data-[state=active]:text-data after:absolute after:inset-x-2 after:-bottom-px after:h-[2px] after:rounded-full after:bg-transparent data-[state=active]:after:bg-data',
      className,
    )}
    {...props}
  />
));
TabsTrigger.displayName = 'TabsTrigger';

/** Pill tabs inside a tinted track (Findings 3 / Open loops 2). */
export const PillTabsList = React.forwardRef<HTMLDivElement, React.ComponentPropsWithoutRef<typeof TabsPrimitive.List>>(({ className, ...props }, ref) => (
  <TabsPrimitive.List ref={ref} className={cn('grid auto-cols-fr grid-flow-col gap-1 rounded-[14px] bg-track p-1', className)} {...props} />
));
PillTabsList.displayName = 'PillTabsList';

export const PillTabsTrigger = React.forwardRef<HTMLButtonElement, React.ComponentPropsWithoutRef<typeof TabsPrimitive.Trigger>>(({ className, ...props }, ref) => (
  <TabsPrimitive.Trigger
    ref={ref}
    className={cn(
      'inline-flex h-9 items-center justify-center gap-2 rounded-[10px] px-3 text-[14px] font-medium text-ink-2 transition-[background-color,color,box-shadow] duration-[140ms] hover:text-ink data-[state=active]:bg-surface data-[state=active]:text-ink data-[state=active]:shadow-control',
      className,
    )}
    {...props}
  />
));
PillTabsTrigger.displayName = 'PillTabsTrigger';
