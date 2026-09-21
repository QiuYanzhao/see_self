<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../api'
import type { Project, TodoNode } from '../api/types'

const props = defineProps<{ id: string }>()
const router = useRouter()
const projectId = Number(props.id)

const tree = ref<TodoNode[]>([])
const project = ref<Project | null>(null)
const loading = ref(true)
const expanded = ref<Set<number>>(new Set())

// 弹窗状态
const showModuleModal = ref(false)
const showTodoModal = ref(false)
const showEditModal = ref(false)
const showDeleteModal = ref(false)
const showDeleteProject = ref(false)

// 新增模块表单
const modForm = ref({ name: '', desc: '' })

// 新增事项表单
const todoForm = ref({ parent_id: null as number | null, title: '', description: '' })

// 编辑表单（模块 / 事项共用）
const editForm = ref({ id: 0, title: '', description: '' })
const editIsModule = ref(false)

// 删除确认
const deleteTarget = ref<TodoNode | null>(null)

// 印章直径 = 模块行实际高度（absolute 脱离文档流，不会撑高行）
function sizeStamps() {
  nextTick(() => {
    setTimeout(() => {
      document.querySelectorAll<HTMLElement>('.module-head').forEach((head) => {
        const img = head.querySelector<HTMLElement>('.done-stamp')
        if (!img) return
        const h = Math.round(head.getBoundingClientRect().height)
        if (h <= 0) return
        const size = Math.round(h * 1.25)
        img.style.width = `${size}px`
        img.style.height = `${size}px`
        const actions = head.querySelector<HTMLElement>('.row-actions')
        if (actions) {
          const hr = head.getBoundingClientRect()
          const ar = actions.getBoundingClientRect()
          img.style.left = `${Math.round(ar.left - hr.left - size - 40)}px`
        }
      })
    }, 120)
  })
}

const stats = computed(() => {
  let total = 0, done = 0
  // 模块（根节点）自身不计入；只统计模块下的事项叶子，空模块不算
  function count(nodes: TodoNode[], isRoot = true) {
    for (const n of nodes) {
      if (n.children.length) {
        count(n.children, false)
      } else if (!isRoot) {
        total++
        if (n.completed_at) done++
      }
    }
  }
  count(tree.value)
  const pct = total ? Math.round(done / total * 100) : 0
  return { total, done, pct }
})

// 进度环：周长 2πr（r=34 → ≈213.6），按完成度绘制
const ringLen = 2 * Math.PI * 34
const ringDash = computed(() => `${(ringLen * stats.value.pct / 100).toFixed(1)} ${ringLen.toFixed(1)}`)

// 顶层模块列表（供新增事项时选择）——全部模块，空模块也要可选
const topModules = computed(() => tree.value)

async function load() {
  loading.value = true
  try {
    const [t, ps] = await Promise.all([api.getTodoTree(projectId), api.listProjects()])
    tree.value = t
    project.value = ps.find(p => p.id === projectId) ?? null
    function expand(nodes: TodoNode[]) {
      for (const n of nodes) {
        if (n.children.length && !moduleDone(n)) {
          // 已完成模块默认折叠，只展开含未完成事项的模块
          expanded.value.add(n.id)
          expand(n.children)
        }
      }
    }
    expand(tree.value)
    sizeStamps()
  } finally {
    loading.value = false
  }
}

async function toggle(node: TodoNode) {
  const updated = (await api.toggleTodo(node.id, !node.completed_at)) as TodoNode
  node.completed_at = updated.completed_at
}

function toggleExpand(id: number) {
  if (expanded.value.has(id)) expanded.value.delete(id)
  else expanded.value.add(id)
}

// ── 本地树操作：写操作后不重载页面，直接改响应式数据 ──
function findNode(nodes: TodoNode[], id: number): TodoNode | null {
  for (const n of nodes) {
    if (n.id === id) return n
    if (n.children.length) {
      const hit = findNode(n.children, id)
      if (hit) return hit
    }
  }
  return null
}
function removeNodeInTree(nodes: TodoNode[], id: number): boolean {
  const idx = nodes.findIndex(n => n.id === id)
  if (idx >= 0) {
    nodes.splice(idx, 1)
    return true
  }
  for (const n of nodes) {
    if (n.children.length && removeNodeInTree(n.children, id)) return true
  }
  return false
}

