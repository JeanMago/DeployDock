<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { HardDrive, Server, Info, Trash2 } from 'lucide-vue-next';
import { api } from '@/services/api';
import type { SystemInfo } from '@/services/types';
import LoadingSpinner from '@/components/common/LoadingSpinner.vue';

const sysInfo = ref<SystemInfo | null>(null);
const loading = ref(true);

const load = async () => {
  try { sysInfo.value = await api.system.info(); }
  catch(e) { console.error(e); }
  finally { loading.value = false; }
};

onMounted(load);

const prune = async () => {
  if (!confirm('Deseja realmente limpar todos os dados não utilizados do Docker (imagens soltas, contêineres e volumes parados)?')) return;
  try {
    const res = await api.system.prune();
    alert(`Limpeza realizada com sucesso! ${(res.reclaimed_space/1024/1024).toFixed(2)} MB liberados.`);
    load();
  } catch (err) {
    alert('Erro ao executar limpeza: ' + err);
  }
};
</script>

<template>
  <div class="max-w-4xl mx-auto space-y-6">
    <h2 class="text-xl font-bold text-dock-text mb-6">Configurações do Sistema</h2>
    
    <div v-if="loading" class="flex justify-center py-10"><LoadingSpinner /></div>
    <div v-else-if="sysInfo" class="space-y-6">
      <div class="glass-panel p-6">
        <h3 class="flex items-center gap-2 font-semibold text-lg border-b border-dock-border pb-3 mb-4 text-dock-text"><Server class="w-5 h-5 text-dock-accent"/> Informações do Host Docker</h3>
        <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div class="bg-dock-surface p-3 rounded-lg border border-dock-border"><div class="text-xs text-dock-text-dim">Sistema Operacional</div><div class="font-medium truncate text-dock-text">{{ sysInfo.os || 'Indisponível' }}</div></div>
          <div class="bg-dock-surface p-3 rounded-lg border border-dock-border"><div class="text-xs text-dock-text-dim">Versão do Docker</div><div class="font-medium truncate text-dock-text">{{ sysInfo.docker_version || 'Offline' }}</div></div>
          <div class="bg-dock-surface p-3 rounded-lg border border-dock-border"><div class="text-xs text-dock-text-dim">CPUs Disponíveis</div><div class="font-medium truncate text-dock-text">{{ sysInfo.cpus ?? 'N/A' }}</div></div>
          <div class="bg-dock-surface p-3 rounded-lg border border-dock-border"><div class="text-xs text-dock-text-dim">Memória Total</div><div class="font-medium truncate text-dock-text">{{ sysInfo.memory_total_mb ? (sysInfo.memory_total_mb / 1024).toFixed(2) + ' GB' : 'N/A' }}</div></div>
        </div>
      </div>

      <div class="glass-panel p-6">
        <h3 class="flex items-center gap-2 font-semibold text-lg border-b border-dock-border pb-3 mb-4 text-dock-text"><HardDrive class="w-5 h-5 text-dock-warning"/> Manutenção e Otimização</h3>
        <p class="text-sm text-dock-text-muted mb-4">Remova contêineres parados, redes órfãs, volumes não montados e imagens sem tag para recuperar espaço em disco.</p>
        <button @click="prune" class="bg-dock-surface hover:bg-dock-warning/10 text-dock-warning border border-dock-warning/30 px-4 py-2 rounded-lg text-sm font-medium transition-colors flex items-center gap-2 cursor-pointer">
          <Trash2 class="w-4 h-4" /> Executar Limpeza (Prune)
        </button>
      </div>

      <div class="flex items-center justify-center text-xs text-dock-text-dim gap-2 mt-12">
        <Info class="w-4 h-4" /> DeployDock v0.1.0-beta • Desenvolvido para TCC em Ciência da Computação
      </div>
    </div>
  </div>
</template>
