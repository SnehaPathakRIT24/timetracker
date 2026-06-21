import { useQuery } from '@tanstack/react-query'
import { getProjectsReport } from '../lib/api'
import { CATEGORY_COLORS, formatSeconds } from '../lib/utils'
import { RadialBarChart, RadialBar, Legend, ResponsiveContainer, Tooltip } from 'recharts'

const BUSINESSES = ['Next Level', 'Outgrow Media', 'Be Rolling Media']

function BusinessCard({ name, weekData, monthData }: any) {
  const color = CATEGORY_COLORS[name]
  const wSecs = weekData?.find((d: any) => d.category === name)?.seconds || 0
  const mSecs = monthData?.find((d: any) => d.category === name)?.seconds || 0
  const wPct = weekData?.find((d: any) => d.category === name)?.percentage || 0

  return (
    <div className="bg-gray-900 rounded-xl p-6 border-l-4" style={{ borderColor: color }}>
      <h3 className="font-semibold text-white mb-1">{name}</h3>
      <div className="grid grid-cols-2 gap-4 mt-4">
        <div>
          <p className="text-xs text-gray-500 mb-1">This week</p>
          <p className="text-2xl font-bold" style={{ color }}>
            {formatSeconds(wSecs)}
          </p>
          <p className="text-xs text-gray-500 mt-0.5">{wPct.toFixed(1)}% of tracked time</p>
        </div>
        <div>
          <p className="text-xs text-gray-500 mb-1">This month</p>
          <p className="text-2xl font-bold text-gray-300">
            {formatSeconds(mSecs)}
          </p>
        </div>
      </div>
    </div>
  )
}

export default function Projects() {
  const { data, isLoading } = useQuery({
    queryKey: ['projects'],
    queryFn: getProjectsReport,
    refetchInterval: 120_000,
  })

  if (isLoading) {
    return <div className="text-gray-500 text-center py-20">Loading…</div>
  }

  const week = data?.this_week || []
  const month = data?.this_month || []

  const radialData = BUSINESSES.map((b) => ({
    name: b,
    value: week.find((d: any) => d.category === b)?.percentage || 0,
    fill: CATEGORY_COLORS[b],
  }))

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-xl font-bold text-white">Projects</h1>
        <p className="text-gray-500 text-sm">Time allocation across businesses</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
        {BUSINESSES.map((b) => (
          <BusinessCard key={b} name={b} weekData={week} monthData={month} />
        ))}
      </div>

      <div className="bg-gray-900 rounded-xl p-6">
        <h2 className="text-sm font-medium text-gray-400 mb-4">This week's breakdown</h2>
        <div className="flex items-center gap-8">
          <ResponsiveContainer width={220} height={220}>
            <RadialBarChart
              cx="50%"
              cy="50%"
              innerRadius="30%"
              outerRadius="90%"
              data={radialData}
              startAngle={90}
              endAngle={-270}
            >
              <RadialBar dataKey="value" background={{ fill: '#1f2937' }} />
              <Tooltip
                contentStyle={{ background: '#111827', border: 'none', borderRadius: 8 }}
                formatter={(v: number) => [`${v.toFixed(1)}%`]}
              />
            </RadialBarChart>
          </ResponsiveContainer>

          <div className="space-y-3 flex-1">
            {week.map((d: any) => (
              <div key={d.category} className="flex items-center gap-3">
                <div
                  className="w-3 h-3 rounded-full flex-shrink-0"
                  style={{ background: CATEGORY_COLORS[d.category] || '#94a3b8' }}
                />
                <span className="text-sm text-gray-300 flex-1">{d.category}</span>
                <span className="text-sm text-gray-500">{formatSeconds(d.seconds)}</span>
                <span className="text-sm font-medium text-gray-300 w-12 text-right">
                  {d.percentage.toFixed(1)}%
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
