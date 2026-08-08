import { describe, it, expect, vi } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ProgressPanel from './ProgressPanel.jsx';

const NO_FILTERS = { station: '', dateRangeStart: '', dateRangeEnd: '', search: '' };

function mockFetchOnce(records) {
  vi.stubGlobal(
    'fetch',
    vi.fn(() => Promise.resolve({ ok: true, json: () => Promise.resolve(records) })),
  );
}

const WARDEN_RECORD = {
  id: 'r1',
  station: 'warden',
  date: '2026-08-08',
  shipped_capabilities: ['hygiene gate', 'osv-scanner'],
  compute_hours: 3.5,
  token_spend: 42000,
  wall_clock_hours: 6,
  unblock_narrative: 'none',
  created_at: '2026-08-08T00:00:00+00:00',
  updated_at: '2026-08-08T00:00:00+00:00',
};

describe('ProgressPanel', () => {
  it('shows an empty state with the herald command when there are no records', async () => {
    mockFetchOnce([]);
    render(<ProgressPanel filters={NO_FILTERS} />);

    expect(await screen.findByText('No progress recorded yet.')).toBeInTheDocument();
    expect(screen.getByText(/herald progress <station> --update/)).toBeInTheDocument();
  });

  it('shows a station-specific empty state when filtered to a station with no records', async () => {
    mockFetchOnce([]);
    render(<ProgressPanel filters={{ ...NO_FILTERS, station: 'warden' }} />);

    expect(await screen.findByText('No progress recorded for warden.')).toBeInTheDocument();
    expect(screen.getByText('herald progress warden --update')).toBeInTheDocument();
  });

  it('shows an error state when the fetch fails', async () => {
    vi.stubGlobal('fetch', vi.fn(() => Promise.resolve({ ok: false, status: 404 })));
    render(<ProgressPanel filters={NO_FILTERS} />);

    expect(await screen.findByRole('alert')).toHaveTextContent('Could not load progress.json.');
  });

  it('renders a card summarizing the latest record per station', async () => {
    mockFetchOnce([WARDEN_RECORD]);
    render(<ProgressPanel filters={NO_FILTERS} />);

    const summary = await screen.findByRole('button', { name: /warden/ });
    expect(within(summary).getByText('2026-08-08')).toBeInTheDocument();
    expect(within(summary).getByText('2 shipped')).toBeInTheDocument();
    expect(within(summary).getByText('3.5h compute')).toBeInTheDocument();
  });

  it('expands a card to show the full capability list, cost, and narrative', async () => {
    mockFetchOnce([WARDEN_RECORD]);
    const user = userEvent.setup();
    render(<ProgressPanel filters={NO_FILTERS} />);

    const summary = await screen.findByRole('button', { name: /warden/ });
    expect(summary).toHaveAttribute('aria-expanded', 'false');

    await user.click(summary);

    expect(summary).toHaveAttribute('aria-expanded', 'true');
    expect(screen.getByText('hygiene gate')).toBeInTheDocument();
    expect(screen.getByText('osv-scanner')).toBeInTheDocument();
    expect(screen.getByText('42000')).toBeInTheDocument();
    expect(screen.getByText('none')).toBeInTheDocument();

    await user.click(summary);
    expect(summary).toHaveAttribute('aria-expanded', 'false');
  });

  it('expands via the keyboard (Enter) since the summary is a real button', async () => {
    mockFetchOnce([WARDEN_RECORD]);
    const user = userEvent.setup();
    render(<ProgressPanel filters={NO_FILTERS} />);

    const summary = await screen.findByRole('button', { name: /warden/ });
    summary.focus();
    await user.keyboard('{Enter}');

    expect(summary).toHaveAttribute('aria-expanded', 'true');
  });

  it('shows only the latest record per station when several are recorded', async () => {
    mockFetchOnce([
      { ...WARDEN_RECORD, date: '2026-08-01', shipped_capabilities: ['old'] },
      { ...WARDEN_RECORD, date: '2026-08-08', shipped_capabilities: ['new'] },
    ]);
    render(<ProgressPanel filters={NO_FILTERS} />);

    expect(await screen.findAllByRole('button', { name: /warden/ })).toHaveLength(1);
    const summary = screen.getByRole('button', { name: /warden/ });
    expect(within(summary).getByText('2026-08-08')).toBeInTheDocument();
  });

  it('filters cards by the sidebar station filter', async () => {
    mockFetchOnce([WARDEN_RECORD, { ...WARDEN_RECORD, station: 'atlas', id: 'r2' }]);
    render(<ProgressPanel filters={{ ...NO_FILTERS, station: 'warden' }} />);

    expect(await screen.findByRole('button', { name: /warden/ })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /atlas/ })).not.toBeInTheDocument();
  });

  it('filters cards by the sidebar date range', async () => {
    mockFetchOnce([WARDEN_RECORD]);
    render(
      <ProgressPanel
        filters={{ ...NO_FILTERS, dateRangeStart: '2026-09-01', dateRangeEnd: '2026-09-30' }}
      />,
    );

    expect(await screen.findByText('No progress recorded yet.')).toBeInTheDocument();
  });
});
