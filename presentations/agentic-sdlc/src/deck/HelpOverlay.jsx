const SHORTCUTS = [
  ['→ · Space · PgDn', 'Next slide'],
  ['← · PgUp', 'Previous slide'],
  ['Home · End', 'First / last slide'],
  ['O', 'Overview grid'],
  ['S', 'Presenter (speaker notes)'],
  ['F', 'Fullscreen'],
  ['Esc', 'Back to deck'],
  ['?', 'Toggle this help'],
];

export default function HelpOverlay({ onClose }) {
  return (
    <div className="help" onClick={onClose} role="presentation">
      <div className="help__card" onClick={(e) => e.stopPropagation()}>
        <h2 className="help__title">Keyboard</h2>
        <dl className="help__list">
          {SHORTCUTS.map(([key, desc]) => (
            <div className="help__row" key={key}>
              <dt>
                <kbd>{key}</kbd>
              </dt>
              <dd>{desc}</dd>
            </div>
          ))}
        </dl>
        <button type="button" className="chip" onClick={onClose}>
          Got it
        </button>
      </div>
    </div>
  );
}
