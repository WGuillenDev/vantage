import type { Area } from './storage.ts'

export const NOTICE = 'Tramos críticos por consecuencia; no son derrumbes confirmados.'
export const UNVALIDATED_BANNER = 'Zona no validada: sus resultados no se han revisado.'
export const REFERRAL_NOTE = 'El orden de los tramos depende de qué hospitales cuentan como referencia: con otro conjunto, los tramos críticos cambian.'

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

export const NO_ROUTE = 'sin ruta al hospital de referencia'

export const suspectLabel = (communityId: string, suspectIds: string[]): string =>
  suspectIds.includes(communityId) ? `${NO_ROUTE} (posible artefacto del modelo)` : NO_ROUTE

export const simulationNote = (communitiesWithoutRoute: number): string | null =>
  communitiesWithoutRoute > 0 ? 'Las comunidades sin ruta pueden incluir artefactos del modelo.' : null
