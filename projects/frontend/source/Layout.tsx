import { useState, useSyncExternalStore, type ReactNode } from 'react'
import { useAppStore } from './store.ts'

type TabId = 'tramos' | 'simulacion' | 'porque'

const WIDE_QUERY = '(min-width: 768px)'

const TABS: { id: TabId; label: string; narrowOnly: boolean }[] = [
  { id: 'tramos', label: 'Tramos', narrowOnly: false },
  { id: 'simulacion', label: 'Simulación', narrowOnly: false },
  { id: 'porque', label: '¿Por qué?', narrowOnly: true },
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

// Placeholders stand in for panels owned by other slices (closure-whatif, segment-detail, trust-signals).
function Placeholder({ children }: { children: ReactNode }) {
  return <p className="p-3 text-sm text-gray-600">{children}</p>
}

export function Layout({ header, footer, map, overlay, ranking }: {
  header: ReactNode
  footer: ReactNode
  map: ReactNode
  overlay: ReactNode
  ranking: ReactNode
}) {
  const wide = useIsWide()
  const selected = useAppStore((state) => state.selectedUnitId)
  const [tab, setTab] = useState<TabId>('tramos')
  const [expanded, setExpanded] = useState(false)
  const [whyOpen, setWhyOpen] = useState(false)

  // INV-05: selecting a unit expands the sheet (it only matters on narrow screens).
  const [seen, setSeen] = useState(selected)
  if (seen !== selected) {
    setSeen(selected)
    if (selected !== null) {
      setTab('tramos')
      setExpanded(true)
    }
  }

  const tabs = TABS.filter((item) => wide ? !item.narrowOnly : true)
  const activeTab = tabs.some((item) => item.id === tab) ? tab : 'tramos'

  return (
    <div className="flex h-full flex-col overflow-x-hidden">
      {header}
      <div className="relative flex min-h-0 min-w-0 flex-1 flex-col md:flex-row">
        <div className="relative min-h-0 min-w-0 flex-1 md:order-2">
          {map}
          {overlay}
          {wide && (
            <div className="absolute right-2 top-2 flex w-72 flex-col items-end gap-1">
              <button
                type="button"
                aria-expanded={whyOpen}
                aria-controls="why-card"
                onClick={() => setWhyOpen((value) => !value)}
                className="rounded bg-white/90 px-3 py-1 text-sm shadow"
              >
                ¿Por qué?
              </button>
              {whyOpen && (
                <section id="why-card" aria-label="¿Por qué?" className="w-full rounded bg-white shadow">
                  <Placeholder>Explicación «¿Por qué?»: pendiente.</Placeholder>
                </section>
              )}
            </div>
          )}
        </div>
        <aside className="flex min-w-0 shrink-0 flex-col border-t bg-white md:order-1 md:w-80 md:border-r md:border-t-0">
          <button
            type="button"
            aria-expanded={expanded}
            aria-controls="sheet-content"
            onClick={() => setExpanded((value) => !value)}
            className="flex min-h-11 min-w-11 items-center justify-center text-sm text-gray-700 md:hidden"
          >
            <span aria-hidden="true" className="mr-2 h-1 w-8 rounded bg-gray-400" />
            {expanded ? 'Contraer panel' : 'Expandir panel'}
          </button>
          <div role="tablist" className="flex border-b">
            {tabs.map((item) => (
              <button
                key={item.id}
                type="button"
                role="tab"
                id={`tab-${item.id}`}
                aria-selected={activeTab === item.id}
                aria-controls="sheet-content"
                onClick={() => {
                  setTab(item.id)
                  setExpanded(true)
                }}
                className={`min-h-11 min-w-11 flex-1 px-2 text-sm ${activeTab === item.id ? 'border-b-2 border-amber-600 font-semibold' : 'text-gray-700'}`}
              >
                {item.label}
              </button>
            ))}
          </div>
          <div
            id="sheet-content"
            role="tabpanel"
            aria-labelledby={`tab-${activeTab}`}
            className={`${expanded ? 'flex' : 'hidden'} max-h-[30vh] min-h-0 flex-col overflow-y-auto md:flex md:max-h-none md:flex-1`}
          >
            {activeTab === 'tramos' && (
              <>
                {selected !== null && (
                  <div className="md:hidden">
                    <Placeholder>Detalle del tramo seleccionado: pendiente.</Placeholder>
                  </div>
                )}
                <div className="min-h-0 flex-1">{ranking}</div>
              </>
            )}
            {activeTab === 'simulacion' && <Placeholder>Simulación de cierre: pendiente.</Placeholder>}
            {activeTab === 'porque' && <Placeholder>Explicación «¿Por qué?»: pendiente.</Placeholder>}
          </div>
        </aside>
      </div>
      {footer}
    </div>
  )
}
