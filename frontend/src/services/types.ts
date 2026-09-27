export interface Container {
  id: string;
  name: string;
  image: string;
  status: string;
  state: string;
  ports: { ip: string; privatePort: number; publicPort: number; type: string }[];
}

export interface ContainerDetail extends Container {
  env: string[];
  mounts: { type: string; source: string; destination: string }[];
  networkMode: string;
}

export interface ContainerStats {
  cpu_percent: number;
  memory_percent: number;
  memory_usage: number;
  memory_limit: number;
  net_rx: number;
  net_tx: number;
  timestamp: string;
}

export interface Project {
  id: string;
  name: string;
  repo_url: string;
  branch: string;
  auto_deploy: boolean;
  last_deploy_status?: string;
  created_at: string;
}

export interface ProjectCreate {
  name: string;
  repo_url: string;
  branch?: string;
  auto_deploy?: boolean;
}

export type ProjectUpdate = Partial<ProjectCreate>;

export interface Deployment {
  id: string;
  project_id: string;
  commit_sha: string;
  commit_message: string;
  author: string;
  status: 'pending' | 'in_progress' | 'success' | 'failed' | 'rolled_back';
  started_at: string;
  finished_at?: string;
  logs?: string;
}

export interface EnvironmentVariable {
  id: string;
  key: string;
  value: string;
  project_id?: string;
}

export interface SystemInfo {
  containers: number;
  containers_running: number;
  containers_stopped: number;
  images: number;
  mem_total: number;
  ncpu: number;
  server_version: string;
  operating_system: string;
}

export interface WebSocketMessage {
  type: string;
  payload: any;
}
