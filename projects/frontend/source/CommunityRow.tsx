import { ArrowRight } from 'lucide-react'
import { PointIcon } from './mapIcons.tsx'
import { NO_ROUTE } from './trustSignals.ts'
import { Badge } from './ui.tsx'

export interface CommunityRowData {
  name: string
  withoutClosure: string
  withClosure: string
  extra: string
  hospital: string
}

// One affected community: the time before and after the closure, the extra time and the hospital it reaches.
export function CommunityRow({ row, suspect = false }: { row: CommunityRowData; suspect?: boolean }) {
  const isolated = row.withClosure.startsWith(NO_ROUTE)
  return (
    <li className="rounded-lg border border-line px-3 py-2 text-sm">
      <div className="flex items-start justify-between gap-2">
        <span className="flex min-w-0 items-center gap-1.5 font-medium">
          <PointIcon kind="community" />
          {row.name}
        </span>
        <span className="flex shrink-0 flex-wrap justify-end gap-1">
          {isolated ? <Badge tone="danger">No route</Badge> : <Badge tone="warning">+{row.extra}</Badge>}
          {suspect && <Badge tone="info">Possible model artifact</Badge>}
        </span>
      </div>
      <p className="mt-1 flex flex-wrap items-center gap-1 text-xs text-muted tabular-nums">
        {row.withoutClosure}
        <ArrowRight aria-label="with closure" className="h-3 w-3" />
        {isolated ? NO_ROUTE : row.withClosure}
      </p>
      {!isolated && (
        <p className="mt-0.5 flex items-center gap-1 text-xs text-muted">
          <PointIcon kind="hospital" size={14} />
          {row.hospital}
        </p>
      )}
    </li>
  )
}
