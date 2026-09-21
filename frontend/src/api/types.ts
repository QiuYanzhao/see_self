// 与后端 schemas 对齐的类型定义（snake_case）

export interface IndicatorItem {
  kind: string // binding / expected
  name: string
  baseline: string | null
  target: string | null
  check_frequency: string | null
  measure: string | null
}

export interface DomainItem {
  domain: string
  status: string // 重点 / 非重点
  baseline: string | null
  five_year_target: string | null
  year1_tasks: string[]
}

export interface SpecialProjectItem {
  name: string
  start: string | null
  end: string | null
  effort: string | null
  milestones: string[]
  acceptance_criteria: string | null
}

export interface RiskItem {
  risk_type: string
  trigger: string | null
  plan: string | null
  reserve: string | null
}

export interface EvaluationInfo {
  annual: string | null
  midterm: string | null
  final: string | null
}

export interface PlaceholderItem {
  item: string
  note: string | null
  impact: string | null
}

export interface Plan {
  id: number
  name: string
  start_year: number
  end_year: number
  description: string | null
  status: string
  okr_count: number
  created_at: string
  // 规划纲要
  period_start: string | null
  period_end: string | null
  vision_positioning: string | null
  vision_core_goals: string[]
  vision_bottom_lines: string[]
  evaluation: EvaluationInfo | null
  year1_goals: string[]
  year1_period: string | null
  placeholders: PlaceholderItem[]
  indicators: IndicatorItem[]
  domains: DomainItem[]
  special_projects: SpecialProjectItem[]
  risks: RiskItem[]
  okrs: Okr[]
}

export interface Okr {
  id: number
  plan_id: number | null
  quarter: string
  objective: string
  kr_note: string | null
  kr_results: string[]
  project_count: number
  created_at: string
}

export interface TodoNote {
  id: number
  todo_id: number
  content: string
  sort_order: number
  created_at: string
}

export interface TodoNode {
  id: number
  project_id: number
  parent_id: number | null
  title: string
  description: string | null
  sort_order: number
  completed_at: string | null
  created_at: string
  children: TodoNode[]
  notes: TodoNote[]
}

export interface ProgressSegment {
  label: string
  start: number
  end: number
  value: number
  color: string
}

export interface Project {
  id: number
  okr_id: number | null
  name: string
  description: string | null
  progress: number
  total_leaves: number
  completed_leaves: number
  segments: ProgressSegment[]
  month_delta: number
  week_delta: number
  yesterday_delta: number
  today_delta: number
  created_at: string
}

export interface ProjectProgress {
  total_leaves: number
  completed_leaves: number
  percent: number
  modules: {
    id: number
    name: string
    total: number
    completed: number
    percent: number
    status: 'todo' | 'active' | 'done'
  }[]
}

export interface HeatmapItem {
  date: string
  count: number
}

export interface TimelineItem {
  id: number
  title: string
  completed_at: string | null
  notes: { id: number; content: string; sort_order: number }[]
}

export interface PendingItem {
  id: number
  title: string
  parent_path: string
}

export interface TimeProgress {
  now: string
  year_progress: number
  month_progress: number
  week_progress: number
  year_label: string
  month_label: string
  week_label: string
}

export interface DashboardData {
  time: TimeProgress
  projects: Project[]
}

export interface Settings {
  timezone: string
}
