import { describe, it, expect, vi } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import OperationsPanel from './OperationsPanel.jsx';

const DEFAULT_FILTERS = { station: '', dateRangeStart: '', dateRangeEnd: '', search: '' };

const SAMPLE_NOTICES = [
  {
    type: 'deprecation',
    component: 'auth-api-v1',
    what: 'auth-api-v1 is deprecated',
    why: 'superseded by v2',
    migration: 'swap the base URL',
    deadline: '2026-09-01',
    reason_link: 'https://example.com/rfc',
    status: 'published',
    created_at: '2026-08-01T00:00:00+00:00',
    closed_at: null,
    close_reason: null,
  },
  {
    type: 'eol',
    component: 'legacy-worker',
    what: 'legacy-worker reaches end of life',
    why: 'unmaintained',
    migration: 'migrate to new-worker',
    deadline: null,
    reason_link: null,
    status: 'closed',
    created_at: '2026-01-15T00:00:00+00:00',
    closed_at: '2026-02-01T00:00:00+00:00',
    close_reason: 'migration complete',
  },
];

function stubFetch(payload, { ok = true, status = 200 } = {}) {
  vi.stubGlobal(
    'fetch',
    vi.fn(() =>
      Promise.resolve({
        ok,
        status,
        json: () => Promise.resolve(payload),
      })
    )
  );
}

describe('OperationsPanel', () => {
  it('shows a loading state before the fetch resolves', () => {
    vi.stubGlobal('fetch', vi.fn(() => new Promise(() => {})));
    render(<OperationsPanel filters={DEFAULT_FILTERS} />);
    expect(screen.getByRole('heading', { name: 'Operations' })).toBeInTheDocument();
    expect(screen.getByRole('status')).toHaveTextContent('Loading notices');
  });

  it('renders an empty state when there are no notices', async () => {
    stubFetch([]);
    render(<OperationsPanel filters={DEFAULT_FILTERS} />);
    expect(await screen.findByText('No operations notices yet.')).toBeInTheDocument();
  });

  it('renders an error state when the fetch fails', async () => {
    stubFetch(null, { ok: false, status: 500 });
    render(<OperationsPanel filters={DEFAULT_FILTERS} />);
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Could not load operations notices.'
    );
  });

  it('lists every notice and expands its detail on click', async () => {
    stubFetch(SAMPLE_NOTICES);
    const user = userEvent.setup();
    render(<OperationsPanel filters={DEFAULT_FILTERS} />);

    const authCard = await screen.findByText('auth-api-v1');
    expect(screen.getByText('legacy-worker')).toBeInTheDocument();
    expect(screen.queryByText(/swap the base URL/)).not.toBeInTheDocument();

    await user.click(authCard.closest('button'));
    expect(screen.getByText(/swap the base URL/)).toBeInTheDocument();
    expect(authCard.closest('button')).toHaveAttribute('aria-expanded', 'true');
  });

  it('filters by category', async () => {
    stubFetch(SAMPLE_NOTICES);
    const user = userEvent.setup();
    render(<OperationsPanel filters={DEFAULT_FILTERS} />);

    await screen.findByText('auth-api-v1');
    await user.selectOptions(screen.getByLabelText('Category'), 'eol');

    expect(screen.queryByText('auth-api-v1')).not.toBeInTheDocument();
    expect(screen.getByText('legacy-worker')).toBeInTheDocument();
  });

  it('filters by the shared sidebar date range', async () => {
    stubFetch(SAMPLE_NOTICES);
    render(
      <OperationsPanel
        filters={{ ...DEFAULT_FILTERS, dateRangeStart: '2026-07-01', dateRangeEnd: '2026-12-31' }}
      />
    );

    expect(await screen.findByText('auth-api-v1')).toBeInTheDocument();
    expect(screen.queryByText('legacy-worker')).not.toBeInTheDocument();
  });

  it('shows the close reason for a closed notice once expanded', async () => {
    stubFetch(SAMPLE_NOTICES);
    const user = userEvent.setup();
    render(<OperationsPanel filters={DEFAULT_FILTERS} />);

    const legacyCard = await screen.findByText('legacy-worker');
    await user.click(legacyCard.closest('button'));

    const detail = legacyCard.closest('li');
    expect(within(detail).getByText(/Closed: migration complete/)).toBeInTheDocument();
  });
});
