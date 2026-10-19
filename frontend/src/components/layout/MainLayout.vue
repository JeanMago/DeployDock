<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from 'vue';
import { RouterView, useRoute } from 'vue-router';
import { ChevronRight } from 'lucide-vue-next';
import AppSidebar from './AppSidebar.vue';
import AppTopbar from './AppTopbar.vue';
import CommandPalette from './CommandPalette.vue';

const DRAWER_WIDTH = 236;

const route = useRoute();
const desktopOpen = ref(true);
const mobileOpen = ref(false);
const paletteOpen = ref(false);

// Controle de gesto Touch + Pointer Drag no Celular (< 1024px)
const isSwiping = ref(false);
const mobileDragTranslate = ref<number | null>(null);
let startX = 0;
let startY = 0;
let gestureMode: 'none' | 'opening' | 'closing' = 'none';
let startedFromHorizontalScrollable = false;
let mouseDownActive = false;

// Fecha automaticamente o menu lateral no celular ao navegar para outra rota
watch(
  () => route.fullPath,
  () => {
    mobileOpen.value = false;
    mobileDragTranslate.value = null;
    isSwiping.value = false;
  }
);

const backdropOpacity = computed(() => {
  if (mobileDragTranslate.value !== null) {
    const progress = (DRAWER_WIDTH + mobileDragTranslate.value) / DRAWER_WIDTH;
    return Math.max(0, Math.min(0.75, progress * 0.75));
  }
  return mobileOpen.value ? 0.75 : 0;
});

const showBackdrop = computed(() => {
  return (
    mobileOpen.value ||
    (mobileDragTranslate.value !== null && mobileDragTranslate.value > -DRAWER_WIDTH)
  );
});

function hasHorizontalScrollParent(el: HTMLElement | null): boolean {
  let curr = el;
  while (curr && curr !== document.body) {
    const style = window.getComputedStyle(curr);
    if (
      (style.overflowX === 'auto' || style.overflowX === 'scroll') &&
      curr.scrollWidth > curr.clientWidth + 8
    ) {
      return true;
    }
    curr = curr.parentElement;
  }
  return false;
}

const beginGesture = (clientX: number, clientY: number, targetEl: HTMLElement | null, isMouse: boolean) => {
  if (window.innerWidth >= 1024) return;
  startX = clientX;
  startY = clientY;
  gestureMode = 'none';
  startedFromHorizontalScrollable = hasHorizontalScrollParent(targetEl);

  // Para mouse no modo responsivo ou toque próximo à borda esquerda (<= 56px)
  if (!mobileOpen.value && startX <= 56) {
    gestureMode = 'opening';
  } else if (mobileOpen.value && (!isMouse || startX <= DRAWER_WIDTH + 40)) {
    gestureMode = 'closing';
  }
};

const moveGesture = (clientX: number, clientY: number, isMouse: boolean) => {
  if (window.innerWidth >= 1024) return;
  const dx = clientX - startX;
  const dy = clientY - startY;

  // Permite iniciar arraste da esquerda para a direita em qualquer área da tela no touch (ou perto da borda no mouse)
  if (gestureMode === 'none' && !mobileOpen.value && !startedFromHorizontalScrollable) {
    if ((!isMouse || startX <= 120) && dx > 22 && Math.abs(dx) > Math.abs(dy) * 1.6) {
      gestureMode = 'opening';
      startX = clientX - 10;
    } else if (Math.abs(dy) > 18) {
      return;
    }
  }

  if (gestureMode === 'opening') {
    if (!isSwiping.value) {
      if (Math.abs(dy) > Math.abs(dx) && dx < 16) {
        gestureMode = 'none';
        return;
      }
      if (dx > 6) {
        isSwiping.value = true;
      }
    }
    if (isSwiping.value) {
      const clamped = Math.min(0, Math.max(-DRAWER_WIDTH, -DRAWER_WIDTH + dx));
      mobileDragTranslate.value = clamped;
    }
  } else if (gestureMode === 'closing') {
    if (!isSwiping.value) {
      if (dx < -10 && Math.abs(dx) > Math.abs(dy) * 1.25) {
        isSwiping.value = true;
      } else if (Math.abs(dy) > 20) {
        gestureMode = 'none';
        return;
      }
    }
    if (isSwiping.value) {
      const clamped = Math.min(0, Math.max(-DRAWER_WIDTH, dx));
      mobileDragTranslate.value = clamped;
    }
  }
};

