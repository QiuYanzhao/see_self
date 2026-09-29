<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../api'
import type { Okr, Project } from '../api/types'

// 计划页：按季度浏览，该季度下按 OKR(Objective) 分组展示项目
const router = useRouter()
const projects = ref<Project[]>([])
const okrs = ref<Okr[]>([])
const loading = ref(true)

// ========== 季度时间轴（与 OKR 页一致，仅季度无年度） ==========
interface OkrPeriod {
  type: 'year' | 'quarter'
  year: number
  quarter?: number
  label: string
  quarterKey: string
  start: Date
  end: Date
}

const QUARTER_RANGES = [
  { m: '01-03', start: [0, 1], end: [2, 31] },
  { m: '04-06', start: [3, 1], end: [5, 30] },
  { m: '07-09', start: [6, 1], end: [8, 30] },
  { m: '10-12', start: [9, 1], end: [11, 31] },
]

function generatePeriods(): OkrPeriod[] {
  const periods: OkrPeriod[] = []
  // 起始：2026 Q4
  const q4 = QUARTER_RANGES[3]
  periods.push({
    type: 'quarter', year: 2026, quarter: 4,
    label: '2026 Q4', quarterKey: '2026 Q4',
    start: new Date(2026, q4.start[0], q4.start[1]),
    end: new Date(2026, q4.end[0], q4.end[1]),
  })
  // 2027 年起：仅按季度推进
  for (let year = 2027; year <= 2035; year++) {
    for (let q = 1; q <= 4; q++) {
      const r = QUARTER_RANGES[q - 1]
      periods.push({
        type: 'quarter', year, quarter: q,
        label: `${year} Q${q}`, quarterKey: `${year} Q${q}`,
        start: new Date(year, r.start[0], r.start[1]),
        end: new Date(year, r.end[0], r.end[1]),
      })
    }
  }
  return periods
}

const periods = generatePeriods()
const today = new Date()
// 进入页默认选中：优先今天真正落在区间内的季度；否则落到第一个尚未结束的周期
const currentIdx = periods.findIndex((p) => p.start <= today && today <= p.end)
const upcomingIdx = periods.findIndex((p) => p.end >= today)
const defaultIndex = Math.max(0, currentIdx !== -1 ? currentIdx : upcomingIdx)

const selectedIndex = ref(defaultIndex)
const hoverLeft = ref(false)
const hoverRight = ref(false)

const selectedPeriod = computed(() => periods[selectedIndex.value])
const visiblePeriods = computed(() =>
  [periods[selectedIndex.value - 1], periods[selectedIndex.value], periods[selectedIndex.value + 1]].filter(Boolean) as OkrPeriod[]
)
const leftPeriods = computed(() => periods.slice(0, selectedIndex.value))
const rightPeriods = computed(() => periods.slice(selectedIndex.value + 1))

function selectPeriod(idx: number) {
  if (idx >= 0 && idx < periods.length) selectedIndex.value = idx
}
function prevPeriod() { if (selectedIndex.value > 0) selectedIndex.value-- }
function nextPeriod() { if (selectedIndex.value < periods.length - 1) selectedIndex.value++ }

// ========== 数据加载 ==========
async function load() {
  loading.value = true
  try {
    const [p, o] = await Promise.all([api.listProjects(), api.listOkrs()])
    projects.value = p
    okrs.value = o
  } finally {
    loading.value = false
  }
}

// 当前季度下的所有 OKR
const quarterOkrs = computed(() =>
  okrs.value.filter((o) => o.quarter === selectedPeriod.value.quarterKey)
)

// 按 Objective(OKR) 分组项目：只保留至少有一个项目的组
interface ProjectGroup {
  okr: Okr
  projects: Project[]
}
const groupedProjects = computed<ProjectGroup[]>(() =>
  quarterOkrs.value
    .map((okr) => ({
      okr,
      projects: projects.value.filter((p) => p.okr_id === okr.id),
    }))
    .filter((g) => g.projects.length > 0)
)

const totalProjectsInQuarter = computed(() =>
  groupedProjects.value.reduce((sum, g) => sum + g.projects.length, 0)
)

// ========== 新建项目弹窗 ==========
const showModal = ref(false)
const formName = ref('')
const formDesc = ref('')
const formOkrId = ref<number | null>(null)