// ── 模块拖拽排序：实时让位 + 落点边界提示 ──
const dragIdx = ref<number | null>(null)
const insertIdx = ref<number | null>(null)

function dragStart(idx: number) {
  dragIdx.value = idx
}
function dragEnd() {
  dragIdx.value = null
  insertIdx.value = null
}
function onDragOver(idx: number, e: DragEvent) {
  if (dragIdx.value === null) return
  const el = e.currentTarget as HTMLElement
  const rect = el.getBoundingClientRect()
  // 鼠标在模块上半 → 插到它前面；下半 → 后面
  const before = e.clientY < rect.top + rect.height / 2
  let target = before ? idx : idx + 1
  if (dragIdx.value < target) target -= 1
  if (insertIdx.value === target) return
  insertIdx.value = target
  const arr = [...tree.value]
  const [moved] = arr.splice(dragIdx.value, 1)
  arr.splice(target, 0, moved)
  tree.value = arr
  dragIdx.value = target
}
async function onDrop() {
  const from = dragIdx.value
  dragIdx.value = null
  insertIdx.value = null
  if (from === null) return
  // 顺序已在拖动中实时重排，静默持久化，不重载页面
  const ids = tree.value.map(n => n.id)
  await Promise.all(ids.map((id, i) => api.updateTodo(id, { sort_order: i })))
}

// 新增模块
function openModuleModal() {
  modForm.value = { name: '', desc: '' }
  showModuleModal.value = true
}
async function submitModule() {
  if (!modForm.value.name.trim()) return
  const created = (await api.createTodo({
    project_id: projectId,
    parent_id: null,
    title: modForm.value.name.trim(),
    description: modForm.value.desc.trim() || undefined,
  })) as TodoNode
  showModuleModal.value = false
  tree.value.push(created)
}

// 新增事项
function openTodoModal(parentId: number | null = null) {
  todoForm.value = { parent_id: parentId, title: '', description: '' }
  showTodoModal.value = true
}
async function submitTodo() {
  if (!todoForm.value.title.trim()) return
  const created = (await api.createTodo({
    project_id: projectId,
    parent_id: todoForm.value.parent_id,
    title: todoForm.value.title.trim(),
    description: todoForm.value.description.trim() || undefined,
  })) as TodoNode
  showTodoModal.value = false
  if (created.parent_id) {
    const parent = findNode(tree.value, created.parent_id)
    if (parent) {
      parent.children.push(created)
      expanded.value.add(parent.id)
    }
  } else {
    tree.value.push(created)
  }
}

// 编辑（模块 / 事项共用）
function openEditModule(node: TodoNode) {
  editIsModule.value = true
  editForm.value = { id: node.id, title: node.title, description: node.description ?? '' }
  showEditModal.value = true
}
function openEditTodo(node: TodoNode) {
  editIsModule.value = false
  editForm.value = { id: node.id, title: node.title, description: node.description ?? '' }
  showEditModal.value = true
}
async function submitEdit() {
  if (!editForm.value.title.trim()) return
  const updated = (await api.updateTodo(editForm.value.id, {
    title: editForm.value.title.trim(),
    description: editForm.value.description.trim() || undefined,
  })) as TodoNode
  showEditModal.value = false
  const node = findNode(tree.value, updated.id)
  if (node) {
    node.title = updated.title
    node.description = updated.description
  }
}

// 删除
function openDelete(node: TodoNode) {
  deleteTarget.value = node
  showDeleteModal.value = true
}
async function confirmDelete() {
  if (!deleteTarget.value) return
  await api.deleteTodo(deleteTarget.value.id)
  removeNodeInTree(tree.value, deleteTarget.value.id)
  expanded.value.delete(deleteTarget.value.id)
  showDeleteModal.value = false
  deleteTarget.value = null
}

// 删除整个项目
async function confirmDeleteProject() {
  await api.deleteProject(projectId)
  showDeleteProject.value = false
  router.push('/tasks')
}

