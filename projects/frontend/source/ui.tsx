import type { ButtonHTMLAttributes, ReactNode } from 'react'

type Tone = 'neutral' | 'warning' | 'danger' | 'info'

const TONES: Record<Tone, string> = {
  neutral: 'bg-white/8 text-slate-200 ring-1 ring-inset ring-white/10',
  warning: 'bg-amber-400/12 text-amber-200 ring-1 ring-inset ring-amber-400/25',
  danger: 'bg-red-500/15 text-red-200 ring-1 ring-inset ring-red-400/30',
  info: 'bg-sky-400/12 text-sky-200 ring-1 ring-inset ring-sky-400/25',
}

export function Badge({ tone = 'neutral', children }: { tone?: Tone; children: ReactNode }) {
  return <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ${TONES[tone]}`}>{children}</span>
}

export function Stat({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="min-w-0 rounded-lg border border-line bg-raised px-3 py-2">
      <dt className="text-xs text-muted">{label}</dt>
      <dd className="truncate text-base font-semibold tabular-nums">{value}</dd>
    </div>
  )
}

const VARIANTS = {
  primary: 'bg-brand font-semibold text-brand-ink shadow-[0_0_0_1px_rgb(45_212_191/0.4),0_6px_20px_-6px_rgb(45_212_191/0.6)] hover:bg-brand-strong disabled:bg-white/10 disabled:text-slate-300 disabled:shadow-none',
  secondary: 'border border-line bg-raised text-ink hover:border-slate-500 hover:bg-white/5',
  ghost: 'text-muted hover:bg-white/5',
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
    <div role="status" aria-label="Loading" className="animate-pulse space-y-3 p-3">
      {Array.from({ length: rows }, (_, i) => (
        <div key={i} className="space-y-1.5">
          <div className="h-3.5 w-2/3 rounded bg-white/10" />
          <div className="h-3 w-full rounded bg-white/5" />
        </div>
      ))}
    </div>
  )
}
