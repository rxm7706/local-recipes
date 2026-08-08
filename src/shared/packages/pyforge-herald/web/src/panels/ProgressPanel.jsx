import { useEffect, useState } from 'react';
import EmptyState from '../components/EmptyState.jsx';
import ErrorState from '../components/ErrorState.jsx';

/**
 * Story 8.4's Progress tab: real card-based rendering over a static
 * `progress.json` snapshot (there is no live REST API in this scaled-down
 * pass -- see docs/dreams/herald-moments-2-4-live-backend.md). The
 * snapshot is written by `npm run sync-progress` (wired as a `predev`/
 * `prebuild` hook) from the operator's local `.herald/progress.json`.
 *
 * Shows the *latest* record per station as an expandable card, filtered by
 * the sidebar's station/date-range filters -- matches the epics doc's own
 * AC shape (card summary: station, date, shipped-capability count, total
 * compute hours; expand for the full capability list, cost breakdown, and
 * the unblock narrative).
 */
export default function ProgressPanel({ filters }) {
  const [state, setState] = useState({ status: 'loading', records: [] });
  const [expandedStations, setExpandedStations] = useState(() => new Set());

  useEffect(() => {
    let cancelled = false;
    fetch(`${import.meta.env.BASE_URL}progress.json`)
      .then((response) => {
        if (!response.ok) throw new Error(`progress.json responded ${response.status}`);
        return response.json();
      })
      .then((records) => {
        if (!cancelled) {
          setState({ status: 'ready', records: Array.isArray(records) ? records : [] });
        }
      })
      .catch(() => {
        if (!cancelled) setState({ status: 'error', records: [] });
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const toggle = (station) => {
    setExpandedStations((prev) => {
      const next = new Set(prev);
      if (next.has(station)) {
        next.delete(station);
      } else {
        next.add(station);
      }
      return next;
    });
  };

  return (
    <section className="moment-panel" aria-labelledby="Progress-heading">
      <h2 id="Progress-heading">Progress</h2>

      {state.status === 'loading' ? <p className="moment-panel__notice">Loading…</p> : null}

      {state.status === 'error' ? (
        <ErrorState
          message="Could not load progress.json."
          suggestion="Run `npm run sync-progress` (or `npm run build`) after recording progress, then reload."
        />
      ) : null}

      {state.status === 'ready' ? (
        <ProgressCards
          records={state.records}
          filters={filters}
          expandedStations={expandedStations}
          onToggle={toggle}
        />
      ) : null}
    </section>
  );
}

function latestPerStation(records) {
  const latest = new Map();
  for (const record of records) {
    const existing = latest.get(record.station);
    if (!existing || record.date > existing.date) {
      latest.set(record.station, record);
    }
  }
  return [...latest.values()];
}

function ProgressCards({ records, filters, expandedStations, onToggle }) {
  const filtered = records.filter((record) => {
    if (filters.station && record.station !== filters.station) return false;
    if (filters.dateRangeStart && record.date < filters.dateRangeStart) return false;
    if (filters.dateRangeEnd && record.date > filters.dateRangeEnd) return false;
    return true;
  });
  const cards = latestPerStation(filtered).sort((a, b) => (a.date < b.date ? 1 : a.date > b.date ? -1 : 0));

  if (cards.length === 0) {
    const station = filters.station || '<station>';
    const message = filters.station
      ? `No progress recorded for ${filters.station}.`
      : 'No progress recorded yet.';
    return <EmptyState message={message} command={`herald progress ${station} --update`} />;
  }

  return (
    <ul className="progress-cards">
      {cards.map((record) => (
        <ProgressCard
          key={record.station}
          record={record}
          expanded={expandedStations.has(record.station)}
          onToggle={() => onToggle(record.station)}
        />
      ))}
    </ul>
  );
}

function ProgressCard({ record, expanded, onToggle }) {
  const capabilities = record.shipped_capabilities || [];
  return (
    <li className="progress-card">
      <button
        type="button"
        className="progress-card__summary"
        aria-expanded={expanded}
        onClick={onToggle}
      >
        <span className="progress-card__station">{record.station}</span>
        <span className="progress-card__date">{record.date}</span>
        <span className="progress-card__stat">{capabilities.length} shipped</span>
        <span className="progress-card__stat">{record.compute_hours}h compute</span>
      </button>
      {expanded ? (
        <div className="progress-card__detail">
          <h3>Shipped capabilities</h3>
          {capabilities.length ? (
            <ul className="progress-card__capabilities">
              {capabilities.map((capability) => (
                <li key={capability}>{capability}</li>
              ))}
            </ul>
          ) : (
            <p>(none recorded)</p>
          )}

          <h3>Cost</h3>
          <dl className="progress-card__cost">
            <dt>Compute hours</dt>
            <dd>{record.compute_hours}</dd>
            <dt>Token spend</dt>
            <dd>{record.token_spend}</dd>
            <dt>Wall-clock hours</dt>
            <dd>{record.wall_clock_hours}</dd>
          </dl>

          <h3>Unblock narrative</h3>
          <p>{record.unblock_narrative || '(none)'}</p>

          <code className="empty-state__command">
            herald progress {record.station} --update
          </code>
        </div>
      ) : null}
    </li>
  );
}
