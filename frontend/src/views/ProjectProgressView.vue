<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../api'
import type { ProjectProgress, TimelineItem, TodoNode } from '../api/types'

// 项目进度：阶段轨道 + 开发日志 + 下一步事项
const props = defineProps<{ id: string }>()
const router = useRouter()
const projectId = Number(props.id)

const progress = ref<ProjectProgress | null>(null)
const projectName = ref('')
const timeline = ref<TimelineItem[]>([])
const tree = ref<TodoNode[]>([])
const completing = ref<Set<number>>(new Set())
const loading = ref(true)

// 阶段标签映射：事项 id → 所属模块名
const stageMap = computed(() => {
  const m = new Map<number, string>()
  for (const node of tree.value) {
    for (const child of node.children) m.set(child.id, node.title)
  }
  return m
})
function stageName(id: number): string {
  return stageMap.value.get(id) ?? ''
}

// 下一步事项：最后一个已完成事项之后（按树顺序）的未完成事项，最多 5 条
const nextSteps = computed(() => {
  const flat: { id: number; title: string; parent: string; done: boolean }[] = []
  for (const node of tree.value) {
    for (const child of node.children) {
      flat.push({ id: child.id, title: child.title, parent: node.title, done: !!child.completed_at })
    }
  }
  let lastDone = -1
  flat.forEach((it, i) => {
    if (it.done) lastDone = i
  })
  return flat
    .slice(lastDone + 1)
    .filter((it) => !it.done)
    .slice(0, 5)
})

// 完成下一步事项：本地更新树 + 进度统计 + 开发日志/曲线（不刷新页面）
async function completeStep(item: { id: number; title?: string }) {
  if (completing.value.has(item.id)) return
  completing.value.add(item.id)
  try {
    const updated = (await api.toggleTodo(item.id, true)) as TodoNode
    const patch = (nodes: TodoNode[]) => {
      for (const n of nodes) {
        if (n.id === item.id) {
          n.completed_at = updated.completed_at
          return true
        }
        if (patch(n.children || [])) return true
      }
      return false
    }
    patch(tree.value)
    // 本地更新完成度统计
    if (progress.value) {
      progress.value.completed_leaves += 1
      progress.value.percent = Math.round(
        (progress.value.completed_leaves / progress.value.total_leaves) * 100
      )
      const modNode = tree.value.find((n) => n.children.some((c) => c.id === item.id))
      if (modNode) {
        const mod = progress.value.modules.find((m) => m.id === modNode.id)
        if (mod) {
          mod.completed += 1
          mod.percent = Math.round((mod.completed / mod.total) * 1000) / 10
        }
      }
    }
    // 开发日志 / 进度曲线 头部补一条实时记录
    timeline.value.unshift({
      id: updated.id,
      title: item.title || '',
      completed_at: updated.completed_at || new Date().toISOString().slice(0, 19),
      notes: [],
    } as TimelineItem)
  } catch (e: any) {
    alert(e.message || '操作失败')
  } finally {
    completing.value.delete(item.id)
  }
}

// 开发日志：按 日期 → 模块 聚合（图二构图：日期 + 项目·模块 + 事项列表）
const logGroups = computed(() => {
  const groups: { date: string; sections: { module: string; items: TimelineItem[] }[] }[] = []
  for (const item of timeline.value) {
    const date = fmtDate(item.completed_at)
    const module = stageName(item.id) || '未分组'
    let g = groups.find((x) => x.date === date)
    if (!g) {
      g = { date, sections: [] }
      groups.push(g)
    }
    let sec = g.sections.find((s) => s.module === module)
    if (!sec) {
      sec = { module, items: [] }
      g.sections.push(sec)
    }
    sec.items.push(item)
  }
  return groups
})

function fmtDate(iso: string | null): string {
  if (!iso) return ''
  return iso.slice(0, 10) // YYYY-MM-DD
}

// ── 项目进度曲线：按完成日期累计进度百分比 ──
interface CurvePt { date: string; label: string; pct: number }
const SVG_W = 900
const SVG_H = 240
const PAD = { l: 44, r: 18, t: 20, b: 34 }

