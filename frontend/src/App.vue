<script setup lang="ts">
import { RouterView } from 'vue-router'
</script>

<template>
  <div class="app-shell">
    <header class="site-header">
      <RouterLink class="brand" to="/">
        <span class="brand-mark">TP</span>
        <span>
          <strong>TripPilot</strong>
          <small>AI travel studio</small>
        </span>
      </RouterLink>
      <span class="header-note">真实地点 · 智能规划 · 清晰预算</span>
    </header>

    <main>
      <RouterView />
    </main>
  </div>
</template>

