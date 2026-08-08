import MomentPanel from './MomentPanel.jsx';

export default function OperationsPanel({ filters }) {
  return (
    <MomentPanel
      title="Operations"
      epic="Epic 10"
      emptyMessage="No operations notices yet."
      emptyCommand="herald notice warden --author"
      filters={filters}
    />
  );
}
