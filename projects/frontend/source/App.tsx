import { Route } from 'lucide-react'
import { lazy, Suspense } from 'react'
import { Layout } from './Layout.tsx'
import { MapView } from './MapView.tsx'
import { SegmentDetail } from './SegmentDetail.tsx'
import { SegmentRanking } from './SegmentRanking.tsx'
import { Simulation } from './Simulation.tsx'
import { TrustFooter, TrustHeader } from './TrustSignals.tsx'
import { Message } from './ui.tsx'
import { useZoneData, type ZoneState } from './zoneData.ts'
import { ZonePicker } from './ZonePicker.tsx'

const WhyPanel = lazy(() => import('./WhyPanel.tsx'))

function TopBar({ state }: { state: ZoneState }) {
  return (
    <header className="flex items-center gap-4 border-b border-line bg-white px-3 py-2">
      <h1 className="flex items-center gap-1.5 text-base font-bold tracking-wide">
        <Route aria-hidden="true" className="h-5 w-5 text-brand" />
        VANTAGE
      </h1>
      <ZonePicker />
      {state.status === 'loading' && <p className="text-sm text-muted">Cargando…</p>}
      {state.status === 'error' && <p className="truncate text-sm text-red-800">{state.message}</p>}
    </header>
  )
}

function App() {
  const state = useZoneData()

  return (
    <Layout
      header={
        <>
          <TopBar state={state} />
          <TrustHeader state={state} />
        </>
      }
      footer={<TrustFooter state={state} />}
      ranking={<SegmentRanking state={state} />}
      detail={(onWhy) => <SegmentDetail state={state} onWhy={onWhy} />}
      simulation={<Simulation state={state} />}
      why={
        <Suspense fallback={<Message>Cargando…</Message>}>
          <WhyPanel state={state} />
        </Suspense>
      }
      map={<MapView state={state} />}
    />
  )
}

export default App
