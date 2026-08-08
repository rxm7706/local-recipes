import TabNav from './TabNav.jsx';

export default function Header({ activeTab, onSelectTab, onToggleSidebar, showHamburger }) {
  return (
    <header className="app-header">
      <div className="app-header__brand">
        {showHamburger ? (
          <button
            type="button"
            className="app-header__hamburger"
            aria-label="Toggle filters menu"
            aria-expanded={undefined}
            onClick={onToggleSidebar}
          >
            <span aria-hidden="true">☰</span>
          </button>
        ) : null}
        <span className="app-header__logo">Herald</span>
      </div>
      <TabNav activeTab={activeTab} onSelect={onSelectTab} />
    </header>
  );
}
