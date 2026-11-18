import { CloudRain, Route, X } from 'lucide-react'
import { CommunityRow } from './CommunityRow.tsx'
import { detailView } from './segmentDetail.ts'
import { useAppStore } from './store.ts'
import { Badge, Button, Stat } from './ui.tsx'
import { readyData, type ZoneState } from './zoneData.ts'

export function SegmentDetail({ state, onWhy }: { state: ZoneState; onWhy: () => void }) {
  const selected = useAppStore((s) => s.selectedUnitId)
  const selectUnit = useAppStore((s) => s.selectUnit)
  const closed = useAppStore((s) => s.closedUnitIds)
  const closeUnit = useAppStore((s) => s.closeUnit)
  const data = readyData(state)
  if (data === null || selected === null) return null
  const unit = data.units.find((item) => item.id === selected)
  if (!unit) return null
  const view = detailView(unit, data.graph, data.baseline)
  const suspects = new Set(unit.suspect_isolated_community_ids ?? [])
  const isClosed = closed.includes(unit.id)

  return (
    <section aria-label="Segment detail" className="space-y-3 border-b border-line bg-surface p-3 text-sm">
      <header className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <h2 className="font-semibold">{view.header}</h2>
          <p className="text-muted">Rank {view.rank}</p>
        </div>
        <Button variant="ghost" aria-label="Close detail" onClick={() => selectUnit(null)} className="px-2!">
          <X aria-hidden="true" className="h-4 w-4" />
        </Button>
      </header>
      <dl className="grid grid-cols-2 gap-2">
        <Stat label="Extra time" value={view.extraTime} />
        <Stat label="Dependent population" value={view.population} />
      </dl>

      <div>
        <h3 className="mb-1.5 font-medium">Affected communities</h3>
        <ul className="space-y-1.5">
          {view.communities.map((c) => (
            <CommunityRow key={c.id} row={c} suspect={suspects.has(c.id)} />
          ))}
        </ul>
      </div>

      <div>
        <h3 className="mb-1.5 flex items-center gap-1.5 font-medium">
          <Route aria-hidden="true" className="h-4 w-4" />
          Alternates
        </h3>
        <ul className="space-y-0.5 text-muted">
          {view.alternates.map((line) => (
            <li key={line}>{line}</li>
          ))}
        </ul>
      </div>

      <div>
        <h3 className="mb-1.5 flex items-center gap-1.5 font-medium">
          <CloudRain aria-hidden="true" className="h-4 w-4" />
          Exposure
        </h3>
        <p>
          Rain: {view.rain} <Badge tone="info">{view.rainLabel}</Badge>
        </p>
      </div>

      <div className="flex flex-wrap gap-2">
        <Button variant="primary" disabled={isClosed} onClick={() => closeUnit(unit.id)}>
          {isClosed ? 'Closed in the simulation' : 'Simulate closing this segment'}
        </Button>
        <Button onClick={onWhy}>Why?</Button>
      </div>
    </section>
  )
}
