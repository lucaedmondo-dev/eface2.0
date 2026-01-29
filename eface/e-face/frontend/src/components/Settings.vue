<template>
  <div class="settings-grid">
    <div class="settings-toolbar">
      <button type="button" class="ghost-btn" @click="$emit('back')">
        <span aria-hidden="true">←</span>
        Torna alla dashboard
      </button>
      <p class="token-help">
        Le immagini personalizzate vanno in <code>src/assets/room-backgrounds</code>. Sono condivise tra tutti gli utenti.
      </p>
    </div>
    <section class="settings-card">
      <div class="card-header">
        <p class="eyebrow">Personalizzazione</p>
        <h2>Look & Feel</h2>
        <p class="muted">{{ personalizationSubtitle }}</p>
      </div>
      <div class="form-grid">
        <label class="form-field">
          <span>Nome interfaccia</span>
          <input v-model="siteName" class="form-control form-control-dark" />
        </label>
        <label class="form-field">
          <span>Colore primario</span>
          <input type="color" v-model="theme.primary" class="color-chip" />
        </label>
        <label class="form-field">
          <span>Colore accento</span>
          <input type="color" v-model="theme.accent" class="color-chip" />
        </label>
        <label class="form-field">
          <span>Background</span>
          <input type="color" v-model="theme.bg" class="color-chip" />
        </label>
      </div>
      <div class="form-grid">
        <label class="form-field">
          <span>Testo</span>
          <input type="color" v-model="theme.text" class="color-chip" />
        </label>
        <label class="form-field">
          <span>Superficie</span>
          <input type="color" v-model="theme.surface" class="color-chip" />
        </label>
      </div>
      <button class="btn btn-primary" @click="savePersonalization">Salva personalizzazione</button>
      <p class="feedback" v-if="message">{{ message }}</p>
    </section>

    <section class="settings-card">
      <div class="card-header">
        <p class="eyebrow">Stanze</p>
        <h3>Sfondo personalizzato</h3>
        <p class="muted">Scegli una scena dalla libreria per aggiornare l'aspetto condiviso.</p>
      </div>
      <div class="form-grid">
        <label class="form-field">
          <span>Stanza</span>
          <select v-model="selectedRoom" class="form-select form-select-dark">
            <option v-for="r in rooms" :key="r.id" :value="r.id">{{ r.name }}</option>
          </select>
        </label>
      </div>
      <div class="background-library" v-if="backgroundLibrary.length">
        <button
          v-for="option in backgroundLibrary"
          :key="option.id"
          class="background-option"
          :class="{ selected: option.id === selectedBackgroundId }"
          type="button"
          @click="selectBackground(option)"
        >
          <div class="background-thumb" :style="{ backgroundImage: cssBackground(option.url) }"></div>
          <div class="background-copy">
            <strong>{{ option.label }}</strong>
            <small>Applicato a tutti gli utenti</small>
          </div>
        </button>
      </div>
      <p v-else class="token-help">Aggiungi immagini in <code>src/assets/room-backgrounds</code> per popolare la libreria.</p>
      <div class="background-preview" v-if="roomBackground" :style="{ backgroundImage: cssBackground(roomBackground) }"></div>
      <p class="token-help">Suggerito: JPG/WEBP 1920×1080 o superiore, peso &lt; 600 KB.</p>
      <button class="btn btn-outline-light" @click="setRoomBackground">Applica sfondo</button>
    </section>

    <section class="settings-card" v-if="isAdmin">
      <div class="card-header">
        <p class="eyebrow">Integrazione</p>
        <h3>Home Assistant</h3>
        <p class="muted">Configura la connessione diretta e monitora lo stato.</p>
      </div>
      <div class="form-grid">
        <label class="form-field">
          <span>Host</span>
          <input v-model="integration.host" class="form-control form-control-dark" placeholder="http://ha.local:8123" />
        </label>
        <label class="form-field">
          <span>Token long-lived</span>
          <input v-model="integration.token" class="form-control form-control-dark" placeholder="LLAT" />
        </label>
      </div>
      <label class="form-field">
        <span>Host remoto (opzionale)</span>
        <input v-model="integration.remote_host" class="form-control form-control-dark" placeholder="https://ha.example.com:8443" />
        <small class="token-help">Usato solo per le connessioni dirette dei tablet fuori rete locale.</small>
      </label>
      <label class="form-field">
        <span>Entità extra (una per riga)</span>
        <textarea v-model="integration.extra_entities_text" rows="2" class="form-control form-control-dark" placeholder="light.giardino\nlight.portico"></textarea>
        <small class="token-help">Usato per includere dispositivi senza stanza (es. luci esterne).</small>
      </label>
      <div class="form-check form-switch">
        <input class="form-check-input" type="checkbox" v-model="integration.enabled" id="integrationEnabled">
        <label class="form-check-label" for="integrationEnabled">Abilita integrazione</label>
      </div>
      <div class="button-row">
        <button class="btn btn-primary" @click="saveIntegration">Salva</button>
        <button class="btn btn-outline-light" @click="testIntegration">Test</button>
        <button class="btn btn-warning" :disabled="refreshing" @click="refreshConfiguration">{{ refreshing ? 'Aggiornamento…' : 'Rigenera configurazione' }}</button>
      </div>
      <p class="token-help">Crea un token in Home Assistant: Profilo → Long-Lived Access Tokens.</p>
      <div v-if="integrationTest" class="mt-2">
        <div v-if="integrationTest.ok" class="text-success">Integrazione OK — {{ integrationTest.rooms }} stanze</div>
        <div v-else class="text-danger">Test fallito: {{ integrationTest.error }}</div>
      </div>
      <div class="diag-box" v-if="diagnostics">
        <div class="diag-row">
          <span>Integration</span>
          <strong>{{ diagnostics.integration.enabled ? 'Attiva' : 'Disattiva' }}</strong>
        </div>
        <div class="diag-row">
          <span>Host</span>
          <strong>{{ diagnostics.integration.host || '—' }}</strong>
        </div>
        <div class="diag-row" v-if="diagnostics.integration.remote_host">
          <span>Host remoto</span>
          <strong>{{ diagnostics.integration.remote_host }}</strong>
        </div>
        <div class="diag-row">
          <span>WS clients</span>
          <strong>{{ diagnostics.ha_ws.ws_clients }}</strong>
        </div>
        <div class="diag-row">
          <span>Eventi recenti</span>
          <strong>{{ diagnostics.ha_ws.recent_events_count }}</strong>
        </div>
        <div class="diag-row" v-if="diagnostics.ha_ws.last_event">
          <span>Ultimo evento</span>
          <small>{{ diagnostics.ha_ws.last_event.event_type || diagnostics.ha_ws.last_event.entity_id }}</small>
        </div>
        <div class="diag-row" v-else-if="lastEvent">
          <span>Ultimo evento (live)</span>
          <small>{{ lastEvent.entity_id || lastEvent.event_type || JSON.stringify(lastEvent) }}</small>
        </div>
        <div class="diag-row" v-if="diagnostics && diagnostics.ping_ms">
          <span>Ping</span>
          <strong>{{ diagnostics.ping_ms }} ms</strong>
        </div>
        <div class="diag-row" v-if="diagnostics && diagnostics.last_error">
          <span>Ultimo errore</span>
          <small>{{ diagnostics.last_error }}</small>
        </div>
        <div class="button-row small">
          <button class="btn btn-sm btn-outline-light" @click="loadEvents">Cronologia eventi</button>
          <button class="btn btn-sm btn-outline-light" @click="clearEvents">Svuota cronologia</button>
        </div>
        <div v-if="events && events.length" class="event-log">
          <div v-for="e in events" :key="e.ts" class="small muted">{{ new Date(e.ts*1000).toLocaleString() }} — <code>{{ e.event.entity_id || e.event.event_type || JSON.stringify(e.event) }}</code></div>
        </div>
      </div>
    </section>

    <section class="settings-card" v-if="isAdmin">
      <div class="card-header">
        <p class="eyebrow">Utenti</p>
        <h3>Gestione account</h3>
      </div>
      <AdminUsers />
    </section>
  </div>
