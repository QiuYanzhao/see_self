<script setup lang="ts">
// 项目状态筛选：分段胶囊 Tabs，默认由父组件设为「进行中」
// 进行中 = 0 < progress < 100；待开始 = progress <= 0；已完成 = progress >= 100
// 选中态由绝对定位滑块承载，切换时滑块平滑滑动到新选项
import { nextTick, onMounted, ref, watch } from 'vue'

export type ProjectStatus = 'active' | 'pending' | 'done'

const props = defineProps<{ modelValue: ProjectStatus }>()
const emit = defineEmits<{ (e: 'update:modelValue', v: ProjectStatus): void }>()

const options: { value: ProjectStatus; label: string }[] = [
  { value: 'active', label: '进行中' },
  { value: 'pending', label: '待开始' },
  { value: 'done', label: '已完成' },
]

const tabEls = ref<(HTMLElement | null)[]>([])
const slider = ref({ left: '0px', width: '0px', transition: 'none' })

function setTabRef(i: number) {
  return (el: unknown) => {
    tabEls.value[i] = el as HTMLElement | null
  }
}

function updateSlider(animate: boolean) {
  const idx = options.findIndex((o) => o.value === props.modelValue)
  const el = tabEls.value[idx]
  if (!el) return
  const ease = 'cubic-bezier(0.4, 0, 0.2, 1)'
  slider.value = {
    left: `${el.offsetLeft}px`,
    width: `${el.offsetWidth}px`,
    transition: animate
      ? `left 0.25s ${ease}, width 0.25s ${ease}`
      : 'none',
  }
}

// 首次挂载：滑块直接定位到默认选中项（不带动画）
onMounted(() => nextTick(() => updateSlider(false)))
// 切换：滑块平滑滑动
watch(
  () => props.modelValue,
  () => nextTick(() => updateSlider(true)),
)

function choose(v: ProjectStatus) {
  if (v === props.modelValue) return
  console.log('[ProjectStatusFilter] status ->', v)
  emit('update:modelValue', v)
}
</script>

<template>
  <div class="status-filter" role="tablist" aria-label="项目状态筛选">
    <span class="slider" :style="slider"></span>
    <button
      v-for="(opt, i) in options"
      :key="opt.value"
      :ref="setTabRef(i)"
      type="button"
      role="tab"
      class="status-tab"
      :class="{ active: modelValue === opt.value }"
      :aria-selected="modelValue === opt.value"
      @click="choose(opt.value)"
    >
      {{ opt.label }}
    </button>
  </div>
</template>

<style scoped>
.status-filter {
  position: relative;
  display: inline-flex;
  align-items: center;
  gap: 2px;
  padding: 3px;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.45);
  border: 1px solid rgba(43, 101, 246, 0.25);
  box-shadow: 0 1px 3px rgba(30, 64, 175, 0.08);
}
.slider {
  position: absolute;
  top: 3px;
  bottom: 3px;
  border-radius: 8px;
  background: #2b65f6;
  box-shadow: 0 1px 3px rgba(43, 101, 246, 0.35);
  pointer-events: none;
  z-index: 0;
  will-change: left, width;
}
.status-tab {
  position: relative;
  z-index: 1;
  padding: 6px 14px;
  font-size: 13px;
  line-height: 1.2;
  color: #5b6b80;
  background: transparent;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  white-space: nowrap;
  transition: color 0.15s, background 0.15s;
}
.status-tab:hover {
  color: #1d4ed8;
  background: rgba(43, 101, 246, 0.08);
}
.status-tab.active {
  color: #fff;
  font-weight: 600;
}
</style>
