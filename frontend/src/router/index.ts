import { createRouter, createWebHistory } from 'vue-router';
import MainLayout from '@/components/layout/MainLayout.vue';

const router = createRouter({
  history: createWebHistory('/'),
  routes: [
    {
      path: '/',
      component: MainLayout,
      redirect: '/dashboard',
      children: [
        {
          path: 'dashboard',
          name: 'Dashboard',
          component: () => import('@/pages/DashboardPage.vue')
        },
        {
          path: 'containers',
          name: 'Containers',
          component: () => import('@/pages/ContainerListPage.vue')
        },
        {
          path: 'containers/:id',
          name: 'ContainerDetail',
          component: () => import('@/pages/ContainerDetailPage.vue')
        },
        {
          path: 'projects',
          name: 'Projects',
          component: () => import('@/pages/ProjectsPage.vue')
        },
        {
          path: 'deployments',
          name: 'Deployments',
          component: () => import('@/pages/DeploymentsPage.vue')
        },
        {
          path: 'settings',
          name: 'Settings',
          component: () => import('@/pages/SettingsPage.vue')
        }
      ]
    }
  ]
});

export default router;
