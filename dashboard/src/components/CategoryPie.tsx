import { PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { CATEGORY_COLORS, formatSeconds } from '../lib/utils'

interface Props {
  breakdown: { category: string; total_seconds: number; percentage: number }[]
  title?: string
}

export default function CategoryPie({ breakdown, title }: Props) {
  const data = breakdown.map((b) => ({
    name: b.category,
    value: b.total_seconds,
    pct: b.percentage,
  }))

  return (
    <div className="bg-gray-900 rounded-xl p-5">
      {title && <h3 className="text-sm font-medium text-gray-400 mb-4">{title}</h3>}
      <ResponsiveContainer width="100%" height={240}>
        <PieChart>
          <Pie
            data={data}
            dataKey="value"
            nameKey="name"
            cx="50%"
            cy="50%"
            innerRadius={60}
            outerRadius={90}
            paddingAngle={2}
          >
            {data.map((entry) => (
              <Cell key={entry.name} fill={CATEGORY_COLORS[entry.name] || '#94a3b8'} />
            ))}
          </Pie>
          <Tooltip
            contentStyle={{ background: '#1f2937', border: 'none', borderRadius: 8 }}
            formatter={(v: number) => formatSeconds(v)}
          />
          <Legend
            formatter={(value) => (
              <span className="text-xs text-gray-300">{value}</span>
            )}
          />
        </PieChart>
      </ResponsiveContainer>
    </div>
  )
}
