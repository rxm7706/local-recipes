import { useEffect, useMemo, useState } from 'react';
import EmptyState from '../components/EmptyState.jsx';
import ErrorState from '../components/ErrorState.jsx';
import Tooltip from '../components/Tooltip.jsx';

/**
 * Story 9.4: the Success tab's real archive, replacing the Epic 7
 * placeholder (which rendered `MomentPanel` with a static "not yet
 * implemented" notice -- ``ProgressPanel``/``OperationsPanel`` still do,
 * pending Epics 8/10).
 *
 * **Static-JSON-snapshot pattern.** There is no live API in this
 * architecture (Herald's web app is a plain static Vite bundle, Epic 7) --
 * this panel fetches a pre-generated ``success.json`` (written by
 * ``scripts/export_web_snapshot.py`` from the operator's local
 * ``.herald/claims.json``) rather than a REST endpoint. ``dataUrl``/
 * ``fetcher`` are both overridable props so a test never depends on
 * ``jsdom``'s real (or absent) global ``fetch``.
 */

const EVIDENCE_LABELS = {
  test_results: 'Tests',
  metrics: 'Metrics',
  adoption: 'Adoption',
  other: 'Other',
};

function evidenceStatus(item) {
  if (!item.validated) return 'broken';
  if (item.is_stale) return 'stale';
  return 'valid';
}

const STATUS_SYMBOL = { valid: '✓', broken: '✗', stale: '⚠' };
const STATUS_TEXT = {
  valid: 'valid',
  broken: 'this link may be broken',
  stale: "hasn't been validated recently; review it",
};

function EvidenceBadge({ item }) {
  const status = evidenceStatus(item);
  const typeLabel = EVIDENCE_LABELS[item.type] || item.type;
  const validatedNote = item.validated_at
    ? `valid since ${item.validated_at}`
    : 'never validated';
  const tooltip = `${typeLabel}: ${STATUS_TEXT[status]} (${validatedNote}) — ${item.url}`;

  return (
    <Tooltip label={tooltip}>
      {(a11yProps) => (
        <span
          {...a11yProps}
          tabIndex={0}
          className={`evidence-badge evidence-badge--${status}`}
        >
          <span aria-hidden="true">{STATUS_SYMBOL[status]}</span>
          <span className="evidence-badge__type">{typeLabel}</span>
        </span>
      )}
    </Tooltip>
  );
}

function ClaimCard({ claim, expanded, onToggle }) {
  const detailId = `claim-detail-${claim.id}`;

  return (
    <li className="claim-card">
      <button
        type="button"
        className="claim-card__summary"
        aria-expanded={expanded}
        aria-controls={detailId}
        onClick={onToggle}
      >
        <span className="claim-card__project">{claim.project_name}</span>
        <span className="claim-card__thesis">{claim.thesis || '(no thesis)'}</span>
        <span className="claim-card__date">{claim.shipped_date || '—'}</span>
        <span className="claim-card__badges">
          {claim.evidence.map((item) => (
            <EvidenceBadge key={item.url} item={item} />
          ))}
        </span>
      </button>
      {expanded ? (
        <div id={detailId} className="claim-card__detail">
          <p className="claim-card__detail-thesis">{claim.thesis || '(no thesis)'}</p>
          <ul className="claim-card__detail-evidence">
            {claim.evidence.map((item) => (
              <li key={item.url}>
                <a href={item.url} target="_blank" rel="noreferrer">
                  {item.label}
                </a>
              </li>
            ))}
          </ul>
          {claim.edit_history.length > 0 ? (
            <>
              <h3>Edit history</h3>
              <ul className="claim-card__edit-history">
                {claim.edit_history.map((version) => (
                  <li key={version.edited_at}>
                    <em>{version.edited_at}</em>: {version.thesis}
                  </li>
                ))}
              </ul>
            </>
          ) : null}
          <dl className="claim-card__detail-dates">
            <dt>Status</dt>
            <dd>{claim.status}</dd>
            <dt>Shipped</dt>
            <dd>{claim.shipped_date || '—'}</dd>
            <dt>Published</dt>
            <dd>{claim.published_at || '—'}</dd>
            <dt>Closed</dt>
            <dd>{claim.closed_at || '—'}</dd>
          </dl>
        </div>
      ) : null}
    </li>
  );
}

function claimMatchesFilters(claim, filters) {
  if (
    filters.station &&
    !claim.project_name.toLowerCase().includes(filters.station.toLowerCase())
  ) {
    return false;
  }
  if (filters.search) {
    const needle = filters.search.toLowerCase();
    const haystack = `${claim.project_name} ${claim.thesis || ''}`.toLowerCase();
    if (!haystack.includes(needle)) return false;
  }
  if (
    filters.dateRangeStart &&
    claim.shipped_date &&
    claim.shipped_date < filters.dateRangeStart
  ) {
    return false;
  }
  if (
    filters.dateRangeEnd &&
    claim.shipped_date &&
    claim.shipped_date > filters.dateRangeEnd
  ) {
    return false;
  }
  return true;
}

const defaultFetcher = (url) => fetch(url);

export default function SuccessPanel({
  filters,
  dataUrl = './success.json',
  fetcher = defaultFetcher,
}) {
  const [state, setState] = useState({ status: 'loading', claims: [] });
  const [expandedId, setExpandedId] = useState(null);

  useEffect(() => {
    let cancelled = false;
    setState({ status: 'loading', claims: [] });
    // Routed through a resolved promise so a *synchronous* throw from
    // `fetcher` (e.g. `ReferenceError: fetch is not defined` in a test
    // environment with no global fetch) lands in the same `.catch` as an
    // ordinary network failure, instead of escaping as an unhandled
    // exception during the effect.
    Promise.resolve()
      .then(() => fetcher(dataUrl))
      .then((response) => {
        if (!response.ok) throw new Error(`fetch failed: ${response.status}`);
        return response.json();
      })
      .then((data) => {
        if (!cancelled) {
          setState({ status: 'ready', claims: Array.isArray(data) ? data : [] });
        }
      })
      .catch(() => {
        if (!cancelled) setState({ status: 'error', claims: [] });
      });
    return () => {
      cancelled = true;
    };
  }, [dataUrl, fetcher]);

  const filtered = useMemo(
    () => state.claims.filter((claim) => claimMatchesFilters(claim, filters)),
    [state.claims, filters]
  );

  return (
    <section className="moment-panel" aria-labelledby="success-heading">
      <h2 id="success-heading">Success</h2>

      {state.status === 'error' ? (
        <ErrorState
          message="Could not load success claims."
          suggestion="Run `python scripts/export_web_snapshot.py` to regenerate success.json."
        />
      ) : null}

      {state.status === 'ready' && filtered.length === 0 ? (
        <EmptyState
          message="No published claims."
          command="herald success create <project> && herald success publish <claim-id>"
        />
      ) : null}

      {state.status === 'ready' && filtered.length > 0 ? (
        <ul className="claim-list">
          {filtered.map((claim) => (
            <ClaimCard
              key={claim.id}
              claim={claim}
              expanded={expandedId === claim.id}
              onToggle={() => setExpandedId(expandedId === claim.id ? null : claim.id)}
            />
          ))}
        </ul>
      ) : null}
    </section>
  );
}
