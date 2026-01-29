<template>
  <div class="wireframe">
    <div class="header card p-3 mb-3">
      <div class="d-flex justify-content-between align-items-center">
        <div><div class="logo">EF</div></div>
        <div>
          <button class="btn btn-sm btn-outline-light">Impostazioni</button>
        </div>
      </div>
    </div>

    <div class="rooms mb-3">
      <div class="room-big card p-3">Stanza selezionata: <strong>Living</strong></div>
    </div>

    <div class="tiles-grid">
      <div class="tile card">Large tile preview</div>
      <div class="tile card">Tile 2</div>
      <div class="tile card">Tile 3</div>
    </div>
  </div>
</template>

<script>
export default { name: 'Wireframe' }
</script>

<style scoped>
.wireframe .logo{ width:42px;height:42px;border-radius:8px;background:linear-gradient(135deg,var(--primary),var(--accent));display:flex;align-items:center;justify-content:center}
.rooms .room-big{ height:160px }
.tiles-grid{ display:grid; grid-template-columns: repeat(3,1fr); gap:12px }
.tile{ height:120px }
@media (max-width:800px){ .tiles-grid{ grid-template-columns: repeat(2,1fr) } }
</style>
