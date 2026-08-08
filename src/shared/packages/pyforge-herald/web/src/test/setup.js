import '@testing-library/jest-dom/vitest';
import { afterEach, beforeEach, vi } from 'vitest';

// Story 8.4: ProgressPanel fetches a static `progress.json` snapshot at
// mount. Default every test to an empty-but-successful response so tests
// that don't care about progress data (tab switching, sidebar breakpoints,
// ...) never hit a real network call in jsdom; ProgressPanel's own tests
// override this per case via `vi.stubGlobal('fetch', ...)`.
beforeEach(() => {
  vi.stubGlobal(
    'fetch',
    vi.fn(() => Promise.resolve({ ok: true, json: () => Promise.resolve([]) })),
  );
});

afterEach(() => {
  vi.unstubAllGlobals();
});
