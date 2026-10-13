import { useEffect, useRef, type CSSProperties, type ElementType, type ReactNode } from 'react';
import { cn } from '@/lib/utils';

/**
 * Fades a block in once it enters the viewport. Used to pace the landing page story;
 * under prefers-reduced-motion the block is shown immediately (see `.reveal` in globals.css).
 */
export function Reveal({ as: Tag = 'div', delay = 0, className, children, ...rest }: { as?: ElementType; delay?: number; className?: string; children: ReactNode; id?: string }) {
  const ref = useRef<HTMLElement>(null);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    // The DOM attribute is the only state; setting it directly avoids a re-render per block.
    const show = () => el.setAttribute('data-shown', '');
    if (typeof IntersectionObserver === 'undefined') {
      show();
      return;
    }
    const io = new IntersectionObserver(
      ([entry]) => {
        if (entry?.isIntersecting) {
          show();
          io.disconnect();
        }
      },
      { rootMargin: '0px 0px -8% 0px', threshold: 0.12 },
    );
    io.observe(el);
    return () => io.disconnect();
  }, []);

  return (
    <Tag ref={ref} style={{ '--reveal-delay': `${delay}ms` } as CSSProperties} className={cn('reveal', className)} {...rest}>
      {children}
    </Tag>
  );
}
