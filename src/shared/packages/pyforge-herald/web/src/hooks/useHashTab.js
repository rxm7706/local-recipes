import { useCallback, useEffect, useState } from 'react';

/**
 * Persist the active tab in the URL hash (e.g. `#progress`) so a reload,
 * bookmark, or shared link lands on the same tab. Falls back to
 * `defaultTab` when the hash is empty or names a tab that isn't in
 * `validTabs`.
 */
export function useHashTab(validTabs, defaultTab) {
  const readHash = useCallback(() => {
    const raw = window.location.hash.replace(/^#/, '');
    return validTabs.includes(raw) ? raw : defaultTab;
  }, [validTabs, defaultTab]);

  const [activeTab, setActiveTabState] = useState(readHash);

  useEffect(() => {
    const onHashChange = () => setActiveTabState(readHash());
    window.addEventListener('hashchange', onHashChange);
    return () => window.removeEventListener('hashchange', onHashChange);
  }, [readHash]);

  const setActiveTab = useCallback((tab) => {
    window.location.hash = tab;
    setActiveTabState(tab);
  }, []);

  return [activeTab, setActiveTab];
}
