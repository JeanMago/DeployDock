<script setup lang="ts">
import { ref } from 'vue';
import {
  CheckCircle2,
  XCircle,
  Clock,
  RotateCcw,
  Terminal,
  ChevronDown,
  ChevronUp,
  AlertTriangle,
  Sparkles,
} from 'lucide-vue-next';
import StatusBadge from '@/components/common/StatusBadge.vue';
import { api } from '@/services/api';
import type { Deployment, DeploymentDiagnosis } from '@/services/types';

defineProps<{ deployments: Deployment[] }>();
defineEmits<{ (e: 'rollback', id: string): void }>();

const expandedLogs = ref<Set<string>>(new Set());
const diagnoses = ref<Record<string, DeploymentDiagnosis>>({});
const diagnosingId = ref<string | null>(null);

const toggleLogs = (id: string) => {
  const next = new Set(expandedLogs.value);
  if (next.has(id)) next.delete(id);
  else next.add(id);
  expandedLogs.value = next;
};

const runDiagnosis = async (id: string) => {
  if (diagnoses.value[id]) {
    const copy = { ...diagnoses.value };
    delete copy[id];
    diagnoses.value = copy;
    return;
  }
  diagnosingId.value = id;
  try {
    diagnoses.value = {
      ...diagnoses.value,
      [id]: await api.deployments.diagnose(id),
    };
  } catch (e: any) {
    alert(e?.message || 'Erro ao executar diagnóstico inteligente.');
  } finally {
    diagnosingId.value = null;
  }
};

const formatDate = (date: string) => new Date(date).toLocaleString('pt-BR');
</script>

