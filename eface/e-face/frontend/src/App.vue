<template>
  <div class="app-wrapper">
    <div class="app-shell">
      <template v-if="view !== 'login'">
      <div v-if="integrationError" class="alert alert-warning" role="alert">
        <template v-if="isAdmin">
          <strong>Attenzione installatore:</strong> la configurazione non è completa. Controlla le impostazioni avanzate.
          <div class="small muted mt-1">Dettaglio: {{ integrationError }}</div>
        </template>
        <template v-else>
          Errore nella configurazione del sistema, rivolgiti al tuo installatore.
        </template>
      </div>
      <main class="main-area">
        <Dashboard
          v-if="view === 'dashboard'"
          :devices="roomDevices"
          :security-devices="securityDevices"
          :roomName="(rooms.find(r=>r.id===currentRoom)||{}).name"
          :rooms="rooms"
          :current-room="currentRoom"
          :is-admin="isAdmin"
          :conn-mode="haConnectionMode"
          :ha-connected="haDirectConnected"
          :backend-connected="backendWsConnected"
          :weather="weatherSnapshot"
          @open-settings="openSettings"
          @must_change="onMustChange"
          @refresh-room="loadRoom(currentRoom)"
          @trigger-refresh="loadRoom(currentRoom)"
          @room-selected="onRoomSelected"
        />
        <div v-else class="card surface-panel">
          <component
            :is="currentView"
            :devices="roomDevices"
            :roomName="(rooms.find(r=>r.id===currentRoom)||{}).name"
            :is-admin="isAdmin"
            :current-room-id="currentRoom"
            @logged="onLogged"
            @open-settings="openSettings"
            @must_change="onMustChange"
            @refresh-room="loadRoom(currentRoom)"
            @back="openDashboard"
          />
        </div>
      </main>
      </template>

      <!-- render login alone when view is 'login' -->
      <template v-if="view === 'login'">
        <div style="display:flex;align-items:center;justify-content:center;height:70vh">
          <component :is="currentView" @logged="onLogged" @must_change="onMustChange" />
        </div>
      </template>
    </div>
  </div>
</template>

<script>
import { ref, computed } from 'vue'

if (typeof window !== 'undefined') {
  const bootMsg = `[e-face][app] bundle evaluated at ${new Date().toISOString()}`
  console.log(bootMsg)
  window.__efaceDebugLog = window.__efaceDebugLog || []
  window.__efaceDebugLog.push({ time: Date.now(), source: 'app', message: 'bundle evaluated', args: [] })
  window.addEventListener('load', () => {
    console.log('[e-face][app] window load event fired')
    window.__efaceDebugLog.push({ time: Date.now(), source: 'app', message: 'window load', args: [] })
  })
}
import Login from './components/Login.vue'
import Dashboard from './components/Dashboard.vue'
import Settings from './components/Settings.vue'
import ChangePassword from './components/ChangePassword.vue'
import AdminUsers from './components/AdminUsers.vue'
import api, { setAuthToken } from './api'

