<template>
  <div>
    <h2>Users</h2>
    <div class="row g-2 mb-3">
      <div class="col"><input v-model="newUser.username" class="form-control form-control-dark" placeholder="username" /></div>
      <div class="col"><input v-model="newUser.temp_password" class="form-control form-control-dark" placeholder="temp password" /></div>
      <div class="col-auto d-flex align-items-center">
        <div class="form-check me-2"><input class="form-check-input" type="checkbox" v-model="newUser.must_change" /><label class="form-check-label">must change</label></div>
        <div class="form-check"><input class="form-check-input" type="checkbox" v-model="newUser.is_admin" /><label class="form-check-label">is admin</label></div>
      </div>
      <div class="col-auto"><button class="btn btn-primary" @click="createUser">Create</button></div>
    </div>
    <div v-if="error" style="color:red">{{ error }}</div>
    <table>
      <thead>
        <tr><th>Username</th><th>Admin</th><th>Must Change</th><th>Actions</th></tr>
      </thead>
      <tbody>
        <tr v-for="u in users" :key="u.username">
          <td>{{ u.username }}</td>
          <td>{{ u.is_admin }}</td>
          <td>{{ u.must_change }}</td>
          <td><button @click="reset(u.username)">Reset</button></td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script>
import axios from 'axios'
export default {
  data() {
    return {
      users: [],
      error: null,
      newUser: { username: '', temp_password: '', must_change: true, is_admin: false }
    }
  },
  mounted() {
    this.load()
  },
  methods: {
    async load() {
      try {
        const res = await axios.get('/api/users')
        this.users = res.data
      } catch (e) {
        this.error = e.response?.data?.detail || 'Failed to load users'
      }
    },
    async createUser() {
      try {
        await axios.post('/api/users', this.newUser)
        this.newUser = { username: '', temp_password: '', must_change: true, is_admin: false }
        this.load()
      } catch (e) {
        this.error = e.response?.data?.detail || 'Failed to create user'
      }
    },
    async reset(username) {
      try {
        const res = await axios.post('/api/users/reset', { username })
        alert('Temp password: ' + res.data.temp_password)
        this.load()
      } catch (e) {
        this.error = e.response?.data?.detail || 'Failed to reset'
      }
    }
  }
}
</script>
