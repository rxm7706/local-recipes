import { useCallback, useEffect, useState } from 'react';

const STORAGE_KEY = 'herald.filters.v1';

const DEFAULT_FILTERS = {
  station: '',
  dateRangeStart: '',
  dateRangeEnd: '',
  search: '',
};

function loadInitial() {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return DEFAULT_FILTERS;
    return { ...DEFAULT_FILTERS, ...JSON.parse(raw) };
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
