/**
 * Helpful error state -- Story 7.2 AC: explain the problem and suggest a
 * fix, e.g. "Station 'unknown' not found. Available: warden, atlas, ...".
 */
export default function ErrorState({ message, suggestion }) {
  return (
    <div className="error-state" role="alert">
      <p className="error-state__message">{message}</p>
      {suggestion ? <p className="error-state__suggestion">{suggestion}</p> : null}
    </div>
  );
}
