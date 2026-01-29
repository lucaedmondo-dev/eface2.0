<template>
  <header class="topbar card d-flex align-items-center justify-content-between p-2">
    <div class="d-flex align-items-center gap-3">
      <div class="logo">EF</div>
      <div class="title">
        <div class="name">{{ title }}</div>
        <div class="subtitle muted">{{ subtitle }}</div>
      </div>
    </div>

    <div class="d-flex align-items-center gap-2">
      <select :value="selectedRoom" @change="onRoomChange($event)" class="form-select form-select-dark me-2">
        <option v-for="r in rooms" :key="r.id" :value="r.id">{{ r.name }}</option>
      </select>
      <button class="btn btn-sm btn-outline-light" @click="$emit('open-settings')">Impostazioni</button>
    </div>
  </header>
</template>

<script>
export default {
  props: { title: { type: String, default: 'e-face' }, subtitle: { type: String, default: 'Interfaccia' }, rooms: { type: Array, default: ()=>[] }, selectedRoom: String },
  emits: ['room-changed','open-settings'],
  methods: {
    onRoomChange(e) { const val = e.target ? e.target.value : e; this.$emit('room-changed', val) }
  }
}
</script>

<style scoped>
.topbar{ display:flex; align-items:center; justify-content:space-between; }
.logo{ width:48px;height:48px;border-radius:10px;background:linear-gradient(135deg,var(--primary),var(--accent));display:flex;align-items:center;justify-content:center;font-weight:700 }
.title .name{ font-weight:700 }
.subtitle{ font-size:12px }
</style>
