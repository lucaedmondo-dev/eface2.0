<template>
  <div class="login-panel card">
    <h2>Access</h2>
    <div class="mb-3" v-if="cloud.enabled">
      <button class="btn btn-secondary w-100" :disabled="loadingCloud" @click="startCloudLogin">
        <span v-if="loadingCloud" class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
        {{ cloudButtonLabel }}
      </button>
      <div class="form-text" v-if="cloudHint">{{ cloudHint }}</div>
      <div v-if="cloudError" class="text-danger small mt-2">{{ cloudError }}</div>
      <div v-if="cloudNotice" class="text-success small mt-2">{{ cloudNotice }}</div>
    </div>
    <form @submit.prevent="doLogin">
      <div class="mb-3">
        <label class="form-label">Username</label>
        <input v-model="username" class="form-control form-control-dark" :readonly="!!pendingCloud" placeholder="admin" />
      </div>
      <div class="mb-3">
        <label class="form-label">Password</label>
        <input type="password" v-model="password" class="form-control form-control-dark" placeholder="password" />
      </div>
      <div class="mb-3">
        <button type="submit" class="btn btn-primary">Login</button>
      </div>
    </form>
    <div v-if="error" class="text-danger">{{ error }}</div>
  </div>
</template>

<script>
import axios from 'axios'
export default {
  data() {
    return {
      username: '',
      password: '',
      error: null,
      cloudError: null,
      loadingCloud: false,
      cloud: {
        enabled: false,
        loginUrl: '',
        provider: 'Cloud'
      },
      pendingCloud: null,
      cloudNotice: ''
    }
  },
  computed: {
    cloudButtonLabel() {
      if (!this.cloud.enabled) {
        return 'Accesso cloud'
      }
      return `Accedi con ${this.cloud.provider || 'Cloud'}`
    },
    cloudHint() {
      if (!this.cloud.enabled) {
        return ''
      }
      return 'Usa l\'autenticazione centralizzata oppure inserisci le credenziali locali.'
    }
  },
  mounted() {
    this.fetchCloudOptions()
    this.consumeStoredCloudPrefill()
    this.tryCloudCallback()
  },
  methods: {
    async doLogin() {
      try {
        const payload = { username: this.username, password: this.password }
        const res = await axios.post('/api/login', payload)
        this.handleLoginSuccess(res.data)
        this.error = null
      } catch (e) {
        this.error = 'Login failed'
      }
    },
    consumeStoredCloudPrefill() {
      if (typeof window === 'undefined') {
        return
      }
      try {
        const raw = sessionStorage.getItem('eface_cloud_prefill')
        if (!raw) {
          return
        }
        sessionStorage.removeItem('eface_cloud_prefill')
        const parsed = JSON.parse(raw)
        if (!parsed) {
          return
        }
        this.applyCloudPrefill(parsed.username || '', parsed.instance_id || null)
      } catch (err) {
        console.warn('[e-face] unable to consume cloud prefill', err)
      }
    },
    async fetchCloudOptions() {
      try {
        const res = await axios.get('/api/config/cloud')
        const cfg = res.data || {}
        this.cloud.enabled = !!cfg.enabled
        this.cloud.loginUrl = cfg.login_url || ''
        this.cloud.provider = cfg.provider || 'Cloud'
      } catch (err) {
        this.cloud.enabled = false
      }
    },
    startCloudLogin() {
      if (!this.cloud.loginUrl) {
        this.cloudError = 'Cloud login non configurato'
        return
      }
      this.cloudError = null
      const redirectUrl = window.location.href
      const placeholder = '{redirect_uri}'
      if (this.cloud.loginUrl.includes(placeholder)) {
        const target = this.cloud.loginUrl.replace(placeholder, encodeURIComponent(redirectUrl))
        window.location.href = target
        return
      }
      try {
        const target = new URL(this.cloud.loginUrl, window.location.href)
        if (!target.searchParams.has('redirect_uri')) {
          target.searchParams.set('redirect_uri', redirectUrl)
        }
        window.location.href = target.toString()
      } catch (err) {
        window.location.href = this.cloud.loginUrl
      }
    },
    tryCloudCallback() {
      if (typeof window === 'undefined') {
        return
      }
      let url
      try {
        url = new URL(window.location.href)
      } catch (err) {
        return
      }
      const token = url.searchParams.get('cloud_token')
      const instanceId = url.searchParams.get('instance_id') || url.searchParams.get('tenant')
      const presetUsername = url.searchParams.get('cloud_username') || url.searchParams.get('username')
      const clean = () => {
        url.searchParams.delete('cloud_token')
        url.searchParams.delete('instance_id')
        url.searchParams.delete('tenant')
        url.searchParams.delete('cloud_username')
        url.searchParams.delete('username')
        const next = url.pathname + (url.searchParams.toString() ? `?${url.searchParams}` : '') + url.hash
        window.history.replaceState({}, document.title, next)
      }
      if (token) {
        this.finishCloudLogin(token, instanceId).finally(clean)
        return
      }
      if (presetUsername) {
        this.applyCloudPrefill(presetUsername, instanceId)
        clean()
      }
    },
    async finishCloudLogin(token, instanceId) {
      this.loadingCloud = true
      this.cloudError = null
      try {
        const res = await axios.post('/api/login', { cloud_token: token, instance_id: instanceId })
        if (res.data && res.data.require_password) {
          this.applyCloudPrefill(res.data.username || '', res.data.instance_id || instanceId || null)
          return
        }
        this.clearCloudPending()
        this.handleLoginSuccess(res.data)
      } catch (err) {
        this.cloudError = (err && err.response && err.response.data && err.response.data.detail) || 'Accesso cloud non riuscito'
      } finally {
        this.loadingCloud = false
      }
    },
    handleLoginSuccess(data) {
      this.cloudNotice = ''
      this.pendingCloud = null
      const t = data.access_token
      const isAdmin = data.is_admin === true
      const mustChange = data.must_change === true
      localStorage.setItem('eface_token', t)
      localStorage.setItem('eface_is_admin', isAdmin ? '1' : '0')
      axios.defaults.headers.common['Authorization'] = `Bearer ${t}`
      if (mustChange) {
        this.$emit('must_change', { token: t })
      } else {
        this.$emit('logged', t)
      }
    },
    clearCloudPending() {
      this.pendingCloud = null
      this.cloudNotice = ''
    },
    applyCloudPrefill(username, instanceId) {
      this.pendingCloud = {
        username: username || '',
        instance_id: instanceId || null
      }
      if (this.pendingCloud.username) {
        this.username = this.pendingCloud.username
      }
      this.cloudNotice = 'Inserisci la password locale per completare l\'accesso.'
    }
  }
}
</script>
