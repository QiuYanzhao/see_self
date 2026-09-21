<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'

const props = defineProps<{ value: number; decimals?: number }>()

const shown = ref(0)
let raf = 0
let guard = 0

function animate(to: number) {
  cancelAnimationFrame(raf)
  clearTimeout(guard)
  const from = shown.value
  const dur = 600
  const t0 = performance.now()
  const step = (t: number) => {
    const p = Math.min(1, (t - t0) / dur)
    const e = 1 - Math.pow(1 - p, 3)
    shown.value = from + (to - from) * e
    if (p < 1) raf = requestAnimationFrame(step)
  }
  raf = requestAnimationFrame(step)
  // 兜底：动画帧不可用时(如后台标签页)直接落到目标值
  guard = window.setTimeout(() => {
    shown.value = to
  }, dur + 200)
}

watch(() => props.value, (v) => animate(v), { immediate: true })
onMounted(() => animate(props.value))
</script>

<template>
  <span class="num">{{ shown.toFixed(decimals ?? 0) }}</span>
</template>

<style scoped>
.num {
  font-family: var(--mono, ui-monospace, 'SF Mono', Menlo, monospace);
  font-variant-numeric: tabular-nums;
  letter-spacing: -0.01em;
}
</style>