export default {
    components: { Dashboard },
    setup() {
    if (typeof window !== 'undefined') {
      window.__efaceDebugLog = window.__efaceDebugLog || []
    }
    const logWs = (source, message, ...rest) => {
      try {
        const prefix = `[e-face][${source}]`
        console.log(prefix, message, ...rest)
        if (typeof window !== 'undefined') {
          window.__efaceDebugLog = window.__efaceDebugLog || []
          window.__efaceDebugLog.push({ time: Date.now(), source, message, args: rest })
        }
      } catch (_) { /* ignore */ }
    }

    const PRIVATE_HOST_PATTERNS = [
      /^localhost$/i,
      /^127\./,
      /^0\.0\.0\.0$/,
      /^10\./,
      /^192\.168\./,
      /^172\.(1[6-9]|2[0-9]|3[0-1])\./
    ]

    const extractHostname = (value) => {
      if (!value) return ''
      const raw = String(value).trim()
      try {
        const normalized = raw.includes('://') ? raw : `http://${raw}`
        const url = new URL(normalized)
        return url.hostname || ''
      } catch (_) {
        return raw
          .replace(/^https?:\/\//i, '')
          .split('/')[0]
          .split(':')[0]
          .trim()
      }
    }

    const isLikelyLocalHost = (host) => {
      if (!host) return false
      return PRIVATE_HOST_PATTERNS.some((pattern) => pattern.test(host.toLowerCase()))
    }

    const shouldPreferRemoteHost = (localHost, remoteHost) => {
      if (typeof window === 'undefined') return false
      if (!remoteHost) return false
      const originHost = (window.location.hostname || '').toLowerCase()
      if (!originHost) return false
      const remote = extractHostname(remoteHost).toLowerCase()
      const local = extractHostname(localHost).toLowerCase()
      if (!remote) return false
      if (local && originHost === local) {
        return false
      }
      if (originHost === remote) {
        return true
      }
      const originIsPrivate = isLikelyLocalHost(originHost)
      return !originIsPrivate
    }

    logWs('app', 'frontend boot', new Date().toISOString())
    const token = ref(localStorage.getItem('eface_token'))
    const view = ref(token.value ? 'dashboard' : 'login')
    const title = ref('e-face')
    const rooms = ref([])
    const currentRoom = ref(null)
    const roomDevices = ref([])
    const securityDevices = ref([])
    const integrationError = ref(null)
    const isAdmin = ref(localStorage.getItem('eface_is_admin') === '1')
    const weatherSnapshot = ref(null)

    function applyTheme(theme = {}) {
      if (typeof document === 'undefined') return
      const root = document.documentElement
      const mapping = {
        '--primary': theme.primary,
        '--accent': theme.accent,
        '--bg': theme.bg,
        '--surface': theme.surface,
        '--text': theme.text
      }
      Object.entries(mapping).forEach(([token, value]) => {
        if (value) root.style.setProperty(token, value)
      })
    }

    function sanitizeCssUrl(value) {
      if (!value) return ''
      return String(value)
        .replace(/"/g, '\\"')
        .replace(/\n|\r/g, '')
        .trim()
    }

    async function loadBranding() {
      try {
        const res = await api.get('/api/config')
        if (res.data?.site_name) title.value = res.data.site_name
        const theme = res.data?.advanced?.theme || {}
        applyTheme(theme)
      } catch (e) {
        if ((e?.response?.status || 0) !== 401) {
          console.warn('Branding unavailable', e?.message || e)
        }
      }
    }

    async function loadRooms() {
      integrationError.value = null
      try {
        const res = await api.get('/api/rooms')
        const previousRoom = currentRoom.value
        rooms.value = res.data.rooms || []
        weatherSnapshot.value = res.data.weather || null
        securityDevices.value = res.data.security_devices || []
        rebuildEntityMetadata(rooms.value, securityDevices.value)

        if (!rooms.value.length) {
          currentRoom.value = null
          roomDevices.value = []
          rebuildEntityMetadata([], securityDevices.value)
          return
        }

        const stillValid = previousRoom && rooms.value.find(r => r.id === previousRoom)
        const targetRoom = stillValid ? previousRoom : rooms.value[0].id
        currentRoom.value = targetRoom
        await loadRoom(targetRoom)
      } catch (e) {
        // if 401 Unauthorized -> token invalid/expired: force logout and redirect to login
        const status = e?.response?.status
        if (status === 401) {
          try { localStorage.removeItem('eface_token'); localStorage.removeItem('eface_is_admin'); delete api.defaults.headers.common['Authorization'] } catch(err){}
          window.location.href = '/'
          return
        }
        // if integration is missing or failed, set integrationError for UI
        const msg = e.response?.data?.detail || e.message || 'Unknown error'
        integrationError.value = msg
        rooms.value = []
        weatherSnapshot.value = null
        securityDevices.value = []
        rebuildEntityMetadata([])
      }
    }

    async function loadRoom(id) {
      try {
        const res = await api.get(`/api/rooms/${id}`)
        roomDevices.value = res.data.devices || []
        upsertEntityTags(roomDevices.value)
        // apply background
        const bg = res.data.background || ''
        const safeBg = sanitizeCssUrl(bg)
        const root = typeof document !== 'undefined' ? document.documentElement : null
        if (safeBg) {
          document.body.style.backgroundImage = `url("${safeBg}")`
          document.body.classList.add('room-bg')
          root?.classList.add('room-bg-active')
        } else {
          document.body.style.backgroundImage = ''
          document.body.classList.remove('room-bg')
          root?.classList.remove('room-bg-active')
        }
      } catch (e) { roomDevices.value = [] }
    }

    function onLogged(t) {
      token.value = t
      // set default Authorization header for all API calls
      try { setAuthToken(t) } catch(e){}
      view.value = 'dashboard'
      // update admin flag from storage
      isAdmin.value = localStorage.getItem('eface_is_admin') === '1'
      bootstrapAuthenticated(true)
    }

    function onMustChange(payload) {
      // payload contains token
      token.value = payload.token
      view.value = 'change_password'
    }

    function openDashboard() { view.value = 'dashboard' }
    function openSettings() { view.value = 'settings' }

    function onRoomChange() {
      if (currentRoom.value) {
        loadRoom(currentRoom.value)
        view.value = 'dashboard'
      }
    }

    function onRoomSelected(id) {
      if (!id) return
      if (currentRoom.value === id) {
        view.value = 'dashboard'
        return
      }
      currentRoom.value = id
      onRoomChange()
    }

    const currentView = computed(() => {
      if (view.value === 'login') return Login
      if (view.value === 'change_password') return ChangePassword
      if (view.value === 'settings') return Settings
      return Dashboard
    })

    // start websocket to receive HA events and refresh UI in real-time
    let _ws
    let _registryRefreshTimer = null
    let _roomsReloadTimer = null
    let haRegistry = { areas: {}, devices: {}, entities: {}, table: [] }

    // direct HA websocket (client -> HA) for zero-latency updates
    let _haWs = null
    let _haWsInfo = null
    let _haWsReconnectTimer = null
    let _haWsPingTimer = null
    let _haWsGuardTimer = null
    let _haWsConnecting = false
    let _haWsUrlIndex = 0
    let _haWsSubId = 1
    const haDirectConnected = ref(false)
    const backendWsConnected = ref(false)
    const haConnectionMode = ref('unknown')
    const hiddenEntities = new Set()
    const knownEntities = new Set()
    const entityTags = new Map()
    const _haPendingCalls = new Map()
    let _lastRegistryRefreshTs = 0
    const registryCounts = (registry = haRegistry) => ({
      areas: Object.keys(registry.areas || {}).length,
      devices: Object.keys(registry.devices || {}).length,
      entities: Object.keys(registry.entities || {}).length
    })
    let _haRegistryCounts = registryCounts()

    const HA_GUARD_TIMEOUT_MS = 2500

    function clearHaWsGuardTimer() {
      if (_haWsGuardTimer) {
        clearTimeout(_haWsGuardTimer)
        _haWsGuardTimer = null
      }
    }

    function armHaWsGuard(wsRef, timeout = HA_GUARD_TIMEOUT_MS) {
      clearHaWsGuardTimer()
      _haWsGuardTimer = setTimeout(() => {
        if (_haWs === wsRef && !haDirectConnected.value) {
          logWs('ha', 'connection attempt timed out', { timeout })
          try { wsRef.close() } catch (closeErr) { console.warn('ha ws guard close failed', closeErr) }
        }
      }, timeout)
    }

    function setHaCallService(fn) {
      if (typeof window !== 'undefined') {
        window.__efaceHaCallService = fn
      }
    }
    setHaCallService(null)

    function rejectAllPending(err) {
      _haPendingCalls.forEach((entry) => {
        try { clearTimeout(entry.timeout) } catch (_) {}
        try { entry.reject(err) } catch (_) {}
      })
      _haPendingCalls.clear()
    }

    function sendHaServiceMessage(body, timeoutMs = 10000) {
      if (!_haWs || _haWs.readyState !== WebSocket.OPEN) {
        throw new Error('ha_ws_not_ready')
      }
      const messageId = _haWsSubId++
      const packet = { id: messageId, ...body }
      return new Promise((resolve, reject) => {
        const timeout = setTimeout(() => {
          _haPendingCalls.delete(messageId)
          reject(new Error('ha_call_timeout'))
        }, timeoutMs)
        _haPendingCalls.set(messageId, { resolve, reject, timeout })
        try {
          _haWs.send(JSON.stringify(packet))
        } catch (e) {
          clearTimeout(timeout)
          _haPendingCalls.delete(messageId)
          reject(e)
        }
      })
    }

    async function callHaService(domain, service, serviceData = {}) {
      const payload = {
        type: 'call_service',
        domain,
        service,
        service_data: serviceData
      }
      return sendHaServiceMessage(payload)
    }

    function normalizeLabels(list = []) {
      if (!Array.isArray(list)) return []
      return list
        .map((item) => (typeof item === 'string' ? item.trim().toLowerCase() : ''))
        .filter(Boolean)
    }

    function upsertEntityTags(devices = []) {
      for (const device of devices) {
        if (!device || !device.id) continue
        knownEntities.add(device.id)
        const labels = normalizeLabels(device.labels || [])
        entityTags.set(device.id, labels)
        if (labels.includes('hidden')) {
          hiddenEntities.add(device.id)
        }
      }
    }

    function rebuildEntityMetadata(roomList = [], extraDevices = []) {
      hiddenEntities.clear()
      entityTags.clear()
      knownEntities.clear()
      for (const room of roomList) {
        upsertEntityTags(room.devices || [])
      }
      if (Array.isArray(extraDevices) && extraDevices.length) {
        upsertEntityTags(extraDevices)
      }
    }

    function applyEntityUpdate(entityId, stateVal, attributes) {
      if (!entityId) return false
      if (hiddenEntities.has(entityId)) return false
      const hasTargets = rooms.value.length || roomDevices.value.length || securityDevices.value.length
      if (!hasTargets) return false
      let mutatedRoomDevices = false
      let mutatedRooms = false
      let mutatedSecurityDevices = false

      const updateDeviceState = (device) => {
        if (device.id !== entityId) return false
        if (typeof stateVal !== 'undefined' && stateVal !== null) {
          device.state = stateVal
          // For climate entities, the state IS the hvac_mode
          if (entityId.startsWith('climate.')) {
            device.hvac_mode = stateVal
          }
        }
        if (attributes) {
          if (!device.attributes) device.attributes = {}
          
          // Light attributes
          if (typeof attributes.brightness !== 'undefined') {
            device.brightness = attributes.brightness
            device.attributes.brightness = attributes.brightness
          }
          if (Array.isArray(attributes.rgb_color)) {
            device.rgb_color = attributes.rgb_color.slice()
            device.attributes.rgb_color = attributes.rgb_color.slice()
          }
          if (typeof attributes.color_temp !== 'undefined') {
            device.color_temp = attributes.color_temp
            device.attributes.color_temp = attributes.color_temp
          }
          
          // Cover attributes
          if (typeof attributes.current_position !== 'undefined') {
            device.current_position = attributes.current_position
            device.attributes.current_position = attributes.current_position
          }
          
          // Climate attributes
          if (typeof attributes.current_temperature !== 'undefined') {
            device.current_temperature = attributes.current_temperature
            device.attributes.current_temperature = attributes.current_temperature
          }
          if (typeof attributes.temperature !== 'undefined') {
            device.temperature = attributes.temperature
            device.target_temperature = attributes.temperature
            device.attributes.temperature = attributes.temperature
          }
          if (typeof attributes.current_humidity !== 'undefined') {
            device.humidity = attributes.current_humidity
            device.attributes.current_humidity = attributes.current_humidity
          }
          if (Array.isArray(attributes.hvac_modes)) {
            device.hvac_modes = attributes.hvac_modes.slice()
            device.attributes.hvac_modes = attributes.hvac_modes.slice()
          }
          if (typeof attributes.hvac_action !== 'undefined') {
            device.hvac_action = attributes.hvac_action
            device.attributes.hvac_action = attributes.hvac_action
          }
          if (typeof attributes.preset_mode !== 'undefined') {
            device.preset_mode = attributes.preset_mode
            device.attributes.preset_mode = attributes.preset_mode
          }
        }
        return true
      }

      for (const dev of roomDevices.value) {
        if (updateDeviceState(dev)) mutatedRoomDevices = true
      }

      for (const room of rooms.value) {
        for (const dev of (room.devices || [])) {
          if (updateDeviceState(dev)) {
            mutatedRooms = true
          }
        }
        // Check covers too
        for (const cover of (room.covers || [])) {
          if (updateDeviceState(cover)) {
            mutatedRooms = true
          }
        }
        // Check climate devices too
        for (const climate of (room.climate || [])) {
          if (updateDeviceState(climate)) {
            mutatedRooms = true
          }
        }
      }

      for (const dev of securityDevices.value) {
        if (updateDeviceState(dev)) mutatedSecurityDevices = true
      }

      if (mutatedRoomDevices) {
        roomDevices.value = roomDevices.value.map(d => ({ ...d }))
      }
      if (mutatedRooms) {
        rooms.value = rooms.value.map(r => ({ 
          ...r, 
          devices: (r.devices || []).map(d => ({ ...d })),
          climate: (r.climate || []).map(c => ({ ...c }))
        }))
      }
      if (mutatedSecurityDevices) {
        securityDevices.value = securityDevices.value.map(d => ({ ...d }))
      }
      const changed = mutatedRoomDevices || mutatedRooms || mutatedSecurityDevices
      if (!changed) {
        if (hiddenEntities.has(entityId)) return changed
        if (!knownEntities.has(entityId)) return changed
        if (!token.value) return changed
        if (_roomsReloadTimer) return changed
        _roomsReloadTimer = setTimeout(() => {
          loadRooms()
          _roomsReloadTimer = null
        }, 200)
      }
      return changed
    }

    function buildHaWsUrl(rawHost, customPath) {
      if (!rawHost) return null
      let normalized = String(rawHost).trim()
      if (!/^https?:\/\//i.test(normalized)) {
        normalized = 'http://' + normalized.replace(/^\/+/, '')
      }
      try {
        const url = new URL(normalized)
        url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:'
        let path = customPath || '/api/websocket'
        if (!path.startsWith('/')) path = '/' + path
        url.pathname = path
        url.search = ''
        url.hash = ''
        return url.toString()
      } catch (e) {
        console.warn('Invalid HA host', e)
        return null
      }
    }

    async function fetchHaWsInfo(force = false) {
      if (!token.value) return null
      if (!force && _haWsInfo) return _haWsInfo
      try {
        const res = await api.get('/api/integration/ws-info')
        if (!res.data || res.data.direct_enabled === false) {
          _haWsInfo = null
          return null
        }
        const targets = []
        const addTarget = (rawHost, customPath, mode) => {
          const built = buildHaWsUrl(rawHost, customPath)
          if (built && !targets.find(t => t.url === built)) {
            targets.push({ url: built, mode })
          }
        }
        addTarget(res.data.host, res.data.path, 'local')
        addTarget(res.data.remote_host, res.data.remote_path || res.data.path, 'cloud')
        if (!targets.length || !res.data.token) {
          console.warn('Missing HA ws params')
          _haWsInfo = null
          return null
        }
        const preferRemote = shouldPreferRemoteHost(res.data.host, res.data.remote_host)
        if (preferRemote) {
          const remoteIndex = targets.findIndex((t) => t.mode === 'cloud')
          if (remoteIndex > 0) {
            const [remoteTarget] = targets.splice(remoteIndex, 1)
            targets.unshift(remoteTarget)
          }
        }
        _haWsUrlIndex = 0
        _haWsInfo = { targets, token: res.data.token }
        return _haWsInfo
      } catch (e) {
        if ((e?.response?.status || 0) === 503) {
          console.warn('HA direct ws disabled', e?.response?.data)
        } else {
          console.warn('Failed to fetch HA ws info', e)
        }
        _haWsInfo = null
        return null
      }
    }

    function cleanupHaDirectWs() {
      clearHaWsGuardTimer()
      if (_haWsPingTimer) {
        clearInterval(_haWsPingTimer)
        _haWsPingTimer = null
      }
      if (_haWs) {
        try { _haWs.close() } catch (e) { console.warn('ha ws close', e) }
        _haWs = null
      }
      haDirectConnected.value = false
      haConnectionMode.value = 'unknown'
      setHaCallService(null)
      rejectAllPending(new Error('ha_ws_disconnected'))
    }

    function scheduleHaWsReconnect(delay = 2000) {
      if (_haWsReconnectTimer) return
      _haWsReconnectTimer = setTimeout(() => {
        _haWsReconnectTimer = null
        startHaDirectWs()
      }, delay)
    }

    function currentHaWsTarget(info = _haWsInfo) {
      if (!info || !Array.isArray(info.targets) || !info.targets.length) return null
      if (_haWsUrlIndex >= info.targets.length) {
        _haWsUrlIndex = 0
      }
      return info.targets[_haWsUrlIndex]
    }

    function advanceHaWsEndpoint(info = _haWsInfo) {
      if (!info || !Array.isArray(info.targets) || info.targets.length < 2) return false
      _haWsUrlIndex = (_haWsUrlIndex + 1) % info.targets.length
      return true
    }

    async function startHaDirectWs(forceInfo = false) {
      if (!token.value) {
        logWs('ha', 'skipping start; missing auth token')
        return
      }
      if (_haWsConnecting) return
      _haWsConnecting = true
      try {
        const info = await fetchHaWsInfo(forceInfo)
        if (!info || !Array.isArray(info.targets) || !info.targets.length) {
          logWs('ha', 'websocket info unavailable; waiting for backend integration data')
          return
        }
        const target = currentHaWsTarget(info)
        if (!target || !target.url) {
          logWs('ha', 'no valid HA ws endpoints available')
          return
        }
        cleanupHaDirectWs()
        haConnectionMode.value = target.mode || 'local'
        logWs('ha', 'connecting', target)
        let ws
        try {
          ws = new WebSocket(target.url)
        } catch (ctorErr) {
          console.warn('ha ws constructor failed', ctorErr)
          if (advanceHaWsEndpoint(info)) {
            logWs('ha', 'falling back to alternate endpoint', currentHaWsTarget(info))
          }
          scheduleHaWsReconnect(1200)
          return
        }
        _haWs = ws
        armHaWsGuard(ws)
        let authenticated = false
        ws.onopen = () => {
          logWs('ha', 'socket opened')
          armHaWsGuard(ws, HA_GUARD_TIMEOUT_MS * 1.5)
        }
        ws.onmessage = (evt) => {
          let payload
          try { payload = JSON.parse(evt.data) } catch (e) {
            return
          }
          if (!payload) return
          if (payload.type === 'auth_required') {
            try { ws.send(JSON.stringify({ type: 'auth', access_token: info.token })) } catch (e) { console.warn('ha ws auth send failed', e) }
            return
          }
          if (payload.type === 'auth_ok') {
            authenticated = true
            logWs('ha', 'authenticated; subscribing state_changed')
            haDirectConnected.value = true
            haConnectionMode.value = target.mode || 'local'
            clearHaWsGuardTimer()
            setHaCallService(callHaService)
            try {
              ws.send(JSON.stringify({ id: _haWsSubId++, type: 'subscribe_events', event_type: 'state_changed' }))
            } catch (e) { console.warn('ha ws subscribe failed', e) }
            if (_haWsPingTimer) clearInterval(_haWsPingTimer)
            _haWsPingTimer = setInterval(() => {
              try { ws.send(JSON.stringify({ id: _haWsSubId++, type: 'ping' })) } catch (e) { /* ignore */ }
            }, 15000)
            return
          }
          if (payload.type === 'auth_invalid') {
            console.warn('HA WS auth invalid', payload?.message)
            _haWsInfo = null
            cleanupHaDirectWs()
            scheduleHaWsReconnect(12000)
            return
          }
          if (payload.type === 'result' && typeof payload.id !== 'undefined') {
            const pending = _haPendingCalls.get(payload.id)
            if (pending) {
              _haPendingCalls.delete(payload.id)
              try { clearTimeout(pending.timeout) } catch (_) {}
              if (payload.success === false) pending.reject(new Error(payload.error?.message || 'ha_call_failed'))
              else pending.resolve(payload.result)
            }
            return
          }
          if (payload.type === 'pong') {
            return
          }
          if (payload.type === 'event' && payload.event?.event_type === 'state_changed') {
            const entityId = payload.event?.data?.entity_id
            const newState = payload.event?.data?.new_state
            const attributes = newState?.attributes || {}
            const stateVal = typeof newState?.state !== 'undefined' ? newState.state : undefined
            applyEntityUpdate(entityId, stateVal, attributes)
            return
          }
        }
        ws.onclose = () => {
          logWs('ha', 'closed; scheduling reconnect', { authenticated, target })
          clearHaWsGuardTimer()
          cleanupHaDirectWs()
          if (!authenticated && advanceHaWsEndpoint(info)) {
            logWs('ha', 'switching HA ws endpoint', currentHaWsTarget(info))
          }
          scheduleHaWsReconnect(authenticated ? 3500 : 1500)
        }
        ws.onerror = () => { /* handled by onclose */ }
      } catch (e) {
        console.warn('Failed to start HA direct WS', e)
        scheduleHaWsReconnect(4000)
      } finally {
        _haWsConnecting = false
      }
    }

    function startWs() {
      try {
        const scheme = location.protocol === 'https:' ? 'wss://' : 'ws://'
        const url = scheme + location.host + '/ws'
        logWs('backend', 'connecting', url)
        _ws = new WebSocket(url)
        _ws.onopen = () => {
          backendWsConnected.value = true
          logWs('backend', 'connected')
        }
        _ws.onmessage = (evt) => {
          try {
            const data = JSON.parse(evt.data)
            if (!data) return

            // registry snapshot: contains mappings areas/devices/entities/table
            if (data.type === 'ha_registry') {
              try {
                const prevCounts = { ..._haRegistryCounts }
                haRegistry.areas = data.areas || {}
                haRegistry.devices = data.devices || {}
                haRegistry.entities = data.entities || {}
                haRegistry.table = data.table || []
                _haRegistryCounts = registryCounts()

                // schedule a debounced pull from backend so rooms/devices stay authoritative
                if (token.value) {
                  const now = Date.now()
                  const countsChanged = ['areas', 'devices', 'entities'].some((key) => prevCounts[key] !== _haRegistryCounts[key])
                  const stale = now - _lastRegistryRefreshTs > 60000
                  const needsRooms = !rooms.value.length
                  if (countsChanged || stale || needsRooms) {
                    _lastRegistryRefreshTs = now
                    if (_registryRefreshTimer) clearTimeout(_registryRefreshTimer)
                    _registryRefreshTimer = setTimeout(() => {
                      loadRooms()
                      _registryRefreshTimer = null
                    }, countsChanged ? 200 : 800)
                  }
                }
              } catch (e) { console.warn('failed to apply ha_registry', e) }
              return
            }

            if (data.type === 'ha_entity_update') {
              try {
                applyEntityUpdate(data.entity_id, data.state, data.attributes || {})
              } catch (e) { console.warn('apply ha_entity_update failed', e) }
              return
            }

            // handle legacy events updating specific entities
            if (data.type === 'ha_event') {
              const ev = data.event
              try { window.__eface_last_event = ev; window.dispatchEvent(new CustomEvent('ha_event', { detail: ev })) } catch(e){}
              // apply event changes directly to device list if present
              try {
                const entityId = ev.entity_id || ev.data?.entity_id || (ev.data && ev.data.entity_id)
                const newState = ev.new_state || ev.state || ev.data?.new_state || ev.data?.state || ev.event?.new_state
                // normalize: newState may be object with state and attributes
                let stateVal = null
                if (typeof newState === 'string') stateVal = newState
                else if (newState && newState.state) stateVal = newState.state
                if (entityId) {
                  applyEntityUpdate(entityId, stateVal, newState?.attributes || {})
                }
              } catch (e) { console.warn('apply ha_event failed', e) }
              return
            }
          } catch (e) { console.warn('ws parse', e) }
        }
        _ws.onclose = () => {
          backendWsConnected.value = false
          setTimeout(startWs, 2000)
        }
        _ws.onerror = () => {
          backendWsConnected.value = false
        }
      } catch (e) {
        backendWsConnected.value = false
        console.warn('ws start failed', e)
        setTimeout(startWs, 5000)
      }
    }
    startWs()

    // if a token was previously stored, ensure axios has the header set and load rooms
    if (token.value) {
      try { setAuthToken(token.value) } catch(e){}
      bootstrapAuthenticated(true)
    }

    function bootstrapAuthenticated(forceHaInfo = false) {
      if (!token.value) return
      loadBranding()
      loadRooms()
      startHaDirectWs(forceHaInfo)
    }

    loadBranding()

    return { title, currentView, onLogged, onMustChange, openSettings, openDashboard, rooms, currentRoom, roomDevices, securityDevices, loadRoom, onRoomChange, onRoomSelected, loadRooms, view, integrationError, isAdmin, haConnectionMode, haDirectConnected, backendWsConnected, Dashboard, weatherSnapshot }
  }
}
</script>

<style>
body { font-family: Arial, Helvetica, sans-serif; margin: 0; }
.container { padding: 1rem; max-width: 960px; margin: auto }
header { margin-bottom: 1rem }
</style>
