<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api } from '../api'

// 设置页：外观子tab
const activeTab = ref('appearance')

// 外观
const bgUrl = ref<string | null>(null)
const bgOpacity = ref(0.85)   // 0.05 ~ 1.0
const bgBlur = ref(30)        // 0 ~ 80 px
const uploading = ref(false)
const fileInput = ref<HTMLInputElement | null>(null)

function applyBgCss() {
  document.body.style.setProperty('--bg-opacity', bgOpacity.value.toFixed(2))
  document.body.style.setProperty('--bg-blur', `${bgBlur.value}px`)
}

async function loadAppearance() {
  try {
    const data = await api.getAppearance()
    bgUrl.value = data.background_image_url
    bgOpacity.value = data.background_opacity
    bgBlur.value = data.background_blur_radius
  } catch {
    // ignore
  }
}

async function onOpacityInput() {
  applyBgCss()
}
async function onOpacityChange() {
  applyBgCss()
  await api.saveAppearance({ background_opacity: bgOpacity.value }).catch((e: any) => alert(e.message))
}
async function onBlurInput() {
  applyBgCss()
}
async function onBlurChange() {
  applyBgCss()
  await api.saveAppearance({ background_blur_radius: bgBlur.value }).catch((e: any) => alert(e.message))
}

async function onUpload(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (!file) return
  uploading.value = true
  try {
    const data = await api.uploadBackground(file)
    bgUrl.value = data.background_image_url
    // 立即应用到 body（经 CSS 降噪层呈现）
    if (bgUrl.value) {
      document.body.style.setProperty('--bg-image', `url(${bgUrl.value})`)
    }
  } catch (err: any) {
    alert(err.message || '上传失败')
  } finally {
    uploading.value = false
    if (fileInput.value) fileInput.value.value = ''
  }
}

const showDeleteConfirm = ref(false)

function askRemove() {
  showDeleteConfirm.value = true
}
async function confirmRemove() {
  showDeleteConfirm.value = false
  try {
    await api.deleteBackground()
    bgUrl.value = null
    document.body.style.removeProperty('--bg-image')
  } catch (err: any) {
    alert(err.message || '删除失败')
  }
}

onMounted(loadAppearance)
</script>

<template>
  <div class="page-container">
    <h2 class="page-title">设置</h2>

    <!-- 子tab -->
    <div class="subtabs">
      <button
        class="subtab"
        :class="{ active: activeTab === 'appearance' }"
        @click="activeTab = 'appearance'"
      >外观</button>
    </div>

    <!-- 外观设置 -->
    <div v-if="activeTab === 'appearance'" class="settings-panel">
      <h3 class="panel-title">背景图片</h3>
      <p class="panel-desc">设置全站背景图片，支持 PNG / JPG / GIF / WebP，最大 10MB。</p>

      <!-- 预览 -->
      <div class="bg-preview">
        <div v-if="bgUrl" class="bg-preview-img" :style="{ backgroundImage: `url(${bgUrl})` }" />
        <div v-else class="bg-preview-empty">未设置背景图片</div>
      </div>

      <!-- 操作按钮 -->
      <div class="bg-actions">
        <button class="btn primary" @click="fileInput?.click()" :disabled="uploading">
          {{ uploading ? '上传中...' : bgUrl ? '更换背景图片' : '上传背景图片' }}
        </button>
        <button v-if="bgUrl" class="btn danger" @click="askRemove">删除背景图片</button>
        <input ref="fileInput" type="file" accept="image/*" style="display:none" @change="onUpload" />
      </div>

      <!-- 背景效果（Ghostty 风格：透明 + 模糊） -->
      <div class="bg-effect">
        <div class="effect-row">
          <label class="effect-label">背景不透明度</label>
          <input
            class="effect-slider"
            type="range"
            min="5"
            max="100"
            step="1"
            :value="Math.round(bgOpacity * 100)"
            @input="bgOpacity = Number(($event.target as HTMLInputElement).value) / 100; onOpacityInput()"
            @change="onOpacityChange"
          />
          <span class="effect-value">{{ Math.round(bgOpacity * 100) }}%</span>
        </div>
        <div class="effect-row">
          <label class="effect-label">背景模糊半径</label>
          <input
            class="effect-slider"
            type="range"
            min="0"
            max="80"
            step="1"
            :value="bgBlur"
            @input="bgBlur = Number(($event.target as HTMLInputElement).value); onBlurInput()"
            @change="onBlurChange"
          />
          <span class="effect-value">{{ bgBlur }}px</span>
        </div>
        <p class="effect-hint">拖动实时预览，松开自动保存。对应 Ghostty 的 background-opacity 与 background-blur-radius。</p>
      </div>

      <!-- 删除背景确认弹窗 -->
      <div v-if="showDeleteConfirm" class="modal-mask" @click.self="showDeleteConfirm = false">
        <div class="modal">
          <h3>删除背景图片</h3>
          <p class="modal-desc">确定要删除当前背景图片吗？删除后将恢复默认渐变背景，此操作不可恢复。</p>
          <div class="modal-actions">
            <button class="btn ghost" @click="showDeleteConfirm = false">取消</button>
            <button class="btn danger" @click="confirmRemove">确认删除</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page-container { max-width: 1080px; margin: 0 auto; }
