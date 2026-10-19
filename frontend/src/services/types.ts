// Tipos TypeScript sincronizados com os schemas Pydantic do backend.

export interface Container {
  id: string;
  name: string;
  image: string;
  status: string;
  state: string | null;
  ports: Record<string, unknown> | null;
  created: string | null;
  labels?: Record<string, string> | null;
  public_url?: string | null;
}

export interface ContainerDetail extends Container {
  env: string[] | null;
  mounts: { type: string; source: string; destination: string }[] | null;
  networks: Record<string, unknown> | null;
  config: Record<string, unknown> | null;
  restart_policy: Record<string, unknown> | null;
}

export interface ContainerStats {
  cpu_percent: number;
  memory_percent: number;
  memory_usage_mb: number;
  memory_limit_mb: number;
  // Bug fix: nomes alinhados com DockerService.get_container_stats()
  network_rx_mb: number;
  network_tx_mb: number;
  timestamp?: string;
}

export interface Project {
  id: string;
  name: string;
  repo_url: string;
  branch: string;
  auto_deploy: boolean;
  webhook_secret?: string | null;
  subdomain?: string | null;
  custom_domain?: string | null;
  container_port?: number | null;
  public_host: string;
  public_url: string;
  last_deploy_status?: string;
  container_id?: string | null;
  created_at?: string;
  updated_at?: string;
}

export interface ProjectCreate {
  name: string;
  repo_url?: string;
  branch?: string;
  auto_deploy?: boolean;
  webhook_secret?: string;
  dockerfile_path?: string;
  docker_compose_path?: string;
  health_check_url?: string | null;
  health_check_interval?: number;
  subdomain?: string | null;
  custom_domain?: string | null;
  container_port?: number | null;
  template?: 'fastapi' | 'express' | 'static' | 'custom';
  dockerfile_content?: string;
}

export interface RoutingConfig {
  base_domain: string;
  tls_enabled: boolean;
  scheme: string;
  port_suffix: string;
}

export type ProjectUpdate = Partial<ProjectCreate>;

export interface Deployment {
  id: string;
  project_id: string;
  commit_sha: string;
  commit_message: string | null;
  commit_author: string | null;
  branch: string;
  status: 'pending' | 'cloning' | 'building' | 'deploying' | 'health_check' | 'healthy' | 'failed' | 'rolled_back';
  build_logs: string | null;
  error_message: string | null;
  previous_image_id: string | null;
  duration_seconds: number | null;
  started_at: string;
  finished_at: string | null;
}

export interface EnvironmentVariable {
  id: string;
  key: string;
  value: string;
  is_secret?: boolean;
  project_id?: string;
  created_at?: string;
}

export interface ContainerLogsResponse {
  container_id: string;
  container_name: string;
  state: string | null;
  lines: string[];
  logs: string;
  count: number;
}

export interface ContainerExecResponse {
  exit_code: number;
  stdout: string;
  stderr: string;
  output: string;
}


// Bug fix: campos alinhados com DockerService.get_system_info() e schema SystemInfo do backend
export interface SystemInfo {
  docker_version: string | null;
  api_version: string | null;
  os: string | null;
  architecture: string | null;
  cpus: number | null;
  memory_total_mb: number | null;
  containers_count: number | null;
  containers_running: number | null;
  containers_stopped: number | null;
  containers_paused: number | null;
  images_count: number | null;
  volumes_count: number | null;
  networks_count: number | null;
}

export interface HostDiskInfo {
  mount: string;
  label: string;
  total_gb: number;
  used_gb: number;
  free_gb: number;
  percent: number;
}

export interface HostMetrics {
  hostname: string;
  os: string;
  architecture: string;
  cpu_model: string;
  cpu_cores: number;
  cpu_percent: number;
  cpu_per_core: number[];
  load_avg: [number, number, number];
  uptime_seconds: number;
  memory_total_mb: number;
  memory_used_mb: number;
  memory_cached_mb: number;
  memory_free_mb: number;
  memory_percent: number;
  swap_total_mb: number;
  swap_used_mb: number;
  swap_percent: number;
  disks: HostDiskInfo[];
}

export interface ContainerResourceItem {
  id: string;
  full_id: string;
  name: string;
  image: string;
  state: string;
  status: string;
  cpu_percent: number;
  memory_usage_mb: number;
  memory_limit_mb: number;
  memory_host_percent: number;
  network_rx_mb: number;
  network_tx_mb: number;
  size_rw_mb: number;
  size_rootfs_mb: number;
}

export interface DockerUsageOverview {
  cpu_percent: number;
  cpu_normalized_percent: number;
  memory_used_mb: number;
  memory_share_of_host_percent: number;
  network_rx_mb: number;
  network_tx_mb: number;
  containers_running: number;
  containers_total: number;
  containers: ContainerResourceItem[];
}

export interface StorageCategoryStats {
  total_count: number;
  active_count: number;
  size_mb: number;
  reclaimable_mb: number;
}

export interface DockerImageDiskItem {
  id: string;
  full_id: string;
  tag: string;
  created: number | string | null;
  size_mb: number;
  shared_mb: number;
  containers_count: number;
  in_use: boolean;
}

export interface DockerVolumeDiskItem {
  name: string;
  driver: string;
  mountpoint: string | null;
  created: string | null;
  size_mb: number;
  ref_count: number;
  in_use: boolean;
}

export interface DockerStorageOverview {
  total_docker_mb: number;
  reclaimable_mb: number;
  repos_dir_mb: number;
  repos_count: number;
  categories: {
    images: StorageCategoryStats;
    containers: StorageCategoryStats;
    volumes: StorageCategoryStats;
    build_cache: StorageCategoryStats;
  };
  images_list: DockerImageDiskItem[];
  volumes_list: DockerVolumeDiskItem[];
}

export interface SystemResourcesOverview {
  host: HostMetrics;
  docker_usage: DockerUsageOverview;
  storage: DockerStorageOverview;
}

export interface PruneResult {
  target?: string;
  containers_deleted: number;
  images_deleted: number;
  volumes_deleted: number;
  networks_deleted: number;
  reclaimed_space: number;
  space_reclaimed_mb: number;
}

export interface WebSocketMessage {
  type: string;
  payload: unknown;
}

export interface User {
  id: string;
  username: string;
  email: string;
  role: 'admin' | 'developer' | 'viewer';
  is_active: boolean;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface ProjectHealthcheck {
  project_id: string;
  name: string;
  public_url: string;
  reachable: boolean;
  status_code: number;
  latency_ms: number;
  error?: string;
}

export interface SecurityConfig {
  waf_enabled: boolean;
  rate_limit_enabled: boolean;
  rate_limit_per_minute: number;
  login_max_attempts: number;
  login_lockout_seconds: number;
  ssrf_protection: boolean;
  container_no_new_privileges: boolean;
  security_headers: boolean;
}

export interface BlockedIpInfo {
  ip: string;
  reason: string;
  blocked_at: string;
  expires_at: number | null;
  permanent: boolean;
}

export interface SecurityAuditLog {
  id: string;
  timestamp: string;
  event_type: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  ip: string;
  path: string;
  detail: string;
  user: string;
  blocked: boolean;
}

export interface SecurityOverview {
  security_score: number;
  enabled_layers: number;
  total_layers: number;
  config: SecurityConfig;
  stats: {
    total_requests_inspected: number;
    waf_attacks_blocked: number;
    rate_limits_triggered: number;
    brute_force_blocks: number;
  };
  blocked_ips: BlockedIpInfo[];
  audit_logs: SecurityAuditLog[];
}


