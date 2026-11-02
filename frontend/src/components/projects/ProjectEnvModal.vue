<script setup lang="ts">
import { ref, onMounted, computed } from 'vue';
import {
  X,
  Plus,
  Trash2,
  Eye,
  EyeOff,
  FileCode2,
  KeyRound,
  RefreshCw,
  Copy,
  Check,
  Webhook,
} from 'lucide-vue-next';
import { api } from '@/services/api';
import type { Project, EnvironmentVariable } from '@/services/types';

const props = defineProps<{ project: Project }>();
const emit = defineEmits<{
  (e: 'close'): void;
}>();

const activeTab = ref<'env' | 'bulk' | 'webhook'>('env');
const envVars = ref<EnvironmentVariable[]>([]);
const loading = ref(true);
const saving = ref(false);
const applying = ref(false);
const revealedIds = ref<Set<string>>(new Set());
const copiedField = ref<string | null>(null);
const feedback = ref<string | null>(null);

const newKey = ref('');
const newValue = ref('');
const newSecret = ref(false);
const bulkContent = ref('');
const applyNow = ref(true);

const webhookUrl = computed(() => {
  return `${window.location.origin.replace(':3000', ':8000')}/api/v1/webhooks/github`;
});

const loadEnv = async () => {
  loading.value = true;
  try {
    const res: any = await api.projects.listEnv(props.project.id);
    envVars.value = Array.isArray(res) ? res : (res.variables || []);
  } catch (e) {
    console.error(e);
  } finally {
    loading.value = false;
  }
};

onMounted(loadEnv);

const toggleReveal = (id: string) => {
  const s = new Set(revealedIds.value);
  if (s.has(id)) s.delete(id);
  else s.add(id);
  revealedIds.value = s;
};

const addSingleVar = async () => {
  if (!newKey.value.trim()) return;
  saving.value = true;
  try {
    envVars.value = await api.projects.saveEnv(props.project.id, {
      key: newKey.value.trim(),
      value: newValue.value,
      is_secret: newSecret.value,
      apply_now: applyNow.value,
    });
    newKey.value = '';
    newValue.value = '';
    newSecret.value = false;
    feedback.value = applyNow.value
      ? 'Variável salva e aplicada ao contêiner.'
      : 'Variável salva.';
  } catch (e: any) {
    alert('Erro ao salvar variável: ' + (e.message || e));
  } finally {
    saving.value = false;
  }
};

const saveBulkEnv = async () => {
  if (!bulkContent.value.trim()) return;
  saving.value = true;
  try {
    envVars.value = await api.projects.saveEnv(props.project.id, {
      bulk_content: bulkContent.value,
      is_secret: false,
      apply_now: applyNow.value,
    });
    bulkContent.value = '';
    activeTab.value = 'env';
    feedback.value = 'Variáveis importadas com sucesso.';
  } catch (e: any) {
    alert('Erro ao importar .env: ' + (e.message || e));
  } finally {
    saving.value = false;
  }
};

const removeVar = async (item: EnvironmentVariable) => {
  if (!confirm(`Remover variável "${item.key}"?`)) return;
  try {
    await api.projects.deleteEnv(props.project.id, item.id, applyNow.value);
    await loadEnv();
  } catch (e: any) {
    alert('Erro ao remover: ' + (e.message || e));
  }
};

const applyToContainerNow = async () => {
  applying.value = true;
  try {
    const res = await api.projects.applyEnv(props.project.id);
    feedback.value = res.message;
  } catch (e: any) {
    alert('Erro ao reaplicar contêiner: ' + (e.message || e));
  } finally {
    applying.value = false;
  }
};

const copyText = async (field: string, val: string) => {
  try {
    await navigator.clipboard.writeText(val);
    copiedField.value = field;
    setTimeout(() => {
      if (copiedField.value === field) copiedField.value = null;
    }, 2000);
  } catch {
    // ignore
  }
};
</script>

