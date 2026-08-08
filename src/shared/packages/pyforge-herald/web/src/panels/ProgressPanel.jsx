import MomentPanel from './MomentPanel.jsx';

export default function ProgressPanel({ filters }) {
  return (
    <MomentPanel
      title="Progress"
      epic="Epic 8"
      emptyMessage="No progress yet."
      emptyCommand="herald progress warden --update"
      filters={filters}
    />
  );
}
