<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import {
  Hexagon,
  Lock,
  User,
  KeyRound,
  ArrowRight,
  AlertCircle,
  Github,
  Mail,
  Copy,
  ExternalLink,
  CheckCircle2,
  RefreshCw,
} from 'lucide-vue-next';
import { useAuth } from '@/composables/useAuth';
import { api } from '@/services/api';
import type { OAuthProvidersInfo } from '@/services/types';

const router = useRouter();
const route = useRoute();
const { login, loginWithGithub, loginWithGoogle, setSession } = useAuth();

const username = ref('');
const password = ref('');
const otpCode = ref('');
const requires2FA = ref(false);
const error = ref('');
const loading = ref(false);

const providersInfo = ref<OAuthProvidersInfo>({
  allow_local_login: true,
  allow_github_login: true,
  allow_google_login: true,
  auto_register_oauth: true,
  github_oauth_client_id: 'Iv1.b507a08c87ecfe98',
  google_oauth_client_id: '',
  paas_github_connected: false,
  paas_github_username: null,
  paas_github_avatar: null,
});

// Abas de login: 'local' | 'github' | 'google'
const authTab = ref<'local' | 'github' | 'google'>('local');

// Estado OAuth GitHub
const ghTokenInput = ref('');
const ghUsernameInput = ref('');
const ghDeviceFlow = ref<{ user_code: string; verification_uri: string; interval: number } | null>(null);
const ghDeviceStatusMsg = ref('');
let ghPollTimer: ReturnType<typeof setInterval> | null = null;

// Estado OAuth Google
const googleEmailInput = ref('');
const googleNameInput = ref('');
const googleTokenInput = ref('');
const googleAppPasswordInput = ref('');
const googleDeviceFlow = ref<{ user_code: string; verification_uri: string; interval: number } | null>(null);
const googleDeviceStatusMsg = ref('');
let googlePollTimer: ReturnType<typeof setInterval> | null = null;

const handleGooglePopupMessage = async (event: MessageEvent) => {
  if (!event.data || event.data.type !== 'DEPLOYDOCK_GOOGLE_OAUTH') return;
  if (event.data.token) {
    googleTokenInput.value = event.data.token;
    await handleGoogleLogin();
  }
};

onMounted(async () => {
  window.addEventListener('message', handleGooglePopupMessage);
  try {
    providersInfo.value = await api.auth.getOAuthProviders();
    if (providersInfo.value.paas_github_username) {
      ghUsernameInput.value = providersInfo.value.paas_github_username;
    }
  } catch {
    // fallback padrão
  }
});

onUnmounted(() => {
  window.removeEventListener('message', handleGooglePopupMessage);
  if (ghPollTimer) clearInterval(ghPollTimer);
  if (googlePollTimer) clearInterval(googlePollTimer);
});

const redirectAfterLogin = () => {
  const redirect = (route.query.redirect as string) || '/dashboard';
  router.push(redirect);
};

