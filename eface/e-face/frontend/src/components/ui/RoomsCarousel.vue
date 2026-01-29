<template>
  <div class="rooms-carousel d-flex align-items-center">
    <div class="rooms-scroll" ref="scroll">
      <div v-for="r in rooms" :key="r.id" class="room-pill" :class="{active: r.id===selected}" @click="select(r.id)">
        {{ r.name }}
      </div>
    </div>
  </div>
</template>

<script>
export default {
  props: { rooms: { type: Array, default: ()=>[] }, selected: String },
  emits: ['select'],
  methods: {
    select(id) { this.$emit('select', id) }
  }
}
</script>

<style scoped>
.rooms-carousel { overflow:hidden; padding:8px 0 }
.rooms-scroll { display:flex; gap:8px; overflow-x:auto; padding-bottom:6px }
.room-pill { padding:8px 12px; background:rgba(255,255,255,0.02); border-radius:999px; cursor:pointer; white-space:nowrap }
.room-pill.active { background: linear-gradient(90deg,var(--primary),var(--accent)); color:#041229 }
</style>
