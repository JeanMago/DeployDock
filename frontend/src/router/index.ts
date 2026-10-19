import { createRouter, createWebHistory } from 'vue-router';
import MainLayout from '@/components/layout/MainLayout.vue';
import { useAuth } from '@/composables/useAuth';

const router = createRouter({
  history: createWebHistory('/'),
  routes: [
    {
      path: '/login',
      name: 'Login',
      component: () => import('@/pages/LoginPage.vue'),
      meta: { public: true }
    },
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
          component: () => import('@/pages/ContainerListPage.vue'),
          meta: { requiresDockerAccess: true }
        },
        {
          path: 'containers/:id',
          name: 'ContainerDetail',
          component: () => import('@/pages/ContainerDetailPage.vue'),
          meta: { requiresDockerAccess: true }
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
          path: 'resources',
          name: 'Resources',
          component: () => import('@/pages/ResourcesPage.vue'),
          meta: { requiresDockerAccess: true }
        },
        {
          path: 'security',
          name: 'Security',
          component: () => import('@/pages/SecurityPage.vue')
        },
        {
          path: 'settings',
          name: 'Settings',
          component: () => import('@/pages/SettingsPage.vue'),
          meta: { requiresAdmin: true }
        },
        {
          path: 'tutorial',
          name: 'Tutorial',
          component: () => import('@/pages/TutorialPage.vue')
        }
      ]
    }
  ]
});

// Guard de navegação para checagem de autenticação e permissões (RBAC)
router.beforeEach((to, _from, next) => {
  const { isAuthenticated, canAccessDocker, isAdmin } = useAuth();

  // 1. Rota pública (ex: login)
  if (to.meta.public) {
    if (isAuthenticated.value && to.path === '/login') {
      return next('/dashboard');
    }
    return next();
  }

  // 2. Não autenticado -> redireciona para login com parâmetro de retorno
  if (!isAuthenticated.value) {
    return next({ path: '/login', query: { redirect: to.fullPath } });
  }

  // 3. Exige permissão para acessar o Docker (admin ou developer)
  if (to.meta.requiresDockerAccess && !canAccessDocker.value) {
    alert('Acesso negado: você precisa de permissão de Administrador ou Desenvolvedor para acessar o Docker.');
    return next('/dashboard');
  }

  // 4. Exige permissão de administrador
  if (to.meta.requiresAdmin && !isAdmin.value) {
    alert('Acesso negado: área restrita a Administradores do sistema.');
    return next('/dashboard');
  }

  next();
});

export default router;
