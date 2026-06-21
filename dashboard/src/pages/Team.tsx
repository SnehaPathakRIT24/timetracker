import { useQuery } from '@tanstack/react-query'
import { getDailyReport, getWeeklyReport } from '../lib/api'
import { CATEGORY_COLORS, formatSeconds } from '../lib/utils'
import { format } from 'date-fns'

const BUSINESSES = ['Next Level', 'Outgrow Media', 'Be Rolling Media', 'Admin', 'Personal']

export default function Team() {
  const today = format(new Date(), 'yyyy-MM-dd')

  const { data: daily } = useQuery({
    queryKey: ['daily', today],
    queryFn: () => getDailyReport(today),
    refetchInterval: 60_000,
  })

  const { data: weekly } = useQuery({
    queryKey: ['weekly'],
    queryFn: () => getWeeklyReport(),
  })

  const members: any[] = daily?.members || []
  const weeklyMembers: any[] = weekly?.per_member || []

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-xl font-bold text-white">Team</h1>
        <p className="text-gray-500 text-sm">Side-by-side comparison</p>
      </div>

      {/* Today comparison */}
      <h2 className="text-sm font-medium text-gray-400 mb-3">Today</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4 mb-8">
        {members.map((m: any) => (
          <div key={m.member_id} className="bg-gray-900 rounded-xl p-5">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-9 h-9 bg-indigo-600 rounded-full flex items-center justify-center font-bold">
                {m.member_name[0]}
              </div>
              <div>
                <p className="font-medium text-white">{m.member_name}</p>
                <p className="text-xs text-gray-500">{formatSeconds(m.total_seconds)} today</p>
              </div>
            </div>

            {/* Stacked bar */}
            <div className="flex h-3 rounded-full overflow-hidden mb-3">
              {m.breakdown.map((b: any) => (
                <div
                  key={b.category}
                  style={{
                    width: `${b.percentage}%`,
                    background: CATEGORY_COLORS[b.category] || '#94a3b8',
                  }}
                  title={`${b.category}: ${formatSeconds(b.total_seconds)}`}
                />
              ))}
            </div>

            <div className="space-y-1.5">
              {m.breakdown.map((b: any) => (
                <div key={b.category} className="flex items-center gap-2 text-xs">
                  <div
                    className="w-2 h-2 rounded-full flex-shrink-0"
                    style={{ background: CATEGORY_COLORS[b.category] || '#94a3b8' }}
                  />
                  <span className="text-gray-400 flex-1">{b.category}</span>
                  <span className="text-gray-300">{formatSeconds(b.total_seconds)}</span>
                  <span className="text-gray-500 w-10 text-right">{b.percentage}%</span>
                </div>
              ))}
            </div>
          </div>
        ))}

        {members.length === 0 && (
          <p className="text-gray-600 col-span-3 text-center py-8">No activity today yet</p>
        )}
      </div>

      {/* Weekly comparison table */}
      <h2 className="text-sm font-medium text-gray-400 mb-3">This week — hours per business</h2>
      <div className="bg-gray-900 rounded-xl overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-800">
              <th className="text-left px-4 py-3 text-gray-500 font-medium">Team member</th>
              {BUSINESSES.map((b) => (
                <th key={b} className="text-right px-4 py-3 text-gray-500 font-medium text-xs">
                  <span style={{ color: CATEGORY_COLORS[b] }}>{b}</span>
                </th>
              ))}
              <th className="text-right px-4 py-3 text-gray-500 font-medium">Total</th>
            </tr>
          </thead>
          <tbody>
            {weeklyMembers.map((m: any, i: number) => (
              <tr
                key={m.member_id}
                className={`border-b border-gray-800/50 ${i % 2 === 0 ? 'bg-gray-900' : 'bg-gray-900/50'}`}
              >
                <td className="px-4 py-3 text-gray-200 font-medium">{m.member_name}</td>
                {BUSINESSES.map((b) => (
                  <td key={b} className="px-4 py-3 text-right text-gray-400">
                    {m.breakdown[b] ? formatSeconds(m.breakdown[b]) : '—'}
                  </td>
                ))}
                <td className="px-4 py-3 text-right text-gray-200 font-medium">
                  {formatSeconds(m.total_seconds)}
                </td>
              </tr>
            ))}
            {weeklyMembers.length === 0 && (
              <tr>
                <td colSpan={7} className="px-4 py-8 text-center text-gray-600">
                  No data for this week
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
