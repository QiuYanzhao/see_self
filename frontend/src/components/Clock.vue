<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'

// 毫秒级实时时钟（仅时分秒毫秒），requestAnimationFrame 驱动。
// 左上角录制红点，每秒闪烁一次。
const now = ref(new Date())
let raf = 0

function loop() {
  now.value = new Date()
  raf = requestAnimationFrame(loop)
}

onMounted(() => {
  raf = requestAnimationFrame(loop)
})
onBeforeUnmount(() => cancelAnimationFrame(raf))
</script>

<template>
  <div class="clock-wrap">
    <div class="clock">
      <span class="rec-dot"></span>
      <span class="time-text">
        {{ String(now.getHours()).padStart(2, '0') }}:{{ String(now.getMinutes()).padStart(2, '0') }}:{{ String(now.getSeconds()).padStart(2, '0') }}<span class="ms">.{{ String(now.getMilliseconds()).padStart(3, '0') }}</span>
      </span>
    </div>
  </div>
</template>

<style scoped>
.clock-wrap {
  position: relative;
  display: block;
  width: 100%;
  padding: 18px 0 14px;
  text-align: center;
}

/* 录制红点：时间数字左侧，每秒闪一次 */
.rec-dot {
  flex-shrink: 0;
  width: 9px;
  height: 9px;
  border-radius: 50%;
  background: #d4706f;
  box-shadow: 0 0 8px rgba(212, 112, 111, 0.7);
  animation: recBlink 1s step-end infinite;
}

@keyframes recBlink {
  0%, 49% { opacity: 1; }
  50%, 100% { opacity: 0.15; }
}

.clock {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  font-variant-numeric: tabular-nums;
  font-family: var(--serif);
  font-size: 28px;
  font-weight: 600;
  letter-spacing: 0.02em;
  color: var(--text, #e8e6e1);
}
.clock .ms {
  font-size: 14px;
  color: #e11d48;
  font-weight: 600;
}
</style>
