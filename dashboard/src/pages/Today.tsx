import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getDailyReport, correctClassification } from '../lib/api'
import { formatSeconds, isAdmin } from '../lib/utils'
import CategoryPie from '../components/CategoryPie'
import Timeline from '../components/Timeline'
import { format } from 'date-fns'
import toast from 'react-hot-toast'

export default function Today() {
  const today = format(new Date(), 'yyyy-MM-dd')
  const qc = useQueryClient()
  const admin = isAdmin()

  const { data, isLoading } = useQuery({
    queryKey: ['daily', today],
    queryFn: () => getDailyReport(today),
    refetchInterval: 60_000,
  })

  const correct = useMutation({
    mutationFn: ({ id, cat }: { id: number; cat: string }) =>
      correctClassification(id, cat),
    onSuccess: () => {
      toast.success('Classification corrected')
      qc.invalidateQueries({ queryKey: ['daily'] })
    },
  })

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64 text-gray-500">
        Loading today's activity…
      </div>
    )
  }

  const members: any[] = data?.members || []

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-bold text-white">Today</h1>
          <p className="text-gray-500 text-sm">{format(new Date(), 'EEEE, MMMM d')}</p>
        </div>
      </div>

      {members.length === 0 && (
        <div className="bg-gray-900 rounded-xl p-8 text-center text-gray-500">
          No activity recorded today yet. Make sure the agent is running.
        </div>
      )}

      <div className="space-y-8">
        {members.map((m: any) => (
          <div key={m.member_id}>
            <div className="flex items-center gap-3 mb-4">
              <div className="w-8 h-8 bg-indigo-600 rounded-full flex items-center justify-center text-sm font-bold">
                {m.member_name[0]}
              </div>
              <div>
                <h2 className="font-semibold text-white">{m.member_name}</h2>
                <p className="text-xs text-gray-500">{formatSeconds(m.total_seconds)} tracked today</p>
              </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-4">
              <CategoryPie breakdown={m.breakdown} title="Time breakdown" />

              {/* Top apps */}
              <div className="bg-gray-900 rounded-xl p-5 lg:col-span-2">
                <h3 className="text-sm font-medium text-gray-400 mb-4">Top apps</h3>
                <div className="space-y-2">
                  {m.top_apps?.slice(0, 8).map((a: any) => {
                    const pct = m.total_seconds > 0 ? (a.seconds / m.total_seconds) * 100 : 0
                    return (
                      <div key={a.app} className="flex items-center gap-3">
                        <span className="text-sm text-gray-300 w-40 truncate">{a.app}</span>
                        <div className="flex-1 bg-gray-800 rounded-full h-1.5">
                          <div
                            className="bg-indigo-500 h-1.5 rounded-full"
                            style={{ width: `${pct}%` }}
                          />
                        </div>
                        <span className="text-xs text-gray-500 w-14 text-right">
                          {formatSeconds(a.seconds)}
                        </span>
                      </div>
                    )
                  })}
                </div>
              </div>
            </div>

            {/* Timeline */}
            {m.timeline && (
              <div className="bg-gray-900 rounded-xl p-5">
                <h3 className="text-sm font-medium text-gray-400 mb-4">Activity timeline</h3>
                <Timeline
                  entries={m.timeline}
                  onCorrect={
                    admin || !isAdmin()
                      ? (id, cat) => correct.mutate({ id, cat })
                      : undefined
                  }
                />
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