<template>
  <div class="space-y-3">
    <div
      v-for="dep in deployments"
      :key="dep.id"
      class="glass-panel overflow-hidden transition-colors"
    >
      <div class="p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div class="flex items-start gap-3 min-w-0">
          <div class="mt-0.5 shrink-0">
            <CheckCircle2 v-if="dep.status === 'healthy'" class="w-4 h-4 text-dock-success" />
            <XCircle v-else-if="dep.status === 'failed'" class="w-4 h-4 text-dock-error" />
            <Clock v-else class="w-4 h-4 text-dock-accent animate-pulse" />
          </div>
          <div class="min-w-0 flex-1">
            <div class="flex flex-wrap items-center gap-2">
              <h4 class="text-sm font-semibold text-dock-text truncate">
                {{ dep.commit_message || 'Deploy da Aplicação' }}
              </h4>
              <StatusBadge :status="dep.status" size="sm" />
            </div>
            <div class="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs font-mono text-dock-text-dim mt-1">
              <span class="bg-dock-bg px-1.5 py-0.5 rounded border border-dock-border text-dock-text-muted">
                {{ dep.commit_sha ? dep.commit_sha.substring(0, 8) : 'initial' }}
              </span>
              <span>branch: {{ dep.branch }}</span>
              <span>autor: {{ dep.commit_author || 'DeployDock' }}</span>
              <span>{{ formatDate(dep.started_at) }}</span>
              <span v-if="dep.duration_seconds !== null && dep.duration_seconds !== undefined" class="text-dock-text-muted">
                duração: {{ dep.duration_seconds }}s
              </span>
            </div>
          </div>
        </div>

        <div class="flex flex-wrap items-center gap-2 self-start sm:self-auto shrink-0">
          <button
            @click="runDiagnosis(dep.id)"
            :disabled="diagnosingId === dep.id"
            class="px-2.5 py-1 text-xs font-mono bg-dock-accent/15 hover:bg-dock-accent/25 border border-dock-accent/30 text-dock-accent rounded transition-colors flex items-center gap-1.5 cursor-pointer"
            title="Diagnóstico Inteligente de Causa Raiz e Solução (Estilo Ployter)"
          >
            <Sparkles class="w-3.5 h-3.5" />
            <span>{{ diagnosingId === dep.id ? 'Analisando...' : diagnoses[dep.id] ? 'Ocultar Diagnóstico' : 'Diagnosticar (IA)' }}</span>
          </button>

          <button
            v-if="dep.build_logs || dep.error_message"
            @click="toggleLogs(dep.id)"
            class="px-2.5 py-1 text-xs font-mono bg-dock-surface hover:bg-dock-bg border border-dock-border text-dock-text-muted hover:text-dock-text rounded transition-colors flex items-center gap-1.5 cursor-pointer"
          >
            <Terminal class="w-3.5 h-3.5" />
            <span>Logs de Build</span>
            <ChevronUp v-if="expandedLogs.has(dep.id)" class="w-3.5 h-3.5" />
            <ChevronDown v-else class="w-3.5 h-3.5" />
          </button>

          <button
            v-if="dep.previous_image_id && dep.status === 'healthy'"
            @click="$emit('rollback', dep.id)"
            class="px-2.5 py-1 text-xs font-mono bg-dock-surface hover:bg-dock-panel border border-dock-border text-dock-text-muted hover:text-dock-warning rounded transition-colors flex items-center gap-1.5 cursor-pointer"
            title="Reverter contêiner para a imagem anterior a este deploy"
          >
            <RotateCcw class="w-3.5 h-3.5" /> Rollback
          </button>
        </div>
      </div>

      <!-- Mensagem de erro se falhou -->
      <div
        v-if="dep.error_message"
        class="mx-4 mb-3 px-3 py-2 rounded bg-dock-error/10 border border-dock-error/30 text-dock-error text-xs font-mono flex items-start gap-2"
      >
        <AlertTriangle class="w-4 h-4 shrink-0 mt-0.5" />
        <span class="break-all">{{ dep.error_message }}</span>
      </div>

      <!-- Painel de Diagnóstico Inteligente de Falhas -->
      <div
        v-if="diagnoses[dep.id]"
        class="mx-4 mb-3 p-3.5 rounded-lg bg-dock-bg border border-dock-accent/40 space-y-2 text-xs"
      >
        <div class="flex flex-wrap items-center justify-between gap-2">
          <div class="flex items-center gap-2">
            <Sparkles class="w-4 h-4 text-dock-accent" />
            <span class="font-semibold text-dock-text">{{ diagnoses[dep.id]?.title }}</span>
            <span class="px-2 py-0.5 rounded bg-dock-accent/15 text-dock-accent font-mono text-[10px]">
              {{ diagnoses[dep.id]?.category }}
            </span>
          </div>
          <span class="font-mono text-[11px] text-dock-success">
            Confiança: {{ diagnoses[dep.id]?.confidence }}%
          </span>
        </div>
        <p class="text-dock-text-muted">{{ diagnoses[dep.id]?.root_cause }}</p>
        <div class="space-y-1 pt-1">
          <div class="text-[11px] font-mono uppercase text-dock-text-dim">Recomendações de Correção:</div>
          <ul class="list-disc list-inside space-y-1 text-dock-text">
            <li v-for="(step, idx) in diagnoses[dep.id]?.recommendations" :key="idx">{{ step }}</li>
          </ul>
        </div>
      </div>

      <!-- Console Expansível de Build Logs -->
      <div
        v-if="expandedLogs.has(dep.id)"
        class="border-t border-dock-border bg-dock-bg p-3 font-mono text-xs"
      >
        <div class="text-[11px] text-dock-text-dim mb-2 flex justify-between">
          <span>Saída do Docker Build ({{ dep.commit_sha?.substring(0, 8) }})</span>
        </div>
        <pre class="max-h-80 overflow-y-auto overflow-x-auto p-2.5 rounded bg-dock-surface border border-dock-border text-dock-text whitespace-pre-wrap break-all leading-relaxed">{{ dep.build_logs || 'Sem saída de build registrada.' }}</pre>
      </div>
    </div>
  </div>
</template>
