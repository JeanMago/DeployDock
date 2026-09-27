<script setup lang="ts">
import { useRouter } from 'vue-router';
import { Play, Square, RotateCw, Trash2 } from 'lucide-vue-next';
import StatusBadge from '@/components/common/StatusBadge.vue';
import type { Container } from '@/services/types';

defineProps<{ containers: Container[] }>();
const emit = defineEmits<{ (e: 'action', type: string, id: string): void }>();
const router = useRouter();

const navigate = (id: string) => router.push(`/containers/${id}`);
</script>

<template>
  <div class="glass-panel overflow-hidden">
    <div class="overflow-x-auto">
      <table class="w-full text-left text-sm border-collapse">
        <thead>
          <tr class="border-b border-dock-border bg-dock-surface/50 text-dock-text-muted">
            <th class="px-4 py-3 font-medium whitespace-nowrap">Name</th>
            <th class="px-4 py-3 font-medium whitespace-nowrap">Status</th>
            <th class="px-4 py-3 font-medium whitespace-nowrap">Image</th>
            <th class="px-4 py-3 font-medium whitespace-nowrap">Ports</th>
            <th class="px-4 py-3 font-medium whitespace-nowrap text-right">Actions</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-dock-border">
          <tr v-for="c in containers" :key="c.id" @click="navigate(c.id)" class="hover:bg-dock-surface/50 transition-colors cursor-pointer group">
            <td class="px-4 py-3 font-medium text-dock-text">{{ c.name }}</td>
            <td class="px-4 py-3"><StatusBadge :status="c.state" size="sm" /></td>
            <td class="px-4 py-3 font-mono text-xs text-dock-text-muted truncate max-w-[200px]" :title="c.image">{{ c.image }}</td>
            <td class="px-4 py-3 text-xs text-dock-text-dim">
              <span v-for="p in c.ports.slice(0, 2)" :key="p.publicPort || p.privatePort" class="inline-block bg-dock-surface px-1.5 py-0.5 rounded border border-dock-border mr-1 mb-1">
                {{ p.publicPort ? `${p.publicPort}:` : '' }}{{ p.privatePort }}
              </span>
              <span v-if="c.ports.length > 2" class="text-dock-text-dim text-xs">...</span>
            </td>
            <td class="px-4 py-3 text-right" @click.stop>
              <div class="flex items-center justify-end gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                <button v-if="c.state !== 'running'" @click="emit('action', 'start', c.id)" class="p-1.5 text-dock-text-muted hover:text-dock-success hover:bg-dock-surface rounded"><Play class="w-4 h-4"/></button>
                <button v-if="c.state === 'running'" @click="emit('action', 'stop', c.id)" class="p-1.5 text-dock-text-muted hover:text-dock-warning hover:bg-dock-surface rounded"><Square class="w-4 h-4"/></button>
                <button @click="emit('action', 'restart', c.id)" class="p-1.5 text-dock-text-muted hover:text-dock-accent hover:bg-dock-surface rounded"><RotateCw class="w-4 h-4"/></button>
                <button @click="emit('action', 'remove', c.id)" class="p-1.5 text-dock-text-muted hover:text-dock-error hover:bg-dock-surface rounded"><Trash2 class="w-4 h-4"/></button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
