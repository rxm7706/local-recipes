import MomentPanel from './MomentPanel.jsx';

export default function SuccessPanel({ filters }) {
  return (
    <MomentPanel
      title="Success"
      epic="Epic 9"
      emptyMessage="No success stories yet."
      emptyCommand="herald success warden --publish"
      filters={filters}
    />
  );
}
