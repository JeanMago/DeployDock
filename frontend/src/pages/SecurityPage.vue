<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue';
import {
  ShieldCheck,
  ShieldAlert,
  Lock,
  Ban,
  Activity,
  RefreshCw,
  Trash2,
  Plus,
  Unlock,
  Zap,
  Search,
  CheckCircle2,
  AlertTriangle,
} from 'lucide-vue-next';
import { api } from '@/services/api';
import type { SecurityOverview } from '@/services/types';
import { useAuth } from '@/composables/useAuth';

const { isAdmin } = useAuth();

const overview = ref<SecurityOverview | null>(null);
const loading = ref(true);
const savingConfig = ref(false);
const simulating = ref<string | null>(null);
const lastSimulationMsg = ref<string | null>(null);

// Filtro de auditoria
const searchQuery = ref('');
const severityFilter = ref<'all' | 'critical' | 'high' | 'medium' | 'low'>('all');

// Formulário de bloqueio manual de IP
const manualIp = ref('');
const manualReason = ref('Atividade suspeita detectada');
const manualDuration = ref<number | null>(3600);

const loadOverview = async () => {
  try {
    overview.value = await api.security.overview();
  } catch (e) {
    console.error('Erro ao carregar dados de segurança:', e);
  } finally {
    loading.value = false;
  }
};

let timer: ReturnType<typeof setInterval> | null = null;
onMounted(() => {
  loadOverview();
  timer = setInterval(loadOverview, 6000);
});

onUnmounted(() => {
  if (timer) clearInterval(timer);
});

const togglePolicy = async (key: keyof SecurityOverview['config']) => {
  if (!overview.value || !isAdmin.value) return;
  const current = overview.value.config[key];
  if (typeof current !== 'boolean') return;
  savingConfig.value = true;
  try {
    await api.security.updateConfig({ [key]: !current });
    await loadOverview();
  } catch (e: any) {
    alert(e?.message || 'Falha ao atualizar política.');
  } finally {
    savingConfig.value = false;
  }
};

const updateNumericPolicy = async () => {
  if (!overview.value || !isAdmin.value) return;
  savingConfig.value = true;
  try {
    await api.security.updateConfig({
      rate_limit_per_minute: Number(overview.value.config.rate_limit_per_minute),
      login_max_attempts: Number(overview.value.config.login_max_attempts),
    });
    await loadOverview();
  } catch (e: any) {
    alert(e?.message || 'Falha ao salvar limites.');
  } finally {
    savingConfig.value = false;
  }
};

const handleBlockIp = async () => {
  if (!manualIp.value.trim()) return;
  try {
    await api.security.blockIp(manualIp.value.trim(), manualReason.value.trim(), manualDuration.value);
    manualIp.value = '';
    await loadOverview();
  } catch (e: any) {
    alert(e?.message || 'Erro ao bloquear IP');
  }
};

const handleUnblockIp = async (ip: string) => {
  try {
    await api.security.unblockIp(ip);
    await loadOverview();
  } catch (e: any) {
    alert(e?.message || 'Erro ao desbloquear IP');
  }
};

const runSimulation = async (type: string) => {
  simulating.value = type;
  lastSimulationMsg.value = null;
  try {
    const res = await api.security.simulateAttack(type);
    lastSimulationMsg.value = `Escudo ativo: Ataque simulado "${res.attack_name}" (${res.simulated_ip}) foi interceptado e registrado na auditoria.`;
    await loadOverview();
  } catch (e: any) {
    alert(e?.message || 'Erro ao simular ataque');
  } finally {
    simulating.value = null;
  }
};

const clearLogs = async () => {
  if (!confirm('Limpar todo o histórico de auditoria de segurança?')) return;
  await api.security.clearAuditLogs();
  await loadOverview();
};

const filteredLogs = computed(() => {
  const logs = overview.value?.audit_logs || [];
  const q = searchQuery.value.trim().toLowerCase();
  return logs.filter((item) => {
    if (severityFilter.value !== 'all' && item.severity !== severityFilter.value) {
      return false;
    }
    if (q) {
      const hay = `${item.ip} ${item.path} ${item.detail} ${item.user} ${item.event_type}`.toLowerCase();
      if (!hay.includes(q)) return false;
    }
    return true;
  });
});