function openCreate() {
  formName.value = ''
  formDesc.value = ''
  formOkrId.value = quarterOkrs.value.length ? quarterOkrs.value[0].id : null
  showModal.value = true
}

async function saveProject() {
  if (!formName.value.trim()) return
  const body = {
    name: formName.value.trim(),
    description: formDesc.value || null,
    okr_id: formOkrId.value,
  }
  try {
    const p = await api.createProject(body)
    showModal.value = false
    router.push(`/projects/${p.id}`)
  } catch (e: any) {
    alert(e.message)
  }
}

function onKey(e: KeyboardEvent) {
  if (e.key === 'Escape' && showModal.value) showModal.value = false
}

onMounted(() => {
  load()
  window.addEventListener('keydown', onKey)
})
onUnmounted(() => window.removeEventListener('keydown', onKey))
</script>

<template>
  <div class="page-container tasks-new">
    <!-- 顶部工具栏：周期标题 + 季度选择器 -->
    <div class="toolbar anim-item stagger-1">
      <div class="toolbar-left">
        <div>
          <div class="period-title">{{ selectedPeriod.label }}</div>
          <div class="period-sub">
            {{ selectedPeriod.start.toLocaleDateString('zh-CN') }} ~ {{ selectedPeriod.end.toLocaleDateString('zh-CN') }}
            · {{ totalProjectsInQuarter }} 个项目
          </div>
        </div>
        <button class="btn primary" @click="openCreate">+ 新建项目</button>
      </div>

      <!-- 季度选择器 -->
      <div class="period-nav">
        <div class="nav-hover-zone" @mouseenter="hoverLeft = true" @mouseleave="hoverLeft = false">
          <button class="nav-arrow" :disabled="selectedIndex === 0" @click="prevPeriod">‹</button>
          <div v-if="hoverLeft && leftPeriods.length" class="hover-list left">
            <div
              v-for="p in [...leftPeriods].reverse()"
              :key="p.quarterKey"
              class="hover-item"
              @click="selectPeriod(periods.indexOf(p))"
            >{{ p.label }}</div>
          </div>
        </div>

        <div
          v-for="p in visiblePeriods"
          :key="p.quarterKey"
          class="period-chip"
          :class="{ active: p.quarterKey === selectedPeriod.quarterKey }"
          @click="selectPeriod(periods.indexOf(p))"
        >{{ p.label }}</div>

        <div class="nav-hover-zone" @mouseenter="hoverRight = true" @mouseleave="hoverRight = false">
          <button class="nav-arrow" :disabled="selectedIndex === periods.length - 1" @click="nextPeriod">›</button>
          <div v-if="hoverRight && rightPeriods.length" class="hover-list right">
            <div
              v-for="p in rightPeriods"
              :key="p.quarterKey"
              class="hover-item"
              @click="selectPeriod(periods.indexOf(p))"
            >{{ p.label }}</div>
          </div>
        </div>
      </div>
    </div>

    <!-- 内容区 -->
    <div v-if="loading" class="empty anim-item stagger-1">加载中...</div>

    <template v-else-if="totalProjectsInQuarter > 0">
      <div v-for="g in groupedProjects" :key="g.okr.id" class="okr-group anim-item stagger-2">
        <div class="group-head">
          <span class="group-okr">{{ g.okr.objective }}</span>
          <span class="group-count">{{ g.projects.length }} 个项目</span>
        </div>
        <div class="project-grid">
          <div
            v-for="p in g.projects"
            :key="p.id"
            class="card project-card"
            @click="router.push(`/projects/${p.id}`)"
          >
            <div class="card-top">
              <h3>{{ p.name }}</h3>
            </div>
            <div class="progress-bar">
              <div class="fill" :style="{ width: p.progress + '%' }" />
            </div>
            <div class="meta">
              {{ p.completed_leaves }}/{{ p.total_leaves }} 事项 · {{ p.progress.toFixed(0) }}%
            </div>
          </div>
        </div>
      </div>
    </template>

    <div v-else class="empty-card anim-item stagger-2">
      <h3>{{ selectedPeriod.label }} 暂无项目</h3>
      <p>该季度下还没有项目，点击左上角「+ 新建项目」开始拆解。</p>
    </div>

    <!-- 新建项目弹窗 -->
    <div v-if="showModal" class="modal-mask" @click.self="showModal = false">
      <div class="modal">
        <h3>新建项目</h3>
        <input v-model="formName" placeholder="项目名称" @keyup.enter="saveProject" />
        <textarea v-model="formDesc" placeholder="描述（可选）" rows="5" />
        <label class="field-label">挂靠 OKR（{{ selectedPeriod.label }}）</label>
        <select v-model="formOkrId">
          <option :value="null">独立项目（不挂靠）</option>
          <option v-for="o in quarterOkrs" :key="o.id" :value="o.id">{{ o.objective }}</option>
        </select>
        <div class="modal-actions">
          <button class="btn" @click="showModal = false">取消</button>
          <button class="btn primary" @click="saveProject" :disabled="!formName.trim()">创建</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page-container { max-width: 1080px; margin: 0 auto; }

