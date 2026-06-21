import { useQuery, useMutation } from '@tanstack/react-query'
import { getDailyInsights, triggerInsights } from '../lib/api'
import { format, subDays } from 'date-fns'
import { useState } from 'react'
import { Lightbulb, AlertTriangle, TrendingUp, RefreshCw } from 'lucide-react'
import toast from 'react-hot-toast'

export default function Insights() {
  const [targetDate, setTargetDate] = useState(
    format(subDays(new Date(), 1), 'yyyy-MM-dd')
  )

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['insights', targetDate],
    queryFn: () => getDailyInsights(targetDate),
  })

  const generate = useMutation({
    mutationFn: () => triggerInsights(targetDate),
    onSuccess: () => {
      toast.success('Insights generated!')
      refetch()
    },
    onError: () => toast.error('Failed to generate insights'),
  })

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-bold text-white">AI Insights</h1>
          <p className="text-gray-500 text-sm">Daily AI-generated team summary</p>
        </div>
        <div className="flex items-center gap-3">
          <input
            type="date"
            value={targetDate}
            onChange={(e) => setTargetDate(e.target.value)}
            className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5 text-sm text-gray-300"
          />
          <button
            onClick={() => generate.mutate()}
            disabled={generate.isPending}
            className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-sm px-4 py-1.5 rounded-lg transition-colors"
          >
            <RefreshCw size={14} className={generate.isPending ? 'animate-spin' : ''} />
            Generate
          </button>
        </div>
      </div>

      {isLoading && <div className="text-gray-500 text-center py-20">Loading…</div>}

      {!isLoading && data?.message && (
        <div className="bg-gray-900 rounded-xl p-8 text-center">
          <Lightbulb className="mx-auto mb-3 text-gray-600" size={32} />
          <p className="text-gray-400">{data.message}</p>
          <p className="text-gray-600 text-sm mt-2">
            Click "Generate" to create insights for {targetDate}
          </p>
        </div>
      )}

      {data?.summary && (
        <div className="space-y-4">
          <div className="bg-gray-900 rounded-xl p-6">
            <div className="flex items-center gap-2 mb-3">
              <Lightbulb className="text-yellow-400" size={18} />
              <h2 className="font-medium text-white">Day Summary</h2>
            </div>
            <p className="text-gray-300 leading-relaxed">{data.summary}</p>
          </div>

          {data.anomalies?.length > 0 && (
            <div className="bg-gray-900 rounded-xl p-6 border border-yellow-900/50">
              <div className="flex items-center gap-2 mb-3">
                <AlertTriangle className="text-yellow-500" size={18} />
                <h2 className="font-medium text-white">Anomalies</h2>
              </div>
              <ul className="space-y-2">
                {data.anomalies.map((a: string, i: number) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-yellow-300">
                    <span className="mt-0.5 flex-shrink-0">⚠</span>
                    {a}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {data.recommendations?.length > 0 && (
            <div className="bg-gray-900 rounded-xl p-6 border border-green-900/50">
              <div className="flex items-center gap-2 mb-3">
                <TrendingUp className="text-green-400" size={18} />
                <h2 className="font-medium text-white">Recommendations for tomorrow</h2>
              </div>
              <ul className="space-y-2">
                {data.recommendations.map((r: string, i: number) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-green-300">
                    <span className="mt-0.5 flex-shrink-0">→</span>
                    {r}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
