import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getLowConfidence, correctClassification } from '../lib/api'
import { CATEGORY_COLORS } from '../lib/utils'
import { format } from 'date-fns'
import toast from 'react-hot-toast'

const CATEGORIES = ['Next Level', 'Outgrow Media', 'Be Rolling Media', 'Admin', 'Personal', 'Unknown']

export default function Corrections() {
  const qc = useQueryClient()

  const { data = [], isLoading } = useQuery({
    queryKey: ['low-confidence'],
    queryFn: getLowConfidence,
  })

  const correct = useMutation({
    mutationFn: ({ id, cat }: { id: number; cat: string }) =>
      correctClassification(id, cat),
    onSuccess: () => {
      toast.success('Saved — AI will learn from this')
      qc.invalidateQueries({ queryKey: ['low-confidence'] })
    },
    onError: () => toast.error('Failed to save correction'),
  })

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-xl font-bold text-white">Review Low-Confidence Classifications</h1>
        <p className="text-gray-500 text-sm">
          {data.length} records below 70% confidence need review
        </p>
      </div>

      {isLoading && <div className="text-gray-500 text-center py-20">Loading…</div>}

      {!isLoading && data.length === 0 && (
        <div className="bg-gray-900 rounded-xl p-12 text-center">
          <p className="text-green-400 text-lg font-medium">All caught up! ✓</p>
          <p className="text-gray-500 text-sm mt-1">No low-confidence records to review</p>
        </div>
      )}

      <div className="space-y-2">
        {data.map((rec: any) => {
          const color = CATEGORY_COLORS[rec.category] || '#94a3b8'
          const conf = Math.round(rec.confidence * 100)

          return (
            <div key={rec.id} className="bg-gray-900 rounded-xl px-5 py-4 flex items-center gap-4">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-xs text-gray-500">
                    {format(new Date(rec.timestamp), 'MMM d, HH:mm')}
                  </span>
                  <span className="text-xs text-gray-600">·</span>
                  <span className="text-xs text-gray-500">{rec.member_name}</span>
                </div>
                <p className="text-sm font-medium text-gray-200 truncate">{rec.app_name}</p>
                {rec.window_title && (
                  <p className="text-xs text-gray-500 truncate">{rec.window_title}</p>
                )}
                {rec.url && (
                  <p className="text-xs text-gray-600 truncate">{rec.url}</p>
                )}
              </div>

              {/* Current AI classification */}
              <div className="flex-shrink-0 text-right">
                <span
                  className="text-xs px-2.5 py-1 rounded-full"
                  style={{ background: color + '22', color }}
                >
                  {rec.category}
                </span>
                <p className="text-xs text-yellow-500 mt-1">AI: {conf}% sure</p>
              </div>

              {/* Correct it */}
              <select
                className="flex-shrink-0 text-sm bg-gray-800 border border-gray-700 text-gray-300 rounded-lg px-3 py-1.5"
                defaultValue={rec.category}
                onChange={(e) => {
                  if (e.target.value !== rec.category) {
                    correct.mutate({ id: rec.id, cat: e.target.value })
                  }
                }}
              >
                {CATEGORIES.map((c) => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            </div>
          )
        })}
      </div>
    </div>
  )
}
