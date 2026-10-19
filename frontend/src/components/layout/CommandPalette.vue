<script setup lang="ts">
import { ref, computed, onMounted, watch, nextTick } from 'vue';
import { useRouter } from 'vue-router';
import {
  Search,
  LayoutDashboard,
  FolderGit2,
  Rocket,
  Box,
  HardDrive,
  ShieldCheck,
  Settings,
  BookOpen,
  Terminal,
  FileText,
  ArrowRight,
  X,
} from 'lucide-vue-next';
import { api } from '@/services/api';
import type { Container, Project } from '@/services/types';

const props = defineProps<{
  open: boolean;
}>();

const emit = defineEmits<{
  (e: 'close'): void;
}>();

const router = useRouter();
const query = ref('');
const inputRef = ref<HTMLInputElement | null>(null);
const selectedIndex = ref(0);

const projects = ref<Project[]>([]);
const containers = ref<Container[]>([]);

const loadEntities = async () => {
  try {
    const [pList, cList] = await Promise.all([
      api.projects.list().catch(() => []),
      api.containers.list(true).catch(() => []),
    ]);
    projects.value = pList;
    containers.value = cList;
  } catch {
    // ignore
  }
};

watch(
  () => props.open,
  async (isOpen) => {
    if (isOpen) {
      query.value = '';
      selectedIndex.value = 0;
      loadEntities();
      await nextTick();
      inputRef.value?.focus();
    }
  }
);

onMounted(loadEntities);

interface PaletteAction {
  id: string;
  category: string;
  title: string;
  subtitle: string;
  icon: any;
  path: string;
}

const allActions = computed<PaletteAction[]>(() => {
  const list: PaletteAction[] = [
    {
      id: 'nav-dashboard',
      category: 'Navegação',
      title: 'Visão Geral (Dashboard)',
      subtitle: 'Resumo operacional da plataforma',
      icon: LayoutDashboard,
      path: '/dashboard',
    },
    {
      id: 'nav-projects',
      category: 'Navegação',
      title: 'Projetos GitOps & 1-Click Apps',
      subtitle: 'Gerenciar repositórios, .env e domínios',
      icon: FolderGit2,
      path: '/projects',
    },
    {
      id: 'nav-containers',
      category: 'Navegação',
      title: 'Contêineres Docker',
      subtitle: 'Inspecionar logs, terminal e estado',
      icon: Box,
      path: '/containers',
    },
    {
      id: 'nav-resources',
      category: 'Navegação',
      title: 'Recursos & Armazenamento',
      subtitle: 'Uso real do host vs. Docker e limpeza de disco',
      icon: HardDrive,
      path: '/resources',
    },
    {
      id: 'nav-security',
      category: 'Navegação',
      title: 'Segurança, WAF & Firewall',
      subtitle: 'Proteção contra ataques, IPs bloqueados e auditoria',
      icon: ShieldCheck,
      path: '/security',
    },
    {
      id: 'nav-deployments',
      category: 'Navegação',
      title: 'Histórico de Deploys',
      subtitle: 'Logs de build e rollback de versões',
      icon: Rocket,
      path: '/deployments',
    },
    {
      id: 'nav-settings',
      category: 'Navegação',
      title: 'Configurações & Usuários (RBAC)',
      subtitle: 'Controle de acesso e manutenção',
      icon: Settings,
      path: '/settings',
    },
    {
      id: 'nav-tutorial',
      category: 'Navegação',
      title: 'Documentação & Guia',
      subtitle: 'Manual de operação do DeployDock',
      icon: BookOpen,
      path: '/tutorial',
    },
  ];

  for (const p of projects.value) {
    const cid = p.container_id || `deploydock_${p.name.toLowerCase()}`;
    list.push({
      id: `proj-logs-${p.id}`,
      category: 'Projetos',
      title: `${p.name} — Abrir Logs`,
      subtitle: p.public_url,
      icon: FileText,
      path: `/containers/${cid}?tab=logs`,
    });
    list.push({
      id: `proj-exec-${p.id}`,
      category: 'Projetos',
      title: `${p.name} — Abrir Terminal Shell`,
      subtitle: `Container ${cid}`,
      icon: Terminal,
      path: `/containers/${cid}?tab=exec`,
    });
  }

  for (const c of containers.value.slice(0, 12)) {
    list.push({
      id: `cnt-${c.id}`,
      category: 'Contêineres',
      title: c.name,
      subtitle: `${c.image} (${c.state || c.status})`,
      icon: Box,
      path: `/containers/${c.id}?tab=logs`,
    });
  }

  return list;
});

