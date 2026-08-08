import { useEffect, useId, useRef, useState } from 'react';

const SHOW_DELAY_MS = 200;

/**
 * Wraps a single interactive child with a hover/focus tooltip. Story 7.2 AC:
 * appears after a 200ms hover delay, disappears on blur/mouse leave, and is
 * reachable by keyboard (Tab to focus shows it immediately -- no delay on
 * focus, since a keyboard user has already committed to the element).
 */
export default function Tooltip({ label, children }) {
  const [visible, setVisible] = useState(false);
  const timerRef = useRef(null);
  const wrapRef = useRef(null);
  const tooltipId = useId();

  const clearTimer = () => {
    if (timerRef.current) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }
  };

  // Regression: a pending show(200) timer that fires after this component
  // unmounts called setVisible on an unmounted component. Harmless today
  // (every Tooltip usage stays mounted for the app's lifetime), but a real
  // gap the moment a future story renders one inside conditionally-mounted
  // content.
  useEffect(() => clearTimer, []);

  const show = (delay) => {
    clearTimer();
    if (delay) {
      timerRef.current = setTimeout(() => setVisible(true), delay);
    } else {
      setVisible(true);
    }
  };

  const hide = () => {
    clearTimer();
    setVisible(false);
  };

  // Regression: a stray mouseleave (mouse moves onto and off the element
  // without touching focus) hid a tooltip that was shown because the
  // element was focused -- the visible tooltip state stopped matching the
  // documented focus-based trigger for any user with both a mouse and
  // keyboard. Only hide on mouse-leave when focus isn't still inside.
  const hideUnlessFocused = () => {
    if (wrapRef.current && wrapRef.current.contains(document.activeElement)) {
      return;
    }
    hide();
  };

  return (
    <span
      ref={wrapRef}
      className="tooltip-wrap"
      onMouseEnter={() => show(SHOW_DELAY_MS)}
      onMouseLeave={hideUnlessFocused}
      onFocus={() => show(0)}
      onBlur={hide}
    >
      {typeof children === 'function'
        ? children({ 'aria-describedby': tooltipId })
        : children}
      {visible ? (
        <span role="tooltip" id={tooltipId} className="tooltip-bubble">
          {label}
        </span>
      ) : null}
    </span>
  );
}
