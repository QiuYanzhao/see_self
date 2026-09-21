<script setup lang="ts">
import { computed, nextTick, onMounted, ref } from 'vue'

// 时间流逝进度条：充能加载（0 → value）+ 每3秒扫光 + 尾部节奏闪动
const props = defineProps<{
  label: string
  value: number
}>()

const fill = ref<HTMLDivElement | null>(null)
const bar = ref<HTMLDivElement | null>(null)
let started = false

// 进度小于10%时不显示扫光
const showShine = computed(() => props.value >= 10)

function start() {
  if (started || !fill.value || !bar.value) return
  started = true
  nextTick(() => {
    setTimeout(() => {
      if (fill.value) fill.value.style.width = props.value + '%'
    }, 100)
  })
}

onMounted(start)
</script>

<template>
  <div>
    <div class="tbar-head">
      <span class="lbl">{{ label }}</span>
      <span class="pct">{{ value.toFixed(2) }}%</span>
    </div>
    <div ref="bar" class="bar" :class="{ 'no-shine': !showShine }">
      <div ref="fill" class="fill gradient">
        <span class="spark" />
        <span v-if="showShine" class="shine" />
      </div>
    </div>
  </div>
</template>
