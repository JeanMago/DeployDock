import type {
  Container, ContainerDetail, ContainerLogsResponse, ContainerExecResponse,
  Project, ProjectCreate, ProjectUpdate, Deployment,
  EnvironmentVariable, SystemInfo, SystemResourcesOverview, PruneResult, RoutingConfig,
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
    changePassword: (current_password: string, new_password: string) =>
      request<{ message: string }>('/auth/password', {
        method: 'PUT',
        body: JSON.stringify({ current_password, new_password }),
      }),
    toggleUser: (userId: string) =>
      request<User>(`/auth/users/${userId}/toggle`, {
        method: 'PATCH',
      }),
    deleteUser: (userId: string) =>
      request<{ message: string }>(`/auth/users/${userId}`, {
        method: 'DELETE',
      }),
  },
  containers: {
    list: () => request<Container[]>('/containers'),
    get: (id: string) => request<ContainerDetail>(`/containers/${id}`),
    start: (id: string) => request<{message: string}>(`/containers/${id}/start`, { method: 'POST' }),
    stop: (id: string) => request<{message: string}>(`/containers/${id}/stop`, { method: 'POST' }),
    restart: (id: string) => request<{message: string}>(`/containers/${id}/restart`, { method: 'POST' }),
    remove: (id: string) => request<{message: string}>(`/containers/${id}`, { method: 'DELETE' }),
    getLogs: (
      id: string,
      params?: { tail?: number; timestamps?: boolean; since_seconds?: number; search?: string }
    ) => {
      const qs = new URLSearchParams();
      if (params?.tail !== undefined) qs.set('tail', String(params.tail));
      if (params?.timestamps !== undefined) qs.set('timestamps', String(params.timestamps));
      if (params?.since_seconds) qs.set('since_seconds', String(params.since_seconds));
      if (params?.search) qs.set('search', params.search);
      const query = qs.toString();
      return request<ContainerLogsResponse | string[]>(`/containers/${id}/logs${query ? '?' + query : ''}`);
    },
    exec: (id: string, command: string, workdir?: string) =>
      request<ContainerExecResponse>(`/containers/${id}/exec`, {
        method: 'POST',
        body: JSON.stringify({ command, workdir }),
      }),
    runQuick: (payload: {
      image: string;
      name?: string;
      host_port?: number | null;
      container_port?: number | null;
      env_text?: string;
      restart_policy?: string;
    }) =>
      request<{ id: string; name: string; image: string; state: string }>('/containers/run', {
        method: 'POST',
        body: JSON.stringify(payload),
      }),
    listFiles: (id: string, path: string = '/') =>
      request<{
        path: string;
        items: {
          name: string;
          path: string;
          is_dir: boolean;
          is_link: boolean;
          permissions: string;
          owner: string;
          size: string;
          modified: string;
        }[];
        stderr: string;
      }>(`/containers/${id}/files?path=${encodeURIComponent(path)}`),
    readFile: (id: string, path: string) =>
      request<{ path: string; content: string; stderr: string; exit_code: number }>(
        `/containers/${id}/files/content?path=${encodeURIComponent(path)}`
      ),
  },
  projects: {
    list: () => request<Project[]>('/projects'),
    get: (id: string) => request<Project>(`/projects/${id}`),
    getRoutingConfig: () => request<RoutingConfig>('/projects/routing-config'),
    create: (data: ProjectCreate) => request<Project>('/projects', { method: 'POST', body: JSON.stringify(data) }),
    update: (id: string, data: ProjectUpdate) => request<Project>(`/projects/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
    delete: (id: string) => request<{message: string}>(`/projects/${id}`, { method: 'DELETE' }),
    triggerDeploy: (id: string) => request<Deployment>(`/projects/${id}/deploy`, { method: 'POST' }),
    listEnv: (id: string) => request<EnvironmentVariable[]>(`/projects/${id}/env`),
    saveEnv: (
      id: string,
      payload: { key?: string; value?: string; is_secret?: boolean; bulk_content?: string; apply_now?: boolean }
    ) =>
      request<EnvironmentVariable[]>(`/projects/${id}/env`, {
        method: 'POST',
        body: JSON.stringify(payload),
      }),
    deleteEnv: (projectId: string, envId: string, applyNow: boolean = false) =>
      request<{ message: string }>(`/projects/${projectId}/env/${envId}?apply_now=${applyNow}`, {
        method: 'DELETE',
      }),
    applyEnv: (projectId: string) =>
      request<{ message: string }>(`/projects/${projectId}/env/apply`, {
        method: 'POST',
      }),
    healthcheck: (projectId: string) =>
      request<import('./types').ProjectHealthcheck>(`/projects/${projectId}/healthcheck`),
  },
  deployments: {
    list: (projectId?: string) => request<Deployment[]>(projectId ? `/deployments?project_id=${projectId}` : '/deployments'),
    get: (id: string) => request<Deployment>(`/deployments/${id}`),
    rollback: (id: string) => request<Deployment>(`/deployments/${id}/rollback`, { method: 'POST' })
  },
  system: {
    info: () => request<SystemInfo>('/system/info'),
    resources: () => request<SystemResourcesOverview>('/system/resources'),
    listImages: () => request<any[]>('/system/images'),
    deleteImage: (id: string) => request<{message: string}>(`/system/images/${encodeURIComponent(id)}`, { method: 'DELETE' }),
    listVolumes: () => request<any[]>('/system/volumes'),
    deleteVolume: (name: string) => request<{message: string}>(`/system/volumes/${encodeURIComponent(name)}`, { method: 'DELETE' }),
    listNetworks: () => request<any[]>('/system/networks'),
    prune: (target: string = 'all') => request<PruneResult>(`/system/prune?target=${encodeURIComponent(target)}`, { method: 'POST' }),
    productionCheck: () =>
      request<{
        score: number;
        passed_count: number;
        total_count: number;
        apps_base_domain: string;
        apps_tls_enabled: boolean;
        checks: { id: string; label: string; passed: boolean; hint: string }[];
      }>('/system/production-check'),
  },
  security: {
    overview: () => request<import('./types').SecurityOverview>('/security/overview'),
    updateConfig: (data: Partial<import('./types').SecurityConfig>) =>
      request<{ config: import('./types').SecurityConfig }>('/security/config', {
        method: 'PUT',
        body: JSON.stringify(data),
      }),
    blockIp: (ip: string, reason: string, duration_seconds: number | null = 3600) =>
      request<import('./types').BlockedIpInfo>('/security/block', {
        method: 'POST',
        body: JSON.stringify({ ip, reason, duration_seconds }),
      }),
    unblockIp: (ip: string) =>
      request<{ unblocked: boolean; ip: string }>('/security/unblock', {
        method: 'POST',
        body: JSON.stringify({ ip }),
      }),
    simulateAttack: (attack_type: string) =>
      request<any>('/security/simulate-attack', {
        method: 'POST',
        body: JSON.stringify({ attack_type }),
      }),
    clearAuditLogs: () =>
      request<{ status: string }>('/security/audit-logs', {
        method: 'DELETE',
      }),
  },
  envVars: {
    list: (projectId?: string) => request<EnvironmentVariable[]>(projectId ? `/env?project_id=${projectId}` : '/env'),
    create: (data: Partial<EnvironmentVariable>) => request<EnvironmentVariable>('/env', { method: 'POST', body: JSON.stringify(data) }),
    delete: (id: string) => request<{message: string}>(`/env/${id}`, { method: 'DELETE' })
  }
};


