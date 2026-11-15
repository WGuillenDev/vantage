import { COMMUNITY_COLOR, HOSPITAL_COLOR } from './colors.ts'

// One drawing per point kind, shared by the map symbols, the legend and the segment detail so they always match.
const INNER = {
  community: `<circle cx="12" cy="12" r="11" fill="${COMMUNITY_COLOR}" stroke="#fff" stroke-width="1.5"/><circle cx="12" cy="9.2" r="2.6" fill="#fff"/><path d="M6.8 17.4c.5-2.6 2.6-4 5.2-4s4.7 1.4 5.2 4z" fill="#fff"/>`,
  hospital: `<circle cx="12" cy="12" r="11" fill="${HOSPITAL_COLOR}" stroke="#fff" stroke-width="1.5"/><path d="M10.2 6.2h3.6v3.6h3.6v4.4h-3.6v3.6h-3.6v-3.6H6.6V9.8h3.6z" fill="#fff"/>`,
}

export type PointKind = keyof typeof INNER

export const svgMarkup = (kind: PointKind, size: number): string =>
  `<svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}" viewBox="0 0 24 24">${INNER[kind]}</svg>`

export const iconDataUrl = (kind: PointKind, size: number): string => `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svgMarkup(kind, size))}`

export function PointIcon({ kind, size = 16, title }: { kind: PointKind; size?: number; title?: string }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width={size}
      height={size}
      viewBox="0 0 24 24"
      className="inline-block shrink-0"
      role={title ? 'img' : undefined}
      aria-label={title}
      aria-hidden={title ? undefined : true}
      dangerouslySetInnerHTML={{ __html: INNER[kind] }}
    />
  )
}
