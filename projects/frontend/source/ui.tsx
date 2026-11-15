import type { ButtonHTMLAttributes, ReactNode } from 'react'

type Tone = 'neutral' | 'warning' | 'danger' | 'info'

const TONES: Record<Tone, string> = {
  neutral: 'bg-slate-100 text-slate-700',
  warning: 'bg-amber-100 text-amber-900',
  danger: 'bg-red-100 text-red-800',
  info: 'bg-sky-100 text-sky-800',
}

export function Badge({ tone = 'neutral', children }: { tone?: Tone; children: ReactNode }) {
  return <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ${TONES[tone]}`}>{children}</span>
}

export function Stat({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="min-w-0 rounded-lg bg-slate-50 px-3 py-2">
      <dt className="text-xs text-muted">{label}</dt>
      <dd className="truncate text-base font-semibold tabular-nums">{value}</dd>
    </div>
  )
}

const VARIANTS = {
  primary: 'bg-brand text-white hover:bg-amber-800 disabled:bg-slate-300 disabled:text-slate-600',
  secondary: 'border border-line bg-white text-ink hover:bg-slate-50',
  ghost: 'text-muted hover:bg-slate-100',
}

export function Button({
  variant = 'secondary',
  className = '',
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: keyof typeof VARIANTS }) {
  return (
    <button
      type="button"
      {...props}
      className={`inline-flex items-center justify-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-medium transition-colors max-md:min-h-11 max-md:min-w-11 ${VARIANTS[variant]} ${className}`}
    />
  )
}

export function Message({ children, alert = false }: { children: ReactNode; alert?: boolean }) {
  return (
    <p role={alert ? 'alert' : undefined} className="p-4 text-sm text-muted">
      {children}
    </p>
  )
}

// Placeholder rows while a panel waits for the zone's files.
export function Skeleton({ rows = 5 }: { rows?: number }) {
  return (
    <div role="status" aria-label="Cargando" className="animate-pulse space-y-3 p-3">
      {Array.from({ length: rows }, (_, i) => (
        <div key={i} className="space-y-1.5">
          <div className="h-3.5 w-2/3 rounded bg-slate-200" />
          <div className="h-3 w-full rounded bg-slate-100" />
        </div>
      ))}
    </div>
  )
}
