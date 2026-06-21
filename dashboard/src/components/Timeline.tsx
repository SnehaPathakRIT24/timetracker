import { CATEGORY_COLORS, formatSeconds } from '../lib/utils'

interface TimelineEntry {
  timestamp: string
  app_name?: string
  window_title?: string
  url?: string
  duration_seconds: number
  category: string
  confidence: number
  id: number
}

interface Props {
  entries: TimelineEntry[]
  onCorrect?: (id: number, category: string) => void
}

const CATEGORIES = ['Next Level', 'Outgrow Media', 'Be Rolling Media', 'Admin', 'Personal', 'Unknown']

export default function Timeline({ entries, onCorrect }: Props) {
  if (!entries?.length) {
    return <p className="text-gray-500 text-sm text-center py-8">No activity recorded yet today.</p>
  }

  return (
    <div className="space-y-1.5">
      {entries.map((e) => {
        const color = CATEGORY_COLORS[e.category] || '#94a3b8'
        const time = new Date(e.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        const lowConf = e.confidence < 0.7

        return (
          <div
            key={e.id}
            className="flex items-center gap-3 bg-gray-900 rounded-lg px-4 py-2.5 group"
          >
            <div className="w-1 h-8 rounded-full flex-shrink-0" style={{ background: color }} />
            <span className="text-xs text-gray-500 w-12 flex-shrink-0">{time}</span>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-gray-200 truncate">
                {e.app_name || e.category}
              </p>
              {e.window_title && (
                <p className="text-xs text-gray-500 truncate">{e.window_title}</p>
              )}
              {e.url && (
                <p className="text-xs text-gray-600 truncate">{e.url}</p>
              )}
            </div>
            <span className="text-xs text-gray-500 flex-shrink-0">{formatSeconds(e.duration_seconds)}</span>
            <span
              className="text-xs px-2 py-0.5 rounded-full flex-shrink-0"
              style={{ background: color + '22', color }}
            >
              {e.category}
            </span>
            {lowConf && onCorrect && (
              <select
                className="text-xs bg-gray-800 border border-yellow-600 text-yellow-400 rounded px-1.5 py-0.5 opacity-0 group-hover:opacity-100 transition-opacity"
                defaultValue=""
                onChange={(ev) => ev.target.value && onCorrect(e.id, ev.target.value)}
              >
                <option value="" disabled>Fix?</option>
                {CATEGORIES.map((c) => <option key={c} value={c}>{c}</option>)}
              </select>
            )}
          </div>
        )
      })}
    </div>
  )
}
