import axios from 'axios'

function getDirectCallFn() {
  if (typeof window === 'undefined') return null
  const fn = window.__efaceHaCallService
  return typeof fn === 'function' ? fn : null
}

export async function callLightService(light, action, payload = {}) {
  if (!light) return false
  const entityId = typeof light === 'string' ? light : light.id
  if (!entityId) return false

  const directFn = getDirectCallFn()
  const serviceName = action === 'color' ? 'turn_on' : action
  const serviceData = { entity_id: entityId, ...payload }

  if (directFn) {
    try {
      await directFn('light', serviceName, serviceData)
      return true
    } catch (err) {
      console.warn('Direct HA call failed, falling back to backend', err)
    }
  }

  try {
    if (action === 'turn_on') {
      const body = {}
      if (typeof payload.brightness !== 'undefined') body.brightness = payload.brightness
      if (typeof payload.color_temp !== 'undefined') body.color_temp = payload.color_temp
      if (Array.isArray(payload.rgb_color)) body.rgb_color = payload.rgb_color
      await axios.post(`/api/devices/${entityId}/turn_on`, Object.keys(body).length ? body : {})
      return true
    }
    if (action === 'turn_off') {
      await axios.post(`/api/devices/${entityId}/turn_off`, {})
      return true
    }
    if (action === 'color') {
      const body = {}
      if (Array.isArray(payload.rgb_color)) body.rgb_color = payload.rgb_color
      if (typeof payload.brightness !== 'undefined') body.brightness = payload.brightness
      if (!Object.keys(body).length) return false
      await axios.post(`/api/devices/${entityId}/color`, body)
      return true
    }
  } catch (err) {
    console.error('Backend light action failed', err)
    throw err
  }

  return false
}

export function extractBrightness(light) {
  if (!light) return 0
  if (typeof light.brightness === 'number') return light.brightness
  const attr = light.attributes || {}
  if (typeof attr.brightness === 'number') return attr.brightness
  return 0
}

export function extractRgb(light) {
  if (!light) return null
  const direct = light.rgb_color
  if (Array.isArray(direct) && direct.length === 3) return direct
  const attr = light.attributes || {}
  const rgb = attr.rgb_color
  if (Array.isArray(rgb) && rgb.length === 3) return rgb
  return null
}

export function rgbToHex(rgb) {
  if (!Array.isArray(rgb) || rgb.length !== 3) return '#ffffff'
  return '#' + rgb.map((c) => {
    const val = Math.max(0, Math.min(255, Number(c) || 0))
    return val.toString(16).padStart(2, '0')
  }).join('')
}

export function hexToRgb(hex) {
  if (!hex) return null
  const value = hex.replace('#', '')
  if (!/^[0-9a-fA-F]{6}$/.test(value)) return null
  return [
    parseInt(value.slice(0, 2), 16),
    parseInt(value.slice(2, 4), 16),
    parseInt(value.slice(4, 6), 16)
  ]
}

export function normalizeBrightness(val) {
  const num = Number(val)
  if (Number.isNaN(num)) return 0
  return Math.max(0, Math.min(255, Math.round(num)))
}

export function isValidHexColor(value) {
  return /^#?[0-9a-fA-F]{6}$/.test((value || '').trim())
}
