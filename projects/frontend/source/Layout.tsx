import { CloudRain, FlaskConical, ListOrdered, type LucideIcon } from 'lucide-react'
import { useEffect, useRef, useState, useSyncExternalStore, type ReactNode } from 'react'
import { useAppStore } from './store.ts'

type TabId = 'tramos' | 'simulacion' | 'porque'

const WIDE_QUERY = '(min-width: 768px)'
const DRAG_THRESHOLD = 24 // px of vertical travel that count as a swipe on the sheet's handle

const TABS: { id: TabId; label: string; icon: LucideIcon }[] = [
  { id: 'tramos', label: 'Tramos', icon: ListOrdered },
  { id: 'simulacion', label: 'Simulación', icon: FlaskConical },
  { id: 'porque', label: '¿Por qué?', icon: CloudRain },
]

function useIsWide(): boolean {
  return useSyncExternalStore(
    (notify) => {
      const query = window.matchMedia(WIDE_QUERY)
      query.addEventListener('change', notify)
      return () => query.removeEventListener('change', notify)
    },
    () => window.matchMedia(WIDE_QUERY).matches,
  )
}

export function Layout({ header, footer, map, ranking, detail, simulation, why }: {
  header: ReactNode
  footer: ReactNode
  map: ReactNode
  ranking: ReactNode
  detail: (onWhy: () => void) => ReactNode
  simulation: ReactNode
  why: ReactNode
}) {
  const wide = useIsWide()
  const selected = useAppStore((state) => state.selectedUnitId)
  const [tab, setTab] = useState<TabId>('tramos')
  const [expanded, setExpanded] = useState(false)
  const dragStart = useRef<number | null>(null)
  const swiped = useRef(false)
  const panel = useRef<HTMLDivElement>(null)

  // A new selection or tab starts at the top of the panel, where the detail and the summaries are.
  useEffect(() => {
    panel.current?.scrollTo({ top: 0 })
  }, [selected, tab])

  // INV-05: selecting a unit expands the sheet (it only matters on narrow screens).
  const [seen, setSeen] = useState(selected)
  if (seen !== selected) {
    setSeen(selected)
    if (selected !== null) {
      setTab('tramos')
      setExpanded(true)
    }
  }

  const showWhy = () => {
    setTab('porque')
    setExpanded(true)
  }

  return (
    <div className="flex h-full flex-col overflow-x-hidden">
      {header}
      <div className="relative flex min-h-0 min-w-0 flex-1 flex-col md:flex-row">
        <div className="relative min-h-0 min-w-0 flex-1 md:order-2">{map}</div>
        <aside className="relative z-10 flex min-w-0 shrink-0 flex-col rounded-t-2xl border-t border-line bg-white shadow-sheet md:order-1 md:w-96 md:rounded-none md:border-r md:border-t-0 md:shadow-none">
          <button
            type="button"
            aria-expanded={expanded}
            aria-controls="sheet-content"
            onClick={() => {
              if (swiped.current) swiped.current = false
              else setExpanded((value) => !value)
            }}
            onPointerDown={(event) => {
              dragStart.current = event.clientY
              swiped.current = false
            }}
            onPointerUp={(event) => {
              if (dragStart.current === null) return
              const travel = event.clientY - dragStart.current
              dragStart.current = null
              if (Math.abs(travel) >= DRAG_THRESHOLD) {
                swiped.current = true
                setExpanded(travel < 0)
              }
            }}
            onPointerCancel={() => (dragStart.current = null)}
            className="flex min-h-11 min-w-11 touch-none flex-col items-center justify-center gap-0.5 text-xs text-muted md:hidden"
          >
            <span aria-hidden="true" className="h-1 w-10 rounded-full bg-slate-300" />
            {expanded ? 'Contraer panel' : 'Expandir panel'}
          </button>
          <div role="tablist" className="flex gap-1 border-b border-line p-1.5">
            {TABS.map(({ id, label, icon: Icon }) => (
              <button
                key={id}
                type="button"
                role="tab"
                id={`tab-${id}`}
                aria-selected={tab === id}
                aria-controls="sheet-content"
                onClick={() => {
                  setTab(id)
                  setExpanded(true)
                }}
                className={`flex min-h-11 min-w-11 flex-1 items-center justify-center gap-1.5 rounded-lg px-2 text-sm transition-colors md:min-h-9 ${tab === id ? 'bg-brand-soft font-semibold text-amber-900' : 'text-muted hover:bg-slate-100'}`}
              >
                <Icon aria-hidden="true" className="h-4 w-4" />
                {label}
              </button>
            ))}
          </div>
          <div
            className={`grid min-h-0 transition-[grid-template-rows] duration-200 ease-out md:flex-1 md:grid-rows-[1fr] ${expanded ? 'grid-rows-[1fr]' : 'grid-rows-[0fr]'}`}
          >
            <div
              ref={panel}
              id="sheet-content"
              role="tabpanel"
              aria-labelledby={`tab-${tab}`}
              inert={!expanded && !wide}
              className="min-h-0 overflow-y-auto max-md:max-h-[40vh]"
            >
              {tab === 'tramos' && (
                <>
                  {detail(showWhy)}
                  {ranking}
                </>
              )}
              {tab === 'simulacion' && simulation}
              {tab === 'porque' && why}
            </div>
          </div>
        </aside>
      </div>
      {footer}
    </div>
  )
}
