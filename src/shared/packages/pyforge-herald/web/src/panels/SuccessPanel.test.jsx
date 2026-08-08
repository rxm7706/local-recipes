import { describe, it, expect } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import SuccessPanel from './SuccessPanel.jsx';

const NO_FILTERS = { station: '', dateRangeStart: '', dateRangeEnd: '', search: '' };

function jsonResponse(data) {
  return Promise.resolve({ ok: true, json: () => Promise.resolve(data) });
}

const CLAIM = {
  id: 'claim-1',
  project_name: 'warden',
  status: 'published',
  thesis: 'Shipped the compliance gate',
  shipped_date: '2026-08-01',
  created_at: '2026-07-01T00:00:00+00:00',
  published_at: '2026-08-01T00:00:00+00:00',
  closed_at: null,
  updated_at: '2026-08-01T00:00:00+00:00',
  evidence: [
    {
      type: 'test_results',
      url: 'https://ci.example/warden/tests',
      label: 'test results',
      validated: true,
      validated_at: '2026-08-01T00:00:00+00:00',
      is_stale: false,
    },
    {
      type: 'metrics',
      url: 'https://dash.example/warden',
      label: 'metrics',
      validated: false,
      validated_at: null,
      is_stale: true,
    },
  ],
  edit_history: [{ thesis: 'Original thesis', edited_at: '2026-07-15T00:00:00+00:00' }],
};

describe('SuccessPanel', () => {
  it('shows the empty state when no claims are returned', async () => {
    render(
      <SuccessPanel filters={NO_FILTERS} fetcher={() => jsonResponse([])} />
    );
    await waitFor(() => expect(screen.getByRole('status')).toBeInTheDocument());
    expect(screen.getByText('No published claims.')).toBeInTheDocument();
  });

  it('shows an error state when the snapshot fails to load', async () => {
    render(
      <SuccessPanel
        filters={NO_FILTERS}
        fetcher={() => Promise.resolve({ ok: false, status: 404 })}
      />
    );
    await waitFor(() => expect(screen.getByRole('alert')).toBeInTheDocument());
    expect(screen.getByText('Could not load success claims.')).toBeInTheDocument();
  });

  it('renders a claim card newest-first order as given, with evidence badges', async () => {
    render(
      <SuccessPanel filters={NO_FILTERS} fetcher={() => jsonResponse([CLAIM])} />
    );
    await waitFor(() =>
      expect(screen.getByText('warden')).toBeInTheDocument()
    );
    expect(screen.getByText('Shipped the compliance gate')).toBeInTheDocument();

    const validBadge = screen.getByText('Tests').closest('.evidence-badge');
    expect(validBadge).toHaveClass('evidence-badge--valid');
    const brokenBadge = screen.getByText('Metrics').closest('.evidence-badge');
    expect(brokenBadge).toHaveClass('evidence-badge--broken');
  });

  it('expands a card to show full thesis, evidence links, and edit history', async () => {
    const user = userEvent.setup();
    render(
      <SuccessPanel filters={NO_FILTERS} fetcher={() => jsonResponse([CLAIM])} />
    );
    await waitFor(() => expect(screen.getByText('warden')).toBeInTheDocument());

    const toggle = screen.getByRole('button', { expanded: false });
    expect(toggle).toHaveAttribute('aria-expanded', 'false');

    await user.click(toggle);

    expect(toggle).toHaveAttribute('aria-expanded', 'true');
    expect(screen.getByRole('link', { name: 'test results' })).toHaveAttribute(
      'href',
      'https://ci.example/warden/tests'
    );
    expect(screen.getByText(/Original thesis/)).toBeInTheDocument();
  });

  it('filters by the shared sidebar search field (project name or thesis)', async () => {
    const other = { ...CLAIM, id: 'claim-2', project_name: 'marshal', thesis: 'Unrelated' };
    render(
      <SuccessPanel
        filters={{ ...NO_FILTERS, search: 'compliance' }}
        fetcher={() => jsonResponse([CLAIM, other])}
      />
    );
    await waitFor(() => expect(screen.getByText('warden')).toBeInTheDocument());
    expect(screen.queryByText('marshal')).not.toBeInTheDocument();
  });

  it('filters by station against the project name', async () => {
    const other = { ...CLAIM, id: 'claim-2', project_name: 'marshal' };
    render(
      <SuccessPanel
        filters={{ ...NO_FILTERS, station: 'marshal' }}
        fetcher={() => jsonResponse([CLAIM, other])}
      />
    );
    await waitFor(() => expect(screen.getByText('marshal')).toBeInTheDocument());
    expect(screen.queryByText('warden')).not.toBeInTheDocument();
  });

  it('filters by date range against shipped_date', async () => {
    const outOfRange = { ...CLAIM, id: 'claim-2', shipped_date: '2026-01-01' };
    render(
      <SuccessPanel
        filters={{ ...NO_FILTERS, dateRangeStart: '2026-08-01', dateRangeEnd: '2026-08-31' }}
        fetcher={() => jsonResponse([CLAIM, outOfRange])}
      />
    );
    await waitFor(() =>
      expect(screen.getAllByText('warden')).toHaveLength(1)
    );
  });

  it('a synchronous fetcher throw (e.g. no global fetch) is caught and rendered as an error', async () => {
    render(
      <SuccessPanel
        filters={NO_FILTERS}
        fetcher={() => {
          throw new ReferenceError('fetch is not defined');
        }}
      />
    );
    await waitFor(() => expect(screen.getByRole('alert')).toBeInTheDocument());
  });
});