<template>
  <div
    class="fixed inset-0 z-50 bg-black/75 flex items-center justify-center p-2 sm:p-4"
    @click.self="emit('close')"
  >
    <div class="glass-panel bg-dock-surface w-full max-w-2xl max-h-[92vh] flex flex-col overflow-hidden">
      <!-- Cabeçalho -->
      <div class="px-4 sm:px-5 py-3.5 border-b border-dock-border flex items-center justify-between">
        <div>
          <h3 class="text-sm font-semibold text-dock-text flex items-center gap-2">
            <KeyRound class="w-4 h-4 text-dock-accent" />
            Ambiente (.env) & Webhook — {{ project.name }}
          </h3>
          <p class="text-[11px] text-dock-text-dim font-mono mt-0.5">
            Variáveis injetadas diretamente no contêiner da aplicação
          </p>
        </div>
        <button
          @click="emit('close')"
          class="p-1.5 rounded text-dock-text-muted hover:text-dock-text hover:bg-dock-panel cursor-pointer"
        >
          <X class="w-4 h-4" />
        </button>
      </div>

      <!-- Abas -->
      <div class="px-4 sm:px-5 pt-2.5 border-b border-dock-border flex overflow-x-auto gap-2 bg-dock-bg/50">
        <button
          @click="activeTab = 'env'"
          class="px-3 py-1.5 text-xs font-medium border-b-2 transition-colors whitespace-nowrap cursor-pointer"
          :class="
            activeTab === 'env'
              ? 'border-dock-accent text-dock-text'
              : 'border-transparent text-dock-text-muted hover:text-dock-text'
          "
        >
          Variáveis ({{ envVars.length }})
        </button>
        <button
          @click="activeTab = 'bulk'"
          class="px-3 py-1.5 text-xs font-medium border-b-2 transition-colors flex items-center gap-1.5 whitespace-nowrap cursor-pointer"
          :class="
            activeTab === 'bulk'
              ? 'border-dock-accent text-dock-text'
              : 'border-transparent text-dock-text-muted hover:text-dock-text'
          "
        >
          <FileCode2 class="w-3.5 h-3.5" /> Importar Arquivo .env
        </button>
        <button
          @click="activeTab = 'webhook'"
          class="px-3 py-1.5 text-xs font-medium border-b-2 transition-colors flex items-center gap-1.5 whitespace-nowrap cursor-pointer"
          :class="
            activeTab === 'webhook'
              ? 'border-dock-accent text-dock-text'
              : 'border-transparent text-dock-text-muted hover:text-dock-text'
          "
        >
          <Webhook class="w-3.5 h-3.5" /> GitOps Webhook
        </button>
      </div>

      <!-- Conteúdo Rolável -->
      <div class="p-4 sm:p-5 overflow-y-auto flex-1 space-y-4">
        <div
          v-if="feedback"
          class="px-3 py-2 rounded bg-dock-success/10 border border-dock-success/30 text-dock-success text-xs font-mono flex items-center justify-between"
        >
          <span>{{ feedback }}</span>
          <button @click="feedback = null" class="underline ml-2 cursor-pointer">ok</button>
        </div>

        <!-- ABA 1: LISTA E ADIÇÃO DE VARIÁVEIS -->
        <template v-if="activeTab === 'env'">
          <form @submit.prevent="addSingleVar" class="p-3 rounded bg-dock-bg border border-dock-border space-y-2.5">
            <div class="text-xs font-medium text-dock-text-muted">Adicionar / Atualizar Variável</div>
            <div class="grid grid-cols-1 sm:grid-cols-12 gap-2">
              <input
                v-model="newKey"
                type="text"
                placeholder="CHAVE (ex: NODE_ENV)"
                class="sm:col-span-5 bg-dock-surface border border-dock-border focus:border-dock-accent rounded px-2.5 py-1.5 text-xs font-mono text-dock-text outline-none"
              />
              <input
                v-model="newValue"
                :type="newSecret ? 'password' : 'text'"
                placeholder="Valor (ex: production)"
                class="sm:col-span-5 bg-dock-surface border border-dock-border focus:border-dock-accent rounded px-2.5 py-1.5 text-xs font-mono text-dock-text outline-none"
              />
              <button
                type="submit"
                :disabled="saving || !newKey.trim()"
                class="sm:col-span-2 bg-dock-accent hover:bg-dock-accent-hover text-white rounded px-3 py-1.5 text-xs font-medium flex items-center justify-center gap-1 disabled:opacity-40 cursor-pointer"
              >
                <Plus class="w-3.5 h-3.5" /> Salvar
              </button>
            </div>
            <div class="flex flex-wrap items-center justify-between gap-2 pt-1 text-xs text-dock-text-dim">
              <label class="inline-flex items-center gap-1.5 cursor-pointer">
                <input v-model="newSecret" type="checkbox" class="rounded border-dock-border" />
                <span>Ocultar valor na interface (segredo)</span>
              </label>
              <label class="inline-flex items-center gap-1.5 cursor-pointer">
                <input v-model="applyNow" type="checkbox" class="rounded border-dock-border" />
                <span>Recriar contêiner automaticamente após salvar</span>
              </label>
            </div>
          </form>

          <div v-if="loading" class="text-center py-6 text-xs font-mono text-dock-text-dim">
            Carregando variáveis...
          </div>
          <div v-else-if="!envVars.length" class="text-center py-8 border border-dashed border-dock-border rounded text-xs text-dock-text-dim">
            Nenhuma variável de ambiente cadastrada neste projeto.
          </div>
          <div v-else class="border border-dock-border rounded overflow-hidden divide-y divide-dock-border font-mono text-xs">
            <div
              v-for="item in envVars"
              :key="item.id"
              class="px-3 py-2 bg-dock-bg flex items-center justify-between gap-2"
            >
              <div class="min-w-0 flex-1 flex flex-col sm:flex-row sm:items-center gap-1 sm:gap-2">
                <span class="text-dock-accent font-semibold truncate">{{ item.key }}</span>
                <span class="hidden sm:inline text-dock-text-dim">=</span>
                <span class="text-dock-text break-all">
                  {{ item.is_secret && !revealedIds.has(item.id) ? '••••••••••••' : item.value }}
                </span>
              </div>
              <div class="flex items-center gap-1 shrink-0">
                <button
                  v-if="item.is_secret"
                  @click="toggleReveal(item.id)"
                  class="p-1 rounded text-dock-text-dim hover:text-dock-text hover:bg-dock-surface cursor-pointer"
                  title="Mostrar/ocultar valor"
                >
                  <EyeOff v-if="revealedIds.has(item.id)" class="w-3.5 h-3.5" />
                  <Eye v-else class="w-3.5 h-3.5" />
                </button>
                <button
                  @click="copyText(item.id, `${item.key}=${item.value}`)"
                  class="p-1 rounded text-dock-text-dim hover:text-dock-text hover:bg-dock-surface cursor-pointer"
                  title="Copiar KEY=VALUE"
                >
                  <Check v-if="copiedField === item.id" class="w-3.5 h-3.5 text-dock-success" />
                  <Copy v-else class="w-3.5 h-3.5" />
                </button>
                <button
                  @click="removeVar(item)"
                  class="p-1 rounded text-dock-text-dim hover:text-dock-error hover:bg-dock-surface cursor-pointer"
                  title="Excluir variável"
                >
                  <Trash2 class="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          </div>
        </template>

        <!-- ABA 2: IMPORTAÇÃO EM LOTE (.ENV) -->
        <template v-else-if="activeTab === 'bulk'">
          <div class="space-y-3">
            <p class="text-xs text-dock-text-muted">
              Cole abaixo o conteúdo de um arquivo <code>.env</code> (uma variável por linha no formato <code>CHAVE=VALOR</code>). Comentários iniciados com <code>#</code> são ignorados.
            </p>
            <textarea
              v-model="bulkContent"
              rows="8"
              placeholder="# Exemplo de arquivo .env&#10;PORT=8080&#10;DATABASE_URL=postgres://user:pass@host:5432/db&#10;API_KEY=segredo123"
              class="w-full bg-dock-bg border border-dock-border focus:border-dock-accent rounded p-3 font-mono text-xs text-dock-text placeholder-dock-text-dim outline-none"
            ></textarea>
            <div class="flex items-center justify-between">
              <label class="inline-flex items-center gap-1.5 text-xs text-dock-text-dim cursor-pointer">
                <input v-model="applyNow" type="checkbox" class="rounded border-dock-border" />
                <span>Aplicar e reiniciar contêiner imediatamente</span>
              </label>
              <button
                @click="saveBulkEnv"
                :disabled="saving || !bulkContent.trim()"
                class="bg-dock-accent hover:bg-dock-accent-hover text-white px-4 py-1.5 rounded text-xs font-medium disabled:opacity-40 cursor-pointer"
              >
                {{ saving ? 'Importando...' : 'Importar Variáveis' }}
              </button>
            </div>
          </div>
        </template>

        <!-- ABA 3: WEBHOOK GITOPS -->
        <template v-else-if="activeTab === 'webhook'">
          <div class="space-y-3 text-xs">
            <p class="text-dock-text-muted">
              Configure estes dados em <strong>Settings → Webhooks</strong> no repositório do GitHub para acionar o deploy automático a cada <code>git push</code> na branch <code>{{ project.branch }}</code>:
            </p>
            <div class="space-y-2">
              <div>
                <div class="text-dock-text-dim font-mono text-[11px] mb-1">Payload URL</div>
                <div class="flex items-center gap-2">
                  <input
                    :value="webhookUrl"
                    readonly
                    class="flex-1 bg-dock-bg border border-dock-border rounded px-3 py-1.5 font-mono text-xs text-dock-text outline-none"
                  />
                  <button
                    @click="copyText('url', webhookUrl)"
                    class="px-3 py-1.5 rounded bg-dock-panel border border-dock-border hover:border-dock-border-light text-dock-text flex items-center gap-1.5 cursor-pointer"
                  >
                    <Check v-if="copiedField === 'url'" class="w-3.5 h-3.5 text-dock-success" />
                    <Copy v-else class="w-3.5 h-3.5" />
                    Copiar
                  </button>
                </div>
              </div>

              <div v-if="project.webhook_secret">
                <div class="text-dock-text-dim font-mono text-[11px] mb-1">Webhook Secret (HMAC-SHA256)</div>
                <div class="flex items-center gap-2">
                  <input
                    :value="project.webhook_secret"
                    readonly
                    class="flex-1 bg-dock-bg border border-dock-border rounded px-3 py-1.5 font-mono text-xs text-dock-text outline-none"
                  />
                  <button
                    @click="copyText('secret', project.webhook_secret || '')"
                    class="px-3 py-1.5 rounded bg-dock-panel border border-dock-border hover:border-dock-border-light text-dock-text flex items-center gap-1.5 cursor-pointer"
                  >
                    <Check v-if="copiedField === 'secret'" class="w-3.5 h-3.5 text-dock-success" />
                    <Copy v-else class="w-3.5 h-3.5" />
                    Copiar
                  </button>
                </div>
              </div>

              <div class="p-3 rounded bg-dock-bg border border-dock-border font-mono text-[11px] text-dock-text-dim">
                Content type: <strong class="text-dock-text">application/json</strong> • Evento: <strong class="text-dock-text">Just the push event</strong>
              </div>
            </div>
          </div>
        </template>
      </div>

      <!-- Rodapé -->
      <div class="px-4 sm:px-5 py-3 border-t border-dock-border bg-dock-bg flex flex-wrap items-center justify-between gap-2">
        <button
          @click="applyToContainerNow"
          :disabled="applying"
          class="px-3 py-1.5 rounded text-xs font-mono bg-dock-surface hover:bg-dock-panel border border-dock-border text-dock-text flex items-center gap-1.5 cursor-pointer"
        >
          <RefreshCw class="w-3.5 h-3.5" :class="{ 'animate-spin': applying }" />
          {{ applying ? 'Aplicando...' : 'Reiniciar Contêiner com .env Atual' }}
        </button>
        <button
          @click="emit('close')"
          class="px-4 py-1.5 rounded text-xs font-medium bg-dock-panel hover:bg-dock-border text-dock-text cursor-pointer"
        >
          Fechar
        </button>
      </div>
    </div>
  </div>
</template>
