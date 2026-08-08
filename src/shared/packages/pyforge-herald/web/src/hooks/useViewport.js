import { useEffect, useState } from 'react';

// Breakpoints per Story 7.1's AC: desktop >=1200px (full sidebar), tablet
// 768-1200px (sidebar collapses to hamburger), mobile <768px (stacked).
export const BREAKPOINT_TABLET = 768;
export const BREAKPOINT_DESKTOP = 1200;

function classify(width) {
  if (width >= BREAKPOINT_DESKTOP) return 'desktop';
  if (width >= BREAKPOINT_TABLET) return 'tablet';
  return 'mobile';
}

/** Tracks the current viewport class (desktop/tablet/mobile) on resize. */
export function useViewport() {
  const [viewport, setViewport] = useState(() =>
    classify(typeof window !== 'undefined' ? window.innerWidth : BREAKPOINT_DESKTOP),
  );

  useEffect(() => {
    const onResize = () => setViewport(classify(window.innerWidth));
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, []);

  return viewport;
}