const formatTime = (iso: string) => {
  try {
    return new Date(iso).toLocaleTimeString('pt-BR', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  } catch {
    return iso;
  }
};
</script>

<template>
  <div class="space-y-5">
    <!-- Cabeçalho -->
    <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-dock-border pb-4">
      <div>
        <div class="flex items-center gap-2">
          <ShieldCheck class="w-5 h-5 text-dock-success" />
          <h2 class="text-lg font-semibold text-dock-text tracking-tight">
            Segurança, WAF & Prevenção contra Ataques
          </h2>
        </div>
        <p class="text-xs text-dock-text-muted mt-0.5">
          Proteção ativa contra força bruta, SQL Injection, XSS, Path Traversal, SSRF e isolamento de contêineres.
        </p>
      </div>

      <div class="flex items-center gap-2">
        <button
          @click="loadOverview"
          class="px-3 py-1.5 rounded bg-dock-surface hover:bg-dock-panel border border-dock-border text-xs font-medium text-dock-text flex items-center gap-1.5 cursor-pointer transition-colors"
        >
          <RefreshCw class="w-3.5 h-3.5" :class="{ 'animate-spin': loading }" />
          Atualizar
        </button>
      </div>
    </div>

    <template v-if="overview">
      <!-- KPIs de Segurança -->
      <div class="grid grid-cols-2 lg:grid-cols-5 gap-3">
        <div class="glass-panel p-3.5">
          <div class="text-[11px] font-mono uppercase text-dock-text-dim flex items-center justify-between">
            <span>Score de Defesa</span>
            <ShieldCheck class="w-3.5 h-3.5 text-dock-success" />
          </div>
          <div class="mt-2 flex items-baseline gap-2">
            <span class="text-2xl font-mono font-bold text-dock-success">{{ overview.security_score }}%</span>
            <span class="text-[11px] font-mono text-dock-text-muted">
              ({{ overview.enabled_layers }}/{{ overview.total_layers }} camadas)
            </span>
          </div>
        </div>

        <div class="glass-panel p-3.5">
          <div class="text-[11px] font-mono uppercase text-dock-text-dim flex items-center justify-between">
            <span>Tráfego Inspecionado</span>
            <Activity class="w-3.5 h-3.5 text-dock-accent" />
          </div>
          <div class="mt-2 text-2xl font-mono font-bold text-dock-text tabular-nums">
            {{ overview.stats.total_requests_inspected }}
          </div>
          <div class="text-[10px] text-dock-text-dim mt-0.5">requisições analisadas pelo WAF</div>
        </div>

        <div class="glass-panel p-3.5">
          <div class="text-[11px] font-mono uppercase text-dock-text-dim flex items-center justify-between">
            <span>Ataques WAF Bloqueados</span>
            <ShieldAlert class="w-3.5 h-3.5 text-dock-error" />
          </div>
          <div class="mt-2 text-2xl font-mono font-bold text-dock-error tabular-nums">
            {{ overview.stats.waf_attacks_blocked }}
          </div>
          <div class="text-[10px] text-dock-text-dim mt-0.5">SQLi, XSS, Traversal, SSRF</div>
        </div>

        <div class="glass-panel p-3.5">
          <div class="text-[11px] font-mono uppercase text-dock-text-dim flex items-center justify-between">
            <span>Brute-Force / Rate Limit</span>
            <Lock class="w-3.5 h-3.5 text-dock-warning" />
          </div>
          <div class="mt-2 text-2xl font-mono font-bold text-dock-warning tabular-nums">
            {{ overview.stats.brute_force_blocks + overview.stats.rate_limits_triggered }}
          </div>
          <div class="text-[10px] text-dock-text-dim mt-0.5">contenção de abuso de API/Login</div>
        </div>

        <div class="glass-panel p-3.5 col-span-2 lg:col-span-1">
          <div class="text-[11px] font-mono uppercase text-dock-text-dim flex items-center justify-between">
            <span>IPs na Blocklist</span>
            <Ban class="w-3.5 h-3.5 text-dock-error" />
          </div>
          <div class="mt-2 text-2xl font-mono font-bold text-dock-text tabular-nums">
            {{ overview.blocked_ips.length }}
          </div>
          <div class="text-[10px] text-dock-text-dim mt-0.5">endereços barrados no firewall</div>
        </div>
      </div>

      <!-- Camadas de Proteção + Simulador de Ataques -->
      <div class="grid grid-cols-1 lg:grid-cols-12 gap-4">
        <!-- Políticas de Proteção -->
        <div class="lg:col-span-7 glass-panel p-4 space-y-3">
          <div class="flex items-center justify-between border-b border-dock-border pb-2.5">
            <h3 class="text-xs font-mono uppercase tracking-wider text-dock-text font-semibold">
              Camadas de Blindagem Ativas
            </h3>
            <span class="text-[11px] font-mono text-dock-success flex items-center gap-1">
              <CheckCircle2 class="w-3.5 h-3.5" /> Shield Middleware Ativo
            </span>
          </div>

          <div class="grid grid-cols-1 sm:grid-cols-2 gap-2.5 text-xs">
            <div class="p-3 rounded bg-dock-bg border border-dock-border flex items-start justify-between gap-2">
              <div>
                <div class="font-medium text-dock-text">WAF (SQLi / XSS / Path Traversal)</div>
                <div class="text-[11px] text-dock-text-dim mt-0.5">
                  Inspeciona URLs e parâmetros contra injeções e leitura de arquivos (`../etc/passwd`).
                </div>
              </div>
              <button
                @click="togglePolicy('waf_enabled')"
                :disabled="!isAdmin || savingConfig"
                class="px-2 py-0.5 rounded font-mono text-[10px] border shrink-0 cursor-pointer"
                :class="
                  overview.config.waf_enabled
                    ? 'bg-dock-success/15 text-dock-success border-dock-success/30'
                    : 'bg-dock-surface text-dock-text-dim border-dock-border'
                "
              >
                {{ overview.config.waf_enabled ? 'ATIVO' : 'OFF' }}
              </button>
            </div>

            <div class="p-3 rounded bg-dock-bg border border-dock-border flex items-start justify-between gap-2">
              <div>
                <div class="font-medium text-dock-text">Anti-SSRF em Clonagem Git</div>
                <div class="text-[11px] text-dock-text-dim mt-0.5">
                  Bloqueia `file://`, loopback (`127.0.0.1`) e IPs de metadata interna (`169.254.169.254`).
                </div>
              </div>
              <button
                @click="togglePolicy('ssrf_protection')"
                :disabled="!isAdmin || savingConfig"
                class="px-2 py-0.5 rounded font-mono text-[10px] border shrink-0 cursor-pointer"
                :class="
                  overview.config.ssrf_protection
                    ? 'bg-dock-success/15 text-dock-success border-dock-success/30'
                    : 'bg-dock-surface text-dock-text-dim border-dock-border'
                "
              >
                {{ overview.config.ssrf_protection ? 'ATIVO' : 'OFF' }}
              </button>
            </div>

            <div class="p-3 rounded bg-dock-bg border border-dock-border flex items-start justify-between gap-2">
              <div>
                <div class="font-medium text-dock-text">Container Hardening (No-New-Privileges)</div>
                <div class="text-[11px] text-dock-text-dim mt-0.5">
                  Aplica `no-new-privileges:true` e `pids_limit=256` contra fork-bombs e escalação root.
                </div>
              </div>
              <button
                @click="togglePolicy('container_no_new_privileges')"
                :disabled="!isAdmin || savingConfig"
                class="px-2 py-0.5 rounded font-mono text-[10px] border shrink-0 cursor-pointer"
                :class="
                  overview.config.container_no_new_privileges
                    ? 'bg-dock-success/15 text-dock-success border-dock-success/30'
                    : 'bg-dock-surface text-dock-text-dim border-dock-border'
                "
              >
                {{ overview.config.container_no_new_privileges ? 'ATIVO' : 'OFF' }}
              </button>
            </div>

            <div class="p-3 rounded bg-dock-bg border border-dock-border flex items-start justify-between gap-2">
              <div>
                <div class="font-medium text-dock-text">Security HTTP Headers + Fernet AES-128</div>
                <div class="text-[11px] text-dock-text-dim mt-0.5">
                  Injeta `X-Frame-Options`, `nosniff` e criptografa segredos `.env` em repouso.
                </div>
              </div>
              <button
                @click="togglePolicy('security_headers')"
                :disabled="!isAdmin || savingConfig"
                class="px-2 py-0.5 rounded font-mono text-[10px] border shrink-0 cursor-pointer"
                :class="
                  overview.config.security_headers
                    ? 'bg-dock-success/15 text-dock-success border-dock-success/30'
                    : 'bg-dock-surface text-dock-text-dim border-dock-border'
                "
              >
                {{ overview.config.security_headers ? 'ATIVO' : 'OFF' }}
              </button>
            </div>
          </div>

          <!-- Limites de Rate Limit e Brute Force -->
          <div class="pt-2 border-t border-dock-border flex flex-wrap items-center justify-between gap-3 text-xs">
            <div class="flex flex-wrap items-center gap-4">
              <label class="flex items-center gap-2 text-dock-text-muted">
                <span>Limite API (req/min por IP):</span>
                <input
                  v-model.number="overview.config.rate_limit_per_minute"
                  type="number"
                  min="30"
                  max="2000"
                  :disabled="!isAdmin"
                  class="w-20 bg-dock-bg border border-dock-border rounded px-2 py-1 font-mono text-dock-text"
                />
              </label>
              <label class="flex items-center gap-2 text-dock-text-muted">
                <span>Máx. falhas de Login:</span>
                <input
                  v-model.number="overview.config.login_max_attempts"
                  type="number"
                  min="3"
                  max="20"
                  :disabled="!isAdmin"
                  class="w-16 bg-dock-bg border border-dock-border rounded px-2 py-1 font-mono text-dock-text"
                />
              </label>
            </div>
            <button
              v-if="isAdmin"
              @click="updateNumericPolicy"
              :disabled="savingConfig"
              class="px-3 py-1 rounded bg-dock-panel hover:bg-dock-border-light border border-dock-border-light text-dock-text font-medium cursor-pointer"
            >
              Salvar Limites
            </button>
          </div>
        </div>

        <!-- Simulador de Ataques & Firewall Blocklist -->
        <div class="lg:col-span-5 glass-panel p-4 flex flex-col justify-between space-y-4">
          <div class="space-y-2.5">
            <div class="flex items-center justify-between border-b border-dock-border pb-2.5">
              <h3 class="text-xs font-mono uppercase tracking-wider text-dock-text font-semibold flex items-center gap-1.5">
                <Zap class="w-3.5 h-3.5 text-dock-warning" /> Simulador de Defesa WAF
              </h3>
              <span class="text-[10px] font-mono text-dock-text-dim">Teste seguro (RFC 5737)</span>
            </div>
            <p class="text-[11px] text-dock-text-muted">
              Dispare um vetor de ataque simulado para verificar a interceptação do WAF e o bloqueio automático de IP:
            </p>
            <div class="grid grid-cols-2 gap-2 pt-1">
              <button
                @click="runSimulation('sqli')"
                :disabled="!!simulating"
                class="px-2.5 py-1.5 rounded bg-dock-bg hover:bg-dock-panel border border-dock-border text-left text-xs font-mono text-dock-text transition-colors cursor-pointer"
              >
                1. SQL Injection
              </button>
              <button
                @click="runSimulation('path_traversal')"
                :disabled="!!simulating"
                class="px-2.5 py-1.5 rounded bg-dock-bg hover:bg-dock-panel border border-dock-border text-left text-xs font-mono text-dock-text transition-colors cursor-pointer"
              >
                2. Path Traversal
              </button>
              <button
                @click="runSimulation('xss')"
                :disabled="!!simulating"
                class="px-2.5 py-1.5 rounded bg-dock-bg hover:bg-dock-panel border border-dock-border text-left text-xs font-mono text-dock-text transition-colors cursor-pointer"
              >
                3. Payload XSS
              </button>
              <button
                @click="runSimulation('brute_force')"
                :disabled="!!simulating"
                class="px-2.5 py-1.5 rounded bg-dock-bg hover:bg-dock-panel border border-dock-border text-left text-xs font-mono text-dock-warning transition-colors cursor-pointer"
              >
                4. Brute-Force IP Ban
              </button>
            </div>
            <div
              v-if="lastSimulationMsg"
              class="p-2.5 rounded bg-dock-success/10 border border-dock-success/30 text-[11px] text-dock-success flex items-start gap-2"
            >
              <CheckCircle2 class="w-4 h-4 shrink-0 mt-0.5" />
              <span>{{ lastSimulationMsg }}</span>
            </div>
          </div>

          <!-- Firewall Blocklist (IPs Bloqueados) -->
          <div class="space-y-2.5 border-t border-dock-border pt-3">
            <div class="text-xs font-mono uppercase tracking-wider text-dock-text font-semibold">
              Firewall Blocklist ({{ overview.blocked_ips.length }} IPs bloqueados)
            </div>

            <div v-if="isAdmin" class="flex gap-1.5">
              <input
                v-model="manualIp"
                type="text"
                placeholder="Ex: 198.51.100.42"
                class="w-36 bg-dock-bg border border-dock-border rounded px-2.5 py-1 text-xs font-mono text-dock-text outline-none focus:border-dock-accent"
              />
              <input
                v-model="manualReason"
                type="text"
                placeholder="Motivo do bloqueio"
                class="flex-1 min-w-0 bg-dock-bg border border-dock-border rounded px-2.5 py-1 text-xs text-dock-text outline-none focus:border-dock-accent"
              />
              <button
                @click="handleBlockIp"
                class="px-2.5 py-1 rounded bg-dock-error/15 hover:bg-dock-error/25 text-dock-error border border-dock-error/30 text-xs font-medium flex items-center gap-1 cursor-pointer shrink-0"
              >
                <Plus class="w-3.5 h-3.5" /> Bloquear
              </button>
            </div>

            <div v-if="overview.blocked_ips.length === 0" class="text-[11px] text-dock-text-dim py-2">
              Nenhum endereço IP bloqueado no momento.
            </div>
            <div v-else class="max-h-32 overflow-y-auto space-y-1.5">
              <div
                v-for="b in overview.blocked_ips"
                :key="b.ip"
                class="flex items-center justify-between gap-2 px-2.5 py-1.5 rounded bg-dock-bg border border-dock-error/30 text-xs"
              >
                <div class="min-w-0">
                  <span class="font-mono font-semibold text-dock-error">{{ b.ip }}</span>
                  <span class="text-dock-text-dim ml-2 truncate">{{ b.reason }}</span>
                </div>
                <button
                  v-if="isAdmin"
                  @click="handleUnblockIp(b.ip)"
                  class="px-2 py-0.5 rounded bg-dock-surface hover:bg-dock-panel border border-dock-border text-[11px] text-dock-text flex items-center gap-1 shrink-0 cursor-pointer"
                >
                  <Unlock class="w-3 h-3" /> Desbloquear
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Log de Auditoria e Eventos de Segurança -->
      <div class="glass-panel p-4 space-y-3">
        <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2.5 border-b border-dock-border pb-3">
          <div class="flex items-center gap-2">
            <h3 class="text-xs font-mono uppercase tracking-wider text-dock-text font-semibold">
              Registro de Auditoria & Eventos de Segurança
            </h3>
            <span class="text-[11px] font-mono px-1.5 py-0.5 rounded bg-dock-bg border border-dock-border text-dock-text-muted">
              {{ filteredLogs.length }} eventos
            </span>
          </div>

          <div class="flex flex-wrap items-center gap-2">
            <div class="relative">
              <Search class="w-3.5 h-3.5 text-dock-text-dim absolute left-2.5 top-1/2 -translate-y-1/2" />
              <input
                v-model="searchQuery"
                type="text"
                placeholder="Buscar IP, rota, usuário..."
                class="pl-8 pr-2.5 py-1 rounded bg-dock-bg border border-dock-border text-xs font-mono text-dock-text outline-none focus:border-dock-accent w-48 sm:w-56"
              />
            </div>

            <select
              v-model="severityFilter"
              class="bg-dock-bg border border-dock-border rounded px-2 py-1 text-xs font-mono text-dock-text outline-none"
            >
              <option value="all">Todas Severidades</option>
              <option value="critical">Crítico (WAF Block)</option>
              <option value="high">Alto (Brute-Force/Ban)</option>
              <option value="medium">Médio (Falha Auth/Rate)</option>
              <option value="low">Baixo (Auditoria Operacional)</option>
            </select>

            <button
              v-if="isAdmin && overview.audit_logs.length > 0"
              @click="clearLogs"
              class="p-1.5 rounded bg-dock-bg hover:bg-dock-panel border border-dock-border text-dock-text-dim hover:text-dock-error cursor-pointer"
              title="Limpar histórico de auditoria"
            >
              <Trash2 class="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        <div class="overflow-x-auto">
          <table class="w-full text-left text-xs border-collapse">
            <thead>
              <tr class="border-b border-dock-border text-dock-text-dim font-mono text-[11px]">
                <th class="py-2 px-2.5">Horário</th>
                <th class="py-2 px-2.5">Severidade</th>
                <th class="py-2 px-2.5">IP Origem</th>
                <th class="py-2 px-2.5">Usuário</th>
                <th class="py-2 px-2.5">Alvo / Rota</th>
                <th class="py-2 px-2.5">Descrição do Evento</th>
                <th class="py-2 px-2.5 text-right">Ação</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-dock-border font-mono">
              <tr v-if="filteredLogs.length === 0">
                <td colspan="7" class="py-8 text-center text-dock-text-dim font-sans">
                  Nenhum evento registrado para o filtro selecionado.
                </td>
              </tr>
              <tr
                v-for="item in filteredLogs"
                :key="item.id"
                class="hover:bg-dock-panel/40 transition-colors"
              >
                <td class="py-2 px-2.5 text-dock-text-muted whitespace-nowrap">
                  {{ formatTime(item.timestamp) }}
                </td>
                <td class="py-2 px-2.5 whitespace-nowrap">
                  <span
                    class="px-1.5 py-0.5 rounded text-[10px] uppercase border"
                    :class="{
                      'bg-dock-error/15 text-dock-error border-dock-error/30': item.severity === 'critical',
                      'bg-dock-warning/15 text-dock-warning border-dock-warning/30': item.severity === 'high' || item.severity === 'medium',
                      'bg-dock-bg text-dock-text-muted border-dock-border': item.severity === 'low',
                    }"
                  >
                    {{ item.severity }}
                  </span>
                </td>
                <td class="py-2 px-2.5 text-dock-text whitespace-nowrap">{{ item.ip }}</td>
                <td class="py-2 px-2.5 text-dock-text-muted whitespace-nowrap">{{ item.user }}</td>
                <td class="py-2 px-2.5 text-dock-text-dim truncate max-w-[200px]" :title="item.path">
                  {{ item.path }}
                </td>
                <td class="py-2 px-2.5 font-sans text-dock-text">{{ item.detail }}</td>
                <td class="py-2 px-2.5 text-right whitespace-nowrap">
                  <span
                    v-if="item.blocked"
                    class="text-[10px] text-dock-error font-semibold flex items-center justify-end gap-1"
                  >
                    <AlertTriangle class="w-3 h-3" /> BLOQUEADO
                  </span>
                  <span v-else class="text-[10px] text-dock-success">REGISTRADO</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </template>
  </div>
</template>
