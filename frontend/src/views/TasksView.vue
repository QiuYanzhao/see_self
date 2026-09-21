<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../api'
import type { Okr, Project } from '../api/types'
import OkrFilterSelect from '../components/OkrFilterSelect.vue'

// 计划页：项目列表，点击进入项目详情（计划编辑页）
const router = useRouter()
const projects = ref<Project[]>([])
const okrs = ref<Okr[]>([])
const filterOkrId = ref<number | null>(null)
const loading = ref(true)
const showModal = ref(false)
// 编辑态：editing=null 为新建，否则为编辑该项目
const editing = ref<Project | null>(null)
const formName = ref('')
const formDesc = ref('')
const formOkrId = ref<number | null>(null)

async function load() {
  loading.value = true
  try {
    projects.value = await api.listProjects()
  } finally {
    loading.value = false
  }
}

async function loadOkrs() {
  okrs.value = await api.listOkrs()
}

function openCreate() {
  editing.value = null
  formName.value = ''
  formDesc.value = ''
  formOkrId.value = null
  showModal.value = true
}

function openEdit(p: Project) {
  editing.value = p
  formName.value = p.name
  formDesc.value = p.description || ''
  formOkrId.value = p.okr_id
  showModal.value = true
}

async function saveProject() {
  if (!formName.value.trim()) return
  const body = {
    name: formName.value.trim(),
    description: formDesc.value || null,
    okr_id: formOkrId.value,
  }
  try {
    if (editing.value) {
      await api.updateProject(editing.value.id, body)
      showModal.value = false
      await load()
    } else {
      const p = await api.createProject(body)
      showModal.value = false
      router.push(`/projects/${p.id}`)
    }
  } catch (e: any) {
    alert(e.message)
  }
}

function okrLabel(okr: Okr) {
  return `${okr.quarter} · ${okr.objective}`
}

function projectOkrLabel(p: Project) {
  const okr = okrs.value.find((o) => o.id === p.okr_id)
  return okr ? okrLabel(okr) : ''
}

// OKR 筛选：null 为全部
const filteredProjects = computed(() => {
  if (!filterOkrId.value) return projects.value
  return projects.value.filter((p) => p.okr_id === filterOkrId.value)
})

// ESC 关闭弹窗
function onKey(e: KeyboardEvent) {
  if (e.key === 'Escape' && showModal.value) showModal.value = false
}

onMounted(() => {
  load()
  loadOkrs()
  window.addEventListener('keydown', onKey)
})

onUnmounted(() => {
  window.removeEventListener('keydown', onKey)
})
</script>

<template>
  <div class="page-container tasks-new">
    <div class="page-head">
      <h2 class="page-title">计划</h2>
      <div class="head-actions">
        <OkrFilterSelect v-model="filterOkrId" :okrs="okrs" />
        <button class="btn primary" @click="openCreate">新建项目</button>
      </div>
    </div>

    <div v-if="loading" class="empty">加载中...</div>
    <div v-else-if="!projects.length" class="empty">还没有项目，点击右上角创建</div>
    <div v-else-if="!filteredProjects.length" class="empty">该 OKR 下暂无项目</div>
    <div v-else class="project-grid">
      <div
        v-for="p in filteredProjects"
        :key="p.id"
        class="card project-card"
        @click="router.push(`/projects/${p.id}`)"
      >
        <div class="card-top">
          <h3>{{ p.name }}</h3>
          <button
            class="edit-btn"
            title="编辑项目"
            @click.stop="openEdit(p)"
          >
            <svg viewBox="0 0 16 16" width="12" height="12"><path d="M11.4 2.6 13.4 4.6 5.5 12.5 2.6 13.4 3.5 10.5 11.4 2.6z" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/></svg>
            编辑
          </button>
        </div>
        <div v-if="p.okr_id" class="okr-chip">{{ projectOkrLabel(p) }}</div>
        <div class="progress-bar">
          <div class="fill" :style="{ width: p.progress + '%' }" />
        </div>
        <div class="meta">
          {{ p.completed_leaves }}/{{ p.total_leaves }} 事项 · {{ p.progress.toFixed(0) }}%
        </div>
      </div>
    </div>

    <!-- 新建/编辑项目弹窗 -->
    <div v-if="showModal" class="modal-mask" @click.self="showModal = false">
      <div class="modal">
        <h3>{{ editing ? '编辑项目' : '新建项目' }}</h3>
        <input v-model="formName" placeholder="项目名称" @keyup.enter="saveProject" />
        <textarea v-model="formDesc" placeholder="描述（可选）" rows="7" />
        <label class="field-label">挂靠 OKR（可选）</label>
        <select v-model="formOkrId">
          <option :value="null">不挂靠</option>
          <option v-for="o in okrs" :key="o.id" :value="o.id">{{ okrLabel(o) }}</option>
        </select>
        <div class="modal-actions">
          <button class="btn" @click="showModal = false">取消</button>
          <button class="btn primary" @click="saveProject" :disabled="!formName.trim()">
            {{ editing ? '保存' : '创建' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 22px;
}
.head-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}
.page-title {
  font-size: 24px;
  font-weight: 700;
  letter-spacing: 0.02em;
  color: var(--text, #1e293b);
}

/* 主按钮：覆盖全局金色为中蓝 */
.tasks-new .btn.primary {
  background: #2b6cd8;
  color: #fff;
  border: 1px solid transparent;
  border-radius: 10px;
  padding: 8px 16px;
  font-size: 13.5px;
  box-shadow: 0 1px 2px rgba(43, 108, 216, 0.3), 0 6px 16px rgba(43, 108, 216, 0.25);
  transition: background 0.15s;
}
.tasks-new .btn.primary:hover {
  background: #1e57b5;
}
.tasks-new .btn.primary:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}
.tasks-new .btn.ghost,
.tasks-new .btn:not(.primary) {
  background: #fff;
  border: 1px solid rgba(43, 108, 216, 0.2);
  color: #5b6b80;
  border-radius: 10px;
  padding: 8px 16px;
  font-size: 13.5px;
  transition: all 0.15s;
}
.tasks-new .btn:not(.primary):hover {
  color: #1e293b;
  border-color: #2b6cd8;
  background: rgba(43, 108, 216, 0.08);
}

