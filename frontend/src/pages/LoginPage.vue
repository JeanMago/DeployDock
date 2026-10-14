<script setup lang="ts">
import { ref } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import { Hexagon, Lock, User, ArrowRight, AlertCircle, ShieldCheck } from 'lucide-vue-next';
import { useAuth } from '@/composables/useAuth';

const router = useRouter();
const route = useRoute();
const { login } = useAuth();

const username = ref('');
const password = ref('');
const error = ref('');
const loading = ref(false);

const handleLogin = async () => {
  if (!username.value.trim() || !password.value) {
    error.value = 'Por favor, preencha o usuário e a senha.';
    return;
  }

  error.value = '';
  loading.value = true;

  try {
    await login(username.value.trim(), password.value);
    const redirect = (route.query.redirect as string) || '/dashboard';
    router.push(redirect);
  } catch (err: any) {
    error.value = err?.message || 'Falha ao autenticar. Verifique suas credenciais.';
  } finally {
    loading.value = false;
  }
};

const fillAdminCredentials = () => {
  username.value = 'admin';
  password.value = 'admin123';
};
</script>

<template>
  <div class="min-h-screen bg-dock-bg flex items-center justify-center p-4 relative overflow-hidden">
    <!-- Efeitos de iluminação de fundo -->
    <div class="absolute -top-40 -left-40 w-96 h-96 bg-dock-accent/15 rounded-full blur-3xl pointer-events-none"></div>
    <div class="absolute -bottom-40 -right-40 w-96 h-96 bg-dock-accent/10 rounded-full blur-3xl pointer-events-none"></div>

    <div class="w-full max-w-md relative z-10 animate-fade-in">
      <!-- Logo e Identidade -->
      <div class="text-center mb-8">
        <div class="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-dock-surface border border-dock-border-light shadow-xl shadow-dock-accent/10 mb-4">
          <Hexagon class="w-9 h-9 text-dock-accent" />
        </div>
        <h1 class="text-2xl font-bold text-dock-text tracking-tight">DeployDock</h1>
        <p class="text-xs text-dock-text-dim mt-1.5">
          Plataforma Segura de GitOps, Contêineres e Orquestração
        </p>
      </div>

      <!-- Card do Formulário -->
      <div class="glass-panel p-8 bg-dock-surface/40 border border-dock-border-light shadow-2xl rounded-2xl">
        <div class="mb-6">
          <h2 class="text-base font-semibold text-dock-text">Entrar no Sistema</h2>
          <p class="text-xs text-dock-text-dim mt-0.5">Informe suas credenciais para gerenciar a infraestrutura</p>
        </div>

        <!-- Mensagem de Erro -->
        <div v-if="error" class="mb-5 p-3 rounded-lg bg-dock-error/15 border border-dock-error/30 text-dock-error text-xs flex items-start gap-2">
          <AlertCircle class="w-4 h-4 shrink-0 mt-0.5" />
          <span>{{ error }}</span>
        </div>

        <form @submit.prevent="handleLogin" class="space-y-4">
          <div>
            <label class="block text-xs font-medium text-dock-text-muted mb-1.5">Usuário ou E-mail</label>
            <div class="relative">
              <input
                v-model="username"
                type="text"
                placeholder="admin"
                autofocus
                class="w-full bg-dock-surface border border-dock-border focus:border-dock-accent rounded-lg pl-10 pr-4 py-2.5 text-sm text-dock-text placeholder-dock-text-dim outline-none transition-colors font-mono"
              />
              <User class="w-4 h-4 text-dock-text-dim absolute left-3.5 top-3" />
            </div>
          </div>

          <div>
            <label class="block text-xs font-medium text-dock-text-muted mb-1.5">Senha</label>
            <div class="relative">
              <input
                v-model="password"
                type="password"
                placeholder="••••••••"
                class="w-full bg-dock-surface border border-dock-border focus:border-dock-accent rounded-lg pl-10 pr-4 py-2.5 text-sm text-dock-text placeholder-dock-text-dim outline-none transition-colors font-mono"
              />
              <Lock class="w-4 h-4 text-dock-text-dim absolute left-3.5 top-3" />
            </div>
          </div>

          <button
            type="submit"
            :disabled="loading"
            class="w-full mt-2 bg-dock-accent hover:bg-dock-accent-hover text-white py-2.5 rounded-lg text-sm font-semibold transition-all shadow-lg shadow-dock-accent/25 flex items-center justify-center gap-2 disabled:opacity-50 cursor-pointer"
          >
            <span>{{ loading ? 'Autenticando...' : 'Acessar Painel' }}</span>
            <ArrowRight v-if="!loading" class="w-4 h-4" />
          </button>
        </form>

        <!-- Dica de Credenciais Iniciais de Admin -->
        <div class="mt-6 pt-5 border-t border-dock-border/70 flex items-start gap-2.5 text-xs text-dock-text-dim bg-dock-bg/50 p-3 rounded-xl border border-dock-border">
          <ShieldCheck class="w-4 h-4 text-dock-accent shrink-0 mt-0.5" />
          <div class="flex-1">
            <span class="font-medium text-dock-text">Credenciais de Administrador:</span>
            <div class="font-mono text-[11px] mt-1 text-dock-text-muted">
              Usuário: <span class="text-dock-accent">admin</span> | Senha: <span class="text-dock-accent">admin123</span>
            </div>
            <button
              type="button"
              @click="fillAdminCredentials"
              class="mt-1.5 text-[11px] text-dock-accent hover:underline font-medium block"
            >
              Preencher dados automaticamente
            </button>
          </div>
        </div>
      </div>

      <!-- Rodapé -->
      <div class="text-center mt-6 text-xs text-dock-text-dim">
        DeployDock v1.0 • Controle de Acesso Baseado em Papéis (RBAC)
      </div>
    </div>
  </div>
</template>
