import { Layout } from './Layout.tsx'
import { MapView } from './MapView.tsx'
import { SegmentDetail } from './SegmentDetail.tsx'
import { SegmentRanking } from './SegmentRanking.tsx'
import { Simulation } from './Simulation.tsx'
import { TrustFooter, TrustHeader } from './TrustSignals.tsx'
import { useZoneData } from './zoneData.ts'
import { WhyPanel } from './WhyPanel.tsx'
import { ZonePicker } from './ZonePicker.tsx'

function App() {
  const zoneData = useZoneData()
  // The zone name is shown by the picker, so the status only says loading or the error.
  const status = zoneData === null ? 'Cargando…' : typeof zoneData === 'string' ? zoneData : null

  return (
    <Layout
      header={<TrustHeader data={zoneData} />}
      footer={<TrustFooter data={zoneData} />}
      ranking={<SegmentRanking data={zoneData} />}
      detail={(onWhy) => <SegmentDetail data={zoneData} onWhy={onWhy} />}
      simulation={<Simulation data={zoneData} />}
      why={<WhyPanel data={zoneData} />}
      map={<MapView data={zoneData} />}
      overlay={
        <div className="absolute left-2 right-2 top-2 flex flex-wrap items-center gap-x-3 rounded bg-white/90 px-2 py-1 text-sm md:right-auto">
          <ZonePicker />
          {status !== null && <p role={typeof zoneData === 'string' ? 'alert' : undefined}>{status}</p>}
        </div>
      }
    />
  )
}

export default App
