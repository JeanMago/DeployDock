<script setup lang="ts">
import { ref, onMounted } from 'vue';
import {
  Database,
  Layers,
  CloudUpload,
  Clock,
  Globe,
  Shield,
  Sparkles,
  Plus,
  Trash2,
  Play,
  Copy,
  Check,
  RefreshCw,
  Github,
} from 'lucide-vue-next';
import { api } from '@/services/api';
import type { Project, DeploymentDiagnosis, GitHubIntegrationStatus } from '@/services/types';
import LoadingSpinner from '@/components/common/LoadingSpinner.vue';

const activeTab = ref<'databases' | 'templates' | 'backups' | 'crons' | 'dns_registries' | 'traefik_ai'>('databases');
const loading = ref(true);
const copiedText = ref('');

const projects = ref<Project[]>([]);
const databases = ref<any[]>([]);
const templates = ref<any[]>([]);
const backupsData = ref<any>({ s3_config: {}, jobs: [], history: [] });
const crons = ref<any[]>([]);
const registries = ref<any[]>([]);
const cloudflareData = ref<any>({ config: {}, records: [] });
const traefikData = ref<any>({ config: {}, certificates: [], active_routers: [] });
const githubStatus = ref<GitHubIntegrationStatus | null>(null);
const githubTokenInput = ref('');
const githubDeviceCode = ref<{ user_code: string; verification_uri: string } | null>(null);

// Forms
const newDb = ref({
  name: 'meu-postgres',
  engine: 'postgres',
  database_name: 'app_db',
  username: 'postgres',
  password: '',
  memory_limit_mb: 512,
});
const creatingDb = ref(false);

const launchingTpl = ref<string | null>(null);

const s3Form = ref({
  enabled: true,
  provider: 'cloudflare_r2',
  endpoint_url: 'https://s3.amazonaws.com',
  bucket: 'deploydock-backups',
  region: 'us-east-1',
  access_key: '',
  secret_key: '',
});
const newBackupJob = ref({
  name: 'Backup Noturno Banco',
  target_type: 'database',
  target_name: 'deploydock_db_meu-postgres',
  cron_expression: '0 3 * * *',
  s3_upload: true,
  retention_count: 7,
});

const newCron = ref({
  project_id: '',
  name: 'Limpeza de Cache / Fila',
  command: 'echo "Cron executado com sucesso"',
  cron_expression: '*/15 * * * *',
});

const newRegistry = ref({
  name: 'GitHub Container Registry (GHCR)',
  server_address: 'https://ghcr.io',
  username: '',
  password: '',
});

const cfConfigForm = ref({
  enabled: true,
  zone_id: '',
  base_domain: 'seudominio.com',
  server_ip: '203.0.113.10',
  proxied_default: true,
  api_token: '',
});

const traefikForm = ref({
  acme_email: 'admin@seudominio.com',
  force_https_redirect: true,
  hsts_enabled: true,
  gzip_compression: true,
});
const newCert = ref({
  domain: '*.seudominio.com',
  issuer: 'Cloudflare Origin CA',
  cert_pem: '-----BEGIN CERTIFICATE-----\nMIIB...\n-----END CERTIFICATE-----',
  key_pem: '-----BEGIN PRIVATE KEY-----\nMIIE...\n-----END PRIVATE KEY-----',
});

const diagInput = ref({
  logs: 'Step 4/7 : RUN pip install -r requirements.txt\nModuleNotFoundError: No module named \'psycopg2\'',
  error_message: 'Build falhou no passo 4',
});
const diagResult = ref<DeploymentDiagnosis | null>(null);
const diagnosing = ref(false);

const copyToClipboard = (text: string) => {
  navigator.clipboard.writeText(text);
  copiedText.value = text;
  setTimeout(() => {
    if (copiedText.value === text) copiedText.value = '';
  }, 2000);
};

const loadAll = async () => {
  loading.value = true;
  try {
    const [ov, projs] = await Promise.all([
      api.paas.overview(),
      api.projects.list(),
    ]);
    projects.value = projs;
    if (projs.length && !newCron.value.project_id) {
      newCron.value.project_id = projs[0].id;
    }
    databases.value = ov.databases || [];
    templates.value = ov.templates || [];
    backupsData.value = ov.backups || { s3_config: {}, jobs: [], history: [] };
    if (ov.backups?.s3_config) {
      Object.assign(s3Form.value, ov.backups.s3_config);
    }
    crons.value = ov.crons || [];
    registries.value = ov.registries || [];
    cloudflareData.value = ov.cloudflare || { config: {}, records: [] };
    if (ov.cloudflare?.config) {
      Object.assign(cfConfigForm.value, ov.cloudflare.config);
    }
    traefikData.value = ov.traefik || { config: {}, certificates: [], active_routers: [] };
    if (ov.traefik?.config) {
      Object.assign(traefikForm.value, ov.traefik.config);
    }
    githubStatus.value = ov.github || null;
  } catch (e) {
    console.error(e);
  } finally {
    loading.value = false;
  }
};

onMounted(loadAll);

const handleCreateDb = async () => {
  if (!newDb.value.name.trim()) return;
  creatingDb.value = true;
  try {
    await api.paas.createDatabase(newDb.value);
    await loadAll();
  } catch (e: any) {
    alert(e?.message || 'Erro ao provisionar banco.');
  } finally {
    creatingDb.value = false;
  }
};

