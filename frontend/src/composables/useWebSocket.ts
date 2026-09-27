import { ref, onMounted, onUnmounted } from 'vue';

export function useWebSocket(url: string, onMessage?: (data: any) => void) {
  const ws = ref<WebSocket | null>(null);
  const status = ref<'connecting' | 'open' | 'closed' | 'error'>('closed');
  let reconnectTimer: any = null;
  let attempt = 0;

  const connect = () => {
    if (ws.value?.readyState === WebSocket.OPEN) return;
    
    status.value = 'connecting';
    const wsUrl = new URL(url, window.location.origin.replace(/^http/, 'ws')).toString();
    ws.value = new WebSocket(wsUrl);

    ws.value.onopen = () => {
      status.value = 'open';
      attempt = 0;
    };

    ws.value.onmessage = (event) => {
      if (onMessage) {
        try {
          const data = JSON.parse(event.data);
          onMessage(data);
        } catch (e) {
          onMessage(event.data);
        }
      }
    };

    ws.value.onclose = () => {
      status.value = 'closed';
      reconnect();
    };

    ws.value.onerror = () => {
      status.value = 'error';
    };
  };

  const reconnect = () => {
    attempt++;
    const delay = Math.min(1000 * (2 ** attempt), 30000);
    reconnectTimer = setTimeout(connect, delay);
  };

  const send = (data: any) => {
    if (ws.value?.readyState === WebSocket.OPEN) {
      ws.value.send(typeof data === 'string' ? data : JSON.stringify(data));
    }
  };

  const disconnect = () => {
    clearTimeout(reconnectTimer);
    if (ws.value) {
      ws.value.close();
      ws.value = null;
    }
  };

  onMounted(() => connect());
  onUnmounted(() => disconnect());

  return { ws, status, send, disconnect, connect };
}
