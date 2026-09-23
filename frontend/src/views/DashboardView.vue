<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../api'
import type { DashboardData, HeatmapItem, Okr, Project } from '../api/types'
import Clock from '../components/Clock.vue'
import TimeProgressBar from '../components/TimeProgressBar.vue'
import OkrFilterSelect from '../components/OkrFilterSelect.vue'
import HeatmapCard from '../components/HeatmapCard.vue'
import StatsNumber from '../components/StatsNumber.vue'
import ProjectStatusFilter, { type ProjectStatus } from '../components/ProjectStatusFilter.vue'

const router = useRouter()
const data = ref<DashboardData | null>(null)
const okrs = ref<Okr[]>([])
const heatmap = ref<HeatmapItem[]>([])
const filterOkrId = ref<number | null>(null)
// 项目状态筛选：默认「进行中」（0 < progress < 100）
const filterStatus = ref<ProjectStatus>('active')
const loading = ref(true)

// 监控指标：累计完成 / 本月完成 / 日均完成（从 365 天热力图数据聚合）
const stats = computed(() => {
  let total = 0
  let month = 0
  let first: Date | null = null
  const monthPrefix = new Date().toISOString().slice(0, 7)
  for (const h of heatmap.value) {
    total += h.count
    if (h.date.startsWith(monthPrefix)) month += h.count
    const d = new Date(h.date + 'T00:00:00')
    if (!first || d < first) first = d
  }
  // 日均 = 累计完成 ÷ 自首次完成日起的天数（含无完成日）
  const days = first ? Math.max(1, Math.floor((Date.now() - first.getTime()) / 86400000) + 1) : 1
  return { total, month, daily: total / days }
})

// 今日已过去（0 点起实时百分比）
const todayProgress = computed(() => {
  const now = new Date()
  return ((now.getHours() * 60 + now.getMinutes()) / (24 * 60)) * 100
})

// 本月/本周/昨日/今日 增量由后端按正确口径计算(月初至今/周一至今/昨日0点至今日0点/今日0点至实时)
function getSegmentMeta(p: Project) {
  return {
    month: p.month_delta || 0,
    week: p.week_delta || 0,
    yesterday: p.yesterday_delta || 0,
    today: p.today_delta || 0,
  }
}

function okrLabel(okr: Okr) {
  return `${okr.quarter} · ${okr.objective}`
}

function projectOkrLabel(p: Project) {
  const okr = okrs.value.find((o) => o.id === p.okr_id)
  return okr ? okrLabel(okr) : ''
}

// 按项目进度判定状态：进行中 / 待开始 / 已完成
// 用 <=0 / >=100 降低浮点误差；无事项项目 progress=0 归入待开始
function matchProjectStatus(p: Project, status: ProjectStatus): boolean {
  const prog = p.progress
  if (status === 'pending') return prog <= 0
  if (status === 'done') return prog >= 100
  return prog > 0 && prog < 100
}

// 组合筛选：状态 ∧ OKR
const filteredProjects = computed(() => {
  const projects = data.value?.projects || []
  return projects.filter((p) => {
    if (!matchProjectStatus(p, filterStatus.value)) return false
    if (filterOkrId.value) return p.okr_id === filterOkrId.value
    return true
  })
})

// 状态文案（空态提示用）
const statusLabel: Record<ProjectStatus, string> = {
  active: '进行中',
  pending: '待开始',
  done: '已完成',
}

async function load() {
  loading.value = true
  try {
    data.value = await api.dashboard()
  } finally {
    loading.value = false
  }
}

async function loadHeatmap() {
  try {
    heatmap.value = await api.heatmapAll()
  } catch {
    // 忽略
  }
}

async function loadOkrs() {
  try {
    okrs.value = await api.listOkrs()
  } catch {
    // 忽略
  }
}

function goProgress(projectId: number) {
  router.push(`/projects/${projectId}/progress`)
}

onMounted(() => {
  load()
  loadOkrs()
  loadHeatmap()
})
</script>

