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

  const setSession = (access_token: string, user: User) => {
    token.value = access_token;
    currentUser.value = user;
    localStorage.setItem('deploydock_token', access_token);
    localStorage.setItem('deploydock_user', JSON.stringify(user));
  };

  const login = async (username: string, password: string, otp_code?: string) => {
    const res = await api.auth.login({ username, password, otp_code });
    setSession(res.access_token, res.user);
    return res;
  };

  const loginWithGithub = async (payload: {
    token?: string;
    username?: string;
    email?: string;
    name?: string;
    avatar_url?: string;
    use_paas_connected?: boolean;
  }) => {
    const res = await api.auth.loginWithGithub(payload);
    setSession(res.access_token, res.user);
    return res;
  };

  const loginWithGoogle = async (payload: {
    id_token?: string;
    access_token?: string;
    app_password?: string;
    email?: string;
    name?: string;
    picture?: string;
    sub?: string;
  }) => {
    const res = await api.auth.loginWithGoogle(payload);
    setSession(res.access_token, res.user);
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
    loginWithGithub,
    loginWithGoogle,
    setSession,
    logout,
    fetchProfile,
  };
}
