import { Layout } from './Layout.tsx'
import { MapView } from './MapView.tsx'
import { SegmentRanking } from './SegmentRanking.tsx'
import { TrustFooter, TrustHeader } from './TrustSignals.tsx'
import { useZoneData } from './zoneData.ts'
import { ZonePicker } from './ZonePicker.tsx'

function App() {
  const zoneData = useZoneData()
  const status = zoneData === null ? 'Cargando…' : typeof zoneData === 'string' ? zoneData : zoneData.zone.name

  return (
    <Layout
      header={<TrustHeader data={zoneData} />}
      footer={<TrustFooter data={zoneData} />}
      ranking={<SegmentRanking data={zoneData} />}
      map={<MapView data={zoneData} />}
      overlay={
        <div className="absolute left-2 right-2 top-2 flex flex-wrap items-center gap-x-3 rounded bg-white/90 px-2 py-1 text-sm md:right-auto">
          <ZonePicker />
          <p role={typeof zoneData === 'string' ? 'alert' : undefined}>{status}</p>
        </div>
      }
    />
  )
}

export default App
