export const CATEGORY_COLORS: Record<string, string> = {
  'Next Level': '#6366f1',
  'Outgrow Media': '#f59e0b',
  'Be Rolling Media': '#10b981',
  'Admin': '#64748b',
  'Personal': '#f43f5e',
  'Unknown': '#94a3b8',
}

export function formatSeconds(s: number): string {
  const h = Math.floor(s / 3600)
  const m = Math.floor((s % 3600) / 60)
  if (h > 0) return `${h}h ${m}m`
  return `${m}m`
}

export function getMember() {
  const raw = localStorage.getItem('member')
  return raw ? JSON.parse(raw) : null
}

export function isAdmin(): boolean {
  return getMember()?.role === 'admin'
}
