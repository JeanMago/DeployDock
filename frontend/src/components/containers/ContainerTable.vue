<script setup lang="ts">
import { useRouter } from 'vue-router';
import { Play, Square, RotateCw, Trash2, ExternalLink } from 'lucide-vue-next';
import StatusBadge from '@/components/common/StatusBadge.vue';
import type { Container } from '@/services/types';

defineProps<{ containers: Container[] }>();
const emit = defineEmits<{ (e: 'action', type: string, id: string): void }>();
const router = useRouter();

const navigate = (id: string) => router.push(`/containers/${id}`);

const formatPorts = (ports: Record<string, unknown> | null | undefined): string[] => {
  if (!ports || typeof ports !== 'object') return [];
  const result: string[] = [];
  for (const [containerPort, bindings] of Object.entries(ports)) {
    if (Array.isArray(bindings) && bindings.length > 0) {
      for (const b of bindings) {
        if (b && typeof b === 'object' && 'HostPort' in b) {
          result.push(`${(b as Record<string, unknown>).HostPort}:${containerPort}`);
        } else {
          result.push(containerPort);
        }
      }
    } else {
      result.push(containerPort);
    }
  }
  return result;
};
</script>

<template>
  <div class="glass-panel overflow-hidden">
    <div class="overflow-x-auto">
      <table class="w-full text-left text-xs border-collapse">
        <thead>
          <tr class="border-b border-dock-border bg-dock-surface text-dock-text-dim font-mono uppercase text-[11px]">
            <th class="px-4 py-2.5 font-medium whitespace-nowrap">Contêiner</th>
            <th class="px-4 py-2.5 font-medium whitespace-nowrap">Status</th>
            <th class="px-4 py-2.5 font-medium whitespace-nowrap">Imagem</th>
            <th class="px-4 py-2.5 font-medium whitespace-nowrap">Portas</th>
            <th class="px-4 py-2.5 font-medium whitespace-nowrap text-right">Controles</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-dock-border">
          <tr v-for="c in containers" :key="c.id" @click="navigate(c.id)" class="hover:bg-dock-surface/70 transition-colors cursor-pointer group">
            <td class="px-4 py-2.5 font-medium text-dock-text">
              <div class="flex items-center gap-2">
                <span>{{ c.name }}</span>
                <a
                  v-if="c.public_url"
                  :href="c.public_url"
                  target="_blank"
                  rel="noopener noreferrer"
                  @click.stop
                  class="inline-flex items-center gap-1 text-[11px] font-mono text-dock-accent hover:underline bg-dock-surface px-1.5 py-0.5 rounded border border-dock-border"
                  :title="'Abrir URL pública: ' + c.public_url"
                >
                  abrir <ExternalLink class="w-3 h-3" />
                </a>
              </div>
            </td>
            <td class="px-4 py-2.5"><StatusBadge :status="c.state || c.status" size="sm" /></td>
            <td class="px-4 py-2.5 font-mono text-xs text-dock-text-muted truncate max-w-[200px]" :title="c.image">{{ c.image }}</td>
            <td class="px-4 py-2.5 font-mono text-xs text-dock-text-dim">
              <span v-for="p in formatPorts(c.ports).slice(0, 2)" :key="p" class="inline-block bg-dock-bg px-1.5 py-0.5 rounded border border-dock-border mr-1 mb-0.5">
                {{ p }}
              </span>
              <span v-if="formatPorts(c.ports).length > 2" class="text-dock-text-dim text-xs">...</span>
              <span v-else-if="!formatPorts(c.ports).length" class="text-dock-text-dim/60">-</span>
            </td>
            <td class="px-4 py-2.5 text-right" @click.stop>
              <div class="flex items-center justify-end gap-1">
                <button v-if="c.state !== 'running'" @click="emit('action', 'start', c.id)" class="p-1.5 text-dock-text-muted hover:text-dock-success hover:bg-dock-surface rounded cursor-pointer" title="Iniciar"><Play class="w-3.5 h-3.5"/></button>
                <button v-if="c.state === 'running'" @click="emit('action', 'stop', c.id)" class="p-1.5 text-dock-text-muted hover:text-dock-warning hover:bg-dock-surface rounded cursor-pointer" title="Parar"><Square class="w-3.5 h-3.5"/></button>
                <button @click="emit('action', 'restart', c.id)" class="p-1.5 text-dock-text-muted hover:text-dock-accent hover:bg-dock-surface rounded cursor-pointer" title="Reiniciar"><RotateCw class="w-3.5 h-3.5"/></button>
                <button @click="emit('action', 'remove', c.id)" class="p-1.5 text-dock-text-muted hover:text-dock-error hover:bg-dock-surface rounded cursor-pointer" title="Remover"><Trash2 class="w-3.5 h-3.5"/></button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

