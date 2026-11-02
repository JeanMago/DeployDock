import type {
  Container, ContainerDetail, ContainerLogsResponse, ContainerExecResponse,
  Project, ProjectCreate, ProjectUpdate, ProjectPreview, ProjectMember, Deployment,
  DeploymentDiagnosis, EnvironmentVariable, SystemInfo, SystemResourcesOverview,
  PruneResult, RoutingConfig, User, TokenResponse, NotificationOverview,
  NotificationConfig, NotificationHistoryItem, ProjectHealthcheck
} from './types';

const API_BASE = '/api/v1';

export function resolvePublicUrl(rawUrl?: string | null): string | null | undefined {
  if (!rawUrl || typeof window === 'undefined') return rawUrl;
  const host = window.location.hostname;
  if (!host || host === 'localhost' || host === '127.0.0.1') {
    return rawUrl;
  }
  const subMatch = rawUrl.match(/^https?:\/\/([^./]+)\.localhost(?::\d+)?\/?$/i);
  if (subMatch) {
    return `${window.location.origin}/open/${subMatch[1]}/`;
  }
  const portMatch = rawUrl.match(/^https?:\/\/(?:localhost|127\.0\.0\.1):(\d+)\/?$/i);
  if (portMatch) {
    return `${window.location.origin}/open/port-${portMatch[1]}/`;
  }
  return rawUrl;
}

function adaptExternalUrls<T>(data: T): T {
  if (!data || typeof window === 'undefined') return data;
  const host = window.location.hostname;
  if (!host || host === 'localhost' || host === '127.0.0.1') return data;

  if (Array.isArray(data)) {
    return data.map((item) => adaptExternalUrls(item)) as unknown as T;
  }
  if (typeof data === 'object') {
    const obj = data as Record<string, any>;
    if (typeof obj.public_url === 'string' && obj.public_url) {
      obj.public_url = resolvePublicUrl(obj.public_url);
    } else if (!obj.public_url && obj.ports && typeof obj.ports === 'object' && obj.name !== 'deploydock-db') {
      for (const bindings of Object.values(obj.ports)) {
        if (Array.isArray(bindings)) {
          const hp = bindings.find((b: any) => b && b.HostPort && !['5432', '443'].includes(String(b.HostPort)));
          if (hp?.HostPort) {
            obj.public_url = `${window.location.origin}/open/port-${hp.HostPort}/`;
            break;
          }
        }
      }
    }
  }
  return data;
}

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

  if (res.status === 401 && !endpoint.includes('/auth/login') && !endpoint.includes('/auth/oauth')) {
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
  const json = (await res.json()) as T;
  return adaptExternalUrls(json);
}

async function downloadBlob(endpoint: string, fallbackFilename: string): Promise<void> {
  const token = localStorage.getItem('deploydock_token');
  const headers: Record<string, string> = {};
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  const res = await fetch(`${API_BASE}${endpoint}`, { headers });
  if (!res.ok) {
    let errorDetail = '';
    try {
      const errJson = await res.json();
      errorDetail = errJson.detail || JSON.stringify(errJson);
    } catch {
      errorDetail = await res.text().catch(() => '');
    }
    throw new Error(errorDetail || `Falha no download (${res.status})`);
  }
  const cd = res.headers.get('Content-Disposition') || '';
  const match = cd.match(/filename="?([^"]+)"?/i);
  const filename = match?.[1] || fallbackFilename;
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

