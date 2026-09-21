<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { api } from '../api'
import type { Okr, Plan } from '../api/types'

// ========== 时间轴 ==========
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
  // 2027 年起：年度 + Q1-Q4
  for (let year = 2027; year <= 2035; year++) {
    periods.push({
      type: 'year', year,
      label: `${year} 年度`, quarterKey: `${year} 年度`,
      start: new Date(year, 0, 1),
      end: new Date(year, 11, 31),
    })
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
const defaultIndex = Math.max(0, periods.findIndex((p) => p.end >= today))

// ========== 状态 ==========
const okrs = ref<Okr[]>([])
const plans = ref<Plan[]>([])
const planMap = ref<Record<number, string>>({})
const loading = ref(true)
const selectedIndex = ref(defaultIndex)
const showCreate = ref(false)
const editingId = ref<number | null>(null)
const error = ref('')
const hoverLeft = ref(false)
const hoverRight = ref(false)

const form = ref({
  quarter: '',
  objective: '',
  plan_id: '' as number | '',
  kr_results: [''] as string[],
})
const editForm = ref({
  quarter: '',
  objective: '',
  plan_id: '' as number | '',
  kr_results: [''] as string[],
})

// ========== 计算 ==========
const selectedPeriod = computed(() => periods[selectedIndex.value])
const currentOkrs = computed(() =>
  okrs.value.filter((o) => o.quarter === selectedPeriod.value.quarterKey)
)
const visiblePeriods = computed(() => {
  const idx = selectedIndex.value
  return [periods[idx - 1], periods[idx], periods[idx + 1]].filter(Boolean) as OkrPeriod[]
})
const leftPeriods = computed(() => periods.slice(0, selectedIndex.value))
const rightPeriods = computed(() => periods.slice(selectedIndex.value + 1))

// ========== 方法 ==========
async function load() {
  loading.value = true
  try {
    const [o, p] = await Promise.all([api.listOkrs(), api.listPlans()])
    okrs.value = o
    plans.value = p
    planMap.value = Object.fromEntries(p.map((x) => [x.id, x.name]))
  } finally {
    loading.value = false
  }
}

function withViewTransition(fn: () => void) {
  if (typeof document !== 'undefined' && 'startViewTransition' in document) {
    document.startViewTransition(fn)
  } else {
    fn()
  }
}

function selectPeriod(idx: number) {
  if (idx >= 0 && idx < periods.length) {
    withViewTransition(() => {
      selectedIndex.value = idx
      hoverLeft.value = false
      hoverRight.value = false
    })
  }
}

function prevPeriod() {
  if (selectedIndex.value > 0) {
    withViewTransition(() => { selectedIndex.value-- })
  }
}
function nextPeriod() {
  if (selectedIndex.value < periods.length - 1) {
    withViewTransition(() => { selectedIndex.value++ })
  }
}

function openCreate() {
  form.value = {
    quarter: selectedPeriod.value.quarterKey,
    objective: '',
    plan_id: plans.value.length ? plans.value[0].id : '',
    kr_results: [''],
  }
  showCreate.value = true
  error.value = ''
}

function addKr(formRef: { kr_results: string[] }) {
  formRef.kr_results.push('')
}
function removeKr(formRef: { kr_results: string[] }, idx: number) {
  if (formRef.kr_results.length > 1) formRef.kr_results.splice(idx, 1)
}

async function createOkr() {
  error.value = ''
  if (!form.value.quarter.trim() || !form.value.objective.trim()) return
  const krs = form.value.kr_results.map((k) => k.trim()).filter(Boolean)
  try {
    await api.createOkr({
      quarter: form.value.quarter,
      objective: form.value.objective,
      plan_id: form.value.plan_id === '' ? null : Number(form.value.plan_id),
      kr_results: krs,
    })
    showCreate.value = false
    await load()
  } catch (e) {
    error.value = (e as Error).message
  }
}

function startEdit(o: Okr) {
  editingId.value = o.id
  editForm.value = {
    quarter: o.quarter,
    objective: o.objective,
    plan_id: o.plan_id ?? '',
    kr_results: o.kr_results.length ? [...o.kr_results] : [''],
  }
}

async function saveEdit(id: number) {
  error.value = ''
  const krs = editForm.value.kr_results.map((k) => k.trim()).filter(Boolean)
  try {
    await api.updateOkr(id, {
      quarter: editForm.value.quarter,
      objective: editForm.value.objective,
      plan_id: editForm.value.plan_id === '' ? null : Number(editForm.value.plan_id),
      kr_results: krs,
    })
    editingId.value = null
    await load()
  } catch (e) {
    error.value = (e as Error).message
  }
}

async function remove(id: number) {
  if (!confirm('删除该 OKR 将级联删除其下全部项目与待办，确定吗？')) return
  await api.deleteOkr(id)
  await load()
}

onMounted(load)
</script>

<style scoped>
.page-container { max-width: 1080px; margin: 0 auto; }

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  flex-wrap: wrap;
  gap: 14px;
}
.toolbar-left {
  display: flex;
  align-items: center;
  gap: 14px;
}
.period-title {
  font-size: 24px;
  font-weight: 700;
  letter-spacing: 0.02em;
  color: #1e293b;
}
.period-sub {
  font-size: 12.5px;
  color: #5b6b80;
  margin-top: 2px;
}