const endGesture = () => {
  mouseDownActive = false;
  if (!isSwiping.value || mobileDragTranslate.value === null) {
    gestureMode = 'none';
    return;
  }

  const currentTranslate = mobileDragTranslate.value;
  if (gestureMode === 'opening') {
    mobileOpen.value = currentTranslate > -DRAWER_WIDTH * 0.72;
  } else if (gestureMode === 'closing') {
    mobileOpen.value = currentTranslate > -65;
  }

  isSwiping.value = false;
  mobileDragTranslate.value = null;
  gestureMode = 'none';
};

// Touch events (Celular/Tablet)
const onTouchStart = (e: TouchEvent) => {
  if (e.touches.length !== 1) return;
  beginGesture(e.touches[0].clientX, e.touches[0].clientY, e.target as HTMLElement | null, false);
};
const onTouchMove = (e: TouchEvent) => {
  if (e.touches.length !== 1) return;
  moveGesture(e.touches[0].clientX, e.touches[0].clientY, false);
};
const onTouchEnd = () => endGesture();

// Mouse drag events para testar o modo celular redimensionando o navegador no PC
const onMouseDown = (e: MouseEvent) => {
  if (window.innerWidth >= 1024 || e.button !== 0) return;
  mouseDownActive = true;
  beginGesture(e.clientX, e.clientY, e.target as HTMLElement | null, true);
};
const onMouseMove = (e: MouseEvent) => {
  if (!mouseDownActive) return;
  moveGesture(e.clientX, e.clientY, true);
};
const onMouseUp = () => {
  if (!mouseDownActive) return;
  endGesture();
};

const onKeydown = (e: KeyboardEvent) => {
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
    e.preventDefault();
    paletteOpen.value = !paletteOpen.value;
  } else if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'b') {
    e.preventDefault();
    desktopOpen.value = !desktopOpen.value;
  }
};

onMounted(() => {
  window.addEventListener('keydown', onKeydown);
  window.addEventListener('mouseup', onMouseUp);
});
onUnmounted(() => {
  window.removeEventListener('keydown', onKeydown);
  window.removeEventListener('mouseup', onMouseUp);
});
</script>

<template>
  <div
    class="flex h-screen w-screen bg-dock-bg text-dock-text overflow-hidden selection:bg-dock-accent/30 relative"
    @touchstart.passive="onTouchStart"
    @touchmove.passive="onTouchMove"
    @touchend.passive="onTouchEnd"
    @touchcancel.passive="onTouchEnd"
    @mousedown="onMouseDown"
    @mousemove="onMouseMove"
  >
    <!-- Alça interativa na borda esquerda do celular (suporta arrastar ou tocar) -->
    <button
      v-if="!mobileOpen && !isSwiping"
      @click="mobileOpen = true"
      class="lg:hidden fixed left-0 top-1/2 -translate-y-1/2 z-30 py-3 px-0.5 rounded-r-md bg-dock-panel/90 hover:bg-dock-accent border border-l-0 border-dock-border-light text-dock-text-muted hover:text-white shadow-lg transition-colors cursor-grab active:cursor-grabbing"
      title="Arraste para a direita ou toque para abrir o menu"
    >
      <ChevronRight class="w-3.5 h-3.5" />
    </button>

    <!-- Backdrop escuro proporcional ao arraste no celular -->
    <div
      v-if="showBackdrop"
      @click="mobileOpen = false"
      :style="{ opacity: backdropOpacity }"
      class="fixed inset-0 bg-black z-30 lg:hidden transition-opacity duration-150"
    ></div>

    <AppSidebar
      :is-open="desktopOpen"
      :mobile-open="mobileOpen"
      :mobile-drag-translate="mobileDragTranslate"
      :is-swiping="isSwiping"
      @toggle="desktopOpen = !desktopOpen"
      @close-mobile="mobileOpen = false"
      @open-palette="paletteOpen = true"
    />

    <div class="flex flex-col flex-1 min-w-0 h-full overflow-hidden">
      <AppTopbar
        @toggle-sidebar="mobileOpen = !mobileOpen"
        @open-palette="paletteOpen = true"
      />

      <main class="flex-1 overflow-y-auto overflow-x-hidden p-3 sm:p-5 lg:p-6 scroll-smooth">
        <div class="max-w-7xl mx-auto space-y-5 pb-8">
          <RouterView v-slot="{ Component }">
            <transition name="fade" mode="out-in">
              <component :is="Component" />
            </transition>
          </RouterView>
        </div>
      </main>
    </div>

    <!-- Command Palette Global (Ctrl+K) -->
    <CommandPalette :open="paletteOpen" @close="paletteOpen = false" />
  </div>
</template>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.15s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
