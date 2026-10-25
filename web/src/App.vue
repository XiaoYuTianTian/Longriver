<template>
  <div class="shell">
    <header class="topbar">
      <router-link class="brand" to="/">Longriver</router-link>
      <nav class="tabs">
        <router-link to="/">图</router-link>
        <router-link to="/browse">览</router-link>
        <router-link to="/mine">我的</router-link>
      </nav>
    </header>
    <router-view />
  </div>
</template>

<script setup lang="ts">
</script>
