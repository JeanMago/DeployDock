// Tipos TypeScript sincronizados com os schemas Pydantic do backend.

export interface Container {
  id: string;
  name: string;
  image: string;
  status: string;
  state: string | null;
  ports: Record<string, unknown> | null;
  created: string | null;
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
  last_deploy_status?: string;
  created_at: string;
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
  template?: 'fastapi' | 'express' | 'static' | 'custom';
  dockerfile_content?: string;
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
  project_id?: string;
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

export interface WebSocketMessage {
  type: string;
  payload: unknown;
}
