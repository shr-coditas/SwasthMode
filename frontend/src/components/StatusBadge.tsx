const labels: Record<string, string> = {
  pending: 'Insight pending', completed: 'Insight ready', failed: 'Insight failed',
  not_requested: 'Synthetic seed · no AI insight', saved: 'Saved', clarification: 'A little more detail',
}
export default function StatusBadge({status}: {status: string}) {
  return <span className={`status status-${status}`}>{labels[status] || status}</span>
}
