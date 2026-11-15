import type { ReactNode } from 'react'
import { Message, Skeleton } from './ui.tsx'
import type { ZoneData, ZoneState } from './zoneData.ts'

// Shows the loading text or the error in place of a panel until the zone's files are ready.
export function ZoneGate({ state, children }: { state: ZoneState; children: (data: ZoneData) => ReactNode }) {
  if (state.status === 'loading') return <Skeleton />
  if (state.status === 'error') return <Message alert>{state.message}</Message>
  return <>{children(state.data)}</>
}