<template>
  <div class="page-container">
    <div v-if="!loading && data" class="dash-layout dash-new">
      <!-- 左栏：监控仪表盘(热力图 + 统计) + 项目进度概览 -->
      <div class="anim-item stagger-1">
        <!-- 监控行：统计 KPI + 热力图(窄) -->
        <div class="monitor-row">
          <!-- 统计仪表盘 -->
          <div class="card stats-card">
            <div class="kpi">
              <div class="kpi-label">累计完成事项</div>
              <div class="kpi-value">
                <StatsNumber :value="stats.total" />
                <span class="kpi-unit">项</span>
              </div>
            </div>
            <div class="kpi">
              <div class="kpi-label">本月完成事项</div>
              <div class="kpi-value">
                <StatsNumber :value="stats.month" />
                <span class="kpi-unit">项</span>
              </div>
            </div>
            <div class="kpi">
              <div class="kpi-label">日均完成事项</div>
              <div class="kpi-value">
                <StatsNumber :value="stats.daily" :decimals="1" />
                <span class="kpi-unit">项/天</span>
              </div>
            </div>
          </div>

          <!-- 推进热力图（近三月，全站） -->
          <div class="card heatmap-card">
            <div class="card-title">推进热力图</div>
            <HeatmapCard :items="heatmap" />
          </div>
        </div>

        <div class="filter-bar">
          <ProjectStatusFilter v-model="filterStatus" />
          <OkrFilterSelect v-model="filterOkrId" :okrs="okrs" />
        </div>
        <p v-if="!data.projects.length" class="empty">还没有项目，去「计划」页创建一个吧</p>
        <p v-else-if="!filteredProjects.length" class="empty">
          {{ statusLabel[filterStatus] }}下暂无项目
          <template v-if="filterOkrId">（当前 OKR 筛选下）</template>
        </p>
        <div v-else class="project-overview">
          <div
            v-for="p in filteredProjects"
            :key="p.id"
            class="card project-card"
            @click="goProgress(p.id)"
          >
            <div class="pc-head">
              <span class="pc-name">{{ p.name }}</span>
              <span class="pc-pct">{{ p.progress.toFixed(0) }}%</span>
            </div>
            <div v-if="projectOkrLabel(p)" class="okr-chip">{{ projectOkrLabel(p) }}</div>
            <!-- 分段进度条 -->
            <div class="seg-bar">
              <div
                v-for="(seg, i) in p.segments"
                :key="i"
                class="seg-fill"
                :style="{
                  left: seg.start + '%',
                  width: seg.value + '%',
                  background: seg.color,
                }"
              />
            </div>
            <!-- 分段标注 -->
            <div class="seg-meta">
              <span class="seg-tag">本月 +{{ getSegmentMeta(p).month.toFixed(1) }}%</span>
              <span class="seg-tag">本周 +{{ getSegmentMeta(p).week.toFixed(1) }}%</span>
              <span class="seg-tag">昨日 +{{ getSegmentMeta(p).yesterday.toFixed(1) }}%</span>
              <span class="seg-tag today">今日 +{{ getSegmentMeta(p).today.toFixed(1) }}%</span>
            </div>
            <div class="pc-meta">
              {{ p.completed_leaves }} / {{ p.total_leaves }} 事项完成
            </div>
          </div>
        </div>
      </div>

      <!-- 右栏：时钟 + 时间流逝进度 -->
      <aside class="dash-side anim-item stagger-2">
        <div class="card clock-card">
          <Clock />
        </div>
        <div class="card">
          <TimeProgressBar :label="`${data.time.year_label.trim()} 已过去`" :value="data.time.year_progress" />
        </div>
        <div class="card">
          <TimeProgressBar :label="`${data.time.month_label.trim()} 已过去`" :value="data.time.month_progress" />
        </div>
        <div class="card">
          <TimeProgressBar :label="`${data.time.week_label.trim()} 已过去`" :value="data.time.week_progress" />
        </div>
        <div class="card">
          <TimeProgressBar label="今日已过去" :value="todayProgress" />
        </div>
      </aside>
    </div>
    <p v-if="!data && !loading" class="empty">暂无数据</p>
  </div>
</template>