const handleLogin = async () => {
  if (!username.value.trim() || !password.value) {
    error.value = 'Por favor, preencha o usuário e a senha.';
    return;
  }

  error.value = '';
  loading.value = true;

  try {
    await login(username.value.trim(), password.value, otpCode.value.trim() || undefined);
    redirectAfterLogin();
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

// Login com GitHub via conta já conectada ou Token/Username
const handleGithubDirectLogin = async (useConnected = false) => {
  error.value = '';
  loading.value = true;
  try {
    await loginWithGithub({
      token: ghTokenInput.value.trim() || undefined,
      username: ghUsernameInput.value.trim() || undefined,
      use_paas_connected: useConnected,
    });
    redirectAfterLogin();
  } catch (e: any) {
    error.value = e?.message || 'Erro ao autenticar com GitHub.';
  } finally {
    loading.value = false;
  }
};

// Login com GitHub via OAuth Device Code
const handleStartGithubDevice = async () => {
  error.value = '';
  ghDeviceStatusMsg.value = '';
  try {
    const flow = await api.auth.startGithubOAuthDevice();
    ghDeviceFlow.value = flow;
    try {
      await navigator.clipboard.writeText(flow.user_code);
    } catch {
      // ignore
    }
    if (ghPollTimer) clearInterval(ghPollTimer);
    ghPollTimer = setInterval(async () => {
      try {
        const res = await api.auth.pollGithubOAuthDevice();
        if (res.status === 'connected' && res.access_token && res.user) {
          if (ghPollTimer) clearInterval(ghPollTimer);
          setSession(res.access_token, res.user);
          redirectAfterLogin();
        } else if (res.error_description) {
          ghDeviceStatusMsg.value = res.error_description;
        }
      } catch {
        // continua aguardando
      }
    }, Math.max(7, (flow.interval || 5) + 2) * 1000);
  } catch (e: any) {
    error.value = e?.message || 'Não foi possível iniciar o OAuth Device do GitHub.';
  }
};

const copyAndOpenGithubDevice = async () => {
  if (!ghDeviceFlow.value) return;
  try {
    await navigator.clipboard.writeText(ghDeviceFlow.value.user_code);
  } catch {
    // ignore
  }
  window.open(ghDeviceFlow.value.verification_uri, '_blank', 'noopener,noreferrer');
};

const handleManualPollGithubDevice = async () => {
  ghDeviceStatusMsg.value = 'Confirmando autorização junto ao GitHub...';
  try {
    const res = await api.auth.pollGithubOAuthDevice();
    if (res.status === 'connected' && res.access_token && res.user) {
      if (ghPollTimer) clearInterval(ghPollTimer);
      setSession(res.access_token, res.user);
      redirectAfterLogin();
    } else {
      ghDeviceStatusMsg.value =
        res.error_description || 'Ainda aguardando autorização do código no GitHub...';
    }
  } catch (e: any) {
    ghDeviceStatusMsg.value = e?.message || 'Erro ao verificar autorização.';
  }
};

// Login com Google via Device Code oficial (google.com/device)
const startGoogleLoginDeviceLoop = (intervalSec = 5) => {
  if (googlePollTimer) clearInterval(googlePollTimer);
  const pollMs = Math.max(6, intervalSec + 1) * 1000;
  googlePollTimer = setInterval(async () => {
    try {
      const res = await api.auth.pollGoogleOAuthDevice();
      if (res.status === 'connected' && res.access_token && res.user) {
        if (googlePollTimer) clearInterval(googlePollTimer);
        setSession(res.access_token, res.user);
        redirectAfterLogin();
      } else if (res.error_description) {
        googleDeviceStatusMsg.value = res.error_description;
      }
    } catch {
      // continua aguardando
    }
  }, pollMs);
};

const handleStartGoogleDevice = async () => {
  error.value = '';
  googleDeviceStatusMsg.value = '';
  try {
    const flow = await api.auth.startGoogleOAuthDevice();
    googleDeviceFlow.value = flow;
    try {
      await navigator.clipboard.writeText(flow.user_code);
    } catch {
      // ignore
    }
    startGoogleLoginDeviceLoop(flow.interval || 5);
  } catch (e: any) {
    error.value = e?.message || 'Erro ao iniciar autenticação Google.';
  }
};

const copyAndOpenGoogleDevice = async () => {
  if (!googleDeviceFlow.value) return;
  try {
    await navigator.clipboard.writeText(googleDeviceFlow.value.user_code);
  } catch {
    // ignore
  }
  window.open(googleDeviceFlow.value.verification_uri || 'https://www.google.com/device', '_blank', 'noopener,noreferrer');
};

const handleManualPollGoogleDevice = async () => {
  googleDeviceStatusMsg.value = 'Confirmando autorização junto ao Google...';
  try {
    const res = await api.auth.pollGoogleOAuthDevice();
    if (res.status === 'connected' && res.access_token && res.user) {
      if (googlePollTimer) clearInterval(googlePollTimer);
      setSession(res.access_token, res.user);
      redirectAfterLogin();
    } else {
      googleDeviceStatusMsg.value =
        res.error_description || 'Aguardando você colar o código em google.com/device...';
    }
  } catch (e: any) {
    googleDeviceStatusMsg.value = e?.message || 'Erro ao verificar autorização.';
  }
};

const handleGoogleLogin = async () => {
  if (!googleEmailInput.value.trim() && !googleTokenInput.value.trim()) {
    error.value = 'Informe seu e-mail da conta Google ou cole o Token OAuth Google.';
    return;
  }
  error.value = '';
  loading.value = true;
  try {
    await loginWithGoogle({
      email: googleEmailInput.value.trim() || undefined,
      name: googleNameInput.value.trim() || undefined,
      id_token: googleTokenInput.value.trim() || undefined,
      access_token: googleTokenInput.value.trim() || undefined,
      app_password: googleAppPasswordInput.value.trim() || undefined,
    });
    redirectAfterLogin();
  } catch (e: any) {
    error.value = e?.message || 'Falha ao autenticar com a conta Google.';
  } finally {
    loading.value = false;
  }
};

const fillAdminCredentials = () => {
  authTab.value = 'local';
  username.value = 'admin';
  password.value = 'admin123';
};
</script>

<template>
  <div class="min-h-screen bg-dock-bg flex items-center justify-center p-4">
    <div class="w-full max-w-md">
      <!-- Identidade -->
      <div class="mb-6">
        <div class="inline-flex items-center gap-2.5 mb-2">
          <div class="w-7 h-7 rounded bg-dock-panel border border-dock-border-light flex items-center justify-center text-dock-text">
            <Hexagon class="w-4 h-4 text-dock-accent" />
          </div>
          <span class="text-base font-semibold text-dock-text tracking-tight">DeployDock</span>
        </div>
        <p class="text-xs text-dock-text-dim">
          Autenticação Unificada • Conta Local, Git (GitHub) e Google SSO
        </p>
      </div>

      <!-- Card do Formulário -->
      <div class="glass-panel p-6 bg-dock-surface space-y-4">
        <!-- Botões de Escolha de Método de Login (Local / GitHub / Google) -->
        <div class="grid grid-cols-3 gap-2 p-1 rounded-lg bg-dock-bg border border-dock-border text-xs">
          <button
            type="button"
            @click="authTab = 'local'; error = ''"
            class="py-2 px-2 rounded-md font-medium flex items-center justify-center gap-1.5 transition-all cursor-pointer"
            :class="
              authTab === 'local'
                ? 'bg-dock-surface text-dock-text shadow-sm border border-dock-border-light'
                : 'text-dock-text-muted hover:text-dock-text'
            "
          >
            <Lock class="w-3.5 h-3.5 text-dock-accent" />
            <span>Conta Local</span>
          </button>
          <button
            v-if="providersInfo.allow_github_login"
            type="button"
            @click="authTab = 'github'; error = ''"
            class="py-2 px-2 rounded-md font-medium flex items-center justify-center gap-1.5 transition-all cursor-pointer"
            :class="
              authTab === 'github'
                ? 'bg-dock-surface text-dock-text shadow-sm border border-dock-border-light'
                : 'text-dock-text-muted hover:text-dock-text'
            "
          >
            <Github class="w-3.5 h-3.5 text-dock-accent" />
            <span>GitHub (Git)</span>
          </button>
          <button
            v-if="providersInfo.allow_google_login"
            type="button"
            @click="authTab = 'google'; error = ''"
            class="py-2 px-2 rounded-md font-medium flex items-center justify-center gap-1.5 transition-all cursor-pointer"
            :class="
              authTab === 'google'
                ? 'bg-dock-surface text-dock-text shadow-sm border border-dock-border-light'
                : 'text-dock-text-muted hover:text-dock-text'
            "
          >
            <Mail class="w-3.5 h-3.5 text-dock-success" />
            <span>Google</span>
          </button>
        </div>

        <!-- Mensagem de Erro -->
        <div
          v-if="error"
          class="p-2.5 rounded bg-dock-error/10 border border-dock-error/30 text-dock-error text-xs flex items-start gap-2"
        >
          <AlertCircle class="w-4 h-4 shrink-0 mt-0.5" />
          <span>{{ error }}</span>
        </div>

        <!-- ABA 1: LOGIN LOCAL -->
        <form v-if="authTab === 'local'" @submit.prevent="handleLogin" class="space-y-4">
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
            class="w-full mt-1 bg-dock-accent hover:bg-dock-accent-hover text-white py-2.5 rounded text-xs font-medium transition-colors flex items-center justify-center gap-2 disabled:opacity-50 cursor-pointer"
          >
            <span>{{ loading ? 'Autenticando...' : 'Entrar no Console' }}</span>
            <ArrowRight v-if="!loading" class="w-3.5 h-3.5" />
          </button>

          <!-- Atalhos rápidos para Git e Google -->
          <div class="pt-2 border-t border-dock-border space-y-2">
            <div class="text-[11px] text-center text-dock-text-dim">Ou entre rapidamente com sua conta externa:</div>
            <div class="grid grid-cols-2 gap-2">
              <button
                v-if="providersInfo.allow_github_login"
                type="button"
                @click="authTab = 'github'"
                class="py-2 px-3 rounded bg-dock-bg hover:bg-dock-panel border border-dock-border text-xs font-medium text-dock-text flex items-center justify-center gap-2 cursor-pointer"
              >
                <Github class="w-3.5 h-3.5 text-dock-accent" />
                Entrar com Git
              </button>
              <button
                v-if="providersInfo.allow_google_login"
                type="button"
                @click="authTab = 'google'"
                class="py-2 px-3 rounded bg-dock-bg hover:bg-dock-panel border border-dock-border text-xs font-medium text-dock-text flex items-center justify-center gap-2 cursor-pointer"
              >
                <Mail class="w-3.5 h-3.5 text-dock-success" />
                Entrar com Google
              </button>
            </div>
          </div>
        </form>

        <!-- ABA 2: LOGIN COM CONTA GIT (GITHUB) -->
        <div v-else-if="authTab === 'github'" class="space-y-3.5 text-xs">
          <div class="p-3 rounded-lg bg-dock-bg border border-dock-border space-y-2">
            <div class="font-semibold text-dock-text flex items-center gap-2">
              <Github class="w-4 h-4 text-dock-accent" />
              Autenticação via Conta Git / GitHub
            </div>
            <p class="text-[11px] text-dock-text-dim">
              Entre com sua conta do GitHub para sincronizar repositórios, branches e permissões automaticamente.
            </p>

            <!-- Se já houver conta GitHub conectada no servidor -->
            <button
              v-if="providersInfo.paas_github_connected"
              type="button"
              @click="handleGithubDirectLogin(true)"
              :disabled="loading"
              class="w-full py-2.5 px-3 rounded-lg bg-dock-success text-white font-semibold flex items-center justify-center gap-2 cursor-pointer hover:opacity-90"
            >
              <CheckCircle2 class="w-4 h-4" />
              Continuar como @{{ providersInfo.paas_github_username }} (GitHub Conectado)
            </button>

            <!-- Opção 1: OAuth Device Code -->
            <div class="pt-1 space-y-2">
              <button
                type="button"
                @click="handleStartGithubDevice"
                class="w-full py-2 px-3 rounded bg-dock-accent hover:bg-dock-accent-hover text-white font-medium flex items-center justify-center gap-2 cursor-pointer"
              >
                <Github class="w-3.5 h-3.5" />
                1. Gerar Código de Login no Navegador (OAuth)
              </button>

              <div
                v-if="ghDeviceFlow"
                class="p-3 rounded-lg bg-dock-surface border-2 border-dock-accent space-y-2"
              >
                <div class="text-[11px] text-dock-text">
                  Copie o código abaixo e autorize em <code>github.com/login/device</code>:
                </div>
                <div class="text-xl font-mono font-bold tracking-widest text-dock-accent text-center py-1 bg-dock-bg rounded border border-dock-border select-all">
                  {{ ghDeviceFlow.user_code }}
                </div>
                <div class="grid grid-cols-1 sm:grid-cols-2 gap-1.5">
                  <button
                    type="button"
                    @click="copyAndOpenGithubDevice"
                    class="py-2 px-2.5 rounded bg-dock-accent text-white font-semibold flex items-center justify-center gap-1.5 cursor-pointer"
                  >
                    <Copy class="w-3.5 h-3.5" />
                    2. Copiar e Abrir GitHub
                    <ExternalLink class="w-3 h-3" />
                  </button>
                  <button
                    type="button"
                    @click="handleManualPollGithubDevice"
                    class="py-2 px-2.5 rounded bg-dock-success text-white font-semibold flex items-center justify-center gap-1.5 cursor-pointer"
                  >
                    <CheckCircle2 class="w-3.5 h-3.5" />
                    3. Já Autorizei — Entrar
                  </button>
                </div>
                <div class="text-[11px] text-dock-text-dim flex items-center gap-1.5">
                  <RefreshCw class="w-3 h-3 animate-spin text-dock-accent shrink-0" />
                  <span>{{ ghDeviceStatusMsg || 'Aguardando confirmação no GitHub...' }}</span>
                </div>
              </div>
            </div>
          </div>

          <!-- Opção 2: Login direto via Token PAT do GitHub -->
          <div class="p-3 rounded-lg bg-dock-bg border border-dock-border space-y-2">
            <div class="flex items-center justify-between">
              <span class="font-medium text-dock-text">Ou entre com Token / Usuário GitHub</span>
              <a
                href="https://github.com/settings/tokens/new?description=DeployDock-Login&scopes=repo,read:user,user:email"
                target="_blank"
                rel="noopener noreferrer"
                class="text-[11px] text-dock-accent hover:underline flex items-center gap-1"
              >
                Gerar Token 1-Clique <ExternalLink class="w-3 h-3" />
              </a>
            </div>
            <input
              v-model="ghUsernameInput"
              type="text"
              placeholder="Seu usuário GitHub (ex: JeanMago)"
              class="w-full bg-dock-surface border border-dock-border rounded px-2.5 py-2 font-mono text-dock-text outline-none focus:border-dock-accent"
            />
            <input
              v-model="ghTokenInput"
              type="password"
              placeholder="Personal Access Token (ghp_xxxx) — opcional se já vinculado"
              class="w-full bg-dock-surface border border-dock-border rounded px-2.5 py-2 font-mono text-dock-text outline-none focus:border-dock-accent"
            />
            <button
              type="button"
              @click="handleGithubDirectLogin(false)"
              :disabled="loading"
              class="w-full py-2 rounded bg-dock-panel hover:bg-dock-accent text-dock-text hover:text-white border border-dock-border-light font-medium transition-colors cursor-pointer"
            >
              {{ loading ? 'Autenticando GitHub...' : 'Entrar com Conta GitHub' }}
            </button>
          </div>
        </div>

        <!-- ABA 3: LOGIN COM CONTA GOOGLE -->
        <form v-else-if="authTab === 'google'" @submit.prevent="handleGoogleLogin" class="space-y-3.5 text-xs">
          <!-- Opção 1: Código de Dispositivo Oficial do Google (google.com/device) -->
          <div class="p-3 rounded-lg bg-dock-bg border border-dock-border space-y-2.5">
            <div class="font-semibold text-dock-text flex items-center gap-2">
              <Mail class="w-4 h-4 text-dock-success" />
              Opção 1 — Login com Código de Dispositivo Google (OAuth)
            </div>
            <p class="text-[11px] text-dock-text-dim">
              Gere um código de 8 letras e autorize direto em <code>google.com/device</code> na sua conta Google.
            </p>
            <button
              type="button"
              @click="handleStartGoogleDevice"
              class="w-full py-2.5 px-3 rounded-lg bg-dock-success hover:opacity-90 text-white font-semibold flex items-center justify-center gap-2 cursor-pointer"
            >
              <Mail class="w-4 h-4" />
              1. Gerar Código de Login Google
            </button>

            <div
              v-if="googleDeviceFlow"
              class="p-3 rounded-lg bg-dock-surface border-2 border-dock-success space-y-2"
            >
              <div class="text-[11px] text-dock-text">
                Copie o código abaixo e autorize em <code>google.com/device</code>:
              </div>
              <div class="text-xl font-mono font-bold tracking-widest text-dock-success text-center py-1 bg-dock-bg rounded border border-dock-border select-all">
                {{ googleDeviceFlow.user_code }}
              </div>
              <div class="grid grid-cols-1 sm:grid-cols-2 gap-1.5">
                <button
                  type="button"
                  @click="copyAndOpenGoogleDevice"
                  class="py-2 px-2.5 rounded bg-dock-success text-white font-semibold flex items-center justify-center gap-1.5 cursor-pointer"
                >
                  <Copy class="w-3.5 h-3.5" />
                  2. Copiar e Abrir Google
                  <ExternalLink class="w-3 h-3" />
                </button>
                <button
                  type="button"
                  @click="handleManualPollGoogleDevice"
                  class="py-2 px-2.5 rounded bg-dock-accent text-white font-semibold flex items-center justify-center gap-1.5 cursor-pointer"
                >
                  <CheckCircle2 class="w-3.5 h-3.5" />
                  3. Já Autorizei — Entrar
                </button>
              </div>
              <div class="text-[11px] text-dock-text-dim flex items-center gap-1.5">
                <RefreshCw class="w-3 h-3 animate-spin text-dock-success shrink-0" />
                <span>{{ googleDeviceStatusMsg || 'Aguardando autorização em google.com/device...' }}</span>
              </div>
            </div>
          </div>

          <!-- Opção 2: E-mail Google + Senha de App (ou Login Direto) -->
          <div class="p-3.5 rounded-lg bg-dock-bg border border-dock-border space-y-2.5">
            <div class="flex items-center justify-between">
              <span class="font-semibold text-dock-text">Opção 2 — Entrar com E-mail Google / Senha de App</span>
              <a
                href="https://myaccount.google.com/apppasswords"
                target="_blank"
                rel="noopener noreferrer"
                class="text-[11px] text-dock-success hover:underline flex items-center gap-1"
              >
                Gerar Senha de App <ExternalLink class="w-3 h-3" />
              </a>
            </div>

            <div>
              <label class="block text-dock-text-muted mb-1">E-mail da Conta Google</label>
              <input
                v-model="googleEmailInput"
                type="email"
                placeholder="seuemail@gmail.com"
                class="w-full bg-dock-surface border border-dock-border focus:border-dock-accent rounded px-3 py-2 font-mono text-dock-text outline-none"
              />
            </div>

            <div>
              <label class="block text-dock-text-muted mb-1">Senha de App Google (16 letras — valida no Google e ativa Gmail)</label>
              <input
                v-model="googleAppPasswordInput"
                type="password"
                placeholder="xxxx xxxx xxxx xxxx (opcional se já autorizado)"
                class="w-full bg-dock-surface border border-dock-border focus:border-dock-accent rounded px-3 py-2 font-mono text-dock-text outline-none"
              />
            </div>

            <div>
              <label class="block text-dock-text-muted mb-1">Nome de Exibição (Opcional)</label>
              <input
                v-model="googleNameInput"
                type="text"
                placeholder="Seu Nome"
                class="w-full bg-dock-surface border border-dock-border focus:border-dock-accent rounded px-3 py-2 text-dock-text outline-none"
              />
            </div>

            <button
              type="submit"
              :disabled="loading"
              class="w-full py-2.5 rounded bg-dock-panel hover:bg-dock-success text-dock-text hover:text-white border border-dock-border-light font-semibold flex items-center justify-center gap-2 transition-colors cursor-pointer"
            >
              <Mail class="w-4 h-4" />
              <span>{{ loading ? 'Autenticando Conta Google...' : 'Continuar com Conta Google' }}</span>
            </button>
          </div>
        </form>

        <!-- Credenciais de Desenvolvimento -->
        <div class="pt-3 border-t border-dock-border flex items-center justify-between text-[11px] font-mono text-dock-text-dim">
          <span>admin / admin123</span>
          <button
            type="button"
            @click="fillAdminCredentials"
            class="text-dock-accent hover:underline cursor-pointer"
          >
            preencher admin
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
