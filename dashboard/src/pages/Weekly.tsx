import { useQuery } from '@tanstack/react-query'
import { getWeeklyReport } from '../lib/api'
import { CATEGORY_COLORS, formatSeconds } from '../lib/utils'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer, CartesianGrid
} from 'recharts'
import { format, startOfWeek, subWeeks, addWeeks } from 'date-fns'
import { useState } from 'react'
import { ChevronLeft, ChevronRight } from 'lucide-react'

const CATS = ['Next Level', 'Outgrow Media', 'Be Rolling Media', 'Admin', 'Personal']

export default function Weekly() {
  const [weekOffset, setWeekOffset] = useState(0)
  const weekStart = format(
    addWeeks(startOfWeek(new Date(), { weekStartsOn: 1 }), weekOffset),
    'yyyy-MM-dd'
  )

  const { data, isLoading } = useQuery({
    queryKey: ['weekly', weekStart],
    queryFn: () => getWeeklyReport(weekStart),
  })

  const chartData = (data?.per_day || []).map((d: any) => ({
    date: format(new Date(d.date), 'EEE d'),
    ...Object.fromEntries(
      CATS.map((cat) => [cat, Math.round((d.breakdown[cat] || 0) / 3600 * 10) / 10])
    ),
  }))

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-bold text-white">Weekly View</h1>
          <p className="text-gray-500 text-sm">
            {data?.week_start} → {data?.week_end}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setWeekOffset((o) => o - 1)}
            className="p-1.5 rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-400"
          >
            <ChevronLeft size={16} />
          </button>
          <button
            onClick={() => setWeekOffset(0)}
            className="px-3 py-1.5 text-xs rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-300"
          >
            This week
          </button>
          <button
            onClick={() => setWeekOffset((o) => o + 1)}
            disabled={weekOffset >= 0}
            className="p-1.5 rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-400 disabled:opacity-30"
          >
            <ChevronRight size={16} />
          </button>
        </div>
      </div>

      {isLoading ? (
        <div className="text-gray-500 text-center py-20">Loading…</div>
      ) : (
        <>
          {/* Daily bar chart */}
          <div className="bg-gray-900 rounded-xl p-5 mb-6">
            <h2 className="text-sm font-medium text-gray-400 mb-4">Hours per day by business</h2>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={chartData} barCategoryGap="30%">
                <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
                <XAxis dataKey="date" tick={{ fill: '#6b7280', fontSize: 12 }} />
                <YAxis tick={{ fill: '#6b7280', fontSize: 12 }} unit="h" />
                <Tooltip
                  contentStyle={{ background: '#111827', border: 'none', borderRadius: 8 }}
                  formatter={(v: number) => [`${v}h`]}
                />
                <Legend formatter={(v) => <span className="text-xs text-gray-300">{v}</span>} />
                {CATS.map((cat) => (
                  <Bar key={cat} dataKey={cat} stackId="a" fill={CATEGORY_COLORS[cat]} radius={[0, 0, 0, 0]} />
                ))}
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Per member breakdown */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {(data?.per_member || []).map((m: any) => (
              <div key={m.member_id} className="bg-gray-900 rounded-xl p-5">
                <div className="flex items-center gap-2 mb-4">
                  <div className="w-7 h-7 bg-indigo-600 rounded-full flex items-center justify-center text-xs font-bold">
                    {m.member_name[0]}
                  </div>
                  <div>
                    <p className="text-sm font-medium text-white">{m.member_name}</p>
                    <p className="text-xs text-gray-500">{formatSeconds(m.total_seconds)} this week</p>
                  </div>
                </div>
                <div className="space-y-2">
                  {CATS.map((cat) => {
                    const secs = m.breakdown[cat] || 0
                    const pct = m.total_seconds > 0 ? (secs / m.total_seconds) * 100 : 0
                    if (secs === 0) return null
                    return (
                      <div key={cat}>
                        <div className="flex justify-between text-xs mb-0.5">
                          <span style={{ color: CATEGORY_COLORS[cat] }}>{cat}</span>
                          <span className="text-gray-500">{formatSeconds(secs)}</span>
                        </div>
                        <div className="bg-gray-800 rounded-full h-1.5">
                          <div
                            className="h-1.5 rounded-full"
                            style={{ width: `${pct}%`, background: CATEGORY_COLORS[cat] }}
                          />
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  )
}
