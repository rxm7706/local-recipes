import Tooltip from './Tooltip.jsx';
import HelpIcon from './HelpIcon.jsx';

export const STATIONS = [
  'warden',
  'atlas',
  'marshal',
  'mason',
  'doctor',
  'scribe',
  'steward',
  'herald',
];

export default function Sidebar({ filters, setField, collapsed, onClose }) {
  return (
    <aside
      className={`sidebar${collapsed ? ' sidebar--collapsed' : ''}`}
      aria-hidden={collapsed}
      aria-label="Filters"
    >
      {onClose ? (
        <button type="button" className="sidebar__close" aria-label="Close filters" onClick={onClose}>
          <span aria-hidden="true">×</span>
        </button>
      ) : null}

      <div className="sidebar__field">
        <label htmlFor="station-filter">Station</label>
        <Tooltip label="Filter by station">
          {(a11yProps) => (
            <select
              {...a11yProps}
              id="station-filter"
              value={filters.station}
              onChange={(event) => setField('station', event.target.value)}
            >
              <option value="">All stations</option>
              {STATIONS.map((station) => (
                <option key={station} value={station}>
                  {station}
                </option>
              ))}
            </select>
          )}
        </Tooltip>
      </div>

      <div className="sidebar__field">
        <span className="sidebar__field-label-row">
          <label htmlFor="date-range-start">Date range</label>
          <HelpIcon label="Date range format help">
            Enter dates as <code>YYYY-MM-DD</code>. Leave either field blank for an open-ended
            range, e.g. start-only means "from that date onward".
          </HelpIcon>
        </span>
        <Tooltip label="Range start (YYYY-MM-DD)">
          {(a11yProps) => (
            <input
              {...a11yProps}
              id="date-range-start"
              type="text"
              inputMode="numeric"
              placeholder="YYYY-MM-DD"
              value={filters.dateRangeStart}
              onChange={(event) => setField('dateRangeStart', event.target.value)}
            />
          )}
        </Tooltip>
        <Tooltip label="Range end (YYYY-MM-DD)">
          {(a11yProps) => (
            <input
              {...a11yProps}
              id="date-range-end"
              type="text"
              inputMode="numeric"
              placeholder="YYYY-MM-DD"
              value={filters.dateRangeEnd}
              onChange={(event) => setField('dateRangeEnd', event.target.value)}
            />
          )}
        </Tooltip>
      </div>

      <div className="sidebar__field">
        <label htmlFor="search-filter">Search</label>
        <Tooltip label="Search records">
          {(a11yProps) => (
            <input
              {...a11yProps}
              id="search-filter"
              type="search"
              placeholder="Search…"
              value={filters.search}
              onChange={(event) => setField('search', event.target.value)}
            />
          )}
        </Tooltip>
      </div>
    </aside>
  );
}
