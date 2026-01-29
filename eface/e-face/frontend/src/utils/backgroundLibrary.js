const modules = import.meta.glob('../assets/room-backgrounds/*.{png,jpg,jpeg,webp,svg}', { eager: true })

function formatLabel(fileName) {
  return fileName
    .replace(/[-_]/g, ' ')
    .replace(/\.[^.]+$/, '')
    .replace(/\s+/g, ' ')
    .replace(/\b\w/g, (m) => m.toUpperCase())
}

export function getBackgroundLibrary() {
  return Object.entries(modules).map(([path, mod]) => {
    const parts = path.split('/')
    const fileName = parts[parts.length - 1]
    const url = mod?.default || mod
    return {
      id: fileName,
      label: formatLabel(fileName),
      url
    }
  }).sort((a, b) => a.label.localeCompare(b.label, 'it', { sensitivity: 'base' }))
}