function nodeProgress(node: TodoNode): string {
  // 模块的进度 = 子事项完成情况；空模块显示 0/0
  function countLeaf(n: TodoNode): [number, number] {
    if (!n.children.length) return [1, n.completed_at ? 1 : 0]
    let t = 0, d = 0
    for (const c of n.children) {
      const [ct, cd] = countLeaf(c)
      t += ct; d += cd
    }
    return [t, d]
  }
  const [t, d] = node.children.length ? countLeaf(node) : [0, 0]
  return `${d}/${t}`
}

// 模块是否已全部完成（有事项且所有叶子事项均已完成；空模块不算）
function moduleDone(node: TodoNode): boolean {
  if (!node.children.length) return false
  const allDone = (n: TodoNode): boolean =>
    n.children.length ? n.children.every(allDone) : !!n.completed_at
  return node.children.every(allDone)
}
function onResize() {
  sizeStamps()
}
onMounted(() => {
  load()
  window.addEventListener('resize', onResize)
})
onBeforeUnmount(() => window.removeEventListener('resize', onResize))
</script>

<template>
  <div class="page-container">
    <!-- 顶栏：返回 / 查看进度 -->
    <div class="proj-head">
      <button class="btn primary" @click="router.push('/tasks')">
        <svg viewBox="0 0 16 16" width="13" height="13"><path d="M10 3 5 8l5 5" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>
        返回计划
      </button>
      <div class="head-actions">
        <button class="btn danger" @click="showDeleteProject = true">删除项目</button>
        <button class="btn primary" @click="router.push(`/projects/${projectId}/progress`)">
          查看进度
          <svg viewBox="0 0 16 16" width="13" height="13"><path d="M6 3l5 5-5 5" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>
        </button>
      </div>
    </div>

    <!-- 项目档案区 -->
    <div class="proj-hero anim-item stagger-1">
      <div class="hero-main">
        <div class="hero-eyebrow">PROJECT</div>
        <h1 class="proj-name">{{ project?.name || '项目详情' }}</h1>
        <p v-if="project?.description" class="proj-desc">{{ project.description }}</p>
        <p v-else class="proj-desc muted">暂无描述</p>
      </div>
      <div class="hero-side">
        <div class="hero-ring-wrap">
          <svg class="hero-ring" viewBox="0 0 80 80">
            <circle class="ring-bg" cx="40" cy="40" r="34" />
            <circle class="ring-fg" cx="40" cy="40" r="34" :stroke-dasharray="ringDash" />
          </svg>
          <div class="ring-pct">{{ stats.pct }}<span>%</span></div>
        </div>
        <div class="hero-nums">
          <div class="num">
            <b>{{ stats.done }}</b>
            <span>已完成</span>
          </div>
          <div class="num">
            <b>{{ stats.total }}</b>
            <span>总事项</span>
          </div>
        </div>
      </div>
    </div>

    <div v-if="loading" class="empty">加载中...</div>

    <div v-else class="tree-wrap">
      <!-- 操作区 -->
      <div class="tree-actions anim-item stagger-2">
        <button class="btn primary" @click="openModuleModal">
          <svg viewBox="0 0 16 16" width="13" height="13"><path d="M8 3v10M3 8h10" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>
          新增模块
        </button>
        <button class="btn" @click="openTodoModal()">
          <svg viewBox="0 0 16 16" width="13" height="13"><path d="M8 3v10M3 8h10" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>
          新增事项
        </button>
        <span v-if="tree.length" class="tree-count">{{ stats.total }} 项 · {{ stats.done }} 已完成</span>
      </div>

      <!-- 空状态 -->
      <div v-if="!tree.length" class="empty-hint">
        <div class="empty-icon">
          <svg viewBox="0 0 24 24" width="30" height="30"><path d="M4 5h16v14H4z" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linejoin="round"/><path d="M4 9h16M8 5v14" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linejoin="round"/></svg>
        </div>
        <h3>还没有模块</h3>
        <p>点击「新增模块」建立第一个模块，开始规划你的项目结构。</p>
      </div>

      <!-- 事项树：模块独立卡片，支持拖动排序 -->
      <TransitionGroup v-else name="module-list" tag="div" class="tree anim-item stagger-3">
        <template v-for="(node, idx) in tree" :key="node.id">
          <div v-if="insertIdx === idx" :key="`line-${node.id}`" class="drop-line" />
          <div
            class="module"
            :class="{
              dragging: dragIdx === idx,
              'drop-before': insertIdx === idx,
              'drop-after': insertIdx === idx + 1,
            }"
            @dragover.prevent="onDragOver(idx, $event)"
            @drop.prevent="onDrop"
            @dragend="dragEnd"
          >
            <!-- 模块行 -->
            <div class="module-head" @click="toggleExpand(node.id)">
              <span class="drag-handle" draggable="true" title="拖动排序" @dragstart="dragStart(idx)" @dragend="dragEnd">
                <svg viewBox="0 0 16 16" width="12" height="12"><path d="M3 4.5h10M3 8h10M3 11.5h10" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/></svg>
              </span>
              <button class="twisty" :class="{ open: expanded.has(node.id) }" @click.stop>
              <svg viewBox="0 0 16 16" width="12" height="12"><path d="M5 3l5 5-5 5" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>
            </button>
            <span class="module-index">{{ String(idx + 1).padStart(2, '0') }}</span>
            <div class="module-info">
              <span class="module-name">{{ node.title }}</span>
              <span v-if="node.description" class="module-desc">{{ node.description }}</span>
            </div>
            <div class="module-progress">
              <span class="module-pct">{{ nodeProgress(node) }}</span>
            </div>
            <img
              v-if="moduleDone(node)"
              class="done-stamp"
              src="/done_stamp.png"
              alt="已完成"
              title="该模块事项已全部完成"
            />
            <div class="row-actions" @click.stop>
              <button class="mini-btn" title="添加事项" @click="openTodoModal(node.id)">
                <svg viewBox="0 0 16 16" width="11" height="11"><path d="M8 3v10M3 8h10" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>
                添加
              </button>
              <button class="mini-btn" title="编辑模块" @click="openEditModule(node)">
                <svg viewBox="0 0 16 16" width="11" height="11"><path d="M11.4 2.6 13.4 4.6 5.5 12.5 2.6 13.4 3.5 10.5 11.4 2.6z" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/></svg>
                编辑
              </button>
              <button class="mini-btn danger" title="删除模块" @click="openDelete(node)">
                <svg viewBox="0 0 16 16" width="11" height="11"><path d="M4 4l8 8M12 4l-8 8" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>
                删除
              </button>
            </div>
          </div>

          <!-- 子事项 -->
          <div v-if="expanded.has(node.id)" class="module-children">
            <div
              v-for="child in node.children"
              :key="child.id"
              class="todo-row"
              :class="{ done: child.completed_at }"
            >
              <div class="row-body">
                <span class="row-title">{{ child.title }}</span>
                <span v-if="child.description" class="row-desc">{{ child.description }}</span>
              </div>
              <div class="row-actions">
                <button class="mini-btn" title="编辑事项" @click="openEditTodo(child)">
                  <svg viewBox="0 0 16 16" width="11" height="11"><path d="M11.4 2.6 13.4 4.6 5.5 12.5 2.6 13.4 3.5 10.5 11.4 2.6z" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/></svg>
                  编辑
                </button>
                <button class="mini-btn danger" title="删除事项" @click="openDelete(child)">
                  <svg viewBox="0 0 16 16" width="11" height="11"><path d="M4 4l8 8M12 4l-8 8" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>
                  删除
                </button>
                <button
                  class="mini-btn done-btn"
                  :class="{ completed: child.completed_at }"
                  :title="child.completed_at ? '取消完成' : '标记完成'"
                  @click="toggle(child)"
                >
                  <svg viewBox="0 0 12 12"><path d="M2 6.2 4.8 9 10 3.2" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
                  {{ child.completed_at ? '已完成' : '完成' }}
                </button>
              </div>
            </div>
          </div>
        </div>
        </template>
        <div v-if="insertIdx === tree.length" :key="'line-end'" class="drop-line" />
      </TransitionGroup>
    </div>

    <!-- 新增模块弹窗 -->
    <div v-if="showModuleModal" class="modal-mask" @click.self="showModuleModal = false">
      <div class="modal">
        <h3>新增模块</h3>
        <div class="form-group">
          <label>模块名称</label>
          <input v-model="modForm.name" placeholder="如：Spring AI Alibaba 核心概念" autofocus />
        </div>
        <div class="form-group">
          <label>模块简介（可选）</label>
          <textarea v-model="modForm.desc" placeholder="这个模块要达成什么目标..." rows="3" />
        </div>
        <div class="modal-actions">
          <button class="btn" @click="showModuleModal = false">取消</button>
          <button class="btn primary" @click="submitModule" :disabled="!modForm.name.trim()">创建</button>
        </div>
      </div>
    </div>

    <!-- 新增事项弹窗 -->
    <div v-if="showTodoModal" class="modal-mask" @click.self="showTodoModal = false">
      <div class="modal">
        <h3>新增事项</h3>
        <div class="form-group">
          <label>所属模块</label>
          <select v-model="todoForm.parent_id">
            <option :value="undefined">顶层（不归属模块）</option>
            <option v-for="m in topModules" :key="m.id" :value="m.id">{{ m.title }}</option>
          </select>
        </div>
        <div class="form-group">
          <label>事项名称</label>
          <input v-model="todoForm.title" placeholder="如：阅读 Agent 模块官方文档" autofocus />
        </div>
        <div class="form-group">
          <label>备注（可选）</label>
          <textarea v-model="todoForm.description" placeholder="补充说明..." rows="2" />
        </div>
        <div class="modal-actions">
          <button class="btn" @click="showTodoModal = false">取消</button>
          <button class="btn primary" @click="submitTodo" :disabled="!todoForm.title.trim()">创建</button>
        </div>
      </div>
    </div>

    <!-- 编辑弹窗（模块 / 事项共用） -->
    <div v-if="showEditModal" class="modal-mask" @click.self="showEditModal = false">
      <div class="modal">
        <h3>{{ editIsModule ? '编辑模块' : '编辑事项' }}</h3>
        <div class="form-group">
          <label>{{ editIsModule ? '模块名称' : '事项名称' }}</label>
          <input v-model="editForm.title" placeholder="名称" autofocus />
        </div>
        <div class="form-group">
          <label>备注（可选）</label>
          <textarea v-model="editForm.description" placeholder="补充说明..." rows="2" />
        </div>
        <div class="modal-actions">
          <button class="btn" @click="showEditModal = false">取消</button>
          <button class="btn primary" @click="submitEdit" :disabled="!editForm.title.trim()">保存</button>
        </div>
      </div>
    </div>

    <!-- 删除确认弹窗 -->
    <div v-if="showDeleteModal" class="modal-mask" @click.self="showDeleteModal = false">
      <div class="modal modal-sm">
        <h3>确认删除</h3>
        <p class="delete-text">
          确定删除「{{ deleteTarget?.title }}」吗？<br />
          <span class="delete-warn">此操作会同时删除其所有子事项，且不可恢复。</span>
        </p>
        <div class="modal-actions">
          <button class="btn" @click="showDeleteModal = false">取消</button>
          <button class="btn danger" @click="confirmDelete">确认删除</button>
        </div>
      </div>
    </div>

    <!-- 删除项目确认弹窗 -->
    <div v-if="showDeleteProject" class="modal-mask" @click.self="showDeleteProject = false">
      <div class="modal modal-sm">
        <h3>删除项目</h3>
        <p class="delete-text">
          确定删除项目「{{ project?.name }}」吗？<br />
          <span class="delete-warn">此操作会删除该项目下的全部模块与事项，且不可恢复。</span>
        </p>
        <div class="modal-actions">
          <button class="btn" @click="showDeleteProject = false">取消</button>
          <button class="btn danger" @click="confirmDeleteProject">确认删除</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* ── 顶栏 ── */