function isoDate(d: Date): string {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

// 曲线点：起点(首个完成日前一天,0%) + 每个完成日累计进度
const curvePoints = computed<CurvePt[]>(() => {
  const total = progress.value?.total_leaves || 0
  if (!total) return []
  const byDate = new Map<string, number>()
  for (const it of timeline.value) {
    const d = it.completed_at ? it.completed_at.slice(0, 10) : ''
    if (!d) continue
    byDate.set(d, (byDate.get(d) || 0) + 1)
  }
  const dates = [...byDate.keys()].sort()
  if (!dates.length) return []
  const first = new Date(dates[0] + 'T00:00:00')
  const start = new Date(first)
  start.setDate(start.getDate() - 1)
  const pts: CurvePt[] = [{ date: isoDate(start), label: isoDate(start).slice(5), pct: 0 }]
  let acc = 0
  for (const d of dates) {
    acc += byDate.get(d)!
    pts.push({ date: d, label: d.slice(5), pct: (acc / total) * 100 })
  }
  return pts
})

// 曲线横轴时间域(起点 → 末日)
const curveDomain = computed(() => {
  const pts = curvePoints.value
  if (pts.length < 2) return null
  const t0 = new Date(pts[0].date + 'T00:00:00').getTime()
  const t1 = new Date(pts[pts.length - 1].date + 'T00:00:00').getTime()
  return { t0, span: Math.max(86400000, t1 - t0) }
})

function sx(date: string): number {
  const dom = curveDomain.value
  if (!dom) return PAD.l
  const t = new Date(date + 'T00:00:00').getTime()
  return PAD.l + ((t - dom.t0) / dom.span) * (SVG_W - PAD.l - PAD.r)
}
function sy(pct: number): number {
  return PAD.t + (1 - pct / 100) * (SVG_H - PAD.t - PAD.b)
}

// 平滑曲线(Catmull-Rom → 三次贝塞尔)
const curvePath = computed(() => {
  const pts = curvePoints.value
  if (pts.length < 2) return ''
  let d = `M ${sx(pts[0].date).toFixed(1)} ${sy(pts[0].pct).toFixed(1)}`
  for (let i = 0; i < pts.length - 1; i++) {
    const p0 = pts[Math.max(0, i - 1)]
    const p1 = pts[i]
    const p2 = pts[i + 1]
    const p3 = pts[Math.min(pts.length - 1, i + 2)]
    const c1x = sx(p1.date) + (sx(p2.date) - sx(p0.date)) / 6
    const c1y = sy(p1.pct) + (sy(p2.pct) - sy(p0.pct)) / 6
    const c2x = sx(p2.date) - (sx(p3.date) - sx(p1.date)) / 6
    const c2y = sy(p2.pct) - (sy(p3.pct) - sy(p1.pct)) / 6
    d += ` C ${c1x.toFixed(1)} ${c1y.toFixed(1)}, ${c2x.toFixed(1)} ${c2y.toFixed(1)}, ${sx(p2.date).toFixed(1)} ${sy(p2.pct).toFixed(1)}`
  }
  return d
})

const curveArea = computed(() => {
  if (!curvePath.value) return ''
  const pts = curvePoints.value
  const first = pts[0]
  const last = pts[pts.length - 1]
  return `${curvePath.value} L ${sx(last.date).toFixed(1)} ${sy(0).toFixed(1)} L ${sx(first.date).toFixed(1)} ${sy(0).toFixed(1)} Z`
})

const gridY = [0, 25, 50, 75, 100]

// ── 曲线 hover：靠近曲线时在最近点旁展示进度百分比 ──
const svgRef = ref<SVGSVGElement | null>(null)
const hoverIdx = ref<number | null>(null)

// 屏幕坐标 → SVG viewBox 坐标（preserveAspectRatio=none 会拉伸，需按边界框换算）
function toSvgXY(e: MouseEvent): { x: number; y: number } | null {
  const svg = svgRef.value
  if (!svg) return null
  const rect = svg.getBoundingClientRect()
  if (!rect.width || !rect.height) return null
  return {
    x: ((e.clientX - rect.left) / rect.width) * SVG_W,
    y: ((e.clientY - rect.top) / rect.height) * SVG_H,
  }
}

// 在曲线数据点中找距离鼠标最近的一个（阈值内才高亮）
const HOVER_HIT_R2 = 42 * 42
function onCurveMove(e: MouseEvent) {
  const pt = toSvgXY(e)
  if (!pt || !curvePoints.value.length) {
    hoverIdx.value = null
    return
  }
  let best = -1
  let bestD2 = Infinity
  for (let i = 0; i < curvePoints.value.length; i++) {
    const p = curvePoints.value[i]
    const dx = sx(p.date) - pt.x
    const dy = sy(p.pct) - pt.y
    const d2 = dx * dx + dy * dy
    if (d2 < bestD2) {
      bestD2 = d2
      best = i
    }
  }
  const next = best >= 0 && bestD2 <= HOVER_HIT_R2 ? best : null
  if (next !== hoverIdx.value) {
    hoverIdx.value = next
    if (next !== null) {
      const p = curvePoints.value[next]
      console.debug(`[curve] hover 点 ${p.label} → ${p.pct.toFixed(1)}%`)
    } else {
      console.debug('[curve] hover 离开命中区')
    }
  }
}

function onCurveLeave() {
  if (hoverIdx.value !== null) {
    hoverIdx.value = null
    console.debug('[curve] hover leave，清除百分比标签')
  }
}

// 悬浮数字标签：只显示进度数值（无日期、无 % 号），轻量胶囊浮在点旁
const hoverTip = computed(() => {
  const i = hoverIdx.value
  if (i === null) return null
  const p = curvePoints.value[i]
  if (!p) return null
  const cx = sx(p.date)
  const cy = sy(p.pct)
  // 纯数字文案：整数不带小数点，避免 "55.0" 显得啰嗦
  const raw = Number(p.pct.toFixed(1))
  const label = Number.isInteger(raw) ? String(raw) : raw.toFixed(1)
  // 胶囊尺寸随数字宽度微调（两位数够用）
  const tipW = 36 + label.length * 7
  const tipH = 26
  // 默认贴在点右上方；靠边则翻到左侧/下方，始终避开出界
  let tipX = cx + 12
  let tipY = cy - tipH - 10
  if (tipX + tipW > SVG_W - PAD.r) tipX = cx - tipW - 12
  if (tipY < PAD.t) tipY = cy + 12
  return {
    x: cx,
    y: cy,
    tipX,
    tipY,
    tipW,
    tipH,
    textX: tipX + tipW / 2,
    textY: tipY + tipH / 2 + 1,
    label,
  }
})

// 曲线加载动画：从左到右生长(stroke-dashoffset)
const lineRef = ref<SVGPathElement | null>(null)
const areaShown = ref(false)
function playCurveAnim() {
  const el = lineRef.value
  if (!el) return
  const len = el.getTotalLength()
  el.style.transition = 'none'
  el.style.strokeDasharray = String(len)
  el.style.strokeDashoffset = String(len)
  requestAnimationFrame(() => {
    requestAnimationFrame(() => {
      el.style.transition = 'stroke-dashoffset 1.1s cubic-bezier(0.4, 0, 0.2, 1)'
      el.style.strokeDashoffset = '0'
    })
  })
  areaShown.value = true
}
watch(curvePath, (p) => {
  if (p) setTimeout(playCurveAnim, 60)
})

async function load() {
  loading.value = true
  try {
    const [p, t, tr, projects] = await Promise.all([
      api.projectProgress(projectId),
      api.projectTimeline(projectId),
      api.getTodoTree(projectId),
      api.listProjects(),
    ])
    progress.value = p
    timeline.value = t
    tree.value = tr
    projectName.value = projects.find((x) => x.id === projectId)?.name || ''
  } finally {
    loading.value = false
  }
}

onMounted(load)
onMounted(() => setTimeout(playCurveAnim, 250))
</script>

<template>
  <div class="page-container">
    <div class="pp-head">
      <button class="btn" @click="router.push('/')">← 返回总览</button>
      <div class="head-right">
        <span v-if="progress" class="stats-row">
          <span class="stat-item"><b>{{ progress.percent }}%</b> 完成度</span>
          <span class="stat-divider">·</span>
          <span class="stat-item"><b>{{ progress.completed_leaves }}</b> 已完成</span>
          <span class="stat-divider">·</span>
          <span class="stat-item"><b>{{ progress.total_leaves }}</b> 总事项</span>
        </span>
        <button class="btn" @click="router.push(`/projects/${projectId}`)">计划详情 →</button>
      </div>
    </div>

    <div v-if="loading" class="empty">加载中...</div>

    <div v-else-if="progress">
      <!-- 阶段轨道 -->
      <div v-if="progress.modules.length" class="card">
        <div class="card-title">阶段轨道</div>
        <div class="phase-track">
          <div v-for="m in progress.modules" :key="m.id" class="phase-item" :class="m.status">
            <div class="phase-bar" :style="{ width: '100%' }" />
            <div class="phase-label">{{ m.name }}</div>
            <div class="phase-meta">{{ m.completed }}/{{ m.total }} · {{ m.percent }}%</div>
          </div>
        </div>
      </div>

      <!-- 主体：左列(曲线 + 开发日志) + 右列(下一步事项) -->
      <div class="pp-row">
        <div class="pp-left">
        <!-- 项目进度曲线：日期 MM-dd × 进度 %，平滑曲线 -->
        <div class="card curve-card">
          <div class="card-title">项目进度</div>
          <div v-if="curvePoints.length < 2" class="empty">暂无完成记录，完成事项后曲线将自动生成</div>
          <!-- hover 最近点时在点旁展示进度百分比；移出曲线区自动隐藏 -->
          <svg
            v-else
            ref="svgRef"
            class="curve-svg"
            :viewBox="`0 0 ${SVG_W} ${SVG_H}`"
            preserveAspectRatio="none"
            @mousemove="onCurveMove"
            @mouseleave="onCurveLeave"
          >
            <defs>
              <linearGradient id="curveGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stop-color="#2b6cd8" stop-opacity=".22" />
                <stop offset="100%" stop-color="#2b6cd8" stop-opacity=".02" />
              </linearGradient>
            </defs>
            <!-- 纵轴网格线 + 刻度 -->
            <g v-for="g in gridY" :key="g">
              <line
                :x1="PAD.l" :x2="SVG_W - PAD.r" :y1="sy(g)" :y2="sy(g)"
                class="curve-grid"
              />
              <text :x="PAD.l - 8" :y="sy(g) + 4" class="curve-y" text-anchor="end">{{ g }}%</text>
            </g>
            <!-- 面积 + 曲线 -->
            <path :d="curveArea" class="curve-area" :class="{ reveal: areaShown }" />
            <path ref="lineRef" :d="curvePath" class="curve-line" />
            <!-- 数据点 + 透明命中区（放大 hover 感知范围） -->
            <g v-for="(p, i) in curvePoints" :key="p.date">
              <circle :cx="sx(p.date)" :cy="sy(p.pct)" r="3.6" class="curve-dot" :class="{ first: i === 0, active: hoverIdx === i }" />
              <circle :cx="sx(p.date)" :cy="sy(p.pct)" r="14" class="curve-hit" />
              <text :x="sx(p.date)" :y="SVG_H - PAD.b + 16" class="curve-x" text-anchor="middle">{{ p.label }}</text>
            </g>
            <!-- hover 提示：引导线 + 点旁纯数字（无日期、无 %） -->
            <g v-if="hoverTip" class="curve-hover">
              <line
                :x1="hoverTip.x" :x2="hoverTip.x"
                :y1="hoverTip.y" :y2="SVG_H - PAD.b"
                class="curve-guide"
              />
              <circle :cx="hoverTip.x" :cy="hoverTip.y" r="5.2" class="curve-dot-active" />
              <rect
                :x="hoverTip.tipX"
                :y="hoverTip.tipY"
                :width="hoverTip.tipW"
                :height="hoverTip.tipH"
                rx="13"
                class="curve-tip-bg"
              />
              <text
                :x="hoverTip.textX"
                :y="hoverTip.textY"
                class="curve-tip-text"
                text-anchor="middle"
                dominant-baseline="central"
              >{{ hoverTip.label }}</text>
            </g>
          </svg>
        </div>


        <!-- 开发日志：日期 + 项目·模块 + 事项列表 -->
        <div class="card log-card">
          <div class="card-title">推进日志</div>
          <div v-if="!logGroups.length" class="empty">暂无完成记录</div>
          <div v-for="g in logGroups" :key="g.date" class="log-group">
            <div class="log-group-date">{{ g.date }}</div>
            <div v-for="sec in g.sections" :key="sec.module" class="log-section">
              <div class="log-module">{{ projectName || '项目' }} · {{ sec.module }}</div>
              <ul class="log-items">
                <li v-for="item in sec.items" :key="item.id" class="log-item">
                  <span class="log-item-title">{{ item.title }}</span>
                  <ul v-if="item.notes.length" class="log-points">
                    <li v-for="n in item.notes" :key="n.id">{{ n.content }}</li>
                  </ul>
                </li>
              </ul>
            </div>
          </div>
        </div>
        </div>

        <!-- 下一步事项 -->
        <div class="card pending-card">
          <div class="card-title">下一步事项</div>
          <div v-if="!nextSteps.length" class="empty">全部完成 🎉</div>
          <div v-for="item in nextSteps" :key="item.id" class="pending-item">
            <span class="pending-path">{{ item.parent }}</span>
            <div class="pending-row">
              <span class="pending-title">{{ item.title }}</span>
              <button
                class="pending-done"
                :disabled="completing.has(item.id)"
                @click="completeStep(item)"
              >完成</button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.pp-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 22px;
}
.head-right {
  display: flex;
  align-items: center;
  gap: 18px;
}
.btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  font-size: 13.5px;
  border-radius: 10px;
  cursor: pointer;
  transition: all .15s;
  border: 1px solid rgba(43,108,216,.2);
  background: #fff;
  color: #5b6b80;
  white-space: nowrap;
}
.btn:hover {
  color: #1e57b5;
  border-color: #2b6cd8;
  background: rgba(43,108,216,.08);
}
.stats-row {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 14px;
  color: #5b6b80;
}
.stat-item b {
  color: #1e293b;
  font-size: 17px;
  font-family: var(--serif);
  font-variant-numeric: tabular-nums;
}
.stat-divider {
  color: rgba(43,108,216,.2);
}