/* 按钮：覆盖全局金色 */
.okrs-new .btn.primary, .okrs-new button:not(.ghost):not(.danger):not(.tiny) {
  background: #2b6cd8;
  color: #fff;
  border: 1px solid transparent;
  border-radius: 10px;
  padding: 8px 16px;
  font-size: 13.5px;
  box-shadow: 0 1px 2px rgba(43,108,216,.3), 0 6px 16px rgba(43,108,216,.25);
  transition: background .15s;
}
.okrs-new button:not(.ghost):not(.danger):not(.tiny):hover { background: #1e57b5; }
.okrs-new .btn.ghost, .okrs-new button.ghost {
  background: #fff;
  border: 1px solid rgba(43,108,216,.2);
  color: #5b6b80;
  border-radius: 10px;
  padding: 8px 16px;
  font-size: 13.5px;
}
.okrs-new .btn.ghost:hover, .okrs-new button.ghost:hover {
  color: #1e293b; border-color: #2b6cd8; background: rgba(43,108,216,.08);
}
.okrs-new .btn.danger, .okrs-new button.danger {
  background: rgba(220,38,38,.1);
  border: 1px solid rgba(220,38,38,.25);
  color: #dc2626;
  border-radius: 10px;
}
.okrs-new .btn.tiny, .okrs-new button.tiny { padding: 4px 12px; font-size: 12.5px; border-radius: 8px; }

/* 时间导航器 */
.period-nav {
  display: flex;
  align-items: center;
  gap: 6px;
  position: relative;
}
.nav-arrow {
  width: 34px;
  height: 34px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 10px;
  border: 1px solid rgba(43,108,216,.1);
  background: #fff;
  color: #5b6b80;
  cursor: pointer;
  font-size: 16px;
  transition: all .15s;
}
.nav-arrow:hover:not(:disabled) {
  border-color: #2b6cd8;
  color: #1e57b5;
}
.nav-arrow:disabled { opacity: .3; cursor: not-allowed; }
.period-chip {
  padding: 7px 15px;
  border-radius: 10px;
  border: 1px solid rgba(43,108,216,.1);
  background: #fff;
  color: #5b6b80;
  font-size: 13px;
  cursor: pointer;
  transition: all .15s;
  white-space: nowrap;
}
.period-chip:hover { border-color: #2b6cd8; color: #1e293b; }
.period-chip.active {
  background: rgba(43,108,216,.1);
  border-color: #2b6cd8;
  color: #1e57b5;
  font-weight: 600;
}

/* hover 弹出列表 */
.nav-hover-zone {
  position: relative;
  padding-bottom: 340px;
  margin-bottom: -340px;
}
.hover-list {
  position: absolute;
  top: 36px;
  background: #fff;
  border: 1px solid rgba(43,108,216,.12);
  border-radius: 10px;
  padding: 6px;
  z-index: 100;
  max-height: 320px;
  overflow-y: auto;
  min-width: 130px;
  box-shadow: 0 12px 32px rgba(22,51,47,.15);
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
  transition: background .1s;
}
.hover-item:hover { background: rgba(43,108,216,.1); color: #1e293b; }

/* 创建/编辑表单 */
.form-card {
  padding: 20px;
  margin-bottom: 16px;
  background: #fff;
  border: 1px solid rgba(43,108,216,.1);
  border-radius: 16px;
  box-shadow: 0 1px 2px rgba(22,51,47,.04), 0 10px 28px rgba(22,51,47,.06);
}
.form-row {
  display: flex;
  gap: 10px;
  align-items: center;
  flex-wrap: wrap;
}
.form-card input, .form-card select {
  padding: 8px 12px;
  background: #f7faff;
  border: 1px solid rgba(43,108,216,.1);
  border-radius: 8px;
  color: #1e293b;
  outline: none;
  transition: border-color .15s, box-shadow .15s;
}
.form-card input:focus, .form-card select:focus {
  border-color: #2b6cd8;
  box-shadow: 0 0 0 3px rgba(43,108,216,.12);
}
.kr-row {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-bottom: 6px;
}
.kr-row input { flex: 1; }
.kr-add { color: #1e57b5; font-size: 12px; cursor: pointer; margin-top: 4px; }
.kr-remove { color: #dc2626; cursor: pointer; font-size: 14px; padding: 0 4px; }

/* OKR 卡片 */
.okr-card {
  background: #fff;
  border: 1px solid rgba(43,108,216,.1);
  border-radius: 18px;
  padding: 20px 22px;
  margin-bottom: 14px;
  box-shadow: 0 1px 2px rgba(22,51,47,.04), 0 10px 28px rgba(22,51,47,.06);
  transition: transform .3s cubic-bezier(.22,1,.36,1), box-shadow .3s;
}
.okr-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 2px 4px rgba(22,51,47,.05), 0 16px 36px rgba(22,51,47,.09);
}
.okr-objective {
  font-size: 17px;
  font-weight: 700;
  color: #1e293b;
  line-height: 1.5;
}
.kr-list {
  margin: 12px 0 0;
  padding: 0;
  list-style: none;
}
.kr-list li {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  font-size: 13.5px;
  color: #5b6b80;
  line-height: 1.6;
  padding: 7px 0;
  border-bottom: 1px dashed rgba(43,108,216,.1);
}
.kr-list li:last-child { border-bottom: none; }
.kr-list li::before {
  content: '';
  flex-shrink: 0;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #2b6cd8;
  margin-top: 9px;
}
.empty-period {
  text-align: center;
  padding: 52px 20px;
  color: #5b6b80;
  border: 1.5px dashed rgba(43,108,216,.25);
  border-radius: 16px;
  background: rgba(255,255,255,.5);
}
.empty-period h3 {
  font-size: 16px;
  color: #1e293b;
  margin-bottom: 6px;
}

.okr-content {
  view-transition-name: okr-content;
  contain: layout;
}
</style>

<!-- View Transitions 全局伪元素（不能 scoped） -->
<style>
@keyframes okr-fade-out {
  from { opacity: 1; transform: translateY(0) scale(1); }
  to { opacity: 0; transform: translateY(-8px) scale(0.99); }
}
@keyframes okr-fade-in {
  from { opacity: 0; transform: translateY(10px) scale(0.99); }
  to { opacity: 1; transform: translateY(0) scale(1); }
}
::view-transition-old(okr-content) {
  animation: okr-fade-out 0.28s cubic-bezier(0.32, 0, 0.67, 0) both;
}
::view-transition-new(okr-content) {
  animation: okr-fade-in 0.38s cubic-bezier(0.22, 1, 0.36, 1) both;
  animation-delay: 0.06s;
}
@media (prefers-reduced-motion: reduce) {
  ::view-transition-old(okr-content),
  ::view-transition-new(okr-content) {
    animation: none;
  }
}
</style>

<template>
  <div class="page-container okrs-new">
  <!-- 顶部工具栏 -->
  <div class="toolbar">
    <div class="toolbar-left">
      <div>
        <div class="period-title">{{ selectedPeriod.label }}</div>
        <div class="period-sub">
          {{ selectedPeriod.start.toLocaleDateString('zh-CN') }} ~ {{ selectedPeriod.end.toLocaleDateString('zh-CN') }}
          · {{ currentOkrs.length }} 个 Objective
        </div>
      </div>
      <button @click="openCreate">+ 新建 OKR</button>
    </div>

    <!-- 时间导航器 -->
    <div class="period-nav">
      <div class="nav-hover-zone" @mouseenter="hoverLeft = true" @mouseleave="hoverLeft = false">
        <button
          class="nav-arrow"
          :disabled="selectedIndex === 0"
          @click="prevPeriod"
        >‹</button>
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
        <button
          class="nav-arrow"
          :disabled="selectedIndex === periods.length - 1"
          @click="nextPeriod"
        >›</button>
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

  <p v-if="error" class="r3" style="margin-bottom: 12px">{{ error }}</p>

  <!-- 创建视图 -->
  <div v-if="showCreate" class="form-card">
    <h3 style="margin: 0 0 14px">新建 OKR</h3>
    <div class="form-row" style="margin-bottom: 10px">
      <input v-model="form.quarter" placeholder="时间，如 Q4 2026.10-12" style="width: 180px" />
      <select v-model="form.plan_id" style="min-width: 200px">
        <option value="">独立 OKR（不挂靠计划）</option>
        <option v-for="p in plans" :key="p.id" :value="p.id">{{ p.name }}</option>
      </select>
      <input v-model="form.objective" placeholder="Objective 目标" style="flex: 1; min-width: 200px" />
    </div>
    <div style="margin-bottom: 8px">
      <div class="muted" style="font-size: 12px; margin-bottom: 6px">关键结果 KR（若干）</div>
      <div v-for="(kr, idx) in form.kr_results" :key="idx" class="kr-row">
        <input v-model="form.kr_results[idx]" :placeholder="`KR ${idx + 1}`" />
        <span class="kr-remove" @click="removeKr(form, idx)">×</span>
      </div>
      <span class="kr-add" @click="addKr(form)">+ 添加 KR</span>
    </div>
    <div class="form-row" style="margin-top: 14px">
      <button @click="createOkr">创建</button>
      <button class="ghost" @click="showCreate = false">取消</button>
    </div>
  </div>

  <!-- OKR 列表 -->
  <template v-else>
    <div v-if="!loading" class="okr-content anim-item stagger-2">
      <div v-if="!currentOkrs.length" class="empty-period">
        <p style="font-size: 16px; font-weight: 600; color: var(--text)">{{ selectedPeriod.label }} 暂无 OKR</p>
        <p>点击右上角「+ 新建 OKR」创建该周期的目标</p>
      </div>

      <div v-for="o in currentOkrs" :key="o.id" class="card okr-card">
      <template v-if="editingId === o.id">
        <div class="form-row" style="margin-bottom: 10px">
          <input v-model="editForm.quarter" style="width: 180px" />
          <select v-model="editForm.plan_id" style="min-width: 200px">
            <option value="">独立 OKR</option>
            <option v-for="p in plans" :key="p.id" :value="p.id">{{ p.name }}</option>
          </select>
          <input v-model="editForm.objective" style="flex: 1" />
        </div>
        <div v-for="(kr, idx) in editForm.kr_results" :key="idx" class="kr-row">
          <input v-model="editForm.kr_results[idx]" :placeholder="`KR ${idx + 1}`" />
          <span class="kr-remove" @click="removeKr(editForm, idx)">×</span>
        </div>
        <span class="kr-add" @click="addKr(editForm)">+ 添加 KR</span>
        <div class="form-row" style="margin-top: 12px">
          <button class="tiny" @click="saveEdit(o.id)">保存</button>
          <button class="ghost tiny" @click="editingId = null">取消</button>
        </div>
      </template>

      <template v-else>
        <div class="flex-between">
          <div class="okr-objective">{{ o.objective }}</div>
          <div class="form-row">
            <button class="ghost tiny" @click="startEdit(o)">编辑</button>
            <button class="danger tiny" @click="remove(o.id)">删除</button>
          </div>
        </div>
        <p class="muted" style="margin: 6px 0; font-size: 12px">
          挂靠：{{ o.plan_id != null ? planMap[o.plan_id] || '已删除计划' : '独立 OKR' }}
          · {{ o.project_count }} 个项目
        </p>
        <ul v-if="o.kr_results.length" class="kr-list">
          <li v-for="(kr, i) in o.kr_results" :key="i">{{ kr }}</li>
        </ul>
      </template>
    </div>
    </div>
  </template>
  </div>
</template>
