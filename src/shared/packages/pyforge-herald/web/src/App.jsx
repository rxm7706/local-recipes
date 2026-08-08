import { useEffect, useState } from 'react';
import Header from './components/Header.jsx';
import Sidebar from './components/Sidebar.jsx';
import ProgressPanel from './panels/ProgressPanel.jsx';
import SuccessPanel from './panels/SuccessPanel.jsx';
import OperationsPanel from './panels/OperationsPanel.jsx';
import { useHashTab } from './hooks/useHashTab.js';
import { useFilters } from './hooks/useFilters.js';
import { useViewport } from './hooks/useViewport.js';
import './app.css';

const CONTENT_TABS = ['progress', 'success', 'operations'];

export default function App() {
  const [activeTab, setActiveTab] = useHashTab(CONTENT_TABS, 'progress');
  const { filters, setField } = useFilters();
  const viewport = useViewport();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  // Desktop always shows the sidebar; navigating away from desktop closes
  // any leftover open state so tablet/mobile start collapsed.
  useEffect(() => {
    if (viewport === 'desktop') setSidebarOpen(false);
  }, [viewport]);

  const sidebarCollapsed = viewport !== 'desktop' && !sidebarOpen;
  const showHamburger = viewport !== 'desktop';

  return (
    <div className={`app-shell app-shell--${viewport}`}>
      <Header
        activeTab={activeTab}
        onSelectTab={setActiveTab}
        onToggleSidebar={() => setSidebarOpen((prev) => !prev)}
        showHamburger={showHamburger}
        sidebarOpen={sidebarOpen}
      />
      <div className="app-body">
        <Sidebar
          filters={filters}
          setField={setField}
          collapsed={sidebarCollapsed}
          onClose={showHamburger ? () => setSidebarOpen(false) : undefined}
        />
        <main className="app-content">
          {activeTab === 'progress' ? <ProgressPanel filters={filters} /> : null}
          {activeTab === 'success' ? <SuccessPanel filters={filters} /> : null}
          {activeTab === 'operations' ? <OperationsPanel filters={filters} /> : null}
        </main>
      </div>
    </div>
  );
}
