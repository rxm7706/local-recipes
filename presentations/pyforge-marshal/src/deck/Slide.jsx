import { memo } from 'react';
import { SLIDE_WIDTH, SLIDE_HEIGHT } from '../slides/index.js';

// Renders one slide's authored 1920×1080 markup, uniformly scaled.
// The outer element takes the *scaled* footprint so the slide participates
// in normal layout (centered on the stage, tiled in the overview grid),
// while the inner frame keeps its true pixel dimensions and is transformed.
function Slide({ slide, scale = 1, className = '' }) {
  return (
    <div
      className={`slide ${className}`}
      style={{ width: SLIDE_WIDTH * scale, height: SLIDE_HEIGHT * scale }}
    >
      <div
        className="slide__frame"
        style={{
          width: SLIDE_WIDTH,
          height: SLIDE_HEIGHT,
          background: slide.bg,
          transform: `scale(${scale})`,
        }}
      >
        <div
          className="slide__content"
          style={{ width: '100%', height: '100%' }}
          dangerouslySetInnerHTML={{ __html: slide.html }}
        />
      </div>
    </div>
  );
}

export default memo(Slide);
