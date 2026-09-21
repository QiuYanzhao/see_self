<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import type { Okr } from '../api/types'

defineProps<{ okrs: Okr[]; modelValue: number | null }>()
const emit = defineEmits<{ (e: 'update:modelValue', v: number | null): void }>()

const open = ref(false)
const root = ref<HTMLElement | null>(null)

function currentLabel(v: number | null, okrs: Okr[]) {
  if (v === null) return '全部 OKR'
  const okr = okrs.find((o) => o.id === v)
  return okr ? `${okr.quarter} · ${okr.objective}` : '全部 OKR'
}

function choose(v: number | null) {
  emit('update:modelValue', v)
  open.value = false
}

function onDocClick(e: MouseEvent) {
  if (root.value && !root.value.contains(e.target as Node)) open.value = false
}

onMounted(() => document.addEventListener('click', onDocClick))
onBeforeUnmount(() => document.removeEventListener('click', onDocClick))
</script>

<template>
  <div ref="root" class="okr-filter">
    <button class="okr-trigger" :class="{ open }" type="button" @click="open = !open">
      <span class="okr-trigger-label" :title="currentLabel(modelValue, okrs)">{{ currentLabel(modelValue, okrs) }}</span>
      <svg class="chevron" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
        <polyline points="6 9 12 15 18 9" />
      </svg>
    </button>

    <transition name="drop">
      <div v-if="open" class="okr-menu">
        <button class="okr-opt" :class="{ active: modelValue === null }" type="button" @click="choose(null)">
          <span class="opt-text">全部 OKR</span>
          <svg v-if="modelValue === null" class="check" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="20 6 9 17 4 12" />
          </svg>
        </button>
        <button
          v-for="o in okrs"
          :key="o.id"
          class="okr-opt"
          :class="{ active: modelValue === o.id }"
          type="button"
          @click="choose(o.id)"
        >
          <span class="opt-text">{{ o.quarter }} · {{ o.objective }}</span>
          <svg v-if="modelValue === o.id" class="check" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="20 6 9 17 4 12" />
          </svg>
        </button>
      </div>
    </transition>
  </div>
</template>

<style scoped>
.okr-filter {
  position: relative;
}
.okr-trigger {
  display: flex;
  align-items: center;
  gap: 8px;
  max-width: 280px;
  padding: 8px 12px 8px 14px;
  font-size: 13px;
  color: var(--text);
  background-color: rgba(255, 255, 255, 0.55);
  border: 1px solid rgba(166, 124, 47, 0.25);
  border-radius: 8px;
  cursor: pointer;
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  box-shadow: 0 1px 3px rgba(40, 35, 25, 0.06);
  transition: border-color 0.15s, box-shadow 0.15s, background-color 0.15s;
}
.okr-trigger:hover {
  border-color: rgba(166, 124, 47, 0.45);
  background-color: rgba(255, 255, 255, 0.72);
}
.okr-trigger.open {
  border-color: #a67c2f;
  box-shadow: 0 0 0 3px rgba(166, 124, 47, 0.14);
}
.okr-trigger-label {
  flex: 1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  text-align: left;
}
.chevron {
  flex-shrink: 0;
  width: 12px;
  height: 12px;
  color: #a67c2f;
  transition: transform 0.18s;
}
.okr-trigger.open .chevron {
  transform: rotate(180deg);
}
.okr-menu {
  position: absolute;
  top: calc(100% + 6px);
  left: 0;
  right: 0;
  min-width: 260px;
  max-height: 320px;
  overflow-y: auto;
  padding: 6px;
  background: rgba(255, 253, 248, 0.92);
  border: 1px solid rgba(166, 124, 47, 0.28);
  border-radius: 10px;
  box-shadow: 0 10px 28px rgba(60, 50, 30, 0.16);
  backdrop-filter: blur(18px);
  -webkit-backdrop-filter: blur(18px);
  z-index: 60;
}
.okr-opt {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 8px 10px;
  font-size: 13px;
  color: var(--text);
  text-align: left;
  background: transparent;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  transition: background-color 0.12s, color 0.12s;
}
.okr-opt:hover {
  background: rgba(166, 124, 47, 0.12);
  color: #8a6620;
}
.okr-opt.active {
  color: #a67c2f;
  font-weight: 600;
}
.opt-text {
  flex: 1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.check {
  flex-shrink: 0;
  width: 13px;
  height: 13px;
  color: #a67c2f;
}
.drop-enter-active,
.drop-leave-active {
  transition: opacity 0.14s, transform 0.14s;
}
.drop-enter-from,
.drop-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}
</style>
