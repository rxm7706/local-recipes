import Tooltip from './Tooltip.jsx';

export const TABS = [
  { key: 'pitch', label: 'Pitch', external: 'https://github.com/rxm7706/local-recipes', hint: 'Open the pitch deck' },
  { key: 'progress', label: 'Progress', hint: 'Weekly progress updates' },
  { key: 'success', label: 'Success', hint: 'Shipped outcomes' },
  { key: 'operations', label: 'Operations', hint: 'Factory operations' },
];

export default function TabNav({ activeTab, onSelect }) {
  return (
    <nav className="tab-nav" aria-label="Herald sections">
      {TABS.map((tab) =>
        tab.external ? (
          <Tooltip key={tab.key} label={tab.hint}>
            {(a11yProps) => (
              <a
                {...a11yProps}
                className="tab-nav__item tab-nav__item--external"
                href={tab.external}
                target="_blank"
                rel="noreferrer"
              >
                {tab.label} <span aria-hidden="true">↗</span>
              </a>
            )}
          </Tooltip>
        ) : (
          <Tooltip key={tab.key} label={tab.hint}>
            {(a11yProps) => (
              <button
                {...a11yProps}
                type="button"
                className={`tab-nav__item${activeTab === tab.key ? ' tab-nav__item--active' : ''}`}
                aria-current={activeTab === tab.key ? 'page' : undefined}
                onClick={() => onSelect(tab.key)}
              >
                {tab.label}
              </button>
            )}
          </Tooltip>
        ),
      )}
    </nav>
  );
}
