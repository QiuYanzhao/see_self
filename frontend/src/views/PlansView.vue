<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api } from '../api'
import type { Plan } from '../api/types'

const plans = ref<Plan[]>([])
const loading = ref(true)
const fileInput = ref<HTMLInputElement | null>(null)
const importing = ref(false)
const error = ref('')

async function load() {
  loading.value = true
  try {
    plans.value = await api.listPlans()
  } finally {
    loading.value = false
  }
}

function triggerImport() {
  fileInput.value?.click()
}

async function onFileChange(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  error.value = ''
  try {
    const text = await file.text()
    const data = JSON.parse(text)
    if (plans.value.length) {
      const ok = confirm(
        '已存在五年计划，导入将整体覆盖现有计划及其下全部 OKR、项目与待办，确定继续？'
      )
      if (!ok) {
        input.value = ''
        return
      }
    }
    importing.value = true
    await api.importPlan(data)
    await load()
  } catch (err) {
    error.value = (err as Error).message
  } finally {
    importing.value = false
    input.value = ''
  }
}

const hasOutline = (p: Plan) =>
  p.vision_positioning || p.indicators.length || p.domains.length ||
  p.special_projects.length || p.risks.length || p.okrs.length

onMounted(load)
</script>

<style scoped>
.page-container { max-width: 1080px; margin: 0 auto; }

