<script setup lang="ts">
import { ref } from 'vue';
import { RouterView } from 'vue-router';
import AppSidebar from './AppSidebar.vue';
import AppTopbar from './AppTopbar.vue';

const sidebarOpen = ref(true);
</script>

<template>
  <div class="flex h-screen bg-dock-bg text-dock-text overflow-hidden selection:bg-dock-accent/30">
    <AppSidebar :is-open="sidebarOpen" @toggle="sidebarOpen = !sidebarOpen" />
    
    <div class="flex flex-col flex-1 min-w-0">
      <AppTopbar @toggle-sidebar="sidebarOpen = !sidebarOpen" />
      
      <main class="flex-1 overflow-auto p-6 scroll-smooth">
        <div class="max-w-7xl mx-auto space-y-6">
          <RouterView v-slot="{ Component }">
            <transition name="fade" mode="out-in">
              <component :is="Component" />
            </transition>
          </RouterView>
        </div>
      </main>
    </div>
  </div>
</template>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
  transform: translateY(4px);
}
</style>
