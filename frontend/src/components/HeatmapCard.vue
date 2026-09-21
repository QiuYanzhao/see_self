<script setup lang="ts">
import { computed } from 'vue'
import type { HeatmapItem } from '../api/types'

const props = defineProps<{ items: HeatmapItem[] }>()

// 构建最近三个月的格子（从周一开始）
const heatmapDays = computed(() => {
  const today = new Date()
  const start = new Date(today)
  start.setMonth(start.getMonth() - 3)
  start.setDate(start.getDate() - start.getDay() + 1)

  const map = new Map<string, number>()
  for (const h of props.items) map.set(h.date, h.count)

  const weeks: { date: string; count: number }[][] = []
  let cur = new Date(start)
  while (cur <= today) {
    const week: { date: string; count: number }[] = []
    for (let d = 0; d < 7; d++) {
      if (cur > today) break
      const iso = cur.toISOString().slice(0, 10)
      week.push({ date: iso, count: map.get(iso) || 0 })
      cur.setDate(cur.getDate() + 1)
    }
    weeks.push(week)
  }
  return weeks
})

function cellColor(count: number): string {
  // GitHub 浅色热力图色阶
  if (count === 0) return '#ebedf0'
  if (count === 1) return '#9be9a8'
  if (count <= 3) return '#40c463'
  if (count <= 5) return '#30a14e'
  return '#216e39'
}

// 月份标签：对齐到各月第一个格子列（列宽 = 12px 格子 + 3px 间距）
const monthLabels = computed(() => {
  const labels: { label: string; left: number }[] = []
  const colW = 15
  for (let i = 0; i < heatmapDays.value.length; i++) {
    const week = heatmapDays.value[i]
    if (!week.length) continue
    const d = new Date(week[0].date + 'T00:00:00')
    const label = d.toLocaleString('en-US', { month: 'short' })
    if (!labels.length || labels[labels.length - 1].label !== label) {
      labels.push({ label, left: i * colW })
    }
  }
  return labels
})
</script>

<template>
  <div class="heatmap">
    <div class="heatmap-months">
      <span
        v-for="m in monthLabels"
        :key="m.label"
        class="hm-month"
        :style="{ left: m.left + 'px' }"
      >{{ m.label }}</span>
    </div>
    <div class="heatmap-grid">
      <div v-for="(week, wi) in heatmapDays" :key="wi" class="heatmap-col">
        <div
          v-for="(day, di) in week"
          :key="di"
          class="heatmap-cell"
          :style="{ background: cellColor(day.count) }"
          :title="`${day.date}: ${day.count} 个事项`"
        />
      </div>
    </div>
    <div class="heatmap-legend">
      <span>少</span>
      <span class="hm-cell" style="background: #ebedf0" />
      <span class="hm-cell" style="background: #9be9a8" />
      <span class="hm-cell" style="background: #40c463" />
      <span class="hm-cell" style="background: #30a14e" />
      <span class="hm-cell" style="background: #216e39" />
      <span>多</span>
    </div>
  </div>
</template>

<style scoped>
.heatmap {
  padding: 4px 0;
}
.heatmap-months {
  position: relative;
  height: 14px;
  margin-bottom: 4px;
}
.hm-month {
  position: absolute;
  top: 0;
  font-size: 10px;
  color: var(--text-faint);
}
.heatmap-grid {
  display: flex;
  gap: 3px;
  overflow-x: auto;
  padding-bottom: 2px;
}
.heatmap-col {
  display: flex;
  flex-direction: column;
  gap: 3px;
}
.heatmap-cell {
  width: 12px;
  height: 12px;
  border-radius: 3px;
}
.heatmap-legend {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-top: 8px;
  font-size: 10px;
  color: var(--text-faint);
}
.hm-cell {
  width: 10px;
  height: 10px;
  border-radius: 2px;
}
</style>
