import { useId, useState } from 'react';

/**
 * A "?" affordance next to a complex field. Clicking (or Enter/Space via
 * keyboard) expands an inline explanation -- Story 7.2 AC ("Date range
 * format" help explaining YYYY-MM-DD syntax is the worked example).
 */
export default function HelpIcon({ label, children }) {
  const [expanded, setExpanded] = useState(false);
  const panelId = useId();

  return (
    <span className="help-icon-wrap">
      <button
        type="button"
        className="help-icon"
        aria-expanded={expanded}
        aria-controls={panelId}
        aria-label={label}
        onClick={() => setExpanded((prev) => !prev)}
      >
        ?
      </button>
      {expanded ? (
        <span id={panelId} role="note" className="help-icon-panel">
          {children}
        </span>
      ) : null}
    </span>
  );
}
