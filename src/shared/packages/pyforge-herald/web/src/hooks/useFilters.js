import { useCallback, useEffect, useState } from 'react';
import { STATIONS } from '../components/Sidebar.jsx';

const STORAGE_KEY = 'herald.filters.v1';

const DEFAULT_FILTERS = {
  station: '',
  dateRangeStart: '',
  dateRangeEnd: '',
  search: '',
};

// Regression: a persisted `station` value not in the current STATIONS list
// (a hand-edited/corrupted localStorage entry, or a station renamed/removed
// in a later release) left the <select> silently falling back to "All
// stations" while `filters.station` still held the stale value -- the
// dropdown and the panel's live filter echo disagreed on screen at the same
// time. Reconciled at load, mirroring useHashTab's validTabs pattern.
function loadInitial() {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return DEFAULT_FILTERS;
    const merged = { ...DEFAULT_FILTERS, ...JSON.parse(raw) };
    if (merged.station && !STATIONS.includes(merged.station)) {
      merged.station = '';
    }
    return merged;
  } catch {
    return DEFAULT_FILTERS;
  }
}

/**
 * Sidebar filter state (station, date range, search), persisted to
 * localStorage so it survives a reload. The actual data-fetching this
 * feeds is Epic 8/9/10's scope -- this hook only tracks the values.
 */
export function useFilters() {
  const [filters, setFilters] = useState(loadInitial);

  useEffect(() => {
    try {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(filters));
    } catch {
      // localStorage unavailable (private mode, quota) -- filters still
      // work in-memory for the session.
    }
  }, [filters]);

  const setField = useCallback((field, value) => {
    setFilters((prev) => ({ ...prev, [field]: value }));
  }, []);

  return { filters, setField };
}
