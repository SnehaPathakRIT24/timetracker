import axios from 'axios'

const BASE = '/api'

export const api = axios.create({ baseURL: BASE })

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('token')
      localStorage.removeItem('member')
      window.location.href = '/login'
    }
    return Promise.reject(err)
  }
)

export const login = (email: string, password: string) =>
  api.post('/auth/login', { email, password }).then((r) => r.data)

export const getDailyReport = (date?: string, memberId?: number) =>
  api.get('/report/daily', { params: { target_date: date, member_id: memberId } }).then((r) => r.data)

export const getWeeklyReport = (weekStart?: string) =>
  api.get('/report/weekly', { params: { week_start: weekStart } }).then((r) => r.data)

export const getProjectsReport = () =>
  api.get('/report/projects').then((r) => r.data)

export const getLowConfidence = () =>
  api.get('/review/low-confidence').then((r) => r.data)

export const correctClassification = (recordId: number, category: string) =>
  api.post('/classify/manual', { record_id: recordId, corrected_category: category }).then((r) => r.data)

export const getTeamMembers = () =>
  api.get('/team/members').then((r) => r.data)

export const addTeamMember = (data: any) =>
  api.post('/team/member', data).then((r) => r.data)

export const getRules = () =>
  api.get('/rules').then((r) => r.data)

export const addRule = (data: any) =>
  api.post('/rules', data).then((r) => r.data)

export const deleteRule = (id: number) =>
  api.delete(`/rules/${id}`).then((r) => r.data)

export const getDailyInsights = (date?: string) =>
  api.get('/insights/daily', { params: { target_date: date } }).then((r) => r.data)

export const triggerInsights = (date?: string) =>
  api.post('/insights/generate', null, { params: { target_date: date } }).then((r) => r.data)

// WebSocket
export const createWebSocket = () => new WebSocket(`ws://${window.location.host}/ws`)
