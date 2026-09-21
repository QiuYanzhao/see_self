<script setup lang="ts">
import { onMounted } from 'vue'
import { api } from './api'

// 应用外壳：顶部导航 + 路由出口
onMounted(async () => {
  // 加载外观设置：背景图片 + 透明度 + 模糊半径
  try {
    const bg = await api.getAppearance()
    if (bg.background_image_url) {
      document.body.style.setProperty('--bg-image', `url(${bg.background_image_url})`)
    }
    document.body.style.setProperty('--bg-opacity', String(bg.background_opacity))
    document.body.style.setProperty('--bg-blur', `${bg.background_blur_radius}px`)
  } catch {
    // 静默失败，使用默认背景
  }
})
</script>

<template>
  <div class="navbar">
    <RouterLink to="/" class="brand" aria-label="返回总览">
      <span class="brand-badge" aria-hidden="true">
        <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="#fff" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round">
          <path d="M3 17l5-6 4 4 6-8" />
        </svg>
      </span>
      see_self
    </RouterLink>
    <nav>
      <RouterLink to="/">总览</RouterLink>
      <RouterLink to="/tasks">计划</RouterLink>
      <RouterLink to="/okrs">OKR</RouterLink>
      <RouterLink to="/plans">五年计划</RouterLink>
      <RouterLink to="/settings">设置</RouterLink>
    </nav>
  </div>
  <RouterView />
</template>
