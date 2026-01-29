import axios from 'axios'

export function setAuthToken(token) {
  axios.defaults.headers.common['Authorization'] = `Bearer ${token}`
}

export default axios

// Response interceptor: if token expired/invalid, clear auth and redirect to login
axios.interceptors.response.use(
  (response) => response,
  (error) => {
    try {
      const resp = error.response
      if (resp && resp.status === 401) {
        // any 401 should trigger logout/redirect to login
        try { localStorage.removeItem('eface_token'); localStorage.removeItem('eface_is_admin'); delete axios.defaults.headers.common['Authorization'] } catch(e){}
        if (typeof window !== 'undefined') {
          // use replace to avoid back-history to protected page
          window.location.replace('/')
        }
      }
    } catch (e) {
      // ignore
    }
    return Promise.reject(error)
  }
)
