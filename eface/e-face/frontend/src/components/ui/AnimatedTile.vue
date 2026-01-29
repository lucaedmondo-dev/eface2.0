<template>
  <div class="animated-tile card p-3" :class="{active: active}" @click="$emit('click')">
    <div class="icon">{{ icon }}</div>
    <div class="title">{{ title }}</div>
    <div class="subtitle muted">{{ subtitle }}</div>
  </div>
</template>

<script>
export default {
  props: { title: String, subtitle: String, icon: { type: String, default: '💡' }, active: { type: Boolean, default: false } }
}
</script>

<style scoped>
.animated-tile { transition: transform .14s ease, box-shadow .14s ease; cursor:pointer }
.animated-tile:hover { transform: translateY(-6px) }
.animated-tile.active { box-shadow:0 20px 40px rgba(0,0,0,0.35); transform: translateY(-8px) }
.animated-tile .icon{ font-size:28px }
.animated-tile .title{ font-weight:700;margin-top:6px }
</style>