/* ── 顶部工具栏 ── */
.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}
.page-title, .toolbar .section-title {
  font-size: 24px;
  font-weight: 700;
  letter-spacing: .02em;
  color: #1e293b;
}
.plans-new button:not(.ghost) {
  background: #2b6cd8;
  color: #fff;
  border: 1px solid transparent;
  border-radius: 10px;
  padding: 8px 16px;
  font-size: 13.5px;
  box-shadow: 0 1px 2px rgba(43,108,216,.3), 0 6px 16px rgba(43,108,216,.25);
  transition: background .15s;
}
.plans-new button:not(.ghost):hover { background: #1e57b5; }
.plans-new button:disabled { opacity: .55; cursor: not-allowed; }

/* ── Hero 区域 ── */
.hero {
  background: linear-gradient(135deg, rgba(43,108,216,.08), rgba(234,88,12,.05) 60%, transparent);
  border: 1px solid rgba(43,108,216,.28);
  border-radius: 20px;
  padding: 30px 34px;
  margin-bottom: 26px;
  position: relative;
  overflow: hidden;
}
.hero::after {
  content: '';
  position: absolute;
  right: -70px;
  top: -90px;
  width: 280px;
  height: 280px;
  background: radial-gradient(circle, rgba(43,108,216,.14), transparent 68%);
  pointer-events: none;
}
.hero-title {
  font-size: 26px;
  font-weight: 700;
  color: #1e293b;
  margin-bottom: 10px;
  position: relative;
}
.hero-meta {
  display: flex;
  gap: 10px;
  align-items: center;
  flex-wrap: wrap;
  position: relative;
}
.hero-tag {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 13px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
}
.hero-tag.period {
  background: rgba(43,108,216,.1);
  color: #1e57b5;
  border: 1px solid rgba(43,108,216,.28);
}
.hero-tag.okr {
  background: rgba(234,88,12,.1);
  color: #ea580c;
  border: 1px solid rgba(234,88,12,.25);
}
.hero-desc {
  margin-top: 14px;
  color: #5b6b80;
  font-size: 13.5px;
  position: relative;
  max-width: 680px;
  line-height: 1.8;
}

/* ── 区块标题 ── */
.section { margin-bottom: 30px; }
.section-head {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}
.section-num {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  border-radius: 9px;
  font-size: 14px;
  font-weight: 700;
  flex-shrink: 0;
}
.section-num.vision { background: rgba(43,108,216,.1); color: #1e57b5; }
.section-num.indicator { background: rgba(220,38,38,.1); color: #dc2626; }
.section-num.domain { background: rgba(5,150,105,.12); color: #059669; }
.section-num.project { background: rgba(161,98,7,.1); color: #a16207; }
.section-num.risk { background: rgba(234,88,12,.1); color: #ea580c; }
.section-num.eval { background: rgba(109,91,208,.1); color: #6d5bd0; }
.section-num.year1 { background: rgba(43,108,216,.1); color: #1e57b5; }
.section-title {
  font-size: 17px;
  font-weight: 700;
  color: #1e293b;
}

/* 卡片通用 */
.vision-card, .indicator-card, .domain-card, .sp-card, .risk-card, .eval-step, .year1-goals, .okr-card, .ph-list {
  background: #fff;
  border: 1px solid rgba(43,108,216,.1);
  border-radius: 16px;
  box-shadow: 0 1px 2px rgba(22,51,47,.04), 0 10px 28px rgba(22,51,47,.06);
}

/* ── 五年总纲 ── */
.vision-card {
  padding: 22px 26px;
  border-left: 4px solid #2b6cd8;
}
.vision-pos {
  font-size: 19px;
  font-weight: 700;
  color: #1e57b5;
  margin-bottom: 18px;
  line-height: 1.5;
}
.vision-cols {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
}
@media (max-width: 700px) { .vision-cols { grid-template-columns: 1fr; } }
.vision-col h5 {
  font-size: 12px;
  color: #5b6b80;
  text-transform: uppercase;
  letter-spacing: .06em;
  margin-bottom: 10px;
  font-weight: 700;
}
.vision-col ul { margin: 0; padding-left: 18px; }
.vision-col li {
  color: #1e293b;
  font-size: 13.5px;
  line-height: 1.9;
}
.vision-col.bottom { border-left: 2px solid rgba(220,38,38,.1); padding-left: 18px; }
.vision-col.bottom li { color: #dc2626; }

/* ── 指标体系 ── */
.indicator-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 14px;
}
@media (max-width: 700px) { .indicator-grid { grid-template-columns: 1fr; } }
.indicator-card {
  padding: 16px 18px;
  border-left: 4px solid;
}
.indicator-card.binding { border-left-color: #dc2626; }
.indicator-card.expected { border-left-color: #2b6cd8; }
.indicator-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 12px;
}
.indicator-name { font-size: 14.5px; font-weight: 600; color: #1e293b; }
.indicator-kind {
  font-size: 11px;
  padding: 2px 9px;
  border-radius: 999px;
  font-weight: 600;
  flex-shrink: 0;
  margin-left: 8px;
}
.indicator-kind.binding { background: rgba(220,38,38,.1); color: #dc2626; }
.indicator-kind.expected { background: rgba(43,108,216,.1); color: #1e57b5; }
.indicator-row { display: flex; gap: 18px; font-size: 12.5px; }
.indicator-row .item { flex: 1; }
.indicator-row .label { color: #5b6b80; margin-bottom: 3px; font-size: 11.5px; }
.indicator-row .value { font-weight: 600; font-variant-numeric: tabular-nums; color: #1e293b; }
.indicator-row .value.target { color: #059669; }
.indicator-freq { margin-top: 10px; font-size: 11.5px; color: #5b6b80; }

/* ── 重点领域 ── */
.domain-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 14px;
}
@media (max-width: 700px) { .domain-grid { grid-template-columns: 1fr; } }
.domain-card { padding: 18px; }
.domain-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}
.domain-name { font-size: 15px; font-weight: 600; color: #1e293b; }
.domain-status {
  font-size: 11px;
  padding: 2px 10px;
  border-radius: 999px;
  font-weight: 600;
}
.domain-status.key { background: rgba(43,108,216,.1); color: #1e57b5; }
.domain-status.normal { background: #e8effc; color: #5b6b80; }
.domain-field { font-size: 12.5px; margin-bottom: 6px; line-height: 1.6; }
.domain-field .lbl { color: #5b6b80; margin-right: 4px; }
.domain-field .val { color: #1e293b; }
.domain-tasks {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px dashed rgba(43,108,216,.1);
}
.domain-tasks .lbl { font-size: 11.5px; color: #5b6b80; margin-bottom: 5px; font-weight: 600; }
.domain-tasks ul { margin: 0; padding-left: 16px; }
.domain-tasks li { font-size: 12.5px; color: #1e293b; line-height: 1.8; }

/* ── 重大专项 ── */
.sp-list { display: flex; flex-direction: column; gap: 14px; }
.sp-card { padding: 18px 22px; border-left: 4px solid #a16207; }
.sp-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  flex-wrap: wrap;
  gap: 8px;
}
.sp-name { font-size: 16px; font-weight: 600; color: #1e293b; }
.sp-meta { display: flex; gap: 14px; font-size: 12.5px; color: #5b6b80; flex-wrap: wrap; }
.sp-meta b { color: #a16207; font-weight: 700; }
.sp-body {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 18px;
}
@media (max-width: 700px) { .sp-body { grid-template-columns: 1fr; } }
.sp-field .lbl {
  font-size: 11px;
  color: #5b6b80;
  text-transform: uppercase;
  letter-spacing: .05em;
  margin-bottom: 6px;
  font-weight: 700;
}
.sp-field .val { font-size: 13px; color: #1e293b; line-height: 1.7; }
.sp-milestones { display: flex; flex-direction: column; gap: 5px; }
.sp-milestone {
  font-size: 12.5px;
  color: #1e293b;
  padding-left: 18px;
  position: relative;
  line-height: 1.7;
}
.sp-milestone::before {
  content: '';
  position: absolute;
  left: 0;
  top: 8px;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #a16207;
}

/* ── 风险 ── */
.risk-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 14px;
}
@media (max-width: 700px) { .risk-grid { grid-template-columns: 1fr; } }
.risk-card { padding: 16px 18px; border-left: 4px solid #ea580c; }
.risk-type { font-size: 14px; font-weight: 700; color: #ea580c; margin-bottom: 12px; }
.risk-field { margin-bottom: 9px; }
.risk-field:last-child { margin-bottom: 0; }
.risk-field .lbl { font-size: 11px; color: #5b6b80; margin-bottom: 2px; font-weight: 600; }
.risk-field .val { font-size: 12.5px; color: #1e293b; line-height: 1.6; }

/* ── 评估 ── */
.eval-flow {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 14px;
}
@media (max-width: 700px) { .eval-flow { grid-template-columns: 1fr; } }
.eval-step { padding: 18px; text-align: center; }
.step-num {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  border-radius: 50%;
  background: rgba(109,91,208,.1);
  color: #6d5bd0;
  font-size: 15px;
  font-weight: 700;
  margin-bottom: 10px;
}
.step-title { font-size: 14px; font-weight: 600; margin-bottom: 6px; color: #1e293b; }
.step-desc { font-size: 12.5px; color: #5b6b80; line-height: 1.7; }

/* ── 首年 OKR ── */
.year1-goals { padding: 16px 18px; margin-bottom: 14px; }
.year1-goals .lbl { font-size: 12px; color: #5b6b80; margin-bottom: 6px; }
.year1-goals ul { margin: 0; padding-left: 18px; }
.year1-goals li { font-size: 13px; color: #1e293b; line-height: 1.8; }
.okr-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 14px;
}
@media (max-width: 700px) { .okr-grid { grid-template-columns: 1fr; } }
.okr-card { padding: 16px 18px; border-top: 4px solid #2b6cd8; }
.okr-q {
  display: inline-block;
  font-size: 11px;
  font-weight: 700;
  color: #1e57b5;
  background: rgba(43,108,216,.1);
  padding: 2px 9px;
  border-radius: 6px;
  margin-bottom: 8px;
}
.okr-obj { font-size: 14.5px; font-weight: 600; margin-bottom: 8px; line-height: 1.5; color: #1e293b; }
.okr-krs { margin: 0; padding-left: 16px; }
.okr-krs li { font-size: 12.5px; color: #5b6b80; line-height: 1.8; }

/* ── 待补充 ── */
.ph-list {
  background: rgba(161,98,7,.06);
  border: 1px solid rgba(161,98,7,.25);
  padding: 14px 18px;
}
.ph-item {
  font-size: 12px;
  color: #a16207;
  line-height: 1.8;
  padding-left: 18px;
  position: relative;
}
.ph-item::before { content: '⚠'; position: absolute; left: 0; }

/* ── 空状态 ── */
.empty-card {
  border: 1.5px dashed rgba(43,108,216,.25);
  border-radius: 16px;
  padding: 48px 32px;
  text-align: center;
  background: rgba(255,255,255,.6);
}
.empty-card h3 { margin: 0 0 12px; color: #1e293b; font-size: 18px; }
.empty-card p { color: #5b6b80; margin: 8px 0; font-size: 13px; line-height: 1.8; max-width: 560px; margin-left: auto; margin-right: auto; }
.empty-card code { background: #e8effc; padding: 2px 8px; border-radius: 4px; font-size: 12px; }
</style>

<template>
  <div class="page-container plans-new">
    <div class="toolbar">
    <div class="section-title" style="margin: 0">五年计划</div>
    <div>
      <input
        ref="fileInput"
        type="file"
        accept=".json,application/json"
        style="display: none"
        @change="onFileChange"
      />
      <button :disabled="importing" @click="triggerImport">
        {{ importing ? '导入中…' : '导入五年计划' }}
      </button>
    </div>
  </div>

  <p v-if="error" class="r3" style="margin-bottom: 12px">{{ error }}</p>

  <!-- 内容区域：加载完成后才渲染，触发入场动画 -->
  <div v-if="!loading">

  <!-- 空状态 -->
  <div v-if="!plans.length" class="empty-card">
    <h3>尚未创建五年计划</h3>
    <p>请先使用 <strong>Personal Five Year Plan</strong> 技能创建你的五年规划纲要。</p>
    <p>该技能会引导你完成现状基线、五年总定位、指标体系、重点领域、重大专项、风险预案与首年季度 OKR 的完整梳理，并导出为 JSON 文件。</p>
    <p style="margin-top: 20px">
      创建完成后，点击右上角 <strong>「导入五年计划」</strong> 按钮选择导出的 JSON 文件即可。
    </p>
    <p>
      推荐使用 <strong>Agent</strong> 通过 <strong>MCP 接口</strong>（<code>seeself_import_plan</code>）直接导入五年计划。
    </p>
  </div>

  <!-- 已存在计划 -->
  <template v-for="p in plans" :key="p.id">
    <!-- Hero 区域 -->
    <div class="hero anim-item stagger-2">
      <div class="hero-title">{{ p.name }}</div>
      <div class="hero-meta">
        <span class="hero-tag period">{{ p.start_year }}–{{ p.end_year }}</span>
        <span class="hero-tag okr">{{ p.okr_count }} 个 OKR</span>
      </div>
      <p v-if="p.description" class="hero-desc">{{ p.description }}</p>
    </div>

    <div v-if="hasOutline(p)">
      <!-- 〇、五年总纲 -->
      <section v-if="p.vision_positioning || p.vision_core_goals.length || p.vision_bottom_lines.length" class="section anim-item stagger-3">
        <div class="section-head">
          <span class="section-num vision">〇</span>
          <span class="section-title">五年总纲</span>
        </div>
        <div class="vision-card">
          <div class="vision-pos">定位：{{ p.vision_positioning || '待补充' }}</div>
          <div class="vision-cols">
            <div class="vision-col">
              <h5>核心目标</h5>
              <ul v-if="p.vision_core_goals.length">
                <li v-for="(g, i) in p.vision_core_goals" :key="i">{{ g }}</li>
              </ul>
              <p v-else class="muted" style="font-size: 12px">待补充</p>
            </div>
            <div class="vision-col bottom">
              <h5>底线约束</h5>
              <ul v-if="p.vision_bottom_lines.length">
                <li v-for="(b, i) in p.vision_bottom_lines" :key="i">{{ b }}</li>
              </ul>
              <p v-else class="muted" style="font-size: 12px">待补充</p>
            </div>
          </div>
        </div>
      </section>

      <!-- 一、指标体系 -->
      <section v-if="p.indicators.length" class="section anim-item stagger-4">
        <div class="section-head">
          <span class="section-num indicator">一</span>
          <span class="section-title">指标体系</span>
        </div>
        <div class="indicator-grid">
          <div v-for="(ind, i) in p.indicators" :key="i" class="indicator-card" :class="ind.kind">
            <div class="indicator-head">
              <span class="indicator-name">{{ ind.name }}</span>
              <span class="indicator-kind" :class="ind.kind">{{ ind.kind === 'binding' ? '约束性' : '预期性' }}</span>
            </div>
            <div class="indicator-row">
              <div class="item">
                <div class="label">基线</div>
                <div class="value">{{ ind.baseline || '—' }}</div>
              </div>
              <div class="item">
                <div class="label">5 年目标</div>
                <div class="value target">{{ ind.target || '—' }}</div>
              </div>
            </div>
            <div class="indicator-freq">检查频率：{{ ind.check_frequency || ind.measure || '—' }}</div>
          </div>
        </div>
      </section>

      <!-- 二、重点领域 -->
      <section v-if="p.domains.length" class="section anim-item stagger-5">
        <div class="section-head">
          <span class="section-num domain">二</span>
          <span class="section-title">重点领域任务</span>
        </div>
        <div class="domain-grid">
          <div v-for="(d, i) in p.domains" :key="i" class="domain-card">
            <div class="domain-head">
              <span class="domain-name">{{ d.domain }}</span>
              <span class="domain-status" :class="d.status === '重点' ? 'key' : 'normal'">{{ d.status }}</span>
            </div>
            <div class="domain-field">
              <span class="lbl">现状：</span><span class="val">{{ d.baseline || '—' }}</span>
            </div>
            <div class="domain-field">
              <span class="lbl">5 年目标：</span><span class="val">{{ d.five_year_target || '—' }}</span>
            </div>
            <div v-if="d.year1_tasks.length" class="domain-tasks">
              <div class="lbl">第一年任务</div>
              <ul>
                <li v-for="(t, j) in d.year1_tasks" :key="j">{{ t }}</li>
              </ul>
            </div>
          </div>
        </div>
      </section>

      <!-- 三、重大专项工程 -->
      <section v-if="p.special_projects.length" class="section anim-item stagger-6">
        <div class="section-head">
          <span class="section-num project">三</span>
          <span class="section-title">重大专项工程</span>
        </div>
        <div class="sp-list">
          <div v-for="(sp, i) in p.special_projects" :key="i" class="sp-card">
            <div class="sp-head">
              <span class="sp-name">{{ sp.name }}</span>
              <div class="sp-meta">
                <span><b>{{ sp.start || '—' }} ~ {{ sp.end || '—' }}</b></span>
                <span v-if="sp.effort">投入：{{ sp.effort }}</span>
              </div>
            </div>
            <div class="sp-body">
              <div class="sp-field">
                <div class="lbl">里程碑</div>
                <div class="sp-milestones" v-if="sp.milestones.length">
                  <div v-for="(m, j) in sp.milestones" :key="j" class="sp-milestone">M{{ j + 1 }}: {{ m }}</div>
                </div>
                <div v-else class="val">—</div>
              </div>
              <div class="sp-field">
                <div class="lbl">验收标准</div>
                <div class="val">{{ sp.acceptance_criteria || '—' }}</div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- 四、风险研判 -->
      <section v-if="p.risks.length" class="section anim-item stagger-7">
        <div class="section-head">
          <span class="section-num risk">四</span>
          <span class="section-title">风险研判与保障</span>
        </div>
        <div class="risk-grid">
          <div v-for="(r, i) in p.risks" :key="i" class="risk-card">
            <div class="risk-type">{{ r.risk_type }}</div>
            <div class="risk-field">
              <div class="lbl">触发信号</div>
              <div class="val">{{ r.trigger || '—' }}</div>
            </div>
            <div class="risk-field">
              <div class="lbl">预案</div>
              <div class="val">{{ r.plan || '—' }}</div>
            </div>
            <div class="risk-field">
              <div class="lbl">资源储备</div>
              <div class="val">{{ r.reserve || '—' }}</div>
            </div>
          </div>
        </div>
      </section>

      <!-- 五、评估机制 -->
      <section v-if="p.evaluation" class="section anim-item stagger-8">
        <div class="section-head">
          <span class="section-num eval">五</span>
          <span class="section-title">评估机制</span>
        </div>
        <div class="eval-flow">
          <div class="eval-step">
            <div class="step-num">1</div>
            <div class="step-title">年度评估</div>
            <div class="step-desc">{{ p.evaluation.annual || '每年对照指标打分' }}</div>
          </div>
          <div class="eval-step">
            <div class="step-num">2</div>
            <div class="step-title">中期评估</div>
            <div class="step-desc">{{ p.evaluation.midterm || '第3年年初，可调预期指标与专项' }}</div>
          </div>
          <div class="eval-step">
            <div class="step-num">3</div>
            <div class="step-title">期末评估</div>
            <div class="step-desc">{{ p.evaluation.final || '第5年年末，总结并起草下一轮' }}</div>
          </div>
        </div>
      </section>

      <!-- 六、首年拆解 -->
      <section v-if="p.year1_goals.length || p.okrs.length" class="section anim-item stagger-9">
        <div class="section-head">
          <span class="section-num year1">六</span>
          <span class="section-title">首年拆解{{ p.year1_period ? `（${p.year1_period}）` : '' }}</span>
        </div>
        <div v-if="p.year1_goals.length" class="year1-goals">
          <div class="lbl">年度目标</div>
          <ul>
            <li v-for="(g, i) in p.year1_goals" :key="i">{{ g }}</li>
          </ul>
        </div>
        <div v-if="p.okrs.length" class="okr-grid">
          <div v-for="o in p.okrs" :key="o.id" class="okr-card">
            <span class="okr-q">{{ o.quarter }}</span>
            <div class="okr-obj">{{ o.objective }}</div>
            <ul v-if="o.kr_results.length" class="okr-krs">
              <li v-for="(kr, j) in o.kr_results" :key="j">{{ kr }}</li>
            </ul>
          </div>
        </div>
      </section>

      <!-- 待补充清单 -->
      <section v-if="p.placeholders.length" class="section anim-item stagger-10">
        <div class="section-head">
          <span class="section-num" style="background: rgba(168, 134, 47,0.12); color: var(--yellow)">!</span>
          <span class="section-title">待补充清单</span>
        </div>
        <div class="ph-list">
          <div v-for="(ph, i) in p.placeholders" :key="i" class="ph-item">
            {{ ph.item }}{{ ph.note ? `（${ph.note}）` : '' }} —— 影响：{{ ph.impact || '—' }}
          </div>
        </div>
      </section>
    </div>
  </template>
  </div>
  </div>
</template>
