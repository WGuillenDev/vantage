import type { ReactNode } from 'react'
import { Message } from './ui.tsx'
import type { ZoneData, ZoneState } from './zoneData.ts'

// Shows the loading text or the error in place of a panel until the zone's files are ready.
export function ZoneGate({ state, loading = 'Cargando…', children }: { state: ZoneState; loading?: string; children: (data: ZoneData) => ReactNode }) {
  if (state.status === 'loading') return <Message>{loading}</Message>
  if (state.status === 'error') return <Message alert>{state.message}</Message>
  return <>{children(state.data)}</>
}
