// @vitest-environment jsdom
import { describe, it, expect, beforeEach, vi } from 'vitest';

// useWebSocket usa onMounted/onUnmounted; neutralizamos para testar a lógica isoladamente.
vi.mock('vue', async () => {
  const actual = await vi.importActual<typeof import('vue')>('vue');
  return { ...actual, onMounted: () => {}, onUnmounted: () => {} };
});

import { useWebSocket } from './useWebSocket';

class FakeWebSocket {
  static OPEN = 1;
  static instances: FakeWebSocket[] = [];
  readyState = 0;
  onopen: (() => void) | null = null;
  onclose: (() => void) | null = null;
  onerror: (() => void) | null = null;
  onmessage: ((e: { data: string }) => void) | null = null;
  constructor(public url: string) {
    FakeWebSocket.instances.push(this);
  }
  send = vi.fn();
  close = vi.fn();
}

describe('useWebSocket', () => {
  beforeEach(() => {
    FakeWebSocket.instances = [];
    localStorage.clear();
    vi.stubGlobal('WebSocket', FakeWebSocket);
  });

  it('envia o JWT salvo como query string (backend exige autenticação nos WebSockets)', () => {
    localStorage.setItem('deploydock_token', 'abc.def.ghi');
    const { connect } = useWebSocket('/ws/containers/x/logs');
    connect();
    const url = new URL(FakeWebSocket.instances[0].url);
    expect(url.pathname).toBe('/ws/containers/x/logs');
    expect(url.searchParams.get('token')).toBe('abc.def.ghi');
  });

  it('não adiciona token quando o usuário não está autenticado', () => {
    const { connect } = useWebSocket('/ws/containers/x/logs');
    connect();
    expect(new URL(FakeWebSocket.instances[0].url).searchParams.has('token')).toBe(false);
  });

  it('entrega mensagens JSON já decodificadas ao callback', () => {
    const onMessage = vi.fn();
    const { connect } = useWebSocket('/ws/x', onMessage);
    connect();
    FakeWebSocket.instances[0].onmessage?.({ data: '{"type":"log","data":"ok"}' });
    expect(onMessage).toHaveBeenCalledWith({ type: 'log', data: 'ok' });
  });
});
