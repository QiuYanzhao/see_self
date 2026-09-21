<script setup lang="ts">
defineProps<{
  text?: string
}>()
</script>

<style scoped>
.loading-overlay {
  position: absolute;
  inset: 0;
  background: rgba(244, 241, 234, 0.75);
  backdrop-filter: blur(2px);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  z-index: 100;
  border-radius: 10px;
  animation: fadeIn 0.2s ease-out;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

/* 旋转圆环：双层圆环，外层慢转、内层快转，营造层次感 */
.spinner {
  position: relative;
  width: 48px;
  height: 48px;
}

.spinner::before,
.spinner::after {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: 50%;
  border: 3px solid transparent;
}

.spinner::before {
  border-top-color: var(--blue);
  border-right-color: var(--blue);
  animation: spin 1s linear infinite;
}

.spinner::after {
  inset: 8px;
  border-bottom-color: var(--cyan);
  border-left-color: var(--cyan);
  animation: spin 0.7s linear infinite reverse;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.loading-text {
  color: var(--text-dim);
  font-size: 13px;
  letter-spacing: 0.05em;
  animation: pulse 1.5s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 0.5; }
  50% { opacity: 1; }
}

/* 三个跳动小点作为备选动画 */
.dots {
  display: flex;
  gap: 6px;
}
.dots span {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--blue);
  animation: dotBounce 1.2s ease-in-out infinite;
}
.dots span:nth-child(2) { animation-delay: 0.15s; background: var(--cyan); }
.dots span:nth-child(3) { animation-delay: 0.3s; background: var(--green); }

@keyframes dotBounce {
  0%, 80%, 100% { transform: scale(0.6); opacity: 0.4; }
  40% { transform: scale(1); opacity: 1; }
}
</style>

<template>
  <div class="loading-overlay">
    <div class="spinner"></div>
    <div class="loading-text">{{ text || '加载中…' }}</div>
  </div>
</template>