.proj-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 18px;
}
.head-actions {
  display: flex;
  gap: 10px;
}
.btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  white-space: nowrap;
  background: #fff;
  border: 1px solid rgba(43,108,216,.2);
  color: #5b6b80;
  border-radius: 10px;
  padding: 8px 16px;
  font-size: 13.5px;
  cursor: pointer;
  transition: all 0.15s;
}
.btn:hover {
  color: #1e293b;
  border-color: #2b6cd8;
  background: rgba(43,108,216,.08);
}
.btn.primary {
  background: #2b6cd8;
  border-color: #2b6cd8;
  color: #fff;
  box-shadow: 0 1px 2px rgba(43,108,216,.3), 0 6px 16px rgba(43,108,216,.25);
}
.btn.primary:hover {
  background: #1e57b5;
  border-color: #1e57b5;
}
.btn.danger {
  background: rgba(220,38,38,.1);
  border-color: rgba(220,38,38,.25);
  color: #dc2626;
}

/* ── 项目档案区 ── */
.proj-hero {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 24px;
  background:
    linear-gradient(135deg, rgba(43,108,216,.07), transparent 55%),
    #fff;
  border: 1px solid rgba(43,108,216,.1);
  border-radius: 20px;
  padding: 28px 32px;
  margin-bottom: 24px;
  position: relative;
  overflow: hidden;
}
.proj-hero::after {
  content: '';
  position: absolute;
  right: -70px;
  top: -90px;
  width: 260px;
  height: 260px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(43,108,216,.10), transparent 68%);
  pointer-events: none;
}
.hero-main {
  min-width: 0;
  position: relative;
}
.hero-eyebrow {
  font-size: 10.5px;
  letter-spacing: 0.3em;
  color: #1e57b5;
  margin-bottom: 10px;
  font-weight: 700;
}
.proj-name {
  font-family: var(--serif);
  font-size: 28px;
  font-weight: 700;
  color: #1e293b;
  letter-spacing: 0.02em;
  line-height: 1.3;
  margin-bottom: 10px;
}
.proj-desc {
  font-size: 13px;
  color: var(--text-dim);
  line-height: 1.7;
  max-width: 560px;
  white-space: pre-line;
}
.hero-side {
  display: flex;
  align-items: center;
  gap: 22px;
  position: relative;
  flex-shrink: 0;
}
.hero-ring-wrap {
  position: relative;
  width: 88px;
  height: 88px;
}
.hero-ring {
  width: 88px;
  height: 88px;
  transform: rotate(-90deg);
}
.ring-bg {
  fill: none;
  stroke: #e8effc;
  stroke-width: 8;
}
.ring-fg {
  fill: none;
  stroke: #2b6cd8;
  stroke-width: 8;
  stroke-linecap: round;
  transition: stroke-dasharray 0.8s cubic-bezier(0.22, 1, 0.36, 1);
}
.ring-pct {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: var(--serif);
  font-size: 22px;
  font-weight: 600;
  color: var(--text);
}
.ring-pct span {
  font-size: 12px;
  color: var(--text-dim);
  margin-left: 1px;
  margin-top: 5px;
}
.hero-nums {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.num {
  display: flex;
  align-items: baseline;
  gap: 8px;
}
.num b {
  font-family: var(--serif);
  font-size: 22px;
  font-weight: 700;
  color: #1e57b5;
  font-variant-numeric: tabular-nums;
}
.num span {
  font-size: 12px;
  color: var(--text-dim);
}

/* ── 操作区 ── */
.tree-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 16px;
}
.tree-count {
  margin-left: auto;
  font-size: 12px;
  color: var(--text-faint);
  font-variant-numeric: tabular-nums;
}

