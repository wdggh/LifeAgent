<template>
  <div class="app-shell">
    <AppSidebar />
    <main class="shell-main">
      <RouterView />
    </main>
  </div>
</template>

<script setup lang="ts">
import AppSidebar from './AppSidebar.vue'
</script>

<style scoped>
.app-shell {
  display: flex;
  min-height: 100vh;
  background: #f7f8fa;
}

.shell-main {
  flex: 1;
  min-width: 0;
  padding: 24px;
  box-sizing: border-box;
}
</style>
