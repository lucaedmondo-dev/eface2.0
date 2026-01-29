<template>
    <div>
      <h2>Change Password</h2>
      <div v-if="error" class="text-danger">{{ error }}</div>
      <div class="mb-3">
        <label class="form-label">Current Password</label>
        <input type="password" v-model="old_password" class="form-control form-control-dark" />
      </div>
      <div class="mb-3">
        <label class="form-label">New Password</label>
        <input type="password" v-model="new_password" class="form-control form-control-dark" />
      </div>
      <div class="mb-3">
        <button class="btn btn-primary" @click="doChange">Set New Password</button>
      </div>
    </div>
</template>

<script>
import axios from 'axios'
export default {
  props: ['initialToken'],
  data() {
    return { old_password: '', new_password: '', error: null }
  },
  methods: {
    async doChange() {
      try {
        const payload = { old_password: this.old_password, new_password: this.new_password }
        const res = await axios.post('/api/users/change-password', payload)
        if (res.data && res.data.access_token) {
          const t = res.data.access_token
          localStorage.setItem('eface_token', t)
          axios.defaults.headers.common['Authorization'] = `Bearer ${t}`
          this.$emit('logged', t)
        } else {
          this.error = 'Password changed, please re-login.'
        }
      } catch (e) {
        this.error = e.response?.data?.detail || 'Failed to change password'
      }
    }
  }
}
</script>
