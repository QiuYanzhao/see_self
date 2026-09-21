import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'dashboard', component: () => import('../views/DashboardView.vue') },
    { path: '/tasks', name: 'tasks', component: () => import('../views/TasksView.vue') },
    { path: '/okrs', name: 'okrs', component: () => import('../views/OkrsView.vue') },
    { path: '/plans', name: 'plans', component: () => import('../views/PlansView.vue') },
    { path: '/settings', name: 'settings', component: () => import('../views/SettingsView.vue') },
    {
      path: '/projects/:id',
      name: 'project',
      component: () => import('../views/ProjectView.vue'),
      props: true,
    },
    {
      path: '/projects/:id/progress',
      name: 'project-progress',
      component: () => import('../views/ProjectProgressView.vue'),
      props: true,
    },
  ],
})

export default router
