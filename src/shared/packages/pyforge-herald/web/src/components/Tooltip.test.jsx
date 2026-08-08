import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, act } from '@testing-library/react';
import Tooltip from './Tooltip.jsx';

beforeEach(() => {
  vi.useFakeTimers();
});

afterEach(() => {
  vi.useRealTimers();
});

function Target(props) {
  return (
    <button type="button" {...props}>
      Hover me
    </button>
  );
}

describe('Tooltip', () => {
  it('appears after a 200ms hover delay, not immediately', () => {
    render(
      <Tooltip label="Filter by station">{(props) => <Target {...props} />}</Tooltip>,
    );

    fireEvent.mouseEnter(screen.getByRole('button', { name: 'Hover me' }));
    expect(screen.queryByRole('tooltip')).not.toBeInTheDocument();

    act(() => {
      vi.advanceTimersByTime(199);
    });
    expect(screen.queryByRole('tooltip')).not.toBeInTheDocument();

    act(() => {
      vi.advanceTimersByTime(1);
    });
    expect(screen.getByRole('tooltip')).toHaveTextContent('Filter by station');
  });

  it('disappears on mouse leave', () => {
    render(
      <Tooltip label="Filter by station">{(props) => <Target {...props} />}</Tooltip>,
    );

    const target = screen.getByRole('button', { name: 'Hover me' });
    fireEvent.mouseEnter(target);
    act(() => {
      vi.advanceTimersByTime(200);
    });
    expect(screen.getByRole('tooltip')).toBeInTheDocument();

    fireEvent.mouseLeave(target);
    expect(screen.queryByRole('tooltip')).not.toBeInTheDocument();
  });

  it('appears immediately on keyboard focus and disappears on blur', () => {
    render(
      <Tooltip label="Filter by station">{(props) => <Target {...props} />}</Tooltip>,
    );

    const target = screen.getByRole('button', { name: 'Hover me' });
    fireEvent.focus(target);
    expect(screen.getByRole('tooltip')).toBeInTheDocument();

    fireEvent.blur(target);
    expect(screen.queryByRole('tooltip')).not.toBeInTheDocument();
  });

  it('stays visible on a stray mouse leave while the element is still focused', () => {
    render(
      <Tooltip label="Filter by station">{(props) => <Target {...props} />}</Tooltip>,
    );

    const target = screen.getByRole('button', { name: 'Hover me' });
    act(() => {
      target.focus();
    });
    fireEvent.focus(target);
    expect(screen.getByRole('tooltip')).toBeInTheDocument();

    // A stray mouseleave (cursor moves onto and off the element without
    // ever touching focus) must not hide a tooltip that is showing because
    // the element is focused.
    fireEvent.mouseLeave(target);
    expect(screen.getByRole('tooltip')).toBeInTheDocument();

    fireEvent.blur(target);
    expect(screen.queryByRole('tooltip')).not.toBeInTheDocument();
  });
});