/* ── 空状态 ── */
.empty-hint {
  text-align: center;
  padding: 70px 30px;
  border: 1px dashed var(--border-strong);
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.012);
}
.empty-icon {
  width: 56px;
  height: 56px;
  margin: 0 auto 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 16px;
  background: rgba(43,108,216,.1);
  color: #2b6cd8;
}
.empty-hint h3 {
  font-family: var(--serif);
  font-size: 17px;
  color: var(--text);
  margin-bottom: 8px;
}
.empty-hint p {
  font-size: 13px;
  color: var(--text-dim);
}

/* ── 事项树容器：模块独立卡片 ── */
.tree {
  display: flex;
  flex-direction: column;
  gap: 16px;
  background: transparent;
  border: none;
  border-radius: 0;
  overflow: visible;
}
.module {
  background: #fff;
  border: 1px solid rgba(43,108,216,.1);
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 0 1px 2px rgba(22,51,47,.04), 0 8px 22px rgba(22,51,47,.05);
  transition: opacity 0.15s;
}
/* 拖动时其他模块平滑让位 */
.module-list-move {
  transition: transform 0.2s cubic-bezier(0.22, 1, 0.36, 1);
}
.module.dragging {
  opacity: 0.35;
}
/* 落点边界提示线 */
.drop-line {
  height: 0;
  margin: 0 10px;
  border-top: 2px solid #2b6cd8;
  border-radius: 2px;
  box-shadow: 0 0 10px rgba(43,108,216,.45);
  flex-shrink: 0;
}