/* ── 顶部工具栏：周期标题 + 季度选择器 ── */
.toolbar {
  /* anim-item 入场动画残留 transform 会形成层叠上下文，
     这里给正 z-index 让工具栏（含 hover 弹出的季度列表）浮在项目卡片之上 */
  position: relative;
  z-index: 10;
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  margin-bottom: 22px;
  flex-wrap: wrap;
  gap: 14px;
}
.toolbar-left {
  display: flex;
  align-items: flex-end;
  gap: 14px;
  flex-wrap: wrap;
}
.period-title {
  font-size: 26px;
  font-weight: 700;
  letter-spacing: 0.02em;
  color: #1e293b;
  font-family: var(--serif);
  line-height: 1.1;
}
.period-sub {
  font-size: 12.5px;
  color: #5b6b80;
  margin-top: 4px;
}

/* 主按钮：中蓝 */
.tasks-new .btn.primary {
  background: #2b6cd8;
  color: #fff;
  border: 1px solid transparent;
  border-radius: 10px;
  padding: 8px 16px;
  font-size: 13.5px;
  box-shadow: 0 1px 2px rgba(43, 108, 216, 0.3), 0 6px 16px rgba(43, 108, 216, 0.25);
  transition: background 0.15s;
}
.tasks-new .btn.primary:hover { background: #1e57b5; }
.tasks-new .btn.primary:disabled { opacity: 0.55; cursor: not-allowed; }
.tasks-new .btn:not(.primary) {
  background: #fff;
  border: 1px solid rgba(43, 108, 216, 0.2);
  color: #5b6b80;
  border-radius: 10px;
  padding: 8px 16px;
  font-size: 13.5px;
  transition: all 0.15s;
}
.tasks-new .btn:not(.primary):hover {
  color: #1e293b;
  border-color: #2b6cd8;
  background: rgba(43, 108, 216, 0.08);
}

/* ── 季度选择器（与 OKR 页一致） ── */
.period-nav {
  display: flex;
  align-items: center;
  gap: 6px;
}
.nav-arrow {
  width: 34px;
  height: 34px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 10px;
  border: 1px solid rgba(43, 108, 216, 0.1);
  background: #fff;
  color: #5b6b80;
  cursor: pointer;
  font-size: 16px;
  transition: all 0.15s;
}
.nav-arrow:hover:not(:disabled) {
  border-color: #2b6cd8;
  color: #1e57b5;
}
.nav-arrow:disabled { opacity: 0.3; cursor: not-allowed; }
.period-chip {
  padding: 7px 15px;
  border-radius: 10px;
  border: 1px solid rgba(43, 108, 216, 0.1);
  background: #fff;
  color: #5b6b80;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.15s;
  white-space: nowrap;
}
.period-chip:hover { border-color: #2b6cd8; color: #1e293b; }
.period-chip.active {
  background: rgba(43, 108, 216, 0.1);
  border-color: #2b6cd8;
  color: #1e57b5;
  font-weight: 600;
}

/* hover 弹出季度列表 */
.nav-hover-zone {
  position: relative;
  padding-bottom: 200px;
  margin-bottom: -200px;
}
.hover-list {
  position: absolute;
  top: 38px;
  background: #fff;
  border: 1px solid rgba(43, 108, 216, 0.12);
  border-radius: 10px;
  padding: 6px;
  z-index: 100;
  max-height: 320px;
  overflow-y: auto;
  min-width: 130px;
  box-shadow: 0 12px 32px rgba(22, 51, 47, 0.15);
}
.hover-list.left { right: 0; }
.hover-list.right { left: 0; }
.hover-item {
  padding: 6px 10px;
  border-radius: 6px;
  font-size: 12px;
  color: #5b6b80;
  cursor: pointer;
  white-space: nowrap;
  transition: background 0.1s;
}
.hover-item:hover { background: rgba(43, 108, 216, 0.1); color: #1e293b; }

/* ── 按 OKR 分组 ── */
.okr-group { margin-bottom: 26px; }
.group-head {
  display: flex;
  align-items: baseline;
  gap: 10px;
  margin-bottom: 12px;
  padding-left: 2px;
}
.group-okr {
  font-size: 16px;
  font-weight: 700;
  color: #1e293b;
  font-family: var(--serif);
  letter-spacing: 0.01em;
}
.group-count {
  font-size: 12px;
  color: #5b6b80;
  font-variant-numeric: tabular-nums;
}

/* ── 项目卡片网格：卡片高度统一为两行标题的基准高度 ── */
.project-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 18px;
}
.project-card {
  cursor: pointer;
  padding: 18px 20px;
  display: flex;
  flex-direction: column;
  min-height: 125px;
  transition: transform 0.3s cubic-bezier(0.22, 1, 0.36, 1), box-shadow 0.3s;
}
.project-card:hover {
  transform: translateY(-3px);
}
.card-top {
  margin-bottom: 10px;
}
.project-card h3 {
  font-size: 16.5px;
  margin: 0;
  line-height: 1.4;
  color: #1e293b;
  /* 标题最多两行，超出省略；固定两行高度占位，保证所有卡片等高 */
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  min-height: 2.8em;
}
.progress-bar {
  height: 7px;
  background: #e8effc;
  border-radius: 4px;
  overflow: hidden;
  margin: auto 0 8px; /* margin-top:auto 把进度条+meta 推到底部 */
}
.fill {
  height: 100%;
  background: linear-gradient(90deg, #2b6cd8, #7db2ec);
  border-radius: 4px;
}
.meta {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  font-size: 12px;
  color: #5b6b80;
}

/* ── 空状态 ── */
.empty-card {
  border: 1.5px dashed rgba(43, 108, 216, 0.25);
  border-radius: 16px;
  padding: 48px 32px;
  text-align: center;
  background: rgba(255, 255, 255, 0.6);
}
.empty-card h3 {
  margin: 0 0 10px;
  color: #1e293b;
  font-size: 18px;
}
.empty-card p {
  color: #5b6b80;
  margin: 6px 0;
  font-size: 13.5px;
}

/* ── 新建项目弹窗 ── */
.modal-mask {
  position: fixed;
  inset: 0;
  background: rgba(22, 51, 47, 0.45);
  -webkit-backdrop-filter: blur(4px);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
}
.modal {
  background: #fff;
  border: 1px solid rgba(43, 108, 216, 0.1);
  border-radius: 18px;
  padding: 26px 28px;
  width: 70vw;
  max-width: 520px;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: 0 24px 60px rgba(22, 51, 47, 0.25);
  animation: modalIn 0.25s cubic-bezier(0.22, 1, 0.36, 1);
}
@keyframes modalIn {
  from { opacity: 0; transform: translateY(10px) scale(0.98); }
  to { opacity: 1; transform: translateY(0) scale(1); }
}
.modal h3 {
  font-size: 18px;
  margin-bottom: 20px;
  color: #1e293b;
}
.modal input, .modal textarea, .modal select {
  width: 100%;
  padding: 10px 12px;
  margin-bottom: 14px;
  background: #f7faff;
  border: 1px solid rgba(43, 108, 216, 0.1);
  border-radius: 10px;
  color: #1e293b;
  font-size: 14px;
  font-family: inherit;
  outline: none;
  transition: border-color 0.15s, box-shadow 0.15s;
}
.modal input:focus, .modal textarea:focus, .modal select:focus {
  border-color: #2b6cd8;
  box-shadow: 0 0 0 3px rgba(43, 108, 216, 0.12);
}
.modal textarea { resize: vertical; max-height: 50vh; }
.field-label {
  display: block;
  font-size: 12px;
  color: #5b6b80;
  margin-bottom: 6px;
  font-weight: 600;
}
.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 6px;
}
.empty {
  color: #5b6b80;
  text-align: center;
  padding: 60px 0;
}
</style>