const handleDeleteDb = async (id: string) => {
  try {
    await api.paas.deleteDatabase(id);
    await loadAll();
  } catch (e: any) {
    alert(e?.message || 'Erro ao remover banco.');
  }
};

const handleLaunchTemplate = async (tplId: string) => {
  launchingTpl.value = tplId;
  try {
    const res = await api.paas.launchTemplate(tplId);
    alert(`Template "${res.template_name}" iniciado no contêiner "${res.container_name}" (porta ${res.port})!`);
  } catch (e: any) {
    alert(e?.message || 'Erro ao lançar template.');
  } finally {
    launchingTpl.value = null;
  }
};

const handleSaveS3 = async () => {
  try {
    await api.paas.updateS3Config(s3Form.value);
    await loadAll();
    alert('Configuração S3 / Object Storage salva com sucesso!');
  } catch (e: any) {
    alert(e?.message || 'Erro ao salvar S3.');
  }
};

const handleCreateBackupJob = async () => {
  try {
    await api.paas.createBackupJob(newBackupJob.value);
    await loadAll();
  } catch (e: any) {
    alert(e?.message || 'Erro ao criar agendamento de backup.');
  }
};

const handleRunBackupJob = async (jobId: string) => {
  try {
    await api.paas.runBackupJob(jobId);
    await loadAll();
  } catch (e: any) {
    alert(e?.message || 'Erro ao executar backup.');
  }
};

const handleDeleteBackupJob = async (jobId: string) => {
  await api.paas.deleteBackupJob(jobId);
  await loadAll();
};

const handleCreateCron = async () => {
  if (!newCron.value.project_id) {
    alert('Crie ou selecione um projeto primeiro.');
    return;
  }
  try {
    await api.paas.createCron(newCron.value);
    await loadAll();
  } catch (e: any) {
    alert(e?.message || 'Erro ao criar Cron Job.');
  }
};

const handleRunCron = async (cronId: string) => {
  await api.paas.runCron(cronId);
  await loadAll();
};

const handleDeleteCron = async (cronId: string) => {
  await api.paas.deleteCron(cronId);
  await loadAll();
};

const handleAddRegistry = async () => {
  if (!newRegistry.value.username || !newRegistry.value.password) return;
  try {
    await api.paas.addRegistry(newRegistry.value);
    newRegistry.value.password = '';
    await loadAll();
  } catch (e: any) {
    alert(e?.message || 'Erro ao cadastrar Registry.');
  }
};

const handleDeleteRegistry = async (id: string) => {
  await api.paas.deleteRegistry(id);
  await loadAll();
};

const handleConnectGithubPaaS = async () => {
  if (!githubTokenInput.value.trim()) return;
  try {
    githubStatus.value = await api.paas.connectGithub({
      token: githubTokenInput.value.trim(),
      auto_inject_git_token: true,
      auto_create_webhook: true,
      auto_import_env_example: true,
    });
    githubTokenInput.value = '';
    await loadAll();
    alert(`Conta GitHub @${githubStatus.value.username} conectada com sucesso!`);
  } catch (e: any) {
    alert(e?.message || 'Erro ao conectar conta GitHub.');
  }
};

const handleStartGithubDevicePaaS = async () => {
  try {
    const flow = await api.paas.startGithubDeviceFlow();
    githubDeviceCode.value = flow;
    try {
      await navigator.clipboard.writeText(flow.user_code);
    } catch {
      // ignore
    }
  } catch (e: any) {
    alert(e?.message || 'Erro ao iniciar OAuth Device Flow.');
  }
};

const copyAndOpenGithubDevicePaaS = async () => {
  if (!githubDeviceCode.value) return;
  try {
    await navigator.clipboard.writeText(githubDeviceCode.value.user_code);
  } catch {
    // ignore
  }
  window.open(githubDeviceCode.value.verification_uri, '_blank', 'noopener,noreferrer');
};

const handlePollGithubDevicePaaS = async () => {
  try {
    const res = await api.paas.pollGithubDeviceFlow();
    if (res.status === 'connected') {
      githubDeviceCode.value = null;
      githubStatus.value = res.github;
      await loadAll();
      alert(`GitHub autorizado com sucesso como @${res.github.username}!`);
    } else {
      alert(res.error_description || 'Ainda aguardando confirmação do código no GitHub...');
    }
  } catch (e: any) {
    alert(e?.message || 'Erro ao verificar autorização.');
  }
};

const handleDisconnectGithubPaaS = async () => {
  githubStatus.value = await api.paas.disconnectGithub();
  await loadAll();
};

const handleSaveCloudflare = async () => {
  await api.paas.updateCloudflareConfig(cfConfigForm.value);
  await loadAll();
  alert('Configuração Cloudflare DNS atualizada!');
};

const handleSyncProjectCf = async (projectId: string) => {
  await api.paas.syncProjectCloudflare(projectId);
  await loadAll();
};

const handleDeleteCfRecord = async (id: string) => {
  await api.paas.deleteCloudflareRecord(id);
  await loadAll();
};