</template>

<script>
import axios from 'axios'
import AdminUsers from './AdminUsers.vue'
import { getBackgroundLibrary } from '../utils/backgroundLibrary'

export default {
  components: { AdminUsers },
  props: {
    isAdmin: { type: Boolean, default: false }
  },
  data() {
    return {
      siteName: '',
      message: '',
      theme: { primary: '#6c8cff', accent: '#22c1c3', surface: '#141625', bg: '#0f1221', text: '#e6eef8' },
      rooms: [],
      selectedRoom: null,
      roomBackground: '',
      backgroundLibrary: [],
      selectedBackgroundId: '',
      advancedObj: {},
      integration: { host: '', remote_host: '', token: '', enabled: false, extra_entities_text: '' },
      integrationTest: null,
      diagnostics: null,
      lastEvent: null,
      events: [],
      refreshing: false
    }
  },
  created() {
    this.fetch()
    this._haListener = (e) => { this.lastEvent = e.detail }
    window.addEventListener('ha_event', this._haListener)
  },
  beforeUnmount() {
    try { window.removeEventListener('ha_event', this._haListener) } catch (_) {}
  },
  computed: {
    personalizationSubtitle() {
      return this.isAdmin ? 'Aggiorna lo stile globale per tutti gli utenti.' : 'Modifica l’aspetto senza accedere alle impostazioni di sistema.'
    }
  },
  watch: {
    selectedRoom() {
      this.syncSelectedRoomBackground()
    }
  },
  methods: {
    async fetch() {
      try {
        const res = await axios.get('/api/config')
        this.siteName = res.data.site_name
        const adv = res.data.advanced || {}
        this.advancedObj = { ...adv }
        const incomingTheme = adv.theme || {}
        this.theme = { ...this.theme, ...incomingTheme }
        this.applyTheme(this.theme)
      } catch (e) {
        this.message = 'Impossibile caricare la configurazione'
      }
      try {
        const rr = await axios.get('/api/rooms')
        this.rooms = rr.data.rooms || []
        if (!this.selectedRoom && this.rooms.length) {
          this.selectedRoom = this.rooms[0].id
        }
        this.syncSelectedRoomBackground()
      } catch (_) {}

      this.backgroundLibrary = getBackgroundLibrary()
      this.syncBackgroundSelection()

      if (this.isAdmin) {
        try {
          const adminRes = await axios.get('/api/admin')
          const adv = adminRes.data.advanced || {}
          const integration = adv.integration || {}
          const extras = Array.isArray(integration.extra_entities) ? integration.extra_entities : []
          this.integration = {
            host: integration.host || '',
            remote_host: integration.remote_host || '',
            token: integration.token || '',
            enabled: integration.enabled === true,
            extra_entities_text: extras.join('\n')
          }
        } catch (_) {}

        try {
          const dres = await axios.get('/api/admin/diagnostics')
          this.diagnostics = dres.data
          if (dres.data.ha_ws && dres.data.ha_ws.last_event) this.lastEvent = dres.data.ha_ws.last_event
        } catch (_) {}
      }
    },
    syncSelectedRoomBackground() {
      if (!Array.isArray(this.rooms)) return
      const room = this.rooms.find((r) => r.id === this.selectedRoom)
      this.roomBackground = room?.background || ''
      this.syncBackgroundSelection()
    },
    syncBackgroundSelection() {
      if (!this.roomBackground) {
        this.selectedBackgroundId = ''
        return
      }
      const match = this.backgroundLibrary.find((item) => item.url === this.roomBackground)
      this.selectedBackgroundId = match ? match.id : ''
    },
    selectBackground(option) {
      this.selectedBackgroundId = option.id
      this.roomBackground = option.url
    },
    applyTheme(theme) {
      try {
        if (theme.primary) document.documentElement.style.setProperty('--primary', theme.primary)
        if (theme.accent) document.documentElement.style.setProperty('--accent', theme.accent)
        if (theme.bg) document.documentElement.style.setProperty('--bg', theme.bg)
        if (theme.surface) document.documentElement.style.setProperty('--surface', theme.surface)
        if (theme.text) document.documentElement.style.setProperty('--text', theme.text)
      } catch (_) {}
    },
    sanitizeCssUrl(value) {
      if (!value) return ''
      return String(value)
        .replace(/"/g, '\\"')
        .replace(/\n|\r/g, '')
        .trim()
    },
    cssBackground(value) {
      const sanitized = this.sanitizeCssUrl(value)
      return sanitized ? `url("${sanitized}")` : ''
    },
    async savePersonalization() {
      try {
        const updatedAdvanced = { ...this.advancedObj, theme: { ...this.theme } }
        await axios.post('/api/config', { site_name: this.siteName, advanced: updatedAdvanced })
        this.advancedObj = updatedAdvanced
        this.applyTheme(this.theme)
        this.message = 'Personalizzazione salvata'
      } catch (e) {
        this.message = 'Salvataggio fallito: ' + (e?.message || e)
      }
    },
    async setRoomBackground() {
      if (!this.selectedRoom) { this.message = 'Seleziona una stanza'; return }
      if (!this.selectedBackgroundId) {
        this.message = 'Scegli un’immagine dalla libreria'
        return
      }
      try {
        await axios.post(`/api/admin/rooms/${this.selectedRoom}/background`, { background: this.roomBackground })
        this.message = 'Sfondo aggiornato'
        this.$emit('refresh-room')
      } catch (e) {
        this.message = 'Impossibile impostare lo sfondo: ' + (e?.message || e)
      }
    },
    async testIntegration() {
      if (!this.isAdmin) { this.message = 'Permessi insufficienti'; return }
      this.integrationTest = null
      try {
        const payload = { integration: { host: this.integration.host, remote_host: this.integration.remote_host, token: this.integration.token, enabled: !!this.integration.enabled } }
        payload.integration.extra_entities = (this.integration.extra_entities_text || '')
          .split(/[\n,]/)
          .map(s => s.trim())
          .filter(Boolean)
        const res = await axios.post('/api/admin/test-integration', payload)
        this.integrationTest = { ok: true, rooms: res.data.rooms.length }
        this.message = 'Integrazione raggiungibile'
      } catch (e) {
        const detail = e.response?.data?.detail || e.message
        this.integrationTest = { ok: false, error: detail }
        this.message = 'Test integrazione fallito: ' + detail
      }
    },
    async saveIntegration() {
      if (!this.isAdmin) { this.message = 'Permessi insufficienti'; return }
      try {
        const payload = { integration: { host: this.integration.host, remote_host: this.integration.remote_host, token: this.integration.token, enabled: !!this.integration.enabled } }
        payload.integration.extra_entities = (this.integration.extra_entities_text || '')
          .split(/[\n,]/)
          .map(s => s.trim())
          .filter(Boolean)
        await axios.post('/api/admin', { integration: payload.integration })
        this.message = 'Integrazione salvata'
        try { const dres = await axios.get('/api/admin/diagnostics'); this.diagnostics = dres.data } catch (_) {}
      } catch (e) {
        this.message = 'Impossibile salvare: ' + (e.response?.data?.detail || e?.message || e)
      }
    },
    async loadEvents() {
      if (!this.isAdmin) { this.message = 'Permessi insufficienti'; return }
      try {
        const res = await axios.get('/api/admin/events')
        this.events = res.data.events || []
      } catch (e) {
        this.message = 'Impossibile caricare gli eventi: ' + (e?.message || e)
      }
    },
    async clearEvents() {
      if (!this.isAdmin) { this.message = 'Permessi insufficienti'; return }
      try {
        await axios.post('/api/admin/clear-events')
        this.events = []
        this.message = 'Cronologia svuotata'
      } catch (e) {
        this.message = 'Impossibile svuotare: ' + (e?.message || e)
      }
    },
    async refreshConfiguration() {
      if (!this.isAdmin) { this.message = 'Permessi insufficienti'; return }
      this.refreshing = true
      try {
        const res = await axios.post('/api/admin/refresh')
        const roomsCount = res.data?.rooms_count ?? (res.data?.rooms || []).length
        const entitiesCount = res.data?.entities_count ?? 0
        this.message = `Configurazione aggiornata: ${roomsCount} stanze, ${entitiesCount} entità`
        await this.fetch()
      } catch (e) {
        this.message = 'Aggiornamento fallito: ' + (e.response?.data?.detail || e?.message || e)
      } finally {
        this.refreshing = false
      }
    }
  }
}
</script>

<style scoped>
.settings-grid { display: grid; gap: 24px; }
.settings-toolbar { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 12px; padding: 0 4px; }
.ghost-btn { border-radius: 14px; border: 1px solid rgba(255,255,255,0.18); background: transparent; color: var(--text); padding: 8px 14px; display: inline-flex; align-items: center; gap: 8px; cursor: pointer; transition: background var(--transition-fast), border var(--transition-fast), box-shadow var(--transition-base), transform var(--transition-fast); }
.ghost-btn:hover { background: rgba(255,255,255,0.08); transform: translateY(-2px); box-shadow: 0 12px 26px rgba(0,0,0,0.35); }
.ghost-btn:active { transform: translateY(0) scale(0.97); }
.ghost-btn:focus-visible { outline: 2px solid var(--primary); outline-offset: 2px; }
.settings-card { background: var(--surface); border: 1px solid rgba(255,255,255,0.05); border-radius: 16px; padding: 20px; box-shadow: 0 20px 60px rgba(0,0,0,0.25); transition: transform var(--transition-base), box-shadow var(--transition-base); animation: float-in 520ms cubic-bezier(0.22,1,0.36,1); }
.settings-card:hover { transform: translateY(-4px); box-shadow: 0 30px 70px rgba(0,0,0,0.35); }
.card-header { margin-bottom: 16px; }
.eyebrow { text-transform: uppercase; letter-spacing: 0.08em; font-size: 11px; color: var(--muted); margin-bottom: 4px; }
.form-grid { display: grid; gap: 16px; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); margin-bottom: 16px; }
.form-field { display: flex; flex-direction: column; gap: 6px; font-size: 14px; color: var(--muted); }
.color-chip { width: 100%; min-height: 44px; border-radius: 12px; border: 1px solid rgba(255,255,255,0.1); background: transparent; cursor: pointer; transition: border var(--transition-fast), background var(--transition-fast), transform var(--transition-fast); }
.color-chip:hover { border-color: rgba(255,255,255,0.25); background: rgba(255,255,255,0.04); transform: translateY(-1px); }
.background-library { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 12px; margin-bottom: 16px; }
.background-option { border: 1px solid rgba(255,255,255,0.08); border-radius: 14px; padding: 10px; display: flex; gap: 12px; align-items: center; background: rgba(255,255,255,0.02); cursor: pointer; transition: border var(--transition-fast), background var(--transition-fast), transform var(--transition-fast), box-shadow var(--transition-base); }
.background-option.selected { border-color: var(--primary); background: rgba(108,140,255,0.12); }
.background-option:hover { border-color: rgba(255,255,255,0.15); background: rgba(255,255,255,0.06); transform: translateY(-2px); box-shadow: 0 16px 34px rgba(0,0,0,0.35); }
.background-thumb { width: 64px; height: 48px; border-radius: 10px; background-size: cover; background-position: center; border: 1px solid rgba(255,255,255,0.08); }
.background-copy { display: flex; flex-direction: column; gap: 4px; text-align: left; }
.background-preview { width: 100%; height: 150px; border-radius: 16px; border: 1px solid rgba(255,255,255,0.08); background-size: cover; background-position: center; margin-bottom: 12px; }
.button-row { display: flex; flex-wrap: wrap; gap: 12px; margin: 16px 0; }
.button-row.small { gap: 8px; margin-top: 12px; }
.feedback { margin-top: 12px; font-size: 14px; color: var(--muted); }
.token-help { font-size: 13px; color: var(--muted); margin-top: 4px; display: block; }
.diag-box { margin-top: 16px; padding: 16px; border-radius: 12px; background: rgba(255,255,255,0.02); display: flex; flex-direction: column; gap: 8px; }
.diag-row { display: flex; justify-content: space-between; gap: 12px; font-size: 14px; }
.event-log { max-height: 160px; overflow-y: auto; margin-top: 8px; }
</style>
