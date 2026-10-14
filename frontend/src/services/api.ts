import type {
  Container, ContainerDetail,
  Project, ProjectCreate, ProjectUpdate, Deployment,
  EnvironmentVariable, SystemInfo, RoutingConfig,
  User, TokenResponse
} from './types';

const API_BASE = '/api/v1';

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const token = localStorage.getItem('deploydock_token');
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string> || {}),
  };

  if (token && !headers['Authorization']) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  });

  if (res.status === 401 && !endpoint.includes('/auth/login')) {
    // Redireciona para o login caso a sessão expire
    localStorage.removeItem('deploydock_token');
    localStorage.removeItem('deploydock_user');
    if (window.location.pathname !== '/login') {
      window.location.href = '/login';
    }
  }

  if (!res.ok) {
    let errorDetail = '';
    try {
      const errJson = await res.json();
      errorDetail = errJson.detail || JSON.stringify(errJson);
    } catch {
      errorDetail = await res.text().catch(() => '');
    }
    throw new Error(errorDetail || `API Error: ${res.status} ${res.statusText}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  auth: {
    login: (credentials: { username: string; password: string }) =>
      request<TokenResponse>('/auth/login', {
        method: 'POST',
        body: JSON.stringify(credentials),
      }),
    me: () => request<User>('/auth/me'),
    listUsers: () => request<User[]>('/auth/users'),
    createUser: (data: any) =>
      request<User>('/auth/users', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
  },
  containers: {
    list: () => request<Container[]>('/containers'),
    get: (id: string) => request<ContainerDetail>(`/containers/${id}`),
    start: (id: string) => request<{message: string}>(`/containers/${id}/start`, { method: 'POST' }),
    stop: (id: string) => request<{message: string}>(`/containers/${id}/stop`, { method: 'POST' }),
    restart: (id: string) => request<{message: string}>(`/containers/${id}/restart`, { method: 'POST' }),
    remove: (id: string) => request<{message: string}>(`/containers/${id}`, { method: 'DELETE' }),
    getLogs: (id: string) => request<{logs: string}>(`/containers/${id}/logs`)
  },
  projects: {
    list: () => request<Project[]>('/projects'),
    get: (id: string) => request<Project>(`/projects/${id}`),
    getRoutingConfig: () => request<RoutingConfig>('/projects/routing-config'),
    create: (data: ProjectCreate) => request<Project>('/projects', { method: 'POST', body: JSON.stringify(data) }),
    update: (id: string, data: ProjectUpdate) => request<Project>(`/projects/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
    delete: (id: string) => request<{message: string}>(`/projects/${id}`, { method: 'DELETE' }),
    triggerDeploy: (id: string) => request<Deployment>(`/projects/${id}/deploy`, { method: 'POST' })
  },
  deployments: {
    list: (projectId?: string) => request<Deployment[]>(projectId ? `/deployments?project_id=${projectId}` : '/deployments'),
    get: (id: string) => request<Deployment>(`/deployments/${id}`),
    rollback: (id: string) => request<Deployment>(`/deployments/${id}/rollback`, { method: 'POST' })
  },
  system: {
    info: () => request<SystemInfo>('/system/info'),
    listImages: () => request<any[]>('/system/images'),
    deleteImage: (id: string) => request<{message: string}>(`/system/images/${id}`, { method: 'DELETE' }),
    listVolumes: () => request<any[]>('/system/volumes'),
    listNetworks: () => request<any[]>('/system/networks'),
    prune: () => request<{reclaimed_space: number}>('/system/prune', { method: 'POST' })
  },
  envVars: {
    list: (projectId?: string) => request<EnvironmentVariable[]>(projectId ? `/env?project_id=${projectId}` : '/env'),
    create: (data: Partial<EnvironmentVariable>) => request<EnvironmentVariable>('/env', { method: 'POST', body: JSON.stringify(data) }),
    delete: (id: string) => request<{message: string}>(`/env/${id}`, { method: 'DELETE' })
  }
};
