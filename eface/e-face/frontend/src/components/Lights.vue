<template>
  <div>
    <div class="d-flex justify-content-between align-items-center mb-3">
      <h2 class="mb-0">Luci</h2>
      <div>
        <button class="btn btn-sm btn-outline-light" @click="$emit('open-settings')">Impostazioni</button>
      </div>
    </div>

    <div v-if="!lights || lights.length===0" class="muted">Nessuna luce trovata.</div>

    <div v-else class="device-grid">
      <div v-for="light in lights" :key="light.id" class="light-card card p-3" :class="{active: isOn(light)}" @click="openColorPanel(light)">
        <div class="d-flex justify-content-between align-items-center gap-2">
          <div>
            <div class="device-name">{{ light.name }}</div>
            <div class="muted small">Stato: <strong>{{ isOn(light) ? 'Accesa' : 'Spenta' }}</strong></div>
          </div>
          <div class="btn-group">
            <button class="btn btn-sm btn-success" :disabled="isOn(light)" @click.stop="turnOn(light)">Accendi</button>
            <button class="btn btn-sm btn-outline-light ms-2" :disabled="!isOn(light)" @click.stop="turnOff(light)">Spegni</button>
          </div>
        </div>
        <div class="muted tiny mt-2">Tocca per regolare colore e luminosità</div>
      </div>
    </div>

    <div v-if="showColorPanel && selectedLight" class="light-panel-overlay" @click.self="closeColorPanel">
      <div class="light-panel card p-4">
        <div class="d-flex justify-content-between align-items-start mb-3">
          <div>
            <h5 class="mb-1">{{ selectedLight.name }}</h5>
            <div class="muted small">{{ isOn(selectedLight) ? 'Accesa' : 'Spenta' }}</div>
          </div>
          <button class="btn-close" @click="closeColorPanel" aria-label="Chiudi">&times;</button>
        </div>
        <div class="mb-3">
          <label class="form-label small">Colore</label>
          <input type="color" v-model="colorHex" class="form-control form-control-color" />
        </div>
        <div class="mb-3">
          <label class="form-label small">Luminosità: {{ Math.round((panelBrightness/255)*100) }}%</label>
          <input type="range" min="0" max="255" v-model.number="panelBrightness" class="form-range" />
        </div>
        <div class="d-flex flex-wrap justify-content-between gap-3">
          <div class="btn-group">
            <button class="btn btn-sm btn-success" @click="turnOn(selectedLight, panelBrightness)">Accendi</button>
            <button class="btn btn-sm btn-outline-light" @click="turnOff(selectedLight)">Spegni</button>
          </div>
          <div class="d-flex gap-2 flex-wrap">
            <button class="btn btn-outline-light" @click="applyBrightness">Aggiorna luminosità</button>
            <button class="btn btn-primary" :disabled="!colorHexValid" @click="applyColor">Applica colore</button>
          </div>
        </div>
        <div v-if="panelError" class="text-danger small mt-3">{{ panelError }}</div>
        <div v-if="panelMessage" class="text-success small mt-2">{{ panelMessage }}</div>
      </div>
    </div>

    <p v-if="message" class="mt-2">{{ message }}</p>
  </div>
</template>

<script>
import axios from 'axios'
import { callLightService, extractBrightness, extractRgb, rgbToHex, hexToRgb, normalizeBrightness, isValidHexColor } from '../utils/lightControl'

export default {
  props: { devices: { type: Array, required: false } },
  data() {
    return {
      lights: this.devices || [],
      message: '',
      showColorPanel: false,
      selectedLight: null,
      panelBrightness: 0,
      colorHex: '#ffffff',
      panelMessage: '',
      panelError: ''
    }
  },
  computed: {
    colorHexValid() {
      return isValidHexColor(this.colorHex)
    }
  },
  watch: {
    devices(v) {
      this.lights = v || []
      this.syncPanelState()
    }
  },
  created() {
    if (!this.devices) this.fetch()
  },
  methods: {
    isOn(light) {
      return light && (light.state === 'on' || light.state === true)
    },
    syncPanelState() {
      if (!this.showColorPanel || !this.selectedLight) return
      const updated = (this.lights || []).find(l => l.id === this.selectedLight.id)
      if (!updated) return
      this.selectedLight = updated
      this.panelBrightness = extractBrightness(updated)
      const rgb = extractRgb(updated)
      if (rgb) this.colorHex = rgbToHex(rgb)
    },
    async fetch() {
      try {
        const res = await axios.get('/api/devices')
        this.lights = res.data.devices || []
      } catch (e) {
        this.message = 'Impossibile caricare le luci'
      }
    },
    async turnOn(light, brightnessOverride) {
      if (!light) return
      try {
        const payload = {}
        if (typeof brightnessOverride === 'number') payload.brightness = normalizeBrightness(brightnessOverride)
        await callLightService(light, 'turn_on', payload)
        this.message = ''
        this.$emit('refresh-room')
      } catch (e) {
        this.message = 'Impossibile accendere la luce'
      }
    },
    async turnOff(light) {
      if (!light) return
      try {
        await callLightService(light, 'turn_off')
        this.message = ''
        this.$emit('refresh-room')
      } catch (e) {
        this.message = 'Impossibile spegnere la luce'
      }
    },
    openColorPanel(light) {
      if (!light) return
      this.selectedLight = light
      this.panelBrightness = extractBrightness(light)
      const rgb = extractRgb(light)
      this.colorHex = rgb ? rgbToHex(rgb) : '#ffffff'
      this.panelError = ''
      this.panelMessage = ''
      this.showColorPanel = true
    },
    closeColorPanel() {
      this.showColorPanel = false
      this.selectedLight = null
    },
    async applyColor() {
      if (!this.selectedLight) return
      const rgb = hexToRgb(this.colorHex)
      if (!rgb) {
        this.panelError = 'Colore non valido'
        return
      }
      try {
        await callLightService(this.selectedLight, 'color', { rgb_color: rgb, brightness: normalizeBrightness(this.panelBrightness) })
        this.panelMessage = 'Colore aggiornato'
        this.panelError = ''
        this.$emit('refresh-room')
      } catch (e) {
        this.panelError = 'Impossibile aggiornare il colore'
        this.panelMessage = ''
      }
    },
    async applyBrightness() {
      if (!this.selectedLight) return
      try {
        await callLightService(this.selectedLight, 'turn_on', { brightness: normalizeBrightness(this.panelBrightness) })
        this.panelMessage = 'Luminosità aggiornata'
        this.panelError = ''
        this.$emit('refresh-room')
      } catch (e) {
        this.panelError = 'Impossibile aggiornare la luminosità'
        this.panelMessage = ''
      }
    }
  }
}
</script>

<style scoped>
.device-grid { display:grid; grid-template-columns: repeat(auto-fill, minmax(220px,1fr)); gap:12px }
.light-card { transition: transform .14s ease, box-shadow .14s ease; cursor:pointer }
.light-card:hover { transform: translateY(-4px) }
.light-card.active { box-shadow:0 0 20px rgba(255,255,255,0.08) }
.device-name{font-weight:700}
.light-panel-overlay { position:fixed; inset:0; background:rgba(0,0,0,0.7); display:flex; align-items:center; justify-content:center; padding:16px; z-index:2000 }
.light-panel { max-width:420px; width:100% }
.btn-close { background:none; border:0; font-size:1.4rem; color:#fff; line-height:1; cursor:pointer }
.tiny { font-size:11px }
</style>