const filteredActions = computed(() => {
  const q = query.value.trim().toLowerCase();
  if (!q) return allActions.value.slice(0, 10);
  return allActions.value
    .filter((a) => `${a.title} ${a.subtitle} ${a.category}`.toLowerCase().includes(q))
    .slice(0, 12);
});

watch(filteredActions, () => {
  selectedIndex.value = 0;
});

const triggerAction = (action?: PaletteAction) => {
  const target = action || filteredActions.value[selectedIndex.value];
  if (!target) return;
  router.push(target.path);
  emit('close');
};

const handleKeydown = (e: KeyboardEvent) => {
  if (e.key === 'ArrowDown') {
    e.preventDefault();
    if (filteredActions.value.length > 0) {
      selectedIndex.value = (selectedIndex.value + 1) % filteredActions.value.length;
    }
  } else if (e.key === 'ArrowUp') {
    e.preventDefault();
    if (filteredActions.value.length > 0) {
      selectedIndex.value =
        (selectedIndex.value - 1 + filteredActions.value.length) % filteredActions.value.length;
    }
  } else if (e.key === 'Enter') {
    e.preventDefault();
    triggerAction();
  } else if (e.key === 'Escape') {
    emit('close');
  }
};
</script>

<template>
  <div
    v-if="open"
    class="fixed inset-0 z-50 bg-black/75 flex items-start justify-center pt-14 sm:pt-24 px-3"
    @click.self="$emit('close')"
  >
    <div
      class="w-full max-w-xl bg-dock-surface border border-dock-border-light rounded-lg shadow-2xl overflow-hidden"
      @keydown="handleKeydown"
    >
      <div class="flex items-center gap-2.5 px-3.5 py-3 border-b border-dock-border bg-dock-bg">
        <Search class="w-4 h-4 text-dock-accent shrink-0" />
        <input
          ref="inputRef"
          v-model="query"
          type="text"
          placeholder="Ir para página, abrir logs de projeto ou terminal de contêiner..."
          class="flex-1 bg-transparent text-xs sm:text-sm text-dock-text outline-none font-mono placeholder:text-dock-text-dim"
        />
        <button
          @click="$emit('close')"
          class="p-1 rounded text-dock-text-dim hover:text-dock-text cursor-pointer"
        >
          <X class="w-4 h-4" />
        </button>
      </div>

      <div class="max-h-80 overflow-y-auto divide-y divide-dock-border/60 p-1.5">
        <div
          v-if="filteredActions.length === 0"
          class="py-8 text-center text-xs text-dock-text-dim"
        >
          Nenhum resultado encontrado para "{{ query }}".
        </div>

        <button
          v-for="(item, idx) in filteredActions"
          :key="item.id"
          @click="triggerAction(item)"
          @mouseenter="selectedIndex = idx"
          class="w-full flex items-center justify-between gap-3 px-3 py-2 rounded text-left transition-colors cursor-pointer"
          :class="
            idx === selectedIndex
              ? 'bg-dock-panel border border-dock-border-light text-dock-text'
              : 'border border-transparent text-dock-text-muted hover:bg-dock-panel/50'
          "
        >
          <div class="flex items-center gap-2.5 min-w-0">
            <component :is="item.icon" class="w-4 h-4 text-dock-accent shrink-0" />
            <div class="min-w-0">
              <div class="text-xs font-medium text-dock-text truncate">{{ item.title }}</div>
              <div class="text-[11px] font-mono text-dock-text-dim truncate">{{ item.subtitle }}</div>
            </div>
          </div>
          <div class="flex items-center gap-2 shrink-0">
            <span class="text-[10px] font-mono uppercase px-1.5 py-0.5 rounded bg-dock-bg border border-dock-border text-dock-text-dim">
              {{ item.category }}
            </span>
            <ArrowRight class="w-3.5 h-3.5 text-dock-text-dim" />
          </div>
        </button>
      </div>

      <div class="px-3.5 py-2 border-t border-dock-border bg-dock-bg flex items-center justify-between text-[11px] font-mono text-dock-text-dim">
        <span>↑↓ para navegar • Enter para abrir</span>
        <span>ESC para fechar</span>
      </div>
    </div>
  </div>
</template>
