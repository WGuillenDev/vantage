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
      <h1 className="flex items-center gap-2.5 text-lg font-extrabold tracking-[0.14em]">
        {/* The logo's navy outline needs a light plate to read on the dark bar. */}
        <span aria-hidden="true" className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-slate-50 p-0.5 shadow-[0_0_0_1px_rgb(255_255_255/0.1),0_4px_14px_-4px_rgb(45_212_191/0.5)]">
          <img src={`${import.meta.env.BASE_URL}vantage-logo.png`} alt="" width={32} height={32} className="h-8 w-8" />
        </span>
        <span className="bg-gradient-to-r from-white to-brand-strong bg-clip-text text-transparent">VANTAGE</span>
      </h1>
      <span aria-hidden="true" className="hidden h-5 w-px bg-line sm:block" />
      <ZonePicker />
      {state.status === 'loading' && <p className="text-sm text-muted">Cargando…</p>}
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
        <Suspense fallback={<Message>Cargando…</Message>}>
          <WhyPanel state={state} />
        </Suspense>
      }
      map={<MapView state={state} />}
    />
  )
}

export default App