/* ── 模块行 —— 章节标题 ── */
.module-head {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px 20px;
  cursor: pointer;
  transition: background 0.15s;
  background: #fff;
}
.module-head:hover {
  background: #f7faff;
}
.drag-handle {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  color: #94a3b8;
  cursor: grab;
  border-radius: 7px;
  transition: color 0.15s, background 0.15s;
}
.drag-handle:hover {
  color: #5b6b80;
  background: #e8effc;
}
.drag-handle:active {
  cursor: grabbing;
}
.twisty {
  flex-shrink: 0;
  width: 26px;
  height: 26px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: none;
  border: none;
  color: #94a3b8;
  cursor: pointer;
  padding: 0;
  transition: transform 0.2s, color 0.15s;
}
.twisty.open {
  transform: rotate(90deg);
  color: #2b6cd8;
}
.module-index {
  flex-shrink: 0;
  font-family: var(--serif);
  font-size: 13px;
  font-weight: 700;
  color: #2b6cd8;
  letter-spacing: 0.06em;
  min-width: 28px;
}
.module-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 3px;
}
.module-name {
  font-family: var(--serif);
  font-size: 17px;
  font-weight: 700;
  color: #1e293b;
  letter-spacing: 0.015em;
}
.module-desc {
  font-size: 12px;
  color: var(--text-dim);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 560px;
}
.module-progress {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}
.module-pct {
  font-size: 12px;
  color: var(--text-faint);
  font-variant-numeric: tabular-nums;
  min-width: 30px;
  text-align: right;
}
.module-head {
  position: relative;
}
.done-stamp {
  position: absolute;
  top: 50%;
  transform: translateY(-50%) rotate(-8deg);
  width: 44px;
  height: 44px;
  aspect-ratio: 1 / 1;
  border-radius: 50%;
  object-fit: cover;
  filter: drop-shadow(0 2px 5px rgba(63, 158, 99, 0.32));
  opacity: 0.96;
  pointer-events: none;
}

