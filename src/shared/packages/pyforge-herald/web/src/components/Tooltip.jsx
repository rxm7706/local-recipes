import { useId, useRef, useState } from 'react';

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
  const tooltipId = useId();

  const clearTimer = () => {
    if (timerRef.current) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }
  };

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

  return (
    <span
      className="tooltip-wrap"
      onMouseEnter={() => show(SHOW_DELAY_MS)}
      onMouseLeave={hide}
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
