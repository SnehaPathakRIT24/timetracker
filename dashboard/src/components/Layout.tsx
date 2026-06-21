import { Outlet, NavLink, useNavigate } from 'react-router-dom'
import { useEffect, useRef } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import {
  Clock, BarChart2, FolderOpen, Users, AlertCircle,
  Settings, Lightbulb, LogOut
} from 'lucide-react'
import { getMember } from '../lib/utils'
import { createWebSocket } from '../lib/api'
import toast from 'react-hot-toast'

const NAV = [
  { to: '/today', icon: Clock, label: 'Today' },
  { to: '/weekly', icon: BarChart2, label: 'Weekly' },
  { to: '/projects', icon: FolderOpen, label: 'Projects' },
  { to: '/team', icon: Users, label: 'Team' },
  { to: '/corrections', icon: AlertCircle, label: 'Review' },
  { to: '/insights', icon: Lightbulb, label: 'Insights' },
  { to: '/settings', icon: Settings, label: 'Settings' },
]

export default function Layout() {
  const navigate = useNavigate()
  const qc = useQueryClient()
  const member = getMember()
  const wsRef = useRef<WebSocket | null>(null)

  useEffect(() => {
    const ws = createWebSocket()
    wsRef.current = ws
    ws.onmessage = (e) => {
      const data = JSON.parse(e.data)
      if (data.type === 'new_activity') {
        qc.invalidateQueries({ queryKey: ['daily'] })
        toast.success(`New activity from ${data.member_name}`, { duration: 2000 })
      }
    }
    return () => ws.close()
  }, [qc])

  function logout() {
    localStorage.removeItem('token')
    localStorage.removeItem('member')
    navigate('/login')
  }

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Sidebar */}
      <aside className="w-56 bg-gray-900 border-r border-gray-800 flex flex-col">
        <div className="p-5 border-b border-gray-800">
          <div className="flex items-center gap-2">
            <Clock className="text-indigo-400" size={20} />
            <span className="font-bold text-white">TimeTracker</span>
          </div>
          <p className="text-xs text-gray-500 mt-1 truncate">{member?.name}</p>
        </div>

        <nav className="flex-1 p-3 space-y-0.5">
          {NAV.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${
                  isActive
                    ? 'bg-indigo-600 text-white'
                    : 'text-gray-400 hover:bg-gray-800 hover:text-white'
                }`
              }
            >
              <Icon size={16} />
              {label}
            </NavLink>
          ))}
        </nav>

        <div className="p-3 border-t border-gray-800">
          <button
            onClick={logout}
            className="flex items-center gap-3 px-3 py-2 w-full rounded-lg text-sm text-gray-400 hover:bg-gray-800 hover:text-white transition-colors"
          >
            <LogOut size={16} />
            Sign out
          </button>
        </div>
      </aside>

      {/* Main */}
      <main className="flex-1 overflow-y-auto bg-gray-950 p-6">
        <Outlet />
      </main>
    </div>
  )
}
