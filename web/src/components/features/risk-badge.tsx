interface RiskBadgeProps {
  score: number
  size?: 'sm' | 'md'
}

export function RiskBadge({ score, size = 'md' }: RiskBadgeProps) {
  const label = score >= 70 ? 'High' : score >= 40 ? 'Medium' : 'Low'
  const styles =
    score >= 70
      ? 'bg-red-50 text-red-600 border-red-200'
      : score >= 40
      ? 'bg-amber-50 text-amber-600 border-amber-200'
      : 'bg-emerald-50 text-emerald-600 border-emerald-200'
  const textSize = size === 'sm' ? 'text-xs' : 'text-sm'

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 font-medium ${styles} ${textSize}`}
    >
      <span className="tabular-nums">{score}</span>
      <span className="opacity-60">/100</span>
      <span className="font-semibold">{label}</span>
    </span>
  )
}
