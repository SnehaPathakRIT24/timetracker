import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getTeamMembers, addTeamMember, getRules, addRule, deleteRule } from '../lib/api'
import { useState } from 'react'
import { Plus, Trash2, Users, Shield } from 'lucide-react'
import toast from 'react-hot-toast'
import { isAdmin } from '../lib/utils'

const CATEGORIES = ['Next Level', 'Outgrow Media', 'Be Rolling Media', 'Admin', 'Personal', 'Unknown']
const MATCH_TYPES = ['contains', 'startswith', 'exact', 'regex']
const FIELDS = ['window_title', 'app_name', 'url']

export default function Settings() {
  const qc = useQueryClient()
  const admin = isAdmin()

  const { data: members = [] } = useQuery({ queryKey: ['members'], queryFn: getTeamMembers })
  const { data: rules = [] } = useQuery({ queryKey: ['rules'], queryFn: getRules, enabled: admin })

  // Add member form
  const [newMember, setNewMember] = useState({ name: '', email: '', password: '', role: 'member' })
  const addMemberMutation = useMutation({
    mutationFn: addTeamMember,
    onSuccess: () => {
      toast.success('Team member added')
      setNewMember({ name: '', email: '', password: '', role: 'member' })
      qc.invalidateQueries({ queryKey: ['members'] })
    },
    onError: (e: any) => toast.error(e.response?.data?.detail || 'Failed'),
  })

  // Add rule form
  const [newRule, setNewRule] = useState({
    pattern: '', match_type: 'contains', field: 'window_title', category: 'Next Level', priority: 100
  })
  const addRuleMutation = useMutation({
    mutationFn: addRule,
    onSuccess: () => {
      toast.success('Rule added')
      setNewRule({ pattern: '', match_type: 'contains', field: 'window_title', category: 'Next Level', priority: 100 })
      qc.invalidateQueries({ queryKey: ['rules'] })
    },
  })
  const deleteRuleMutation = useMutation({
    mutationFn: deleteRule,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['rules'] }),
  })

  return (
    <div className="max-w-3xl space-y-8">
      <div>
        <h1 className="text-xl font-bold text-white">Settings</h1>
        <p className="text-gray-500 text-sm">Manage team and classification rules</p>
      </div>

      {/* Team members */}
      <section className="bg-gray-900 rounded-xl p-6">
        <div className="flex items-center gap-2 mb-5">
          <Users size={16} className="text-indigo-400" />
          <h2 className="font-medium text-white">Team Members</h2>
        </div>

        <div className="space-y-2 mb-5">
          {members.map((m: any) => (
            <div key={m.id} className="flex items-center gap-3 py-2 border-b border-gray-800">
              <div className="w-8 h-8 bg-indigo-700 rounded-full flex items-center justify-center text-sm font-bold">
                {m.name[0]}
              </div>
              <div className="flex-1">
                <p className="text-sm text-white">{m.name}</p>
                <p className="text-xs text-gray-500">{m.email}</p>
              </div>
              {m.role === 'admin' && (
                <span className="flex items-center gap-1 text-xs text-indigo-400 bg-indigo-900/30 px-2 py-0.5 rounded-full">
                  <Shield size={10} /> Admin
                </span>
              )}
            </div>
          ))}
        </div>

        {admin && (
          <div className="border-t border-gray-800 pt-4">
            <p className="text-xs text-gray-500 mb-3">Add team member</p>
            <div className="grid grid-cols-2 gap-3">
              <input
                placeholder="Name"
                value={newMember.name}
                onChange={(e) => setNewMember({ ...newMember, name: e.target.value })}
                className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white"
              />
              <input
                placeholder="Email"
                type="email"
                value={newMember.email}
                onChange={(e) => setNewMember({ ...newMember, email: e.target.value })}
                className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white"
              />
              <input
                placeholder="Password"
                type="password"
                value={newMember.password}
                onChange={(e) => setNewMember({ ...newMember, password: e.target.value })}
                className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white"
              />
              <select
                value={newMember.role}
                onChange={(e) => setNewMember({ ...newMember, role: e.target.value })}
                className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-300"
              >
                <option value="member">Member</option>
                <option value="admin">Admin</option>
              </select>
            </div>
            <button
              onClick={() => addMemberMutation.mutate(newMember)}
              disabled={addMemberMutation.isPending}
              className="mt-3 flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-sm px-4 py-2 rounded-lg"
            >
              <Plus size={14} /> Add member
            </button>
          </div>
        )}
      </section>

      {/* Classification rules */}
      {admin && (
        <section className="bg-gray-900 rounded-xl p-6">
          <h2 className="font-medium text-white mb-1">Classification Rules</h2>
          <p className="text-xs text-gray-500 mb-5">
            Rules are checked before AI — they're free and instant.
            Lower priority number = checked first.
          </p>

          <div className="space-y-2 mb-5">
            {rules.map((r: any) => (
              <div key={r.id} className="flex items-center gap-3 py-2 border-b border-gray-800 text-sm">
                <span className="text-gray-500 w-6 text-right text-xs">{r.priority}</span>
                <span className="text-gray-400 text-xs">{r.field}</span>
                <span className="text-gray-400 text-xs">{r.match_type}</span>
                <code className="text-indigo-300 flex-1 truncate text-xs bg-gray-800 px-2 py-0.5 rounded">
                  {r.pattern}
                </code>
                <span className="text-xs text-gray-300">→</span>
                <span className="text-xs font-medium text-gray-200">{r.category}</span>
                <button
                  onClick={() => deleteRuleMutation.mutate(r.id)}
                  className="text-gray-600 hover:text-red-400"
                >
                  <Trash2 size={13} />
                </button>
              </div>
            ))}
            {rules.length === 0 && (
              <p className="text-gray-600 text-sm">No rules yet. Add one below.</p>
            )}
          </div>

          <div className="border-t border-gray-800 pt-4">
            <p className="text-xs text-gray-500 mb-3">Add rule</p>
            <div className="grid grid-cols-2 gap-3">
              <input
                placeholder="Pattern (e.g. BeRolling)"
                value={newRule.pattern}
                onChange={(e) => setNewRule({ ...newRule, pattern: e.target.value })}
                className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white col-span-2"
              />
              <select
                value={newRule.field}
                onChange={(e) => setNewRule({ ...newRule, field: e.target.value })}
                className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-300"
              >
                {FIELDS.map((f) => <option key={f}>{f}</option>)}
              </select>
              <select
                value={newRule.match_type}
                onChange={(e) => setNewRule({ ...newRule, match_type: e.target.value })}
                className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-300"
              >
                {MATCH_TYPES.map((t) => <option key={t}>{t}</option>)}
              </select>
              <select
                value={newRule.category}
                onChange={(e) => setNewRule({ ...newRule, category: e.target.value })}
                className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-300"
              >
                {CATEGORIES.map((c) => <option key={c}>{c}</option>)}
              </select>
              <input
                type="number"
                placeholder="Priority (1=highest)"
                value={newRule.priority}
                onChange={(e) => setNewRule({ ...newRule, priority: parseInt(e.target.value) })}
                className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white"
              />
            </div>
            <button
              onClick={() => addRuleMutation.mutate(newRule)}
              disabled={!newRule.pattern || addRuleMutation.isPending}
              className="mt-3 flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-sm px-4 py-2 rounded-lg"
            >
              <Plus size={14} /> Add rule
            </button>
          </div>
        </section>
      )}
    </div>
  )
}