const handleSaveTraefik = async () => {
  await api.paas.updateTraefikConfig(traefikForm.value);
  await loadAll();
  alert('Configuração dinâmica do Traefik atualizada!');
};

const handleAddCert = async () => {
  try {
    await api.paas.addTraefikCertificate(newCert.value);
    await loadAll();
  } catch (e: any) {
    alert(e?.message || 'Erro ao importar certificado PEM.');
  }
};

const handleDeleteCert = async (id: string) => {
  await api.paas.deleteTraefikCertificate(id);
  await loadAll();
};

const handleDiagnose = async () => {
  diagnosing.value = true;
  try {
    diagResult.value = await api.paas.diagnoseLogs({
      logs: diagInput.value.logs,
      error_message: diagInput.value.error_message,
      status: 'failed',
    });
  } finally {
    diagnosing.value = false;
  }
};
</script>

<template>
  <div class="space-y-5">
    <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-dock-border">
      <div>
        <h2 class="text-lg font-semibold text-dock-text">
          Central PaaS & Cloud (Dokploy + Ployter Suite)
        </h2>
        <p class="text-xs text-dock-text-dim mt-0.5">
          Bancos gerenciados de 1ª classe, Catálogo 1-Clique, Backups Agendados S3/R2, Cron Jobs por App, Cloudflare DNS, Registries Privados, Traefik TLS e Diagnóstico IA
        </p>
      </div>
      <button
        @click="loadAll"
        class="bg-dock-surface hover:bg-dock-panel border border-dock-border text-dock-text px-3 py-2 rounded text-xs font-medium flex items-center gap-1.5 cursor-pointer self-start"
      >
        <RefreshCw class="w-3.5 h-3.5 text-dock-accent" /> Atualizar
      </button>
    </div>

    <!-- Navegação de Abas -->
    <div class="flex flex-wrap gap-1.5 border-b border-dock-border pb-3">
      <button
        v-for="tab in [
          { id: 'databases', label: 'Bancos Gerenciados', icon: Database },
          { id: 'templates', label: 'Catálogo 1-Clique', icon: Layers },
          { id: 'backups', label: 'Backups S3 & Cron', icon: CloudUpload },
          { id: 'crons', label: 'Cron Jobs por App', icon: Clock },
          { id: 'dns_registries', label: 'Cloudflare DNS & Registries', icon: Globe },
          { id: 'traefik_ai', label: 'Traefik TLS & Diagnóstico IA', icon: Sparkles },
        ]"
        :key="tab.id"
        @click="activeTab = tab.id as any"
        class="px-3 py-2 rounded-lg text-xs font-medium flex items-center gap-1.5 transition-colors cursor-pointer border"
        :class="
          activeTab === tab.id
            ? 'bg-dock-accent text-white border-dock-accent'
            : 'bg-dock-surface text-dock-text-muted border-dock-border hover:text-dock-text'
        "
      >
        <component :is="tab.icon" class="w-3.5 h-3.5" />
        {{ tab.label }}
      </button>
    </div>

    <div v-if="loading" class="flex justify-center py-16"><LoadingSpinner /></div>

    <!-- ABA 1: BANCOS DE DADOS GERENCIADOS -->
    <div v-else-if="activeTab === 'databases'" class="grid grid-cols-1 lg:grid-cols-3 gap-5">
      <div class="glass-panel p-4 space-y-3">
        <h3 class="text-sm font-semibold text-dock-text flex items-center gap-2">
          <Database class="w-4 h-4 text-dock-accent" /> Provisionar Novo Banco Dedicado
        </h3>
        <div class="space-y-2.5 text-xs">
          <div>
            <label class="block text-dock-text-muted mb-1">Engine do Banco</label>
            <select v-model="newDb.engine" class="w-full bg-dock-bg border border-dock-border rounded px-2.5 py-2 text-dock-text">
              <option value="postgres">PostgreSQL 16 Alpine</option>
              <option value="mysql">MySQL 8.0</option>
              <option value="mariadb">MariaDB 11</option>
              <option value="mongodb">MongoDB 7</option>
              <option value="redis">Redis 7 Alpine</option>
            </select>
          </div>
          <div>
            <label class="block text-dock-text-muted mb-1">Identificador do Serviço</label>
            <input v-model="newDb.name" type="text" class="w-full bg-dock-bg border border-dock-border rounded px-2.5 py-2 font-mono text-dock-text" />
          </div>
          <div class="grid grid-cols-2 gap-2">
            <div>
              <label class="block text-dock-text-muted mb-1">Nome do Banco</label>
              <input v-model="newDb.database_name" type="text" class="w-full bg-dock-bg border border-dock-border rounded px-2.5 py-2 font-mono text-dock-text" />
            </div>
            <div>
              <label class="block text-dock-text-muted mb-1">Limite RAM (MB)</label>
              <input v-model.number="newDb.memory_limit_mb" type="number" class="w-full bg-dock-bg border border-dock-border rounded px-2.5 py-2 font-mono text-dock-text" />
            </div>
          </div>
          <button
            @click="handleCreateDb"
            :disabled="creatingDb"
            class="w-full bg-dock-accent hover:bg-dock-accent-hover text-white py-2 rounded font-medium flex items-center justify-center gap-1.5 cursor-pointer"
          >
            <Plus class="w-4 h-4" /> {{ creatingDb ? 'Provisionando...' : 'Criar Banco Gerenciado' }}
          </button>
        </div>
      </div>

      <div class="lg:col-span-2 space-y-3">
        <div v-if="!databases.length" class="glass-panel p-8 text-center text-xs text-dock-text-dim">
          Nenhum banco gerenciado provisionado ainda. Crie PostgreSQL, MySQL, MariaDB, MongoDB ou Redis ao lado!
        </div>
        <div
          v-for="db in databases"
          :key="db.id"
          class="glass-panel p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3"
        >
          <div class="space-y-1 min-w-0 flex-1">
            <div class="flex items-center gap-2">
              <span class="font-semibold text-sm text-dock-text">{{ db.name }}</span>
              <span class="text-[11px] font-mono px-2 py-0.5 rounded bg-dock-accent/15 text-dock-accent">
                {{ db.engine_label }}
              </span>
              <span class="text-[10px] font-mono text-dock-success">{{ db.status }}</span>
            </div>
            <div class="text-xs font-mono text-dock-text-dim truncate">
              Host Interno: <span class="text-dock-text">{{ db.internal_host }}:{{ db.internal_port }}</span>
            </div>
            <div class="flex items-center gap-2 bg-dock-bg p-2 rounded border border-dock-border text-[11px] font-mono">
              <span class="truncate text-dock-accent flex-1">{{ db.connection_url }}</span>
              <button
                @click="copyToClipboard(db.connection_url)"
                class="px-2 py-0.5 rounded bg-dock-surface hover:bg-dock-panel text-dock-text flex items-center gap-1 cursor-pointer shrink-0"
              >
                <Check v-if="copiedText === db.connection_url" class="w-3 h-3 text-dock-success" />
                <Copy v-else class="w-3 h-3" /> Copiar URI
              </button>
            </div>
          </div>
          <button
            @click="handleDeleteDb(db.id)"
            class="px-2.5 py-1.5 rounded bg-dock-surface hover:bg-dock-error/15 text-dock-text-muted hover:text-dock-error border border-dock-border text-xs flex items-center gap-1 cursor-pointer self-start"
          >
            <Trash2 class="w-3.5 h-3.5" /> Excluir
          </button>
        </div>
      </div>
    </div>

    <!-- ABA 2: CATÁLOGO DE TEMPLATES 1-CLIQUE -->
    <div v-else-if="activeTab === 'templates'" class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
      <div
        v-for="tpl in templates"
        :key="tpl.id"
        class="glass-panel p-4 flex flex-col justify-between space-y-3"
      >
        <div class="space-y-1.5">
          <div class="flex items-center justify-between">
            <span class="font-semibold text-sm text-dock-text">{{ tpl.name }}</span>
            <span class="text-[10px] font-mono px-2 py-0.5 rounded bg-dock-surface border border-dock-border text-dock-accent">
              {{ tpl.category }}
            </span>
          </div>
          <p class="text-xs text-dock-text-dim">{{ tpl.description }}</p>
          <div class="text-[11px] font-mono text-dock-text-muted pt-1">
            Imagem: <code class="text-dock-text">{{ tpl.image }}</code> • Porta: {{ tpl.default_port }}
          </div>
        </div>
        <button
          @click="handleLaunchTemplate(tpl.id)"
          :disabled="launchingTpl === tpl.id"
          class="w-full bg-dock-accent hover:bg-dock-accent-hover text-white py-2 rounded text-xs font-medium flex items-center justify-center gap-1.5 cursor-pointer"
        >
          <Play class="w-3.5 h-3.5" />
          {{ launchingTpl === tpl.id ? 'Subindo Stack...' : 'Lançar em 1 Clique' }}
        </button>
      </div>
    </div>

    <!-- ABA 3: BACKUPS AGENDADOS (CRON) + S3 / OBJECT STORAGE -->
    <div v-else-if="activeTab === 'backups'" class="grid grid-cols-1 lg:grid-cols-2 gap-5">
      <div class="glass-panel p-4 space-y-3 text-xs">
        <h3 class="text-sm font-semibold text-dock-text flex items-center gap-2">
          <CloudUpload class="w-4 h-4 text-dock-accent" /> Destino S3 / Object Storage (AWS S3, Cloudflare R2, MinIO)
        </h3>
        <div class="grid grid-cols-2 gap-2">
          <div>
            <label class="block text-dock-text-muted mb-1">Provedor</label>
            <select v-model="s3Form.provider" class="w-full bg-dock-bg border border-dock-border rounded px-2.5 py-1.5 text-dock-text">
              <option value="aws_s3">Amazon S3</option>
              <option value="cloudflare_r2">Cloudflare R2</option>
              <option value="minio">MinIO Self-Hosted</option>
              <option value="backblaze_b2">Backblaze B2</option>
            </select>
          </div>
          <div>
            <label class="block text-dock-text-muted mb-1">Bucket</label>
            <input v-model="s3Form.bucket" type="text" class="w-full bg-dock-bg border border-dock-border rounded px-2.5 py-1.5 font-mono text-dock-text" />
          </div>
        </div>
        <div>
          <label class="block text-dock-text-muted mb-1">Endpoint S3 URL</label>
          <input v-model="s3Form.endpoint_url" type="text" class="w-full bg-dock-bg border border-dock-border rounded px-2.5 py-1.5 font-mono text-dock-text" />
        </div>
        <div class="grid grid-cols-2 gap-2">
          <div>
            <label class="block text-dock-text-muted mb-1">Access Key ID</label>
            <input v-model="s3Form.access_key" type="text" class="w-full bg-dock-bg border border-dock-border rounded px-2.5 py-1.5 font-mono text-dock-text" />
          </div>
          <div>
            <label class="block text-dock-text-muted mb-1">Secret Access Key (Fernet)</label>
            <input v-model="s3Form.secret_key" type="password" placeholder="••••••••" class="w-full bg-dock-bg border border-dock-border rounded px-2.5 py-1.5 font-mono text-dock-text" />
          </div>
        </div>
        <button @click="handleSaveS3" class="bg-dock-accent hover:bg-dock-accent-hover text-white px-4 py-2 rounded font-medium cursor-pointer">
          Salvar Credenciais S3 (AWS SigV4)
        </button>
      </div>

      <div class="glass-panel p-4 space-y-3 text-xs">
        <h3 class="text-sm font-semibold text-dock-text">Agendar Política de Backup (Cron)</h3>
        <div class="grid grid-cols-2 gap-2">
          <input v-model="newBackupJob.name" placeholder="Nome da Política" class="bg-dock-bg border border-dock-border rounded px-2.5 py-1.5 text-dock-text" />
          <input v-model="newBackupJob.cron_expression" placeholder="Cron (ex: 0 3 * * *)" class="bg-dock-bg border border-dock-border rounded px-2.5 py-1.5 font-mono text-dock-text" />
        </div>
        <div class="grid grid-cols-2 gap-2">
          <select v-model="newBackupJob.target_type" class="bg-dock-bg border border-dock-border rounded px-2.5 py-1.5 text-dock-text">
            <option value="database">Dump de Banco de Dados</option>
            <option value="volume">Volume Docker (.tar.gz)</option>
          </select>
          <input v-model="newBackupJob.target_name" placeholder="Nome do Volume ou Contêiner" class="bg-dock-bg border border-dock-border rounded px-2.5 py-1.5 font-mono text-dock-text" />
        </div>
        <button @click="handleCreateBackupJob" class="bg-dock-accent hover:bg-dock-accent-hover text-white px-4 py-2 rounded font-medium flex items-center gap-1.5 cursor-pointer">
          <Plus class="w-3.5 h-3.5" /> Criar Agendamento
        </button>

        <div class="space-y-2 pt-2">
          <div
            v-for="job in backupsData.jobs"
            :key="job.id"
            class="p-2.5 rounded bg-dock-bg border border-dock-border flex items-center justify-between gap-2"
          >
            <div>
              <div class="font-medium text-dock-text">{{ job.name }} <span class="font-mono text-dock-accent">({{ job.cron_expression }})</span></div>
              <div class="text-[11px] font-mono text-dock-text-dim">
                Alvo: {{ job.target_name }} • Último S3: {{ job.last_s3_url || 'Pendente' }}
              </div>
            </div>
            <div class="flex items-center gap-1.5">
              <button @click="handleRunBackupJob(job.id)" class="px-2 py-1 rounded bg-dock-surface hover:bg-dock-accent hover:text-white border border-dock-border cursor-pointer">
                Executar Agora
              </button>
              <button @click="handleDeleteBackupJob(job.id)" class="p-1 text-dock-text-dim hover:text-dock-error cursor-pointer">
                <Trash2 class="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- ABA 4: CRON JOBS POR APLICAÇÃO -->
    <div v-else-if="activeTab === 'crons'" class="grid grid-cols-1 lg:grid-cols-3 gap-5 text-xs">
      <div class="glass-panel p-4 space-y-3">
        <h3 class="text-sm font-semibold text-dock-text flex items-center gap-2">
          <Clock class="w-4 h-4 text-dock-accent" /> Novo Cron Job por Projeto
        </h3>
        <div>
          <label class="block text-dock-text-muted mb-1">Projeto Alvo</label>
          <select v-model="newCron.project_id" class="w-full bg-dock-bg border border-dock-border rounded px-2.5 py-2 text-dock-text">
            <option v-for="p in projects" :key="p.id" :value="p.id">{{ p.name }}</option>
          </select>
        </div>
        <div>
          <label class="block text-dock-text-muted mb-1">Nome da Tarefa</label>
          <input v-model="newCron.name" type="text" class="w-full bg-dock-bg border border-dock-border rounded px-2.5 py-2 text-dock-text" />
        </div>
        <div>
          <label class="block text-dock-text-muted mb-1">Expressão Cron</label>
          <input v-model="newCron.cron_expression" type="text" class="w-full bg-dock-bg border border-dock-border rounded px-2.5 py-2 font-mono text-dock-text" />
        </div>
        <div>
          <label class="block text-dock-text-muted mb-1">Comando no Contêiner</label>
          <input v-model="newCron.command" type="text" class="w-full bg-dock-bg border border-dock-border rounded px-2.5 py-2 font-mono text-dock-text" />
        </div>
        <button @click="handleCreateCron" class="w-full bg-dock-accent hover:bg-dock-accent-hover text-white py-2 rounded font-medium cursor-pointer">
          Cadastrar Cron Job
        </button>
      </div>

      <div class="lg:col-span-2 space-y-2.5">
        <div v-if="!crons.length" class="glass-panel p-8 text-center text-dock-text-dim">
          Nenhum Cron Job cadastrado. Adicione tarefas periódicas (ex: `php artisan schedule:run`, `python manage.py clearsessions`) ao lado.
        </div>
        <div
          v-for="c in crons"
          :key="c.id"
          class="glass-panel p-4 space-y-2"
        >
          <div class="flex items-center justify-between">
            <div>
              <span class="font-semibold text-sm text-dock-text">{{ c.name }}</span>
              <span class="ml-2 font-mono text-dock-accent">{{ c.cron_expression }}</span>
              <span class="ml-2 text-dock-text-dim">({{ c.project_name }})</span>
            </div>
            <div class="flex items-center gap-1.5">
              <button @click="handleRunCron(c.id)" class="px-2.5 py-1 rounded bg-dock-surface hover:bg-dock-accent hover:text-white border border-dock-border flex items-center gap-1 cursor-pointer">
                <Play class="w-3 h-3" /> Disparar Agora
              </button>
              <button @click="handleDeleteCron(c.id)" class="p-1.5 text-dock-text-dim hover:text-dock-error cursor-pointer">
                <Trash2 class="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
          <div class="font-mono text-[11px] bg-dock-bg p-2 rounded border border-dock-border">
            $ {{ c.command }}
            <div v-if="c.last_output" class="mt-1 text-dock-success border-t border-dock-border pt-1">
              Saída (Exit {{ c.last_exit_code }}): {{ c.last_output }}
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- ABA 5: INTEGRAÇÃO GITHUB, CLOUDFLARE DNS AUTOMÁTICO & CONTAINER REGISTRIES PRIVADOS -->
    <div v-else-if="activeTab === 'dns_registries'" class="space-y-5 text-xs">
      <!-- Card Principal: Integração Automática com GitHub -->
      <div class="glass-panel p-4 space-y-3 border border-dock-accent/30">
        <div class="flex flex-wrap items-center justify-between gap-2">
          <div>
            <h3 class="text-sm font-semibold text-dock-text flex items-center gap-2">
              <Github class="w-4 h-4 text-dock-accent" />
              Integração GitHub Automática (Auto-Auth no Código, OAuth Device Flow, Auto-Webhook & `.env.example`)
            </h3>
            <p class="text-[11px] text-dock-text-dim mt-0.5">
              Conecte sua conta GitHub uma vez para autenticar `git clone`/`git pull`, listar repositórios privados, registrar Webhooks e extrair variáveis `.env.example` do código automaticamente.
            </p>
          </div>
          <div class="flex items-center gap-2">
            <span
              v-if="githubStatus?.connected"
              class="px-2.5 py-1 rounded bg-dock-success/15 border border-dock-success/30 text-dock-success font-mono"
            >
              Conectado: @{{ githubStatus.username }}
            </span>
            <button
              v-if="githubStatus?.connected"
              @click="handleDisconnectGithubPaaS"
              class="px-2.5 py-1 rounded bg-dock-error/15 border border-dock-error/30 text-dock-error cursor-pointer"
            >
              Desconectar
            </button>
          </div>
        </div>

        <div class="grid grid-cols-1 lg:grid-cols-2 gap-3">
          <div class="p-3 rounded bg-dock-bg border border-dock-border space-y-2.5">
            <div class="font-medium text-dock-text">Opção A — Código OAuth no Navegador (Sem criar Token manualmente)</div>
            <div class="flex flex-wrap items-center gap-2">
              <button
                @click="handleStartGithubDevicePaaS"
                class="bg-dock-accent hover:bg-dock-accent-hover text-white px-3 py-1.5 rounded font-medium cursor-pointer"
              >
                1. Gerar Código no DeployDock
              </button>
            </div>
            <div v-if="githubDeviceCode" class="p-3 rounded bg-dock-surface border-2 border-dock-accent space-y-2">
              <div class="text-[11px] text-dock-text">
                Este é o seu código (ele <strong class="text-dock-warning">não</strong> chega no celular; copie daqui e cole na página do GitHub):
              </div>
              <div class="text-xl font-mono font-bold tracking-widest text-dock-accent select-all">
                {{ githubDeviceCode.user_code }}
              </div>
              <div class="flex flex-wrap items-center gap-2">
                <button
                  @click="copyAndOpenGithubDevicePaaS"
                  class="px-3 py-1.5 rounded bg-dock-success text-white font-semibold cursor-pointer"
                >
                  2. Copiar {{ githubDeviceCode.user_code }} e Abrir GitHub
                </button>
                <button
                  @click="handlePollGithubDevicePaaS"
                  class="px-3 py-1.5 rounded bg-dock-accent/20 border border-dock-accent/40 text-dock-accent font-medium cursor-pointer"
                >
                  3. Já colei e autorizei no GitHub
                </button>
              </div>
            </div>
          </div>

          <div class="p-3 rounded bg-dock-bg border border-dock-border space-y-2">
            <div class="flex items-center justify-between">
              <span class="font-medium text-dock-text">Opção B — Personal Access Token (PAT Global)</span>
              <a
                href="https://github.com/settings/tokens/new?description=DeployDock-PaaS&scopes=repo,read:user,admin:repo_hook,read:packages"
                target="_blank"
                rel="noopener noreferrer"
                class="text-[11px] text-dock-accent hover:underline"
              >
                Criar Token no GitHub em 1 clique →
              </a>
            </div>
            <div class="flex gap-2">
              <input
                v-model="githubTokenInput"
                type="password"
                placeholder="ghp_xxxxxxxxxxxxxxxxxxxx ou github_pat_xxxx"
                class="flex-1 bg-dock-surface border border-dock-border rounded px-2.5 py-1.5 font-mono text-dock-text"
              />
              <button
                @click="handleConnectGithubPaaS"
                class="bg-dock-accent hover:bg-dock-accent-hover text-white px-3.5 py-1.5 rounded font-medium cursor-pointer"
              >
                Conectar Token
              </button>
            </div>
          </div>
        </div>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-2 gap-5">
      <div class="glass-panel p-4 space-y-3">
        <h3 class="text-sm font-semibold text-dock-text flex items-center gap-2">
          <Globe class="w-4 h-4 text-dock-accent" /> Gerenciamento Automático de DNS (Cloudflare API v4)
        </h3>
        <div class="grid grid-cols-2 gap-2">
          <input v-model="cfConfigForm.zone_id" placeholder="Cloudflare Zone ID" class="bg-dock-bg border border-dock-border rounded px-2.5 py-1.5 font-mono text-dock-text" />
          <input v-model="cfConfigForm.server_ip" placeholder="IP Público do Servidor" class="bg-dock-bg border border-dock-border rounded px-2.5 py-1.5 font-mono text-dock-text" />
        </div>
        <input v-model="cfConfigForm.api_token" type="password" placeholder="Cloudflare API Bearer Token (Fernet)" class="w-full bg-dock-bg border border-dock-border rounded px-2.5 py-1.5 font-mono text-dock-text" />
        <button @click="handleSaveCloudflare" class="bg-dock-accent hover:bg-dock-accent-hover text-white px-3.5 py-1.5 rounded font-medium cursor-pointer">
          Salvar Integração Cloudflare
        </button>

        <div class="pt-2 border-t border-dock-border space-y-2">
          <div class="font-medium text-dock-text">Sincronizar Domínio de Projeto em 1 Clique:</div>
          <div class="flex flex-wrap gap-1.5">
            <button
              v-for="p in projects"
              :key="p.id"
              @click="handleSyncProjectCf(p.id)"
              class="px-2.5 py-1 rounded bg-dock-surface hover:bg-dock-accent hover:text-white border border-dock-border font-mono cursor-pointer"
            >
              + DNS {{ p.public_host }}
            </button>
          </div>
          <div
            v-for="rec in cloudflareData.records"
            :key="rec.id"
            class="p-2 rounded bg-dock-bg border border-dock-border flex items-center justify-between font-mono text-[11px]"
          >
            <span>[{{ rec.type }}] {{ rec.name }} → {{ rec.content }} (Proxied: {{ rec.proxied ? 'ON' : 'OFF' }})</span>
            <button @click="handleDeleteCfRecord(rec.id)" class="text-dock-text-dim hover:text-dock-error cursor-pointer">
              <Trash2 class="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>

      <div class="glass-panel p-4 space-y-3">
        <h3 class="text-sm font-semibold text-dock-text flex items-center gap-2">
          <Shield class="w-4 h-4 text-dock-accent" /> Container Registries Privados (GHCR, Docker Hub, ECR, GitLab)
        </h3>
        <div class="grid grid-cols-2 gap-2">
          <input v-model="newRegistry.name" placeholder="Nome (ex: GHCR)" class="bg-dock-bg border border-dock-border rounded px-2.5 py-1.5 text-dock-text" />
          <input v-model="newRegistry.server_address" placeholder="https://ghcr.io" class="bg-dock-bg border border-dock-border rounded px-2.5 py-1.5 font-mono text-dock-text" />
        </div>
        <div class="grid grid-cols-2 gap-2">
          <input v-model="newRegistry.username" placeholder="Usuário" class="bg-dock-bg border border-dock-border rounded px-2.5 py-1.5 font-mono text-dock-text" />
          <input v-model="newRegistry.password" type="password" placeholder="Token / Senha" class="bg-dock-bg border border-dock-border rounded px-2.5 py-1.5 font-mono text-dock-text" />
        </div>
        <button @click="handleAddRegistry" class="bg-dock-accent hover:bg-dock-accent-hover text-white px-3.5 py-1.5 rounded font-medium cursor-pointer">
          Autenticar Registry Privado
        </button>

        <div class="space-y-2 pt-2">
          <div
            v-for="reg in registries"
            :key="reg.id"
            class="p-2.5 rounded bg-dock-bg border border-dock-border flex items-center justify-between font-mono text-[11px]"
          >
            <div>
              <div class="text-dock-text font-semibold">{{ reg.name }}</div>
              <div class="text-dock-text-dim">{{ reg.server_address }} • user: {{ reg.username }}</div>
            </div>
            <button @click="handleDeleteRegistry(reg.id)" class="text-dock-text-dim hover:text-dock-error cursor-pointer">
              <Trash2 class="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>
      </div>
    </div>

    <!-- ABA 6: TRAEFIK TLS CUSTOMIZADO & DIAGNÓSTICO INTELIGENTE DE FALHAS (IA) -->
    <div v-else-if="activeTab === 'traefik_ai'" class="grid grid-cols-1 lg:grid-cols-2 gap-5 text-xs">
      <div class="glass-panel p-4 space-y-3">
        <h3 class="text-sm font-semibold text-dock-text">
          Configuração Visual do Traefik & Certificados TLS Customizados
        </h3>
        <div class="grid grid-cols-2 gap-2">
          <div>
            <label class="block text-dock-text-muted mb-1">E-mail ACME Let's Encrypt</label>
            <input v-model="traefikForm.acme_email" class="w-full bg-dock-bg border border-dock-border rounded px-2.5 py-1.5 font-mono text-dock-text" />
          </div>
          <div class="flex flex-col justify-end gap-1">
            <label class="flex items-center gap-2 text-dock-text">
              <input type="checkbox" v-model="traefikForm.force_https_redirect" /> Redirect HTTP → HTTPS
            </label>
            <label class="flex items-center gap-2 text-dock-text">
              <input type="checkbox" v-model="traefikForm.hsts_enabled" /> HSTS Strict-Transport-Security
            </label>
          </div>
        </div>
        <button @click="handleSaveTraefik" class="bg-dock-accent hover:bg-dock-accent-hover text-white px-3.5 py-1.5 rounded font-medium cursor-pointer">
          Aplicar Configuração Traefik
        </button>

        <div class="pt-3 border-t border-dock-border space-y-2">
          <div class="font-medium text-dock-text">Importar Certificado TLS Customizado (PEM):</div>
          <input v-model="newCert.domain" placeholder="Domínio (ex: *.seudominio.com)" class="w-full bg-dock-bg border border-dock-border rounded px-2.5 py-1.5 font-mono text-dock-text" />
          <textarea v-model="newCert.cert_pem" rows="2" class="w-full bg-dock-bg border border-dock-border rounded p-2 font-mono text-[11px] text-dock-text"></textarea>
          <textarea v-model="newCert.key_pem" rows="2" class="w-full bg-dock-bg border border-dock-border rounded p-2 font-mono text-[11px] text-dock-text"></textarea>
          <button @click="handleAddCert" class="bg-dock-surface hover:bg-dock-panel border border-dock-border text-dock-text px-3 py-1.5 rounded cursor-pointer">
            Importar Certificado PEM
          </button>
          <div
            v-for="c in traefikData.certificates"
            :key="c.id"
            class="p-2 rounded bg-dock-bg border border-dock-border flex items-center justify-between font-mono text-[11px]"
          >
            <span>{{ c.domain }} ({{ c.issuer }}) • SHA256: {{ c.fingerprint_sha256.slice(0, 12) }}...</span>
            <button @click="handleDeleteCert(c.id)" class="text-dock-text-dim hover:text-dock-error cursor-pointer">
              <Trash2 class="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>

      <div class="glass-panel p-4 space-y-3">
        <h3 class="text-sm font-semibold text-dock-text flex items-center gap-2">
          <Sparkles class="w-4 h-4 text-dock-accent" /> Diagnóstico Inteligente de Falhas de Build/Deploy
        </h3>
        <p class="text-dock-text-dim">
          Cole um trecho de log de erro de build ou inicialização de contêiner para identificar a causa raiz e a correção recomendada:
        </p>
        <textarea
          v-model="diagInput.logs"
          rows="4"
          class="w-full bg-dock-bg border border-dock-border rounded p-2.5 font-mono text-[11px] text-dock-text"
        ></textarea>
        <button
          @click="handleDiagnose"
          :disabled="diagnosing"
          class="bg-dock-accent hover:bg-dock-accent-hover text-white px-4 py-2 rounded font-medium flex items-center gap-1.5 cursor-pointer"
        >
          <Sparkles class="w-3.5 h-3.5" /> {{ diagnosing ? 'Analisando...' : 'Diagnosticar Causa Raiz' }}
        </button>

        <div v-if="diagResult" class="p-3.5 rounded-xl bg-dock-bg border border-dock-accent/40 space-y-2">
          <div class="flex items-center justify-between">
            <span class="font-semibold text-dock-text">{{ diagResult.root_cause }}</span>
            <span class="font-mono text-[10px] px-2 py-0.5 rounded bg-dock-accent/15 text-dock-accent">
              {{ diagResult.category }} ({{ Math.round((diagResult.confidence || 0.9) * 100) }}% confiança)
            </span>
          </div>
          <p class="text-dock-text-muted">{{ diagResult.explanation }}</p>
          <div v-if="diagResult.suggested_fixes?.length" class="space-y-1 pt-1">
            <div class="font-medium text-dock-success">Correções Recomendadas:</div>
            <ul class="list-disc list-inside space-y-1 text-dock-text font-mono text-[11px]">
              <li v-for="(fix, i) in diagResult.suggested_fixes" :key="i">{{ fix }}</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
