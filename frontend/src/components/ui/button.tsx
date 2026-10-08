import { cva, type VariantProps } from 'class-variance-authority';
import { Slot } from 'radix-ui';
import * as React from 'react';
import { cn } from '@/lib/utils';

export const buttonVariants = cva(
  'inline-flex shrink-0 items-center justify-center gap-2 whitespace-nowrap rounded-control text-[15px] font-medium tracking-[-0.005em] transition-[background-color,box-shadow,color,border-color] duration-[140ms] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus disabled:pointer-events-none disabled:opacity-100 [&_svg]:pointer-events-none [&_svg]:size-[18px] [&_svg]:shrink-0',
  {
    variants: {
      variant: {
        primary: 'bg-action text-on-action shadow-action hover:bg-action-hover disabled:bg-track disabled:text-ink-3 disabled:shadow-none',
        secondary: 'bg-surface text-ink border border-hairline shadow-control hover:bg-sunken disabled:text-ink-3 disabled:bg-sunken',
        tonal: 'bg-track text-ink hover:bg-[#e6e9ec] disabled:text-ink-3',
        ghost: 'text-ink-2 hover:bg-track hover:text-ink disabled:text-ink-3',
        data: 'bg-data-tint text-data-strong hover:bg-data-soft disabled:text-ink-3',
        link: 'h-auto px-0 text-data hover:underline underline-offset-4',
        danger: 'bg-surface text-discrepancy border border-hairline hover:bg-discrepancy-tint',
      },
      size: {
        default: 'h-11 px-[18px]',
        sm: 'h-9 px-3.5 text-[14px] rounded-[10px] [&_svg]:size-4',
        xs: 'h-7 px-2.5 text-[13px] rounded-[8px] gap-1.5 [&_svg]:size-3.5',
        lg: 'h-12 px-6',
        icon: 'size-10 rounded-full',
        'icon-sm': 'size-8 rounded-full [&_svg]:size-4',
      },
    },
    defaultVariants: { variant: 'secondary', size: 'default' },
  },
);

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement>, VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(({ className, variant, size, asChild = false, type, ...props }, ref) => {
  const Comp = asChild ? Slot.Root : 'button';
  return <Comp ref={ref} type={asChild ? undefined : (type ?? 'button')} className={cn(buttonVariants({ variant, size }), className)} {...props} />;
});
Button.displayName = 'Button';
