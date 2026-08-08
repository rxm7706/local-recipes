import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, fireEvent, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import App from './App.jsx';

function setViewportWidth(width) {
  window.innerWidth = width;
  fireEvent(window, new Event('resize'));
}

beforeEach(() => {
  window.location.hash = '';
  window.localStorage.clear();
  setViewportWidth(1280); // desktop by default
});

describe('tab navigation', () => {
  it('switches the active panel and persists the choice via the URL hash', async () => {
    const user = userEvent.setup();
    render(<App />);

    // Defaults to Progress.
    expect(screen.getByRole('heading', { name: 'Progress' })).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Success' }));

    expect(screen.getByRole('heading', { name: 'Success' })).toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: 'Progress' })).not.toBeInTheDocument();
    expect(window.location.hash).toBe('#success');

    const successTab = screen.getByRole('button', { name: 'Success' });
    expect(successTab).toHaveAttribute('aria-current', 'page');
  });

  it('reads the initial tab from an existing URL hash', () => {
    window.location.hash = '#operations';
    render(<App />);

    expect(screen.getByRole('heading', { name: 'Operations' })).toBeInTheDocument();
  });

  it('corrects an invalid URL hash to the default tab instead of leaving it desynced', () => {
    window.location.hash = '#bogus-tab-xyz';
    render(<App />);

    expect(screen.getByRole('heading', { name: 'Progress' })).toBeInTheDocument();
    expect(window.location.hash).toBe('#progress');
  });
});

describe('sidebar responsiveness', () => {
  it('shows the sidebar uncollapsed at desktop width', () => {
    setViewportWidth(1280);
    render(<App />);

    expect(screen.getByLabelText('Filters')).not.toHaveClass('sidebar--collapsed');
    expect(screen.queryByLabelText('Toggle filters menu')).not.toBeInTheDocument();
  });

  it('collapses the sidebar behind a hamburger at tablet width', async () => {
    setViewportWidth(900);
    const user = userEvent.setup();
    render(<App />);

    expect(screen.getByLabelText('Filters')).toHaveClass('sidebar--collapsed');
    const hamburger = screen.getByLabelText('Toggle filters menu');
    expect(hamburger).toBeInTheDocument();

    await user.click(hamburger);
    expect(screen.getByLabelText('Filters')).not.toHaveClass('sidebar--collapsed');
  });

  it('reflects the drawer open/closed state via aria-expanded on the hamburger', async () => {
    setViewportWidth(900);
    const user = userEvent.setup();
    render(<App />);

    const hamburger = screen.getByLabelText('Toggle filters menu');
    expect(hamburger).toHaveAttribute('aria-expanded', 'false');

    await user.click(hamburger);
    expect(hamburger).toHaveAttribute('aria-expanded', 'true');

    await user.click(hamburger);
    expect(hamburger).toHaveAttribute('aria-expanded', 'false');
  });

  it('collapses the sidebar behind a hamburger at mobile width', () => {
    setViewportWidth(375);
    render(<App />);

    expect(screen.getByLabelText('Filters')).toHaveClass('sidebar--collapsed');
    expect(screen.getByLabelText('Toggle filters menu')).toBeInTheDocument();
  });
});

describe('sidebar filters reacting in the content area', () => {
  it('shows the selected station in the active panel', async () => {
    const user = userEvent.setup();
    render(<App />);

    await user.selectOptions(screen.getByLabelText('Station'), 'warden');

    const panel = screen.getByRole('heading', { name: 'Progress' }).closest('section');
    expect(within(panel).getByText('warden')).toBeInTheDocument();
  });

  it('reconciles a stale/unknown persisted station instead of desyncing the dropdown from the panel', () => {
    window.localStorage.setItem(
      'herald.filters.v1',
      JSON.stringify({ station: 'nonexistent-station' })
    );
    render(<App />);

    expect(screen.getByLabelText('Station')).toHaveValue('');
    const panel = screen.getByRole('heading', { name: 'Progress' }).closest('section');
    expect(within(panel).queryByText('nonexistent-station')).not.toBeInTheDocument();
  });
});
