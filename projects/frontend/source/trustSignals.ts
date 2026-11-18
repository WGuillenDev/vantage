import type { Area } from './storage.ts'

export const NOTICE = 'Critical segments by consequence; not confirmed landslides.'
export const UNVALIDATED_BANNER = 'Unvalidated zone: its results have not been reviewed.'
export const REFERRAL_NOTE = 'The order of the segments depends on which hospitals count as referral hospitals: with another set, the critical segments change.'

export interface TrustMeta {
  speed_model_kmh: Record<string, number>
  detection_limits?: { note?: string }
  attributions: string[]
  rain?: { end: string }
}

export const attributionLines = (meta: Pick<TrustMeta, 'attributions'>): string[] => meta.attributions

export const isUnvalidated = (zone: Area | undefined): boolean => zone?.validated === false

export function readingPanel(meta: TrustMeta, graph: { hospitals: { name: string }[] }) {
  return {
    speeds: Object.entries(meta.speed_model_kmh).map(([roadClass, kmh]) => ({ roadClass, kmh })),
    hospitals: graph.hospitals.map((hospital) => hospital.name),
    radarNote: meta.detection_limits?.note ?? null,
  }
}

export const NO_ROUTE = 'no route to the referral hospital'

export const suspectLabel = (communityId: string, suspectIds: string[]): string =>
  suspectIds.includes(communityId) ? `${NO_ROUTE} (possible model artifact)` : NO_ROUTE

export const simulationNote = (communitiesWithoutRoute: number): string | null =>
  communitiesWithoutRoute > 0 ? 'Communities without a route may include model artifacts.' : null
