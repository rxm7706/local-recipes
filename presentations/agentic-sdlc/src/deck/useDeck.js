import { useCallback, useEffect, useState } from 'react';
import { slides } from '../slides/index.js';

const clamp = (n) => Math.max(0, Math.min(slides.length - 1, n));

// Parse the current slide index from the URL hash (#/7 → index 6).
function indexFromHash() {
  const m = window.location.hash.match(/^#\/(\d+)/);
  if (!m) return 0;
  return clamp(parseInt(m[1], 10) - 1);
}

// Central deck state: current slide, view mode (deck | overview | presenter),
// and all navigation. Keyboard shortcuts and hash sync live here so every
// view stays in agreement.
export function useDeck() {
  const [current, setCurrent] = useState(indexFromHash);
  const [mode, setMode] = useState('deck'); // 'deck' | 'overview' | 'presenter'

  const goto = useCallback((n) => setCurrent(clamp(n)), []);
  const next = useCallback(() => setCurrent((c) => clamp(c + 1)), []);
  const prev = useCallback(() => setCurrent((c) => clamp(c - 1)), []);

  // Keep the hash in sync (deep-linkable, survives reloads).
  useEffect(() => {
    const target = `#/${current + 1}`;
    if (window.location.hash !== target) {
      window.history.replaceState(null, '', target);
    }
  }, [current]);

  // Respond to manual hash edits / back-forward.
  useEffect(() => {
    const onHash = () => setCurrent(indexFromHash());
    window.addEventListener('hashchange', onHash);
    return () => window.removeEventListener('hashchange', onHash);
  }, []);

  // Keyboard shortcuts.
  useEffect(() => {
    const onKey = (e) => {
      const target = e.target;
      if (target && (target.isContentEditable || /^(INPUT|TEXTAREA|SELECT)$/i.test(target.tagName))) {
        return;
      }
      if (e.metaKey || e.ctrlKey || e.altKey) return;
      switch (e.key) {
        case 'ArrowRight':
        case 'PageDown':
        case ' ':
          e.preventDefault();
          next();
          break;
        case 'ArrowLeft':
        case 'PageUp':
          e.preventDefault();
          prev();
          break;
        case 'Home':
          e.preventDefault();
          goto(0);
          break;
        case 'End':
          e.preventDefault();
          goto(slides.length - 1);
          break;
        case 'o':
        case 'O':
          setMode((m) => (m === 'overview' ? 'deck' : 'overview'));
          break;
        case 's':
        case 'S':
          setMode((m) => (m === 'presenter' ? 'deck' : 'presenter'));
          break;
        case 'f':
        case 'F':
          if (document.fullscreenElement) document.exitFullscreen?.();
          else document.documentElement.requestFullscreen?.();
          break;
        case 'Escape':
          setMode('deck');
          break;
        default:
          break;
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [next, prev, goto, setMode]);

  return {
    slides,
    current,
    slide: slides[current],
    mode,
    setMode,
    goto,
    next,
    prev,
    total: slides.length,
  };
}