/* OKR 筛选下拉在本页也蓝化 */
.tasks-new :deep(.okr-filter-trigger) {
  background: #fff;
  border: 1px solid rgba(43, 108, 216, 0.28);
  border-radius: 10px;
}
.tasks-new :deep(.okr-filter-trigger:hover) {
  border-color: #2b6cd8;
}

.project-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 18px;
}
.project-card {
  position: relative;
  cursor: pointer;
  background: #fff;
  border: 1px solid rgba(43, 108, 216, 0.1);
  border-radius: 18px;
  padding: 18px 20px;
  box-shadow: 0 1px 2px rgba(22, 51, 47, 0.04), 0 10px 28px rgba(22, 51, 47, 0.06);
  transition: transform 0.3s cubic-bezier(0.22, 1, 0.36, 1), box-shadow 0.3s;
}
.project-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 2px 4px rgba(22, 51, 47, 0.05), 0 16px 36px rgba(22, 51, 47, 0.1);
}
.card-top {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 8px;
  margin-bottom: 10px;
}
.project-card h3 {
  font-size: 16.5px;
  margin: 0;
  line-height: 1.4;
  color: #1e293b;
}
.edit-btn {
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  font-size: 12px;
  color: #5b6b80;
  background: #f7faff;
  border: 1px solid rgba(43, 108, 216, 0.1);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.15s;
}
.edit-btn:hover {
  color: #1e57b5;
  border-color: rgba(43, 108, 216, 0.28);
  background: rgba(43, 108, 216, 0.08);
}
.okr-chip {
  display: inline-block;
  font-size: 11px;
  color: #1e57b5;
  background: rgba(43, 108, 216, 0.1);
  border: 1px solid rgba(43, 108, 216, 0.28);
  border-radius: 999px;
  padding: 2px 10px;
  margin-bottom: 12px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 100%;
}
.progress-bar {
  height: 7px;
  background: #e8effc;
  border-radius: 4px;
  overflow: hidden;
  margin-bottom: 8px;
}
.fill {
  height: 100%;
  background: linear-gradient(90deg, #2b6cd8, #7db2ec);
  border-radius: 4px;
}
.meta {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  font-size: 12px;
  color: #5b6b80;
}
.meta b {
  font-weight: 700;
  color: #1e57b5;
  font-variant-numeric: tabular-nums;
}

/* 弹窗：半透明遮罩 + 模糊，白卡片 */
.modal-mask {
  position: fixed;
  inset: 0;
  background: rgba(22, 51, 47, 0.45);
  -webkit-backdrop-filter: blur(4px);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
}
.modal {
  background: #fff;
  border: 1px solid rgba(43, 108, 216, 0.1);
  border-radius: 18px;
  padding: 26px 28px;
  width: 70vw;
  max-width: 70vw;
  min-height: 50vh;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: 0 24px 60px rgba(22, 51, 47, 0.25);
  animation: modalIn 0.25s cubic-bezier(0.22, 1, 0.36, 1);
}
@keyframes modalIn {
  from { opacity: 0; transform: translateY(10px) scale(0.98); }
  to { opacity: 1; transform: translateY(0) scale(1); }
}
.modal h3 {
  font-size: 18px;
  margin-bottom: 20px;
  color: #1e293b;
}
.modal input, .modal textarea, .modal select {
  width: 100%;
  padding: 10px 12px;
  margin-bottom: 14px;
  background: #f7faff;
  border: 1px solid rgba(43, 108, 216, 0.1);
  border-radius: 10px;
  color: #1e293b;
  font-size: 14px;
  font-family: inherit;
  outline: none;
  transition: border-color 0.15s, box-shadow 0.15s;
}
.modal input:focus, .modal textarea:focus, .modal select:focus {
  border-color: #2b6cd8;
  box-shadow: 0 0 0 3px rgba(43, 108, 216, 0.12);
}
/* 描述框：只允许纵向拉伸，且有高度上限，避免拖出弹窗边界 */
.modal textarea {
  resize: vertical;
  max-height: 50vh;
}
.field-label {
  display: block;
  font-size: 12px;
  color: #5b6b80;
  margin-bottom: 6px;
  font-weight: 600;
}
.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 6px;
}
.empty {
  color: #5b6b80;
  text-align: center;
  padding: 60px 0;
}
</style>
