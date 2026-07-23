import { useEffect, useState } from 'react';
import Slide from './Slide.jsx';
import Overview from './Overview.jsx';
import Presenter from './Presenter.jsx';
import HelpOverlay from './HelpOverlay.jsx';
import { useDeck } from './useDeck.js';
import { useFit } from './useFit.js';
import './deck.css';

export default function Deck() {
  const deck = useDeck();
  const { slides, current, slide, mode, setMode, goto, next, prev, total } = deck;
  const [stageRef, scale] = useFit(0);
  const [showHelp, setShowHelp] = useState(false);

  // '?' toggles the shortcut cheat-sheet.
  useEffect(() => {
    const onKey = (e) => {
      const target = e.target;
      if (target && (target.isContentEditable || /^(INPUT|TEXTAREA|SELECT)$/i.test(target.tagName))) {
        return;
      }
      if (e.key === '?') setShowHelp((v) => !v);
      if (e.key === 'Escape') setShowHelp(false);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  if (mode === 'overview') {
    return (
      <Overview
        slides={slides}
        current={current}
        onPick={(i) => {
          goto(i);
          setMode('deck');
        }}
        onClose={() => setMode('deck')}
      />
    );
  }

  if (mode === 'presenter') {
    return <Presenter {...deck} onClose={() => setMode('deck')} />;
  }

  const progress = ((current + 1) / total) * 100;

  return (
    <div className="deck">
      <div className="deck__stage" ref={stageRef}>
        <Slide slide={slide} scale={scale} />
      </div>

      {/* Edge click zones for touch / mouse advance */}
      <button
        type="button"
        className="deck__edge deck__edge--prev"
        aria-label="Previous slide"
        onClick={prev}
        disabled={current === 0}
      />
      <button
        type="button"
        className="deck__edge deck__edge--next"
        aria-label="Next slide"
        onClick={next}
        disabled={current === total - 1}
      />

      <div className="deck__progress" style={{ width: `${progress}%` }} />

      <div className="deck__chrome">
        <button type="button" className="chip" onClick={() => setMode('overview')} title="Overview (O)">
          ▦ Overview
        </button>
        <button type="button" className="chip" onClick={() => setMode('presenter')} title="Presenter (S)">
          ◑ Notes
        </button>
        <span className="deck__counter">
          <span className="deck__counter-num">{slide.number}</span>
          <span className="deck__counter-sep">/</span>
          {total}
        </span>
        <button type="button" className="chip" onClick={() => setShowHelp(true)} title="Shortcuts (?)">
          ?
        </button>
      </div>

      {showHelp && <HelpOverlay onClose={() => setShowHelp(false)} />}
    </div>
  );
}