/* ── 子事项行 —— 清单化,层级缩进 ── */
.module-children {
  border-top: 1px solid var(--border);
}
.todo-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 20px 10px 54px;
  transition: background 0.15s;
  position: relative;
}
.todo-row:hover {
  background: #f7faff;
}
.todo-row::before {
  content: '';
  position: absolute;
  left: 34px;
  top: 0;
  bottom: 0;
  width: 1px;
  background: var(--border);
}
.todo-row:last-child::before {
  bottom: 50%;
}

/* ── 行内容 ── */
.row-body {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.row-title {
  font-size: 14px;
  color: var(--text);
  transition: color 0.15s;
}
/* 完成态:勾选变绿 + 文字转暗 + 名称删除线 */
.todo-row.done .row-title {
  color: var(--text-faint);
  text-decoration: line-through;
  text-decoration-color: rgba(23, 20, 13, 0.35);
  text-decoration-thickness: 1.5px;
}
.row-desc {
  font-size: 12px;
  color: var(--text-dim);
  line-height: 1.45;
  white-space: pre-line;
}

/* ── 行操作：常显，悬停加深 ── */
.row-actions {
  display: flex;
  gap: 4px;
  opacity: 0.85;
  transition: opacity 0.15s;
  flex-shrink: 0;
}
.module-head:hover .row-actions,
.todo-row:hover .row-actions {
  opacity: 1;
}
.mini-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 5px 11px;
  font-size: 12px;
  line-height: 1;
  color: #5b6b80;
  background: #f7faff;
  border: 1px solid rgba(43,108,216,.1);
  border-radius: 8px;
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.15s;
}
.mini-btn:hover {
  color: #1e57b5;
  background: rgba(43,108,216,.1);
  border-color: rgba(43,108,216,.28);
}
.mini-btn.danger:hover {
  color: #dc2626;
  background: rgba(220,38,38,.1);
  border-color: rgba(220,38,38,.3);
}
/* ── 完成按钮：最右侧，完成态绿色填充 ── */
.done-btn:not(.completed) {
  color: #059669;
  border-color: rgba(5,150,105,.3);
  background: rgba(5,150,105,.12);
}
.done-btn:not(.completed):hover {
  color: #059669;
  background: rgba(5,150,105,.18);
  border-color: rgba(5,150,105,.4);
}
.done-btn.completed {
  color: #fff;
  background: #059669;
  border-color: #059669;
}
.done-btn.completed:hover {
  background: #047857;
  border-color: #047857;
}

