import { useLayoutEffect, useRef, useState } from 'react';
import { SLIDE_WIDTH, SLIDE_HEIGHT } from '../slides/index.js';

// Observes an element's size and returns the largest scale at which a
// 1920×1080 slide fits inside it (contain), plus a ref to attach.
export function useFit(padding = 0) {
  const ref = useRef(null);
  const [scale, setScale] = useState(0.1);

  useLayoutEffect(() => {
    const el = ref.current;
    if (!el) return undefined;

    const measure = () => {
      const w = el.clientWidth - padding * 2;
      const h = el.clientHeight - padding * 2;
      if (w <= 0 || h <= 0) return;
      setScale(Math.min(w / SLIDE_WIDTH, h / SLIDE_HEIGHT));
    };

    measure();
    const ro = new ResizeObserver(measure);
    ro.observe(el);
    return () => ro.disconnect();
  }, [padding]);

  return [ref, scale];
}