.page-title {
  font-size: 24px;
  font-weight: 700;
  margin-bottom: 22px;
  letter-spacing: .02em;
  color: #1e293b;
}

.subtabs {
  display: flex;
  gap: 6px;
  margin-bottom: 24px;
  border-bottom: 1px solid rgba(43,108,216,.1);
}
.subtab {
  padding: 9px 18px;
  background: none;
  border: none;
  color: #5b6b80;
  cursor: pointer;
  font-size: 14px;
  border-bottom: 2.5px solid transparent;
  margin-bottom: -1px;
  transition: color .15s;
}
.subtab:hover { color: #1e293b; }
.subtab.active {
  color: #1e57b5;
  border-bottom-color: #2b6cd8;
  font-weight: 600;
}

.settings-panel {
  background: #fff;
  border: 1px solid rgba(43,108,216,.1);
  border-radius: 20px;
  padding: 28px 30px;
  box-shadow: 0 1px 2px rgba(22,51,47,.04), 0 10px 28px rgba(22,51,47,.06);
}
.panel-title {
  font-size: 17px;
  font-weight: 700;
  margin-bottom: 8px;
  color: #1e293b;
}
.panel-desc {
  color: #5b6b80;
  font-size: 13px;
  margin-bottom: 20px;
}

.bg-preview {
  width: 100%;
  height: 210px;
  border-radius: 14px;
  overflow: hidden;
  border: 1px solid rgba(43,108,216,.1);
  margin-bottom: 18px;
  background: linear-gradient(135deg, #1e57b5 0%, #2b6cd8 40%, #7db2ec 70%, #b3d4f5 100%);
  position: relative;
}
.bg-preview-img {
  width: 100%;
  height: 100%;
  background-size: cover;
  background-position: center;
}
.bg-preview-empty {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: rgba(255,255,255,.92);
  font-size: 13px;
  background: rgba(22,51,47,.15);
}

.bg-actions {
  display: flex;
  gap: 10px;
}
.bg-effect {
  margin-top: 26px;
  padding-top: 22px;
  border-top: 1px solid rgba(43,108,216,.1);
}
.effect-row {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 18px;
}
.effect-label {
  width: 110px;
  flex-shrink: 0;
  font-size: 13.5px;
  color: #5b6b80;
  font-weight: 600;
}
.effect-slider {
  flex: 1;
  -webkit-appearance: none;
  appearance: none;
  height: 6px;
  border-radius: 3px;
  background: linear-gradient(90deg, #2b6cd8 0%, #7db2ec 100%);
  outline: none;
  accent-color: #2b6cd8;
}
.effect-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: #fff;
  border: 2.5px solid #2b6cd8;
  box-shadow: 0 1px 4px rgba(22,51,47,.25);
  cursor: pointer;
}
.effect-value {
  width: 52px;
  flex-shrink: 0;
  text-align: right;
  font-size: 13.5px;
  font-variant-numeric: tabular-nums;
  color: #1e293b;
}
.effect-hint {
  font-size: 12px;
  color: #94a3b8;
  line-height: 1.7;
  margin: 2px 0 0;
}

.btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 9px 18px;
  font-size: 13.5px;
  border-radius: 10px;
  cursor: pointer;
  transition: all .15s;
  border: 1px solid transparent;
}
.btn.primary {
  background: #2b6cd8;
  color: #fff;
  box-shadow: 0 1px 2px rgba(43,108,216,.3), 0 6px 16px rgba(43,108,216,.25);
}
.btn.primary:hover { background: #1e57b5; }
.btn.danger {
  background: rgba(220,38,38,.1);
  border-color: rgba(220,38,38,.25);
  color: #dc2626;
}
.btn.danger:hover { background: rgba(220,38,38,.16); }
.btn:disabled { opacity: .55; cursor: not-allowed; }

.modal-mask {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.45);
  backdrop-filter: blur(4px);
  -webkit-backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
  animation: maskIn 0.18s ease-out;
}
@keyframes maskIn { from { opacity: 0; } to { opacity: 1; } }
.modal {
  width: 420px;
  background: #fff;
  border: 1px solid rgba(43,108,216,.1);
  border-radius: 18px;
  padding: 26px 28px;
  box-shadow: 0 24px 60px rgba(15,23,42,.25);
  animation: modalIn 0.22s cubic-bezier(.22,1,.36,1);
}
@keyframes modalIn { from { opacity: 0; transform: translateY(8px) scale(.98); } to { opacity: 1; transform: translateY(0) scale(1); } }
.modal h3 {
  font-size: 17px;
  font-weight: 700;
  margin-bottom: 10px;
  color: #1e293b;
}
.modal-desc {
  font-size: 13.5px;
  color: #5b6b80;
  line-height: 1.7;
  margin-bottom: 22px;
}
.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
.btn.ghost {
  background: #fff;
  border-color: rgba(43,108,216,.2);
  color: #5b6b80;
}
.btn.ghost:hover {
  color: #1e57b5;
  background: rgba(43,108,216,.08);
}
</style>
