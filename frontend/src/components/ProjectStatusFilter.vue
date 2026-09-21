<script setup lang="ts">
// 项目状态筛选：分段胶囊 Tabs，默认由父组件设为「进行中」
// 进行中 = 0 < progress < 100；待开始 = progress <= 0；已完成 = progress >= 100
export type ProjectStatus = 'active' | 'pending' | 'done'

const props = defineProps<{ modelValue: ProjectStatus }>()
const emit = defineEmits<{ (e: 'update:modelValue', v: ProjectStatus): void }>()

const options: { value: ProjectStatus; label: string }[] = [
  { value: 'active', label: '进行中' },
  { value: 'pending', label: '待开始' },
  { value: 'done', label: '已完成' },
]

function choose(v: ProjectStatus) {
  if (v === props.modelValue) return
  console.log('[ProjectStatusFilter] status ->', v)
  emit('update:modelValue', v)
}
</script>

<template>
  <div class="status-filter" role="tablist" aria-label="项目状态筛选">
    <button
      v-for="opt in options"
      :key="opt.value"
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
  display: inline-flex;
  align-items: center;
  gap: 2px;
  padding: 3px;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.45);
  border: 1px solid rgba(43, 101, 246, 0.25);
  box-shadow: 0 1px 3px rgba(30, 64, 175, 0.08);
}
.status-tab {
  padding: 6px 14px;
  font-size: 13px;
  line-height: 1.2;
  color: #5b6b80;
  background: transparent;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  white-space: nowrap;
  transition: color 0.15s, background 0.15s, box-shadow 0.15s;
}
.status-tab:hover {
  color: #1d4ed8;
  background: rgba(43, 101, 246, 0.08);
}
.status-tab.active {
  color: #fff;
  font-weight: 600;
  background: #2b65f6;
  box-shadow: 0 1px 3px rgba(43, 101, 246, 0.35);
}
</style>