export const api = {
  auth: {
    login: (credentials: { username: string; password: string; otp_code?: string }) =>
      request<TokenResponse>('/auth/login', {
        method: 'POST',
        body: JSON.stringify(credentials),
      }),
    me: () => request<User>('/auth/me'),
    setup2FA: () =>
      request<{ secret: string; otpauth_uri: string; totp_enabled: boolean }>('/auth/2fa/setup', {
        method: 'POST',
      }),
    enable2FA: (code: string) =>
      request<{ totp_enabled: boolean; message: string }>('/auth/2fa/enable', {
        method: 'POST',
        body: JSON.stringify({ code }),
      }),
    disable2FA: (code: string) =>
      request<{ totp_enabled: boolean; message: string }>('/auth/2fa/disable', {
        method: 'POST',
        body: JSON.stringify({ code }),
      }),
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
    updateUserRole: (userId: string, role: 'admin' | 'developer' | 'viewer') =>
      request<User>(`/auth/users/${userId}/role`, {
        method: 'PATCH',
        body: JSON.stringify({ role }),
      }),
    toggleUser: (userId: string) =>
      request<User>(`/auth/users/${userId}/toggle`, {
        method: 'PATCH',
      }),
    deleteUser: (userId: string) =>
      request<{ message: string }>(`/auth/users/${userId}`, {
        method: 'DELETE',
      }),
    getOAuthProviders: () =>
      request<import('./types').OAuthProvidersInfo>('/auth/oauth/providers'),
    startGithubOAuthDevice: (client_id?: string) =>
      request<{
        user_code: string;
        verification_uri: string;
        expires_in: number;
        interval: number;
      }>(`/auth/oauth/github/device/start${client_id ? `?client_id=${encodeURIComponent(client_id)}` : ''}`, {
        method: 'POST',
      }),
    pollGithubOAuthDevice: () =>
      request<{
        status: string;
        error_description?: string;
        access_token?: string;
        user?: User;
        github?: import('./types').GitHubIntegrationStatus;
      }>('/auth/oauth/github/device/poll', {
        method: 'POST',
      }),
    startGoogleOAuthDevice: () =>
      request<{
        user_code: string;
        verification_uri: string;
        expires_in: number;
        interval: number;
      }>('/auth/oauth/google/device/start', {
        method: 'POST',
      }),
    pollGoogleOAuthDevice: () =>
      request<{
        status: string;
        error_description?: string;
        access_token?: string;
        user?: User;
        google?: { email: string; name: string; picture: string; sub: string };
      }>('/auth/oauth/google/device/poll', {
        method: 'POST',
      }),
    loginWithGithub: (payload: {
      token?: string;
      username?: string;
      email?: string;
      name?: string;
      avatar_url?: string;
      use_paas_connected?: boolean;
    }) =>
      request<TokenResponse>('/auth/oauth/github', {
        method: 'POST',
        body: JSON.stringify(payload),
      }),
    loginWithGoogle: (payload: {
      id_token?: string;
      access_token?: string;
      app_password?: string;
      email?: string;
      name?: string;
      picture?: string;
      sub?: string;
    }) =>
      request<TokenResponse>('/auth/oauth/google', {
        method: 'POST',
        body: JSON.stringify(payload),
      }),
    getAccount: () =>
      request<{
        user: User;
        meta: Record<string, any>;
        sessions: import('./types').LoggedSessionItem[];
        github_paas: import('./types').GitHubIntegrationStatus;
        policies: import('./types').AdminAccessPolicies;
      }>('/auth/account'),
    updateAccountProfile: (payload: {
      full_name?: string;
      email?: string;
      avatar_url?: string;
      email_notifications?: boolean;
      notify_deploy_email?: boolean;
      notify_security_email?: boolean;
    }) =>
      request<{ user: User; meta: Record<string, any> }>('/auth/account/profile', {
        method: 'PUT',
        body: JSON.stringify(payload),
      }),
    linkGithubAccount: (payload: {
      token?: string;
      username?: string;
      email?: string;
      name?: string;
      avatar_url?: string;
      use_paas_connected?: boolean;
    }) =>
      request<{ user: User; meta: Record<string, any>; github_paas: import('./types').GitHubIntegrationStatus }>(
        '/auth/account/link/github',
        {
          method: 'POST',
          body: JSON.stringify(payload),
        }
      ),
    unlinkGithubAccount: () =>
      request<{ user: User; meta: Record<string, any> }>('/auth/account/link/github', {
        method: 'DELETE',
      }),
    linkGoogleAccount: (payload: {
      id_token?: string;
      access_token?: string;
      app_password?: string;
      email?: string;
      name?: string;
      picture?: string;
    }) =>
      request<{ user: User; meta: Record<string, any> }>('/auth/account/link/google', {
        method: 'POST',
        body: JSON.stringify(payload),
      }),
    unlinkGoogleAccount: () =>
      request<{ user: User; meta: Record<string, any> }>('/auth/account/link/google', {
        method: 'DELETE',
      }),
    getAdminAccessOverview: () =>
      request<import('./types').AdminAccessOverview>('/auth/admin/access'),
    updateAdminAccessPolicies: (payload: Partial<import('./types').AdminAccessPolicies>) =>
      request<{ policies: import('./types').AdminAccessPolicies }>('/auth/admin/access/policies', {
        method: 'PUT',
        body: JSON.stringify(payload),
      }),
    adminUpdateUserAccess: (
      userId: string,
      payload: {
        role?: 'admin' | 'developer' | 'viewer';
        is_active?: boolean;
        account_type?: string;
        github_username?: string;
        google_email?: string;
        email_notifications?: boolean;
      }
    ) =>
      request<User>(`/auth/admin/users/${userId}/access`, {
        method: 'PATCH',
        body: JSON.stringify(payload),
      }),
    adminRevokeUserSessions: (userId: string) =>
      request<{ revoked_sessions: number; username: string }>(
        `/auth/admin/users/${userId}/revoke-sessions`,
        { method: 'POST' }
      ),
    adminRevokeSingleSession: (sessionId: string) =>
      request<{ revoked: string }>(`/auth/admin/sessions/${sessionId}`, {
        method: 'DELETE',
      }),
  },
  containers: {
    list: (all = true) => request<Container[]>(`/containers?all=${all}`),
    get: (id: string) => request<ContainerDetail>(`/containers/${id}`),
    start: (id: string) => request<{message: string}>(`/containers/${id}/start`, { method: 'POST' }),
    stop: (id: string) => request<{message: string}>(`/containers/${id}/stop`, { method: 'POST' }),
    restart: (id: string) => request<{message: string}>(`/containers/${id}/restart`, { method: 'POST' }),
    remove: (id: string) => request<{message: string}>(`/containers/${id}`, { method: 'DELETE' }),
    updateResources: (
      id: string,
      payload: { memory_limit_mb?: number | null; cpu_limit_cores?: number | null }
    ) =>
      request<{ id: string; name: string; memory_limit_mb: number | null; cpu_limit_cores: number | null }>(
        `/containers/${id}/resources`,
        {
          method: 'PUT',
          body: JSON.stringify(payload),
        }
      ),
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
    writeFile: (id: string, path: string, content: string, restart: boolean = false) =>
      request<{ path: string; size_bytes: number; restarted: boolean }>(
        `/containers/${id}/files/content`,
        {
          method: 'PUT',
          body: JSON.stringify({ path, content, restart }),
        }
      ),
    uploadFile: (id: string, dir_path: string, filename: string, content_base64: string) =>
      request<{ path: string; filename: string; size_bytes: number }>(
        `/containers/${id}/files/upload`,
        {
          method: 'POST',
          body: JSON.stringify({ dir_path, filename, content_base64 }),
        }
      ),
    downloadFile: (id: string, path: string) =>
      downloadBlob(
        `/containers/${id}/files/download?path=${encodeURIComponent(path)}`,
        path.split('/').pop() || 'arquivo'
      ),
    deleteFile: (id: string, path: string) =>
      request<{ deleted: string; exit_code: number }>(
        `/containers/${id}/files?path=${encodeURIComponent(path)}`,
        { method: 'DELETE' }
      ),
    downloadDbDump: (id: string, containerName: string = 'container') =>
      downloadBlob(`/containers/${id}/db-dump`, `dump_${containerName}.sql`),
  },
  projects: {
    list: () => request<Project[]>('/projects'),
    get: (id: string) => request<Project>(`/projects/${id}`),
    getRoutingConfig: () => request<RoutingConfig>('/projects/routing-config'),
    create: (data: ProjectCreate) => request<Project>('/projects', { method: 'POST', body: JSON.stringify(data) }),
    update: (id: string, data: ProjectUpdate) => request<Project>(`/projects/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
    delete: (id: string) => request<{message: string}>(`/projects/${id}`, { method: 'DELETE' }),
    triggerDeploy: (id: string) => request<Deployment>(`/projects/${id}/deploy`, { method: 'POST' }),
    scale: (
      id: string,
      payload: {
        replicas: number;
        autoscale_enabled?: boolean;
        autoscale_min_replicas?: number;
        autoscale_max_replicas?: number;
        autoscale_cpu_target?: number;
      }
    ) =>
      request<any>(`/projects/${id}/scale`, {
        method: 'POST',
        body: JSON.stringify(payload),
      }),
    listMembers: (projectId: string) =>
      request<ProjectMember[]>(`/projects/${projectId}/members`),
    addMember: (
      projectId: string,
      userOrPayload: string | { user_id?: string; username?: string; role: 'admin' | 'developer' | 'viewer' },
      role?: 'admin' | 'developer' | 'viewer'
    ) =>
      request<ProjectMember>(`/projects/${projectId}/members`, {
        method: 'POST',
        body: JSON.stringify(
          typeof userOrPayload === 'string'
            ? { user_id: userOrPayload, role: role || 'developer' }
            : userOrPayload
        ),
      }),
    removeMember: (projectId: string, userId: string) =>
      request<{ removed: string }>(`/projects/${projectId}/members/${userId}`, {
        method: 'DELETE',
      }),
    listEnv: (id: string) => request<any>(`/projects/${id}/env`),
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
      request<ProjectHealthcheck>(`/projects/${projectId}/healthcheck`),
    uptimeOverview: () =>
      request<{ total_auto_heals: number; projects: Record<string, ProjectHealthcheck> }>(
        '/projects/uptime/overview'
      ),
    uptimeCheckNow: () =>
      request<{ total_auto_heals: number; projects: Record<string, ProjectHealthcheck> }>(
        '/projects/uptime/check-now',
        { method: 'POST' }
      ),
    listPreviews: (projectId: string) =>
      request<ProjectPreview[]>(`/projects/${projectId}/previews`),
    createPreview: (projectId: string, branch: string) =>
      request<ProjectPreview>(`/projects/${projectId}/previews`, {
        method: 'POST',
        body: JSON.stringify({ branch }),
      }),
    deletePreview: (projectId: string, branchSlug: string) =>
      request<{ deleted: string }>(
        `/projects/${projectId}/previews/${encodeURIComponent(branchSlug)}`,
        { method: 'DELETE' }
      ),
  },
  deployments: {
    list: (projectId?: string) => request<Deployment[]>(projectId ? `/deployments?project_id=${projectId}` : '/deployments'),
    get: (id: string) => request<Deployment>(`/deployments/${id}`),
    rollback: (id: string) => request<Deployment>(`/deployments/${id}/rollback`, { method: 'POST' }),
    diagnose: (id: string) => request<DeploymentDiagnosis>(`/deployments/${id}/diagnose`),
  },
  paas: {
    overview: () => request<any>('/paas/overview'),
    listDatabases: () => request<any[]>('/paas/databases'),
    createDatabase: (data: {
      name: string;
      engine: string;
      database_name?: string;
      username?: string;
      password?: string;
      expose_port?: number | null;
      memory_limit_mb?: number | null;
    }) =>
      request<any>('/paas/databases', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    deleteDatabase: (id: string) =>
      request<any>(`/paas/databases/${id}`, { method: 'DELETE' }),
    listTemplates: () => request<any[]>('/paas/templates'),
    launchTemplate: (templateId: string, payload?: { app_name?: string; env_overrides?: Record<string, string> }) =>
      request<any>(`/paas/templates/${templateId}/launch`, {
        method: 'POST',
        body: JSON.stringify(payload || {}),
      }),
    getBackups: () => request<any>('/paas/backups'),
    updateS3Config: (data: any) =>
      request<any>('/paas/backups/s3-config', {
        method: 'PUT',
        body: JSON.stringify(data),
      }),
    createBackupJob: (data: any) =>
      request<any>('/paas/backups/jobs', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    runBackupJob: (jobId: string) =>
      request<any>(`/paas/backups/jobs/${jobId}/run`, { method: 'POST' }),
    deleteBackupJob: (jobId: string) =>
      request<any>(`/paas/backups/jobs/${jobId}`, { method: 'DELETE' }),
    listCrons: (projectId?: string) =>
      request<any[]>(projectId ? `/paas/crons?project_id=${projectId}` : '/paas/crons'),
    createCron: (data: { project_id: string; name: string; command: string; cron_expression: string }) =>
      request<any>('/paas/crons', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    runCron: (cronId: string) =>
      request<any>(`/paas/crons/${cronId}/run`, { method: 'POST' }),
    deleteCron: (cronId: string) =>
      request<any>(`/paas/crons/${cronId}`, { method: 'DELETE' }),
    listRegistries: () => request<any[]>('/paas/registries'),
    addRegistry: (data: { name: string; server_address: string; username: string; password: string }) =>
      request<any>('/paas/registries', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    deleteRegistry: (id: string) =>
      request<any>(`/paas/registries/${id}`, { method: 'DELETE' }),
    getCloudflare: () => request<any>('/paas/cloudflare'),
    updateCloudflareConfig: (data: any) =>
      request<any>('/paas/cloudflare/config', {
        method: 'PUT',
        body: JSON.stringify(data),
      }),
    upsertCloudflareRecord: (data: { type: string; name: string; content: string; proxied?: boolean }) =>
      request<any>('/paas/cloudflare/records', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    syncProjectCloudflare: (projectId: string) =>
      request<any>(`/paas/cloudflare/sync-project/${projectId}`, { method: 'POST' }),
    deleteCloudflareRecord: (id: string) =>
      request<any>(`/paas/cloudflare/records/${id}`, { method: 'DELETE' }),
    getTraefik: () => request<any>('/paas/traefik'),
    updateTraefikConfig: (data: any) =>
      request<any>('/paas/traefik/config', {
        method: 'PUT',
        body: JSON.stringify(data),
      }),
    addTraefikCertificate: (data: { domain: string; cert_pem: string; key_pem: string; issuer?: string }) =>
      request<any>('/paas/traefik/certificates', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    deleteTraefikCertificate: (id: string) =>
      request<any>(`/paas/traefik/certificates/${id}`, { method: 'DELETE' }),
    diagnoseLogs: (data: { logs?: string; error_message?: string; status?: string }) =>
      request<DeploymentDiagnosis>('/paas/diagnose', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    evaluateAutoscaler: (simulated_cpu_by_project?: Record<string, number>) =>
      request<any>('/paas/autoscaler/evaluate', {
        method: 'POST',
        body: JSON.stringify({ simulated_cpu_by_project }),
      }),
    githubStatus: () => request<import('./types').GitHubIntegrationStatus>('/paas/github'),
    connectGithub: (data: {
      token: string;
      auto_inject_git_token?: boolean;
      auto_create_webhook?: boolean;
      auto_import_env_example?: boolean;
    }) =>
      request<import('./types').GitHubIntegrationStatus>('/paas/github/connect', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    startGithubDeviceFlow: (client_id?: string) =>
      request<{
        user_code: string;
        verification_uri: string;
        expires_in: number;
        interval: number;
      }>('/paas/github/device/start', {
        method: 'POST',
        body: JSON.stringify({ client_id: client_id || undefined }),
      }),
    pollGithubDeviceFlow: () =>
      request<{
        status: string;
        error_description?: string;
        github: import('./types').GitHubIntegrationStatus;
      }>('/paas/github/device/poll', {
        method: 'POST',
      }),
    updateGithubPreferences: (data: {
      username?: string;
      oauth_client_id?: string;
      auto_inject_git_token?: boolean;
      auto_create_webhook?: boolean;
      auto_import_env_example?: boolean;
    }) =>
      request<import('./types').GitHubIntegrationStatus>('/paas/github/preferences', {
        method: 'PATCH',
        body: JSON.stringify(data),
      }),
    disconnectGithub: () =>
      request<import('./types').GitHubIntegrationStatus>('/paas/github/disconnect', {
        method: 'DELETE',
      }),
    listGithubRepos: (username?: string) =>
      request<import('./types').GitHubRepoItem[]>(
        `/paas/github/repos${username ? `?username=${encodeURIComponent(username)}` : ''}`
      ),
    inspectGithubRepo: (repo_or_url: string, branch?: string) =>
      request<import('./types').GitHubRepoInspection>('/paas/github/inspect', {
        method: 'POST',
        body: JSON.stringify({ repo_or_url, branch }),
      }),
    createGithubWebhook: (repo_or_url: string, webhook_url: string, webhook_secret: string) =>
      request<any>('/paas/github/webhook', {
        method: 'POST',
        body: JSON.stringify({ repo_or_url, webhook_url, webhook_secret }),
      }),
  },
  system: {
    info: () => request<SystemInfo>('/system/info'),
    resources: () => request<SystemResourcesOverview>('/system/resources'),
    listImages: () => request<any[]>('/system/images'),
    deleteImage: (id: string) => request<{message: string}>(`/system/images/${encodeURIComponent(id)}`, { method: 'DELETE' }),
    listVolumes: () => request<any[]>('/system/volumes'),
    deleteVolume: (name: string) => request<{message: string}>(`/system/volumes/${encodeURIComponent(name)}`, { method: 'DELETE' }),
    backupVolume: (name: string) =>
      downloadBlob(`/system/volumes/${encodeURIComponent(name)}/backup`, `volume_${name}.tar.gz`),
    restoreVolume: (name: string, archive_base64: string) =>
      request<{ volume: string; restored_bytes: number; status: string }>(
        `/system/volumes/${encodeURIComponent(name)}/restore`,
        {
          method: 'POST',
          body: JSON.stringify({ archive_base64 }),
        }
      ),
    listNetworks: () => request<any[]>('/system/networks'),
    prune: (target: string = 'all') => request<PruneResult>(`/system/prune?target=${encodeURIComponent(target)}`, { method: 'POST' }),
    notifications: () => request<NotificationOverview>('/system/notifications'),
    updateNotificationsConfig: (data: Partial<NotificationConfig>) =>
      request<{ config: NotificationConfig; overview: NotificationOverview }>(
        '/system/notifications/config',
        {
          method: 'PUT',
          body: JSON.stringify(data),
        }
      ),
    testNotification: (payload?: { title?: string; message?: string; severity?: string; email_to?: string }) =>
      request<NotificationHistoryItem>('/system/notifications/test', {
        method: 'POST',
        body: JSON.stringify(payload || {}),
      }),
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
