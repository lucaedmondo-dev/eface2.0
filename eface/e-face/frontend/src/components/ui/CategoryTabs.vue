<template>
  <div class="category-tabs d-flex gap-2">
    <button v-for="c in categories" :key="c" class="btn btn-sm" :class="{active: c===current}" @click="$emit('change', c)">{{ c }}</button>
  </div>
</template>

<script>
export default {
  props: { categories: { type: Array, default: ()=>['Lights','Media','Security','Comfort'] }, current: { type: String, default: 'Lights' } }
}
</script>

<style scoped>
.category-tabs .btn{ background:transparent; border:1px solid rgba(255,255,255,0.04); color:var(--text) }
.category-tabs .btn.active{ background: linear-gradient(90deg,var(--primary),var(--accent)); color:#041229 }
</style>
