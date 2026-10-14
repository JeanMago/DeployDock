import { ref, computed } from 'vue';
import { api } from '@/services/api';
import type { User } from '@/services/types';

const token = ref<string | null>(localStorage.getItem('deploydock_token'));
const currentUser = ref<User | null>(
  localStorage.getItem('deploydock_user')
    ? JSON.parse(localStorage.getItem('deploydock_user')!)
    : null
);

export function useAuth() {
  const isAuthenticated = computed(() => !!token.value);
  const isAdmin = computed(() => currentUser.value?.role === 'admin');
  const isDeveloper = computed(() => currentUser.value?.role === 'developer');
  const canAccessDocker = computed(() => isAdmin.value || isDeveloper.value);

  const login = async (username: string, password: string) => {
    const res = await api.auth.login({ username, password });
    token.value = res.access_token;
    currentUser.value = res.user;
    localStorage.setItem('deploydock_token', res.access_token);
    localStorage.setItem('deploydock_user', JSON.stringify(res.user));
    return res;
  };

  const logout = () => {
    token.value = null;
    currentUser.value = null;
    localStorage.removeItem('deploydock_token');
    localStorage.removeItem('deploydock_user');
    window.location.href = '/login';
  };

  const fetchProfile = async () => {
    if (!token.value) return null;
    try {
      const user = await api.auth.me();
      currentUser.value = user;
      localStorage.setItem('deploydock_user', JSON.stringify(user));
      return user;
    } catch {
      logout();
      return null;
    }
  };

  return {
    token,
    currentUser,
    isAuthenticated,
    isAdmin,
    isDeveloper,
    canAccessDocker,
    login,
    logout,
    fetchProfile,
  };
}
