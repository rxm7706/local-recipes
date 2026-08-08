import '@testing-library/jest-dom/vitest';
import { afterEach, beforeEach, vi } from 'vitest';

// Stories 8.4/9.4/10.5: ProgressPanel/SuccessPanel/OperationsPanel each
// fetch a static JSON snapshot at mount. Default every test to an
// empty-but-successful response so tests that don't care about that data
// (tab switching, sidebar breakpoints, ...) never hit a real network call
// in jsdom (which would otherwise resolve/reject after the test finished
// and trip React's "not wrapped in act(...)" warning); each panel's own
// tests override this per case via `vi.stubGlobal('fetch', ...)`.
beforeEach(() => {
  vi.stubGlobal(
    'fetch',
    vi.fn(() => Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve([]) }))
  );
});

afterEach(() => {
  vi.unstubAllGlobals();
});
