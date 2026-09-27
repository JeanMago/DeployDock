import type {
  Container, ContainerDetail,
  Project, ProjectCreate, ProjectUpdate, Deployment,
  EnvironmentVariable, SystemInfo
} from './types';

const API_BASE = '/api/v1';

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...options.headers },
  });
  if (!res.ok) {
    const errorText = await res.text().catch(() => '');
    throw new Error(`API Error: ${res.status} ${res.statusText} ${errorText}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
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
