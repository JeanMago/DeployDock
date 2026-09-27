<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from 'vue';
import { Terminal } from '@xterm/xterm';
import { FitAddon } from '@xterm/addon-fit';
import { WebLinksAddon } from '@xterm/addon-web-links';
import { Trash2 } from 'lucide-vue-next';
import '@xterm/xterm/css/xterm.css';
import { useWebSocket } from '@/composables/useWebSocket';
import { api } from '@/services/api';

const props = defineProps<{ containerId: string }>();
const terminalRef = ref<HTMLElement | null>(null);
let term: Terminal | null = null;
let fitAddon: FitAddon | null = null;

const { status } = useWebSocket(`/ws/containers/${props.containerId}/logs`, (data) => {
  if (term) term.write(data + '\r\n');
});

const loadHistory = async () => {
  try {
    const res = await api.containers.getLogs(props.containerId);
    if (term && res.logs) {
      term.write(res.logs.replace(/\n/g, '\r\n') + '\r\n');
    }
  } catch (e) {
    console.error(e);
  }
};

onMounted(async () => {
  if (!terminalRef.value) return;
  
  term = new Terminal({
    theme: {
      background: '#070b14',
      foreground: '#e2e8f0',
      cursor: '#0ea5e9',
      selectionBackground: '#1e2a45',
      black: '#070b14',
      red: '#ef4444',
      green: '#22c55e',
      yellow: '#eab308',
      blue: '#3b82f6',
      magenta: '#d946ef',
      cyan: '#0ea5e9',
      white: '#f8fafc'
    },
    fontFamily: '"JetBrains Mono", monospace',
    fontSize: 13,
    lineHeight: 1.2,
    cursorBlink: true,
    disableStdin: true
  });
  
  fitAddon = new FitAddon();
  term.loadAddon(fitAddon);
  term.loadAddon(new WebLinksAddon());
  
  term.open(terminalRef.value);
  fitAddon.fit();
  
  window.addEventListener('resize', () => fitAddon?.fit());
  
  await loadHistory();
});

onBeforeUnmount(() => {
  term?.dispose();
  window.removeEventListener('resize', () => fitAddon?.fit());
});

const clearLogs = () => term?.clear();
</script>

<template>
  <div class="glass-panel flex flex-col h-[500px] overflow-hidden border border-dock-border">
    <div class="flex items-center justify-between px-4 py-2 bg-dock-surface border-b border-dock-border">
      <div class="flex items-center gap-2">
        <span class="w-2 h-2 rounded-full" :class="status === 'open' ? 'bg-dock-success shadow-[0_0_8px_rgba(34,197,94,0.6)]' : 'bg-dock-error'"></span>
        <span class="text-xs font-mono text-dock-text-muted">Terminal Logs</span>
      </div>
      <div class="flex gap-2">
        <button @click="clearLogs" class="p-1.5 text-dock-text-muted hover:text-dock-text rounded bg-dock-bg border border-dock-border hover:border-dock-border-light transition-colors" title="Clear">
          <Trash2 class="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
    <div ref="terminalRef" class="flex-1 p-2 bg-[#070b14] overflow-hidden"></div>
  </div>
</template>
