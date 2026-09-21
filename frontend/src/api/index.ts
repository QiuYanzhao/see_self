// API 客户端：统一封装 fetch，开发期走 Vite 代理，生产期同源
import type {
  DashboardData,
  HeatmapItem,
  Okr,
  PendingItem,
  Plan,
  Project,
  ProjectProgress,
  Settings,
  TimelineItem,
  TodoNode,
} from './types'

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const resp = await fetch(url, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!resp.ok) {
    const detail = await resp.json().catch(() => ({ detail: resp.statusText }))
    throw new Error(detail.detail || `请求失败 ${resp.status}`)
  }
  if (resp.status === 204) return undefined as T
  return resp.json() as Promise<T>
}

const jsonPost = (url: string, body: unknown) =>
  request(url, { method: 'POST', body: JSON.stringify(body) })
const jsonPut = (url: string, body: unknown) =>
  request(url, { method: 'PUT', body: JSON.stringify(body) })
const jsonDelete = (url: string) => request(url, { method: 'DELETE' })

export const api = {
  dashboard: () => request<DashboardData>('/api/dashboard'),

  listPlans: () => request<Plan[]>('/api/plans'),
  createPlan: (body: Partial<Plan>) => jsonPost('/api/plans', body),
  updatePlan: (id: number, body: Partial<Plan>) => jsonPut(`/api/plans/${id}`, body),
  deletePlan: (id: number) => jsonDelete(`/api/plans/${id}`),
  importPlan: (body: unknown) => jsonPost('/api/plans/import', body),

  listOkrs: (planId?: number) =>
    request<Okr[]>(`/api/okrs${planId != null ? `?plan_id=${planId}` : ''}`),
  createOkr: (body: Partial<Okr>) => jsonPost('/api/okrs', body),
  updateOkr: (id: number, body: Partial<Okr>) => jsonPut(`/api/okrs/${id}`, body),
  deleteOkr: (id: number) => jsonDelete(`/api/okrs/${id}`),

  listProjects: (okrId?: number) =>
    request<Project[]>(`/api/projects${okrId != null ? `?okr_id=${okrId}` : ''}`),
  createProject: (body: Partial<Project>) => request<Project>('/api/projects', { method: 'POST', body: JSON.stringify(body) }),
  updateProject: (id: number, body: Partial<Project>) => jsonPut(`/api/projects/${id}`, body),
  deleteProject: (id: number) => jsonDelete(`/api/projects/${id}`),

  getTodoTree: (projectId: number) => request<TodoNode[]>(`/api/todos/tree/${projectId}`),
  createTodo: (body: { project_id: number; parent_id?: number | null; title: string; description?: string; sort_order?: number }) =>
    jsonPost('/api/todos', body),
  updateTodo: (id: number, body: Partial<TodoNode>) => jsonPut(`/api/todos/${id}`, body),
  toggleTodo: (id: number, completed: boolean) =>
    jsonPut(`/api/todos/${id}/toggle`, { completed }),
  deleteTodo: (id: number) => jsonDelete(`/api/todos/${id}`),

  addNote: (todoId: number, content: string, sort_order = 0) =>
    jsonPost(`/api/todos/${todoId}/notes`, { content, sort_order }),
  deleteNote: (noteId: number) => jsonDelete(`/api/todos/notes/${noteId}`),

  projectProgress: (projectId: number) => request<ProjectProgress>(`/api/todos/progress/${projectId}`),
  projectHeatmap: (projectId: number) => request<HeatmapItem[]>(`/api/todos/heatmap/${projectId}`),
  heatmapAll: () => request<HeatmapItem[]>('/api/todos/heatmap'),
  projectTimeline: (projectId: number) => request<TimelineItem[]>(`/api/todos/timeline/${projectId}`),
  projectPending: (projectId: number) => request<PendingItem[]>(`/api/todos/pending/${projectId}`),

  getSettings: () => request<Settings>('/api/settings'),
  updateSettings: (body: Partial<Settings>) => jsonPut('/api/settings', body),

  getAppearance: () => request<{ background_image_url: string | null; background_opacity: number; background_blur_radius: number }>('/api/settings/appearance'),
  saveAppearance: (body: { background_opacity?: number; background_blur_radius?: number }) =>
    jsonPut('/api/settings/appearance', body),
  uploadBackground: (file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    return fetch('/api/settings/background', { method: 'POST', body: formData }).then(r => r.json())
  },
  deleteBackground: () => jsonDelete('/api/settings/background'),
}
