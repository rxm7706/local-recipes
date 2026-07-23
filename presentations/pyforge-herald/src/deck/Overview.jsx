import Slide from './Slide.jsx';
import { SLIDE_WIDTH } from '../slides/index.js';

const THUMB_WIDTH = 300;
const thumbScale = THUMB_WIDTH / SLIDE_WIDTH;

// Grid of every slide as a scaled thumbnail. Click to jump.
export default function Overview({ slides, current, onPick, onClose }) {
  return (
    <div className="overview">
      <header className="overview__bar">
        <span className="overview__title">All slides · {slides.length}</span>
        <button type="button" className="chip" onClick={onClose}>
          Close ✕
        </button>
      </header>
      <div className="overview__grid">
        {slides.map((slide) => (
          <button
            type="button"
            key={slide.id}
            className={`thumb ${slide.index === current ? 'thumb--active' : ''}`}
            onClick={() => onPick(slide.index)}
            title={slide.label}
          >
            <Slide slide={slide} scale={thumbScale} />
            <span className="thumb__meta">
              <span className="thumb__num">{slide.number}</span>
              <span className="thumb__label">{slide.label}</span>
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}
