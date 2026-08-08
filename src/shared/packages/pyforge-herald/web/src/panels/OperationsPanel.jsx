import { useEffect, useState } from 'react';
import EmptyState from '../components/EmptyState.jsx';
import ErrorState from '../components/ErrorState.jsx';

const CATEGORIES = ['deprecation', 'fix', 'eol'];

/**
 * Operations notice board (Story 10.5). Static-JSON-snapshot pattern --
 * Herald has no running server to query live, so this fetches
 * `notices.json` (exported by
 * `scripts/export_notices_snapshot.py` from `.herald/notices-index.json`)
 * once on mount. Category filter is local to this panel (notices don't
 * have a "station"); date range reuses the shared sidebar filter wired in
 * Epic 7.
 */
export default function OperationsPanel({ filters }) {
  const [allNotices, setAllNotices] = useState(null); // null = still loading
  const [error, setError] = useState(null);
  const [category, setCategory] = useState('');
  const [expanded, setExpanded] = useState(null);

  useEffect(() => {
    let cancelled = false;
    fetch('./notices.json')
      .then((response) => {
        if (!response.ok) {
          throw new Error(`notices.json responded ${response.status}`);
        }
        return response.json();
      })
      .then((data) => {
        if (!cancelled) setAllNotices(Array.isArray(data) ? data : []);
      })
      .catch((err) => {
        if (!cancelled) setError(err);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const notices = (allNotices ?? []).filter((notice) => {
    if (category && notice.type !== category) return false;
    const created = notice.created_at ? notice.created_at.slice(0, 10) : '';
    if (filters.dateRangeStart && created < filters.dateRangeStart) return false;
    if (filters.dateRangeEnd && created > filters.dateRangeEnd) return false;
    return true;
  });

  return (
    <section className="operations-panel" aria-labelledby="Operations-heading">
      <h2 id="Operations-heading">Operations</h2>

      <div className="operations-panel__toolbar">
        <label htmlFor="operations-category-filter">Category</label>
        <select
          id="operations-category-filter"
          value={category}
          onChange={(event) => setCategory(event.target.value)}
        >
          <option value="">All categories</option>
          {CATEGORIES.map((cat) => (
            <option key={cat} value={cat}>
              {cat}
            </option>
          ))}
        </select>
      </div>

      {error ? (
        <ErrorState
          message="Could not load operations notices."
          suggestion="Run `herald notice list` from the CLI, or re-export web/public/notices.json."
        />
      ) : allNotices === null ? (
        <p className="operations-panel__loading" role="status">
          Loading notices…
        </p>
      ) : notices.length === 0 ? (
        <EmptyState
          message="No operations notices yet."
          command="herald notice author --type deprecation --component <name> --publish"
        />
      ) : (
        <ul className="notice-board">
          {notices.map((notice) => {
            const isOpen = expanded === notice.component;
            return (
              <li
                key={notice.component}
                className={`notice-card notice-card--${notice.status}`}
              >
                <button
                  type="button"
                  className="notice-card__header"
                  aria-expanded={isOpen}
                  onClick={() => setExpanded(isOpen ? null : notice.component)}
                >
                  <span className={`notice-card__badge notice-card__badge--${notice.type}`}>
                    {notice.type}
                  </span>
                  <span className="notice-card__component">{notice.component}</span>
                  <span className="notice-card__status">{notice.status}</span>
                  {notice.deadline ? (
                    <span className="notice-card__deadline">deadline {notice.deadline}</span>
                  ) : null}
                </button>
                {isOpen ? (
                  <div className="notice-card__detail">
                    <p>
                      <strong>What:</strong> {notice.what}
                    </p>
                    <p>
                      <strong>Why:</strong> {notice.why}
                    </p>
                    <p>
                      <strong>Migration:</strong> {notice.migration}
                    </p>
                    {notice.reason_link ? (
                      <p>
                        <a href={notice.reason_link} target="_blank" rel="noreferrer">
                          Evidence link
                        </a>
                      </p>
                    ) : null}
                    {notice.status === 'closed' ? (
                      <p className="notice-card__closed-note">
                        Closed{notice.close_reason ? `: ${notice.close_reason}` : ''}
                      </p>
                    ) : null}
                  </div>
                ) : null}
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
