import { createApp } from 'vue'
import App from './App.vue'
import './styles.css'
import axios from './api'

function captureInitialCloudPrefill() {
	if (typeof window === 'undefined') return
	try {
		const url = new URL(window.location.href)
		const token = url.searchParams.get('cloud_token')
		const username = url.searchParams.get('cloud_username') || url.searchParams.get('username')
		const instanceId = url.searchParams.get('instance_id') || url.searchParams.get('tenant')
		if (!token && username) {
			const payload = { username, instance_id: instanceId || null }
			sessionStorage.setItem('eface_cloud_prefill', JSON.stringify(payload))
			url.searchParams.delete('cloud_username')
			url.searchParams.delete('username')
			if (!instanceId) {
				url.searchParams.delete('instance_id')
				url.searchParams.delete('tenant')
			}
			const next = url.pathname + (url.searchParams.toString() ? `?${url.searchParams}` : '') + url.hash
			window.history.replaceState({}, document.title, next)
		}
	} catch (err) {
		console.warn('[e-face] failed to capture cloud prefill', err)
	}
}

captureInitialCloudPrefill()

// load token from localStorage if present
const token = localStorage.getItem('eface_token')
if (token) axios.defaults.headers.common['Authorization'] = `Bearer ${token}`

createApp(App).mount('#app')

if ('serviceWorker' in navigator) {
	window.addEventListener('load', () => {
		navigator.serviceWorker
			.register('/sw.js')
			.catch((err) => console.warn('[e-face] service worker registration failed', err))
	})
}
