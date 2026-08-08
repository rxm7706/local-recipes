import EmptyState from '../components/EmptyState.jsx';

/**
 * Shared placeholder panel for the Success/Operations Moment tabs. Real
 * data-fetching lands with Epics 9/10 -- for now this just proves the
 * content area reacts to the active filters, per Story 7.1's AC.
 * ``ProgressPanel`` (Epic 8, Story 8.4) no longer uses this -- it has real
 * card-based rendering over a static ``progress.json`` snapshot.
 */
export default function MomentPanel({ title, epic, emptyMessage, emptyCommand, filters }) {
  const hasAnyFilter =
    filters.station || filters.dateRangeStart || filters.dateRangeEnd || filters.search;

  return (
    <section className="moment-panel" aria-labelledby={`${title}-heading`}>
      <h2 id={`${title}-heading`}>{title}</h2>
      <p className="moment-panel__notice">Not yet implemented — {epic}.</p>

      <dl className="moment-panel__filters">
        <dt>Station</dt>
        <dd>{filters.station || '(all)'}</dd>
        <dt>Date range</dt>
        <dd>
          {filters.dateRangeStart || '(open)'} — {filters.dateRangeEnd || '(open)'}
        </dd>
        <dt>Search</dt>
        <dd>{filters.search || '(none)'}</dd>
      </dl>

      {!hasAnyFilter ? <EmptyState message={emptyMessage} command={emptyCommand} /> : null}
    </section>
  );
}
