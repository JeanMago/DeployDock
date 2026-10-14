<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { HardDrive, Server, Info, Trash2 } from 'lucide-vue-next';
import { api } from '@/services/api';
import type { SystemInfo, User } from '@/services/types';
import LoadingSpinner from '@/components/common/LoadingSpinner.vue';

const sysInfo = ref<SystemInfo | null>(null);
const usersList = ref<User[]>([]);
const loading = ref(true);

const isCreatingUser = ref(false);
const newUser = ref({
  username: '',
  email: '',
  password: '',
  role: 'developer' as 'admin' | 'developer' | 'viewer',
  is_active: true,
});

const load = async () => {
  try {
    sysInfo.value = await api.system.info();
    usersList.value = await api.auth.listUsers();
  }
  catch(e) { console.error(e); }
  finally { loading.value = false; }
};

onMounted(load);

const createUser = async () => {
  if (!newUser.value.username || !newUser.value.password || !newUser.value.email) {
    alert('Preencha username, e-mail e senha.');
    return;
  }
  isCreatingUser.value = true;
  try {
    await api.auth.createUser(newUser.value);
    alert(`Usuário "${newUser.value.username}" criado com sucesso!`);
    newUser.value.username = '';
    newUser.value.email = '';
    newUser.value.password = '';
    load();
  } catch (err: any) {
    alert('Erro ao criar usuário: ' + err.message);
  } finally {
    isCreatingUser.value = false;
  }
};

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

      <!-- Gerenciamento de Usuários e Permissões (RBAC) -->
      <div class="glass-panel p-6">
        <h3 class="flex items-center gap-2 font-semibold text-lg border-b border-dock-border pb-3 mb-4 text-dock-text">
          <Server class="w-5 h-5 text-dock-accent"/> Controle de Acesso e Usuários (RBAC)
        </h3>
        <p class="text-sm text-dock-text-muted mb-4">
          Usuários com nível <strong>admin</strong> ou <strong>developer</strong> possuem permissão para gerenciar contêineres Docker. Contas <strong>viewer</strong> possuem acesso apenas de leitura.
        </p>

        <!-- Formulário Rápido de Criação de Usuário -->
        <div class="p-4 rounded-xl bg-dock-surface/40 border border-dock-border mb-6">
          <h4 class="text-xs font-semibold text-dock-text mb-3">Cadastrar Novo Usuário</h4>
          <div class="grid grid-cols-1 sm:grid-cols-4 gap-3">
            <input
              v-model="newUser.username"
              type="text"
              placeholder="Username (ex: dev1)"
              class="bg-dock-surface border border-dock-border focus:border-dock-accent rounded-lg px-3 py-2 text-xs text-dock-text outline-none font-mono"
            />
            <input
              v-model="newUser.email"
              type="email"
              placeholder="E-mail"
              class="bg-dock-surface border border-dock-border focus:border-dock-accent rounded-lg px-3 py-2 text-xs text-dock-text outline-none font-mono"
            />
            <input
              v-model="newUser.password"
              type="password"
              placeholder="Senha"
              class="bg-dock-surface border border-dock-border focus:border-dock-accent rounded-lg px-3 py-2 text-xs text-dock-text outline-none font-mono"
            />
            <div class="flex gap-2">
              <select
                v-model="newUser.role"
                class="bg-dock-surface border border-dock-border focus:border-dock-accent rounded-lg px-3 py-2 text-xs text-dock-text outline-none flex-1 font-mono"
              >
                <option value="developer">Developer</option>
                <option value="viewer">Viewer</option>
                <option value="admin">Admin</option>
              </select>
              <button
                @click="createUser"
                :disabled="isCreatingUser"
                class="bg-dock-accent hover:bg-dock-accent-hover text-white px-3 py-2 rounded-lg text-xs font-semibold transition-colors disabled:opacity-50 cursor-pointer shrink-0"
              >
                {{ isCreatingUser ? '...' : 'Criar' }}
              </button>
            </div>
          </div>
        </div>

        <!-- Lista de Usuários -->
        <div class="overflow-x-auto">
          <table class="w-full text-left text-xs border-collapse">
            <thead>
              <tr class="border-b border-dock-border text-dock-text-muted">
                <th class="py-2.5 font-medium">Usuário</th>
                <th class="py-2.5 font-medium">E-mail</th>
                <th class="py-2.5 font-medium">Papel (Role)</th>
                <th class="py-2.5 font-medium">Acesso Docker</th>
                <th class="py-2.5 font-medium text-right">Status</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-dock-border">
              <tr v-for="u in usersList" :key="u.id" class="hover:bg-dock-surface/40">
                <td class="py-2.5 font-mono text-dock-text font-medium">{{ u.username }}</td>
                <td class="py-2.5 text-dock-text-dim">{{ u.email }}</td>
                <td class="py-2.5">
                  <span
                    class="font-mono text-[10px] uppercase px-2 py-0.5 rounded-full"
                    :class="u.role === 'admin' ? 'bg-dock-accent/15 text-dock-accent border border-dock-accent/30' : (u.role === 'developer' ? 'bg-dock-success/15 text-dock-success border border-dock-success/30' : 'bg-dock-surface text-dock-text-dim border border-dock-border')"
                  >
                    {{ u.role }}
                  </span>
                </td>
                <td class="py-2.5">
                  <span v-if="u.role === 'admin' || u.role === 'developer'" class="text-dock-success font-medium">✓ Permitido</span>
                  <span v-else class="text-dock-text-dim font-medium">✗ Bloqueado</span>
                </td>
                <td class="py-2.5 text-right">
                  <span class="inline-block w-2 h-2 rounded-full" :class="u.is_active ? 'bg-dock-success' : 'bg-dock-error'"></span>
                </td>
              </tr>
            </tbody>
          </table>
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
