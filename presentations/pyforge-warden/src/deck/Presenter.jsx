import { useEffect, useRef, useState } from 'react';
import Slide from './Slide.jsx';
import { useFit } from './useFit.js';

let presenterStartTime = null;

function useTimer() {
  const start = useRef(null);
  if (start.current === null) {
    if (presenterStartTime === null) {
      presenterStartTime = Date.now();
    }
    start.current = presenterStartTime;
  }
  const [elapsed, setElapsed] = useState(Date.now() - start.current);
  useEffect(() => {
    const id = setInterval(() => setElapsed(Date.now() - start.current), 1000);
    return () => clearInterval(id);
  }, []);
  const total = Math.floor(elapsed / 1000);
  const mm = String(Math.floor(total / 60)).padStart(2, '0');
  const ss = String(total % 60).padStart(2, '0');
  return `${mm}:${ss}`;
}

// Speaker view: current slide large, next slide preview, notes + timer.
export default function Presenter({ slides, current, slide, next, prev, goto, onClose }) {
  const [mainRef, mainScale] = useFit(0);
  const [nextRef, nextScale] = useFit(0);
  const elapsed = useTimer();
  const upcoming = slides[current + 1];

  return (
    <div className="presenter">
      <header className="presenter__bar">
        <span className="presenter__brand">Presenter view</span>
        <span className="presenter__clock">{elapsed}</span>
        <span className="presenter__count">
          {slide.number} / {slides.length}
        </span>
        <button type="button" className="chip" onClick={onClose}>
          Exit (S)
        </button>
      </header>

      <div className="presenter__body">
        <div className="presenter__main">
          <div className="presenter__stage" ref={mainRef}>
            <Slide slide={slide} scale={mainScale} />
          </div>
          <div className="presenter__controls">
            <button type="button" className="chip" onClick={prev} disabled={current === 0}>
              ← Prev
            </button>
            <span className="presenter__label">{slide.label}</span>
            <button
              type="button"
              className="chip"
              onClick={next}
              disabled={current === slides.length - 1}
            >
              Next →
            </button>
          </div>
        </div>

        <aside className="presenter__side">
          <div className="presenter__nextwrap">
            <div className="presenter__eyebrow">Next</div>
            {upcoming ? (
              <button
                type="button"
                className="presenter__next"
                ref={nextRef}
                onClick={() => goto(current + 1)}
              >
                <Slide slide={upcoming} scale={nextScale} />
              </button>
            ) : (
              <div className="presenter__end">End of deck</div>
            )}
            {upcoming && <div className="presenter__nextlabel">{upcoming.label}</div>}
          </div>
          <div className="presenter__notes">
            <div className="presenter__eyebrow">Speaker notes</div>
            <p>{slide.notes || 'No notes for this slide.'}</p>
          </div>
        </aside>
      </div>
    </div>
  );
}
