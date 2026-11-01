<script setup lang="ts">
import { ref } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import { Hexagon, Lock, User, KeyRound, ArrowRight, AlertCircle } from 'lucide-vue-next';
import { useAuth } from '@/composables/useAuth';

const router = useRouter();
const route = useRoute();
const { login } = useAuth();

const username = ref('');
const password = ref('');
const otpCode = ref('');
const requires2FA = ref(false);
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
    await login(username.value.trim(), password.value, otpCode.value.trim() || undefined);
    const redirect = (route.query.redirect as string) || '/dashboard';
    router.push(redirect);
  } catch (err: any) {
    const msg = err?.message || 'Falha ao autenticar. Verifique suas credenciais.';
    if (msg.includes('2FA_REQUIRED')) {
      requires2FA.value = true;
      error.value = 'Sua conta possui 2FA ativo. Digite o código de 6 dígitos do seu autenticador.';
    } else {
      error.value = msg;
    }
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
  <div class="min-h-screen bg-dock-bg flex items-center justify-center p-4">
    <div class="w-full max-w-sm">
      <!-- Identidade -->
      <div class="mb-6">
        <div class="inline-flex items-center gap-2.5 mb-2">
          <div class="w-7 h-7 rounded bg-dock-panel border border-dock-border-light flex items-center justify-center text-dock-text">
            <Hexagon class="w-4 h-4 text-dock-accent" />
          </div>
          <span class="text-base font-semibold text-dock-text tracking-tight">DeployDock</span>
        </div>
        <p class="text-xs text-dock-text-dim">
          Autenticação do console de orquestração e GitOps
        </p>
      </div>

      <!-- Card do Formulário -->
      <div class="glass-panel p-6 bg-dock-surface">
        <!-- Mensagem de Erro -->
        <div v-if="error" class="mb-4 p-2.5 rounded bg-dock-error/10 border border-dock-error/30 text-dock-error text-xs flex items-start gap-2">
          <AlertCircle class="w-4 h-4 shrink-0 mt-0.5" />
          <span>{{ error }}</span>
        </div>

        <form @submit.prevent="handleLogin" class="space-y-4">
          <div>
            <label class="block text-xs font-medium text-dock-text-muted mb-1">Usuário ou E-mail</label>
            <div class="relative">
              <input
                v-model="username"
                type="text"
                placeholder="admin"
                autofocus
                class="w-full bg-dock-bg border border-dock-border focus:border-dock-accent rounded pl-9 pr-3 py-2 text-xs text-dock-text placeholder-dock-text-dim outline-none transition-colors font-mono"
              />
              <User class="w-3.5 h-3.5 text-dock-text-dim absolute left-3 top-2.5" />
            </div>
          </div>

          <div>
            <label class="block text-xs font-medium text-dock-text-muted mb-1">Senha</label>
            <div class="relative">
              <input
                v-model="password"
                type="password"
                placeholder="••••••••"
                class="w-full bg-dock-bg border border-dock-border focus:border-dock-accent rounded pl-9 pr-3 py-2 text-xs text-dock-text placeholder-dock-text-dim outline-none transition-colors font-mono"
              />
              <Lock class="w-3.5 h-3.5 text-dock-text-dim absolute left-3 top-2.5" />
            </div>
          </div>

          <div v-if="requires2FA">
            <label class="block text-xs font-medium text-dock-accent mb-1">Código 2FA (TOTP — 6 dígitos)</label>
            <div class="relative">
              <input
                v-model="otpCode"
                type="text"
                maxlength="6"
                placeholder="123456"
                class="w-full bg-dock-bg border border-dock-accent rounded pl-9 pr-3 py-2 text-xs text-dock-text placeholder-dock-text-dim outline-none transition-colors font-mono tracking-widest"
              />
              <KeyRound class="w-3.5 h-3.5 text-dock-accent absolute left-3 top-2.5" />
            </div>
          </div>

          <button
            type="submit"
            :disabled="loading"
            class="w-full mt-1 bg-dock-accent hover:bg-dock-accent-hover text-white py-2 rounded text-xs font-medium transition-colors flex items-center justify-center gap-2 disabled:opacity-50 cursor-pointer"
          >
            <span>{{ loading ? 'Autenticando...' : 'Entrar' }}</span>
            <ArrowRight v-if="!loading" class="w-3.5 h-3.5" />
          </button>
        </form>

        <!-- Credenciais de Desenvolvimento -->
        <div class="mt-5 pt-4 border-t border-dock-border flex items-center justify-between text-[11px] font-mono text-dock-text-dim">
          <span>admin / admin123</span>
          <button
            type="button"
            @click="fillAdminCredentials"
            class="text-dock-accent hover:underline cursor-pointer"
          >
            preencher
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