/* ── 响应式：窄屏纵向堆叠 ── */
@media (max-width: 760px) {
  .proj-hero {
    flex-direction: column;
    align-items: flex-start;
    padding: 22px 20px;
  }
  .hero-side {
    width: 100%;
    justify-content: flex-start;
    margin-top: 4px;
  }
  .module-head {
    padding: 13px 14px;
    flex-wrap: wrap;
    row-gap: 8px;
  }
  .module-progress {
    margin-left: 34px;
  }
  .row-actions {
    margin-left: auto;
  }
  .todo-row {
    padding-left: 42px;
  }
  .todo-row::before {
    left: 24px;
  }
  .module-desc {
    max-width: none;
    white-space: normal;
  }
}

/* ── 弹窗 ── */
.modal-mask {
  position: fixed;
  inset: 0;
  background: rgba(5, 5, 8, 0.62);
  backdrop-filter: blur(3px);
  -webkit-backdrop-filter: blur(3px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
  animation: maskIn 0.18s ease-out;
}
@keyframes maskIn {
  from { opacity: 0; }
  to { opacity: 1; }
}
.modal {
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.018), transparent 45%), var(--bg-card);
  border: 1px solid var(--border-strong);
  border-radius: 16px;
  padding: 26px 28px;
  width: 440px;
  box-shadow: 0 24px 60px rgba(0, 0, 0, 0.45);
  animation: modalIn 0.2s cubic-bezier(0.22, 1, 0.36, 1);
}
@keyframes modalIn {
  from { opacity: 0; transform: translateY(8px) scale(0.98); }
  to { opacity: 1; transform: translateY(0) scale(1); }
}
.modal-sm { width: 380px; }
.modal h3 {
  font-family: var(--serif);
  margin-bottom: 20px;
  font-size: 18px;
  font-weight: 600;
}
.form-group { margin-bottom: 16px; }
.form-group label {
  display: block;
  font-size: 12px;
  color: var(--text-dim);
  margin-bottom: 6px;
  letter-spacing: 0.02em;
}
.form-group input,
.form-group select,
.form-group textarea {
  width: 100%;
  padding: 9px 12px;
  background: var(--bg-inset);
  border: 1px solid var(--border);
  border-radius: 8px;
  color: var(--text);
  font-size: 14px;
  outline: none;
  box-sizing: border-box;
  transition: border-color 0.15s, box-shadow 0.15s;
}
.form-group input:focus,
.form-group select:focus,
.form-group textarea:focus {
  border-color: rgba(43,108,216,.5);
  box-shadow: 0 0 0 3px rgba(43,108,216,.1);
}
.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 8px;
}
.delete-text {
  font-size: 14px;
  line-height: 1.7;
  margin-bottom: 20px;
  color: var(--text);
}
.delete-warn {
  font-size: 13px;
  color: var(--red);
}
</style>