<style scoped>
.monitor-row {
  display: flex;
  gap: 14px;
  align-items: stretch;
  margin-bottom: 14px;
}
.heatmap-card {
  width: 272px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  justify-content: center;
}
.stats-card {
  flex: 1;
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  /* 仪表盘微网格 */
  background-image:
    linear-gradient(rgba(43, 101, 246, 0.06) 1px, transparent 1px),
    linear-gradient(90deg, rgba(43, 101, 246, 0.06) 1px, transparent 1px);
  background-size: 24px 24px;
  background-color: rgba(255, 255, 255, 0.45);
}
.kpi {
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 18px 22px;
  border-right: 1px dashed rgba(43, 101, 246, 0.18);
}
.kpi:last-child {
  border-right: none;
}
.kpi-label {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: #2b6cd8;
  margin-bottom: 10px;
}
.kpi-value {
  font-family: var(--mono, ui-monospace, 'SF Mono', Menlo, monospace);
  font-size: 32px;
  font-weight: 700;
  color: #17140d;
  font-variant-numeric: tabular-nums;
  line-height: 1.1;
}
.kpi-unit {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-dim);
  margin-left: 5px;
}
@media (max-width: 800px) {
  .monitor-row { flex-direction: column; }
  .heatmap-card { width: 100%; }
}
.filter-bar {
  margin-bottom: 14px;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
}
.okr-chip {
  display: inline-block;
  margin-bottom: 8px;
  padding: 2px 10px;
  font-size: 11px;
  color: #1d4ed8;
  background: rgba(43, 101, 246, 0.10);
  border: 1px solid rgba(43, 101, 246, 0.25);
  border-radius: 999px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 100%;
}
.project-overview {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.project-card {
  cursor: pointer;
}
.pc-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}
.pc-name {
  font-weight: 700;
  font-size: 15px;
}
.pc-pct {
  font-family: monospace;
  font-size: 14px;
  color: #2b65f6;
  font-weight: 600;
}
.seg-bar {
  position: relative;
  height: 8px;
  background: #eef2fa;
  border-radius: 4px;
  overflow: hidden;
  margin-bottom: 6px;
}
.seg-fill {
  position: absolute;
  top: 0;
  height: 100%;
}
.seg-meta {
  display: flex;
  gap: 12px;
  margin-bottom: 4px;
}
.seg-tag {
  font-size: 11px;
  color: var(--text-dim);
  font-family: monospace;
}
.seg-tag.today {
  color: #ea580c;
  font-weight: 700;
}
.pc-meta {
  font-size: 12px;
  color: var(--text-dim);
}

/* ── 新设计落地：仅总览页用纯白实体卡，其它页保留玻璃卡 ── */
.dash-new .card {
  background: linear-gradient(140deg, rgba(255, 255, 255, 0.66) 0%, rgba(255, 255, 255, 0.34) 100%);
  -webkit-backdrop-filter: blur(28px) saturate(180%);
  backdrop-filter: blur(28px) saturate(180%);
  border: 1px solid rgba(255, 255, 255, 0.85);
  border-radius: 20px;
  box-shadow:
    inset 0 1.5px 0 rgba(255, 255, 255, 0.95),
    inset 0 -1px 2px rgba(255, 255, 255, 0.4),
    0 8px 24px rgba(30, 64, 175, 0.07),
    0 1px 3px rgba(30, 64, 175, 0.04);
}
.dash-new .card:hover {
  box-shadow:
    0 12px 30px rgba(30, 64, 175, 0.09),
    0 2px 6px rgba(30, 64, 175, 0.05);
}

/* ── OKR 筛选下拉：仅总览页蓝化（计划页保持原样） ── */
.dash-new :deep(.okr-trigger) {
  background-color: rgba(255, 255, 255, 0.45);
  border-color: rgba(43, 101, 246, 0.25);
  box-shadow: 0 1px 3px rgba(30, 64, 175, 0.08);
}
.dash-new :deep(.okr-trigger:hover) {
  border-color: rgba(43, 101, 246, 0.5);
  background-color: #f5f8ff;
}
.dash-new :deep(.okr-trigger.open) {
  border-color: #2b65f6;
  box-shadow: 0 0 0 3px rgba(43, 101, 246, 0.14);
}
.dash-new :deep(.chevron) { color: #2b65f6; }
.dash-new :deep(.okr-menu) {
  background: rgba(255, 255, 255, 0.96);
  border-color: rgba(43, 101, 246, 0.22);
  box-shadow: 0 10px 28px rgba(30, 64, 175, 0.16);
}
.dash-new :deep(.okr-opt:hover) {
  background: rgba(43, 101, 246, 0.10);
  color: #1d4ed8;
}
.dash-new :deep(.okr-opt.active) { color: #1d4ed8; }
.dash-new :deep(.check) { color: #2b65f6; }
</style>