.card {
  position: relative;
  background: #fff;
  border: 1px solid rgba(43,108,216,.1);
  border-radius: 18px;
  padding: 20px 22px;
  margin-bottom: 16px;
  box-shadow: 0 1px 2px rgba(22,51,47,.04), 0 10px 28px rgba(22,51,47,.06);
}
.card-title {
  font-size: 11.5px;
  text-transform: uppercase;
  letter-spacing: 0.14em;
  color: #5b6b80;
  margin-bottom: 16px;
  font-weight: 700;
}

/* ── 主体两列：开发日志(左) + 下一步事项(右) ── */
/* flex-start：右侧卡片高度按内容自适应，不被左侧长列拉伸 */
.pp-row {
  display: flex;
  gap: 16px;
  align-items: flex-start;
}
.pp-row > .card,
.pp-row > .pp-left {
  margin-bottom: 0;
}
.pp-left {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.pending-card {
  width: 320px;
  flex-shrink: 0;
  /* 高度完全由卡片内事项数量决定 */
  height: auto;
  align-self: flex-start;
}
@media (max-width: 800px) {
  .pp-row { flex-direction: column; }
  .pending-card { width: 100%; }
}

/* ── 阶段轨道 ── */
.phase-track {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(110px, 1fr));
  gap: 10px;
}
.phase-item { text-align: center; }
.phase-bar {
  height: 6px;
  border-radius: 3px;
  margin-bottom: 6px;
}
.phase-item.done .phase-bar { background: linear-gradient(90deg,#059669,#34d399); }
.phase-item.active .phase-bar { background: linear-gradient(90deg,#2b6cd8,#7db2ec); }
.phase-item.todo .phase-bar { background: #e8effc; }
.phase-label { font-size: 12.5px; color: #1e293b; margin-bottom: 3px; font-weight: 600; }
.phase-meta { font-size: 11px; color: #5b6b80; font-family: var(--mono, monospace); }

/* ── 开发日志：日期 + 项目·模块 + 事项列表 ── */
.log-group {
  padding: 12px 0;
  border-bottom: 1px dashed var(--border);
}
.log-group:first-of-type {
  padding-top: 4px;
}
.log-group:last-child {
  border-bottom: none;
  padding-bottom: 4px;
}
.log-group-date {
  font-family: var(--serif);
  font-size: 16px;
  font-weight: 700;
  color: #1e57b5;
  font-variant-numeric: tabular-nums;
  margin-bottom: 10px;
}
.log-section {
  margin-bottom: 10px;
}
.log-section:last-child {
  margin-bottom: 2px;
}
.log-module {
  font-size: 12px;
  font-weight: 700;
  color: #1e57b5;
  background: rgba(43,108,216,.1);
  border: 1px solid rgba(43,108,216,.28);
  border-radius: 7px;
  padding: 3px 11px;
  display: inline-block;
  margin-bottom: 7px;
}
.log-items {
  margin: 0;
  padding: 0;
  list-style: none;
}
.log-item {
  padding: 4px 0 4px 16px;
  position: relative;
}
.log-item::before {
  content: '';
  position: absolute;
  left: 3px;
  top: 14px;
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: #2b6cd8;
  opacity: .5;
}
.log-item-title {
  font-size: 13.5px;
  color: #1e293b;
  font-weight: 600;
}
.log-points {
  margin: 4px 0 0;
  padding: 0;
  list-style: none;
}
.log-points li {
  position: relative;
  padding: 2px 0 2px 16px;
  font-size: 12px;
  color: var(--text-dim);
  line-height: 1.55;
}
.log-points li::before {
  content: '';
  position: absolute;
  left: 2px;
  top: 10px;
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: var(--text-faint);
  opacity: 0.6;
}

/* ── 下一步事项 ── */
.pending-item {
  padding: 8px 0;
  border-bottom: 1px dashed var(--border);
}
.pending-item:last-child {
  border-bottom: none;
}
.pending-path {
  font-size: 11px;
  color: var(--text-dim);
  display: block;
  margin-bottom: 2px;
}
.pending-row {
  display: flex;
  align-items: center;
  gap: 10px;
}
.pending-title {
  flex: 1;
  font-size: 13px;
  line-height: 1.5;
}
.pending-done {
  flex-shrink: 0;
  padding: 3px 12px;
  font-size: 12px;
  color: #fff;
  background: linear-gradient(135deg, #3f9e63, #2f7d4c);
  border: none;
  border-radius: 6px;
  cursor: pointer;
  transition: opacity 0.15s, transform 0.1s;
}
.pending-done:hover {
  opacity: 0.88;
}
.pending-done:active {
  transform: scale(0.96);
}
.pending-done:disabled {
  opacity: 0.5;
  cursor: default;
}
/* ── 项目进度曲线 ── */
.curve-svg {
  width: 100%;
  height: 240px;
  display: block;
}
.curve-grid {
  stroke: rgba(43,108,216,.15);
  stroke-dasharray: 3 4;
}
.curve-y {
  font-size: 11px;
  fill: #5b6b80;
  font-family: monospace;
}
.curve-x {
  font-size: 11px;
  fill: #5b6b80;
  font-family: monospace;
}
.curve-line {
  fill: none;
  stroke: #2b6cd8;
  stroke-width: 2.6;
  stroke-linecap: round;
}
.curve-area {
  fill: url(#curveGrad);
  opacity: 0;
  transition: opacity 0.9s ease 0.5s;
}
.curve-area.reveal {
  opacity: 1;
}
.curve-dot {
  fill: #2b6cd8;
  stroke: #fff;
  stroke-width: 1.6;
  transition: r .12s ease, fill .12s ease;
}
.curve-dot.first {
  fill: #94a3b8;
}
.curve-dot.active {
  fill: #1e57b5;
}
/* 透明命中区：放大鼠标可感知范围，便于 hover 到点旁百分比 */
.curve-hit {
  fill: transparent;
  cursor: pointer;
}
.curve-guide {
  stroke: rgba(43,108,216,.22);
  stroke-width: 1;
  stroke-dasharray: 3 4;
  pointer-events: none;
}
.curve-dot-active {
  fill: #2b6cd8;
  stroke: #fff;
  stroke-width: 2.2;
  pointer-events: none;
}
/* 轻量数字胶囊：半透明毛玻璃感 + 柔和蓝字，贴合页面浅色气质 */
.curve-tip-bg {
  fill: rgba(255, 255, 255, 0.92);
  stroke: rgba(43, 108, 216, 0.1);
  stroke-width: 1;
  filter: drop-shadow(0 2px 8px rgba(43, 108, 216, 0.12));
  pointer-events: none;
}
.curve-tip-text {
  fill: #2b6cd8;
  font-size: 13px;
  font-family: var(--serif);
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  pointer-events: none;
}
.curve-hover {
  pointer-events: none;
}
</style>
