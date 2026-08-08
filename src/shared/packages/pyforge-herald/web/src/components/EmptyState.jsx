/**
 * Helpful empty state -- Story 7.2 AC: never just "No data", always a
 * next-step. `command` renders as a copy-paste-friendly code snippet.
 */
export default function EmptyState({ message, command }) {
  return (
    <div className="empty-state" role="status">
      <p className="empty-state__message">{message}</p>
      {command ? <code className="empty-state__command">{command}</code> : null}
    </div>
  );
}
