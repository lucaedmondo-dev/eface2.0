Wireframe / Mockup for e-face Control4-like redesign

Overview
- Purpose: capture the major visual & interaction elements for the full redesign.

Screens
1) Main dashboard
  - TopBar: app logo, title, room selector, quick settings button.
  - Room carousel: horizontally scrollable list of rooms.
  - Category tabs: Lights / Media / Security / Comfort.
  - Tile grid: animated tiles for devices with real-time status.
  - Per-room background with overlay and readable tiles.

2) Settings / Installer
  - Integration wizard: Test → Save with clear token instructions.
  - Diagnostics panel: WS status, ping, last event, event history.
  - User management: create users, reset temp passwords.

Interaction patterns
- Tiles are large, touch-first, and show quick actions (tap to toggle, long-press for details).
- Rooms can be swiped horizontally; selecting a room loads its devices.
- Categories filter tiles client-side.

Next steps to implement
- Replace current components gradually with the wireframe components:
  1. Implement TopBar (done) and RoomsCarousel (done).
  2. Replace Dashboard with tile grid using AnimatedTile components (done).
  3. Add theme/preset editor and per-room background editor.

Design notes
- Dark theme with color accents driven by CSS variables.
- Keep UI performant on mobile (virtualize large lists if needed).

Deliverables
- `frontend/src/components/Wireframe.vue` (interactive placeholder)
- `frontend/src/components/ui/TopBar.vue` (already added)
- Proposed phases and checklist in the repo for the design rollout.
