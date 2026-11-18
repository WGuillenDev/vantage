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
    <div className="flex items-center gap-4 border-b border-line bg-surface/95 px-3 py-2 backdrop-blur">
      <h1 className="text-lg font-semibold tracking-[0.22em] text-white">VANTAGE</h1>
      <span aria-hidden="true" className="hidden h-5 w-px bg-line sm:block" />
      <ZonePicker />
      {state.status === 'loading' && <p className="text-sm text-muted">Loading…</p>}
      {state.status === 'error' && <p className="truncate text-sm text-red-300">{state.message}</p>}
    </div>
  )
}

function App() {
  const state = useZoneData()

  return (
    <Layout
      header={
        <header>
          <TopBar state={state} />
          <TrustHeader state={state} />
        </header>
      }
      footer={<TrustFooter state={state} />}
      ranking={<SegmentRanking state={state} />}
      detail={(onWhy) => <SegmentDetail state={state} onWhy={onWhy} />}
      simulation={<Simulation state={state} />}
      why={
        <Suspense fallback={<Message>Loading…</Message>}>
          <WhyPanel state={state} />
        </Suspense>
      }
      map={<MapView state={state} />}
    />
  )
}

export default App
