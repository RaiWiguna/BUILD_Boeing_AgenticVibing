import * as React from 'react';
import { cn } from '@/lib/utils';

const FADE = 28;

/**
 * Scroll container that fades the edge where more content is hidden, so a clipped
 * list always shows a cue that it scrolls (plus an optional "N more" hint for lists).
 */
export const ScrollArea = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement> & { as?: 'div' | 'ul' | 'ol'; moreLabel?: (hiddenBelow: boolean) => React.ReactNode }>(
  ({ className, style, children, as: As = 'div', moreLabel, onScroll, ...props }, forwarded) => {
    const ref = React.useRef<HTMLElement | null>(null);
    const [edges, setEdges] = React.useState({ top: false, bottom: false });
    const update = React.useCallback(() => {
      const el = ref.current;
      if (!el) return;
      const top = el.scrollTop > 2;
      const bottom = el.scrollTop + el.clientHeight < el.scrollHeight - 2;
      setEdges((e) => (e.top === top && e.bottom === bottom ? e : { top, bottom }));
    }, []);
    React.useLayoutEffect(() => {
      const el = ref.current;
      if (!el) return;
      update();
      const ro = new ResizeObserver(update);
      ro.observe(el);
      for (const child of Array.from(el.children)) ro.observe(child);
      const mo = new MutationObserver(update);
      mo.observe(el, { childList: true, subtree: true });
      return () => {
        ro.disconnect();
        mo.disconnect();
      };
    }, [update]);
    const mask = edges.top || edges.bottom ? `linear-gradient(to bottom, ${edges.top ? `transparent, #000 ${FADE}px` : '#000'}, ${edges.bottom ? `#000 calc(100% - ${FADE}px), transparent` : '#000'})` : undefined;
    const setRef = (el: HTMLElement | null) => {
      ref.current = el;
      if (typeof forwarded === 'function') forwarded(el as HTMLDivElement);
      else if (forwarded) forwarded.current = el as HTMLDivElement;
    };
    // Polymorphic list/div host; typed as div because only shared attributes are used.
    const Host = As as 'div';
    return (
      <>
        <Host
          ref={setRef}
          onScroll={(e: React.UIEvent<HTMLDivElement>) => {
            update();
            onScroll?.(e);
          }}
          className={cn('overflow-y-auto overscroll-contain scrollbar-thin', className)}
          style={{ ...style, maskImage: mask, WebkitMaskImage: mask }}
          {...props}
        >
          {children}
        </Host>
        {moreLabel && edges.bottom && moreLabel(true)}
      </>
    );
  },
);
ScrollArea.displayName = 'ScrollArea';
