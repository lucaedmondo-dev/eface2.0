<template>
  <div class="control4-shell">
    <header class="dashboard-header card compact-header">
      <div class="header-inline">
        <div class="brand-logo tiny" aria-label="Logo">
          <img :src="brandLogo" alt="Logo E-face" />
        </div>
        <div class="status-inline">
          <div
            class="weather-chip compact interactive"
            role="button"
            tabindex="0"
            :title="`Meteo: ${weatherSnapshot.condition}`"
            :aria-label="`Dettagli meteo: ${weatherSnapshot.condition}`"
            @click="openWeatherDetails"
            @keydown.enter.prevent="openWeatherDetails"
            @keydown.space.prevent="openWeatherDetails"
          >
            <span class="icon" aria-hidden="true" v-html="iconMarkup(weatherSnapshot.icon)"></span>
            <div class="weather-meta">
              <strong>{{ weatherSnapshot.temperature }}</strong>
              <small>{{ weatherSnapshot.condition }}</small>
            </div>
          </div>
          <div class="alarm-chip" :class="alarmStatusChip.tone">
            <span class="icon" aria-hidden="true" v-html="iconMarkup(alarmStatusChip.icon)"></span>
            <div>
              <strong>{{ alarmStatusChip.label }}</strong>
              <small>{{ alarmStatusChip.details }}</small>
            </div>
          </div>
        </div>
      </div>
      <div class="header-actions compact">
        <div
          v-if="!isAdmin"
          class="connection-dot"
          :class="`tone-${connectionStatusChip.tone}`"
          role="status"
          aria-live="polite"
          :aria-label="`Connessione ${connectionStatusChip.label}`"
          :title="`Connessione ${connectionStatusChip.label}`"
        >
          <span class="dot"></span>
          <span class="sr-only">{{ connectionStatusChip.details }}</span>
        </div>
        <button class="ghost-btn icon-only" type="button" @click="openLightsModal" aria-label="Luci attive">
          <span class="icon" aria-hidden="true" v-html="iconMarkup('bulb')"></span>
        </button>
        <button class="ghost-btn icon-only" type="button" @click="openCoversModal" aria-label="Tapparelle">
          <span class="icon" aria-hidden="true" v-html="iconMarkup('blinds')"></span>
        </button>
        <button class="ghost-btn icon-only" type="button" @click="openGatesModal" aria-label="Cancelli">
          <span class="icon" aria-hidden="true" v-html="iconMarkup('gate')"></span>
        </button>
        <button class="ghost-btn icon-only" type="button" @click="openDoorbellPicker" aria-label="Apri campanello">
          <span class="icon" aria-hidden="true" v-html="iconMarkup('doorbell')"></span>
        </button>
        <button class="ghost-btn icon-only" type="button" @click="$emit('open-settings')" aria-label="Impostazioni">
          <span class="icon" aria-hidden="true" v-html="iconMarkup('settings')"></span>
        </button>
      </div>
    </header>
    <section class="console" :class="{ 'console--compact': !isAdmin }">
      <aside class="nav rail card">
        <h3 class="sr-only">Sezioni</h3>
        <button
          v-for="cat in categories"
          :key="cat.id"
          class="nav-btn"
          :class="{ active: activeCategory === cat.id }"
          type="button"
          :title="cat.label"
          @click="setCategory(cat.id)"
        >
          <span class="nav-icon" aria-hidden="true" v-html="iconMarkup(cat.icon)"></span>
          <span class="sr-only">{{ cat.label }}</span>
        </button>
      </aside>

      <div class="content">
        <!-- Selettore stanza globale -->
        <section v-if="structuredRooms.length > 1" class="room-selector card">
          <div class="room-select-mobile">
            <label class="sr-only" for="roomSelectMobile">Seleziona stanza</label>
            <select
              id="roomSelectMobile"
              aria-label="Seleziona stanza"
              :value="currentRoomId ?? (structuredRooms[0] && structuredRooms[0].id)"
              @change="focusRoom($event.target.value)"
            >
              <option v-for="room in structuredRooms" :key="room.id" :value="room.id">{{ room.name }}</option>
            </select>
          </div>
          <div class="room-chip-row">
            <button
              v-for="room in structuredRooms"
              :key="room.id"
              class="room-chip"
              :class="{ active: room.id === currentRoomId }"
              type="button"
              @click="focusRoom(room.id)"
            >
              <span class="chip-icon" aria-hidden="true" v-html="iconMarkup(roomIcon(room))"></span>
              <div>
                <strong>{{ room.name }}</strong>
              </div>
            </button>
          </div>
        </section>

        <!-- Vista Overview della stanza -->
        <template v-if="activeCategory === 'overview'">
          <section v-if="structuredRooms.length" class="rooms-grid">
            <article
              v-for="room in visibleRooms"
              :key="room.id"
              class="room-card card"
              :class="{ focused: room.id === currentRoomId, 'has-bg': !!room.background }"
              :style="roomBackgroundStyle(room)"
            >
              <header class="room-head">
                <div class="room-title-group">
                  <h3>{{ room.name }}</h3>
                  <div v-if="room.temperatures && room.temperatures.length > 0" class="room-temp-banner">
                    <span class="temp-icon" v-html="iconMarkup('thermo')"></span>
                    <div class="temp-values">
                      <span 
                        v-for="(sensor, index) in room.temperatures" 
                        :key="sensor.id"
                        class="temp-reading"
                      >
                        {{ sensor.value !== null ? sensor.value : '--' }}{{ sensor.unit || '°C' }}<span v-if="index < room.temperatures.length - 1" class="temp-separator"> • </span>
                      </span>
                    </div>
                  </div>
                </div>
                <div class="room-actions">
                  <div class="primary-actions">
                    <button class="pill" type="button" :class="{ on: hasRoomLightsOn(room) }" @click="toggleRoom(room)">
                      {{ hasRoomLightsOn(room) ? 'Spegni tutto' : 'Accendi tutto' }}
                    </button>
                    <button
                      class="pill ghost"
                      v-if="room.id !== currentRoomId"
                      type="button"
                      @click="focusRoom(room.id)"
                    >
                      Apri stanza
                    </button>
                  </div>
                  <div class="scene-actions" v-if="room.scenes && room.scenes.length">
                    <button
                      v-for="scene in room.scenes"
                      :key="scene.id"
                      class="pill scene"
                      type="button"
                      :disabled="sceneTriggering === scene.id"
                      @click="triggerScene(scene)"
                    >
                      {{ scene.name }}
                    </button>
                  </div>
                </div>
              </header>

              <div class="lights-grid">
                <article
                  v-for="device in room.devices"
                  :key="device.id"
                  class="light-card"
                  :class="{ active: isOn(device) }"
                  :style="lightCardStyle(device)"
                  role="button"
                  tabindex="0"
                  @click="tryOpenDevicePanel(device, room)"
                  @keydown.enter.prevent="tryOpenDevicePanel(device, room)"
                  @keydown.space.prevent="tryOpenDevicePanel(device, room)"
                >
                  <div class="light-head">
                    <div class="device-chip">
                      <button
                        class="device-icon-btn"
                        type="button"
                        :aria-pressed="isOn(device)"
                        :style="deviceIconStyle(device)"
                        @click.stop="toggle(device)"
                      >
                        <span class="device-icon" aria-hidden="true" v-html="iconMarkup(deviceIcon(device))"></span>
                      </button>
                      <div class="light-text-block">
                        <p class="light-label">{{ device.name }}</p>
                        <p class="muted tiny">{{ deviceStateLabel(device) }}</p>
                        <div class="device-tags" v-if="device.labels && device.labels.length">
                          <span
                            v-for="tag in device.labels"
                            :key="device.id + '-' + tag"
                            class="device-tag"
                          >{{ formatTag(tag) }}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </article>
              </div>

              <!-- Tapparelle -->
              <div v-if="room.covers && room.covers.length > 0" class="covers-section">
                <h4 class="section-title">Tapparelle</h4>
                <div class="covers-grid">
                  <article
                    v-for="cover in room.covers"
                    :key="cover.id"
                    class="cover-overview-card"
                    :class="{ open: isCoverOpen(cover) }"
                  >
                    <div class="cover-header">
                      <div class="cover-info">
                        <p class="cover-name">{{ cover.friendly_name || cover.name }}</p>
                        <p class="muted tiny">{{ coverStateLabel(cover) }}</p>
                      </div>
                      <div class="cover-controls-compact">
                        <button
                          class="cover-control-btn-sm"
                          type="button"
                          @click="openCover(cover)"
                          :disabled="cover.current_position === 100"
                          title="Apri"
                        >
                          <span v-html="iconMarkup('chevronUp')"></span>
                        </button>
                        <button
                          class="cover-control-btn-sm"
                          type="button"
                          @click="stopCover(cover)"
                          title="Stop"
                        >
                          <span v-html="iconMarkup('pause')"></span>
                        </button>
                        <button
                          class="cover-control-btn-sm"
                          type="button"
                          @click="closeCover(cover)"
                          :disabled="cover.current_position === 0"
                          title="Chiudi"
                        >
                          <span v-html="iconMarkup('chevronDown')"></span>
                        </button>
                      </div>
                    </div>
                    <div class="cover-position-bar">
                      <div class="position-fill" :style="{ width: cover.current_position + '%' }"></div>
                      <span class="position-label">{{ cover.current_position }}%</span>
                    </div>
                  </article>
                </div>
              </div>

              <!-- Clima -->
              <div v-if="room.climate && room.climate.length > 0" class="climate-section">
                <h4 class="section-title">Clima</h4>
                <div class="climate-grid">
                  <article
                    v-for="climate in room.climate"
                    :key="climate.id"
                    class="climate-overview-card"
                    :class="{
                      on: isClimateOn(climate),
                      'mode-heat': climate.hvac_mode === 'heat',
                      'mode-cool': climate.hvac_mode === 'cool',
                      'mode-auto': climate.hvac_mode === 'auto',
                      'mode-dry': climate.hvac_mode === 'dry',
                      'mode-fan': climate.hvac_mode === 'fan_only'
                    }"
                  >
                    <div class="climate-header-compact">
                      <div>
                        <h5 class="climate-name">{{ climate.name }}</h5>
                        <span v-if="climate.hvac_action" class="climate-state-badge-sm">
                          {{ formatHvacAction(climate.hvac_action) }}
                        </span>
                      </div>
                      <button 
                        class="climate-toggle-sm"
                        :class="{ active: isClimateOn(climate) }"
                        @click="toggleClimate(climate)"
                        type="button"
                      >
                        <span v-html="iconMarkup('power')"></span>
                      </button>
                    </div>

                    <div v-if="isClimateOn(climate)" class="climate-compact-display">
                      <div class="climate-temps">
                        <div class="current-temp-sm">
                          <span class="temp-value-sm">{{ climate.current_temperature || '--' }}</span>
                          <span class="temp-unit-sm">°C</span>
                        </div>
                        <div class="target-temp-sm">
                          <span class="target-label-sm">Target</span>
                          <span class="target-value-sm">{{ climate.temperature || '--' }}°C</span>
                        </div>
                      </div>
                      <div class="climate-temp-controls-sm">
                        <button 
                          class="temp-btn-sm"
                          @click="decreaseTemp(climate)"
                          type="button"
                        >
                          <span v-html="iconMarkup('minus')"></span>
                        </button>
                        <button 
                          class="temp-btn-sm"
                          @click="increaseTemp(climate)"
                          type="button"
                        >
                          <span v-html="iconMarkup('plus')"></span>
                        </button>
                      </div>
                    </div>

                    <div v-else class="climate-off-sm">
                      <span class="off-temp-sm">{{ climate.temperature || climate.target_temperature || '--' }}°C</span>
                    </div>
                  </article>
                </div>
              </div>
            </article>
          </section>

          <!-- Messaggio se nessuna stanza selezionata -->
          <div v-else class="empty-state card">
            <div class="empty-icon" aria-hidden="true" v-html="iconMarkup('grid')"></div>
            <h3>Seleziona una stanza</h3>
            <p class="muted">Scegli una stanza per vedere la panoramica dei dispositivi.</p>
          </div>
        </template>

        <template v-if="activeCategory === 'lights'">
          <section v-if="hasLights" class="rooms-grid">
            <article
              v-for="room in visibleRooms"
              :key="room.id"
              class="room-card card"
              :class="{ focused: room.id === currentRoomId, 'has-bg': !!room.background }"
              :style="roomBackgroundStyle(room)"
            >
              <header class="room-head">
                <div class="room-title-group">
                  <h3>{{ room.name }}</h3>
                  <div v-if="room.temperatures && room.temperatures.length > 0" class="room-temp-banner">
                    <span class="temp-icon" v-html="iconMarkup('thermo')"></span>
                    <div class="temp-values">
                      <span 
                        v-for="(sensor, index) in room.temperatures" 
                        :key="sensor.id"
                        class="temp-reading"
                      >
                        {{ sensor.value !== null ? sensor.value : '--' }}{{ sensor.unit || '°C' }}<span v-if="index < room.temperatures.length - 1" class="temp-separator"> • </span>
                      </span>
                    </div>
                  </div>
                </div>
                <div class="room-actions">
                  <div class="primary-actions">
                    <button class="pill" type="button" :class="{ on: roomActiveLights(room) > 0 }" @click="toggleRoom(room)">
                      {{ roomActiveLights(room) ? 'Spegni tutto' : 'Accendi tutto' }}
                    </button>
                    <button
                      class="pill ghost"
                      v-if="room.id !== currentRoomId"
                      type="button"
                      @click="focusRoom(room.id)"
                    >
                      Apri stanza
                    </button>
                  </div>
                  <div class="scene-actions" v-if="room.scenes && room.scenes.length">
                    <button
                      v-for="scene in room.scenes"
                      :key="scene.id"
                      class="pill scene"
                      type="button"
                      :disabled="sceneTriggering === scene.id"
                      @click="triggerScene(scene)"
                    >
                      {{ scene.name }}
                    </button>
                  </div>
                </div>
              </header>

              <div class="lights-grid">
                <article
                  v-for="device in room.devices"
                  :key="device.id"
                  class="light-card"
                  :class="{ active: isOn(device) }"
                  :style="lightCardStyle(device)"
                  role="button"
                  tabindex="0"
                  @click="tryOpenDevicePanel(device, room)"
                  @keydown.enter.prevent="tryOpenDevicePanel(device, room)"
                  @keydown.space.prevent="tryOpenDevicePanel(device, room)"
                >
                  <div class="light-head">
                    <div class="device-chip">
                      <button
                        class="device-icon-btn"
                        type="button"
                        :aria-pressed="isOn(device)"
                        :style="deviceIconStyle(device)"
                        @click.stop="toggle(device)"
                      >
                        <span class="device-icon" aria-hidden="true" v-html="iconMarkup(deviceIcon(device))"></span>
                      </button>
                      <div class="light-text-block">
                        <p class="light-label">{{ device.name }}</p>
                        <p class="muted tiny">{{ deviceStateLabel(device) }}</p>
                        <div class="device-tags" v-if="device.labels && device.labels.length">
                          <span
                            v-for="tag in device.labels"
                            :key="device.id + '-' + tag"
                            class="device-tag"
                          >{{ formatTag(tag) }}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </article>
              </div>
            </article>
          </section>
          <div v-else class="empty-state card">
            <div class="empty-icon" aria-hidden="true" v-html="iconMarkup('plug')"></div>
            <h3>Nessuna luce sincronizzata</h3>
            <p class="muted">Assicurati che l'integrazione Home Assistant sia attiva e che le stanze siano assegnate.</p>
            <button class="ghost-btn" type="button" @click="$emit('open-settings')">
              Apri impostazioni
            </button>
          </div>
        </template>

        <template v-else-if="activeCategory === 'security'">
          <div class="security-stack">
            <section
              v-if="showSecurityHub"
              class="security-hub card"
              aria-label="Panoramica sicurezza"
            >
              <div class="security-hero">
                <div class="security-hero-main">
                  <p class="eyebrow">Stato sicurezza</p>
                  <h2>{{ alarmStatusChip.label }}</h2>
                  <p class="muted tiny" v-if="alarmStatusChip.details">{{ alarmStatusChip.details }}</p>
                </div>
                <div class="security-hero-stats">
                  <article v-for="stat in securityHeroStats" :key="stat.id">
                    <p class="tiny muted">{{ stat.label }}</p>
                    <strong>{{ stat.value }}</strong>
                  </article>
                </div>
              </div>

              <div class="security-hub-row">
                <button
                  v-for="option in securityViewOptions"
                  :key="option.id"
                  class="security-hub-btn"
                  type="button"
                  @click="setSecurityView(option.id)"
                >
                  <span class="icon" aria-hidden="true" v-html="iconMarkup(option.icon)"></span>
                  <div class="security-hub-btn-copy">
                    <strong>{{ option.label }}</strong>
                    <small class="muted tiny">{{ securityViewSubtitle(option.id) }}</small>
                  </div>
                </button>
              </div>
            </section>

            <template v-else-if="securityView">
              <div v-if="activeSecurityOption && shouldShowSecurityToolbar" class="security-view-toolbar card">
                <div class="security-view-toolbar-left">
                  <button
                    v-if="canShowSecurityBack"
                    class="back-btn"
                    type="button"
                    @click="resetSecurityView"
                  >
                    <span class="icon" aria-hidden="true" v-html="iconMarkup('arrowLeft')"></span>
                    <span>Indietro</span>
                  </button>
                  <div class="security-view-title">
                    <p class="eyebrow">{{ activeSecurityOption.label }}</p>
                    <small class="muted tiny">{{ securityViewSubtitle(activeSecurityOption.id) }}</small>
                  </div>
                </div>
                <div class="security-view-toolbar-badge">
                  <div class="alarm-chip" :class="alarmStatusChip.tone">
                    <span class="icon" aria-hidden="true" v-html="iconMarkup(alarmStatusChip.icon)"></span>
                    <div class="alarm-chip-body">
                      <strong>{{ alarmStatusChip.label }}</strong>
                      <small v-if="alarmStatusChip.details">{{ alarmStatusChip.details }}</small>
                    </div>
                  </div>
                </div>
              </div>

              <section
                v-if="securityView === 'partitions'"
                class="security-panel card"
                aria-label="Partizioni allarme"
              >
                <header class="security-panel-head">
                  <div>
                    <p class="eyebrow">Partizioni</p>
                    <h3>Stato allarme</h3>
                    <small class="muted tiny">{{ securityViewSubtitle('partitions') }}</small>
                  </div>
                  <div
                    class="security-panel-meta"
                    v-if="!shouldShowSecurityToolbar"
                  >
                    <div class="alarm-chip" :class="alarmStatusChip.tone">
                      <span class="icon" aria-hidden="true" v-html="iconMarkup(alarmStatusChip.icon)"></span>
                      <div class="alarm-chip-body">
                        <strong>{{ alarmStatusChip.label }}</strong>
                        <small v-if="alarmStatusChip.details">{{ alarmStatusChip.details }}</small>
                      </div>
                    </div>
                  </div>
                </header>
                <div class="alarm-zone-grid">
                  <article
                    v-for="partition in alarmPartitions"
                    :key="partition.id"
                    class="alarm-zone-card"
                    :class="partition.tone"
                  >
                    <div class="zone-head">
                      <p class="eyebrow" v-if="partitionLocationLabel(partition)">{{ partitionLocationLabel(partition) }}</p>
                      <span class="alarm-state" :class="partition.tone">{{ partition.label }}</span>
                    </div>
                    <h4>{{ partition.name }}</h4>
                    <small class="muted tiny">{{ joinDetailParts(partition.detailParts) || partition.detail }}</small>
                  </article>
                </div>
              </section>

              <section
                v-else-if="securityView === 'zones'"
                class="security-panel card"
                aria-label="Zone allarme"
              >
                <header class="security-panel-head">
                  <div>
                    <p class="eyebrow">Zone</p>
                    <h3>Sensori collegati</h3>
                    <small class="muted tiny">{{ securityViewSubtitle('zones') }}</small>
                  </div>
                  <div class="security-panel-meta" v-if="groupedAlarmZones.length || !shouldShowSecurityToolbar">
                    <span class="tag ghost tiny" v-if="groupedAlarmZones.length">{{ groupedAlarmZones.length }} stanze</span>
                    <div
                      v-if="!shouldShowSecurityToolbar"
                      class="alarm-chip"
                      :class="alarmStatusChip.tone"
                    >
                      <span class="icon" aria-hidden="true" v-html="iconMarkup(alarmStatusChip.icon)"></span>
                      <div class="alarm-chip-body">
                        <strong>{{ alarmStatusChip.label }}</strong>
                        <small v-if="alarmStatusChip.details">{{ alarmStatusChip.details }}</small>
                      </div>
                    </div>
                  </div>
                </header>
                <div
                  v-if="groupedAlarmZones.length"
                  class="rooms-grid security-rooms-grid"
                  aria-label="Zone raggruppate per stanza"
                >
                  <article
                    v-for="group in groupedAlarmZones"
                    :key="group.roomKey"
                    class="room-card card security-room-card"
                  >
                    <header class="room-head">
                      <div>
                        <p class="eyebrow">{{ group.roomLabel }}</p>
                        <h3>{{ group.displayName }}</h3>
                        <small class="muted tiny">
                          {{ group.zones.length }} {{ group.zones.length === 1 ? 'sensore' : 'sensori' }}
                        </small>
                      </div>
                    </header>

                    <div class="security-zone-list">
                      <article
                        v-for="zone in group.zones"
                        :key="zone.id"
                        class="zone-row"
                        :class="zone.tone"
                      >
                        <div class="zone-row-meta">
                          <strong>{{ zone.name }}</strong>
                          <small class="muted tiny">{{ zone.detail }}</small>
                        </div>
                        <span class="zone-state-chip" :class="zone.tone">
                          {{ zoneStateLabel(zone) }}
                        </span>
                      </article>
                    </div>
                  </article>
                </div>

                <div v-else class="empty-state compact">
                  <div class="empty-icon" aria-hidden="true" v-html="iconMarkup('rows')"></div>
                  <h4>Nessuna zona disponibile</h4>
                  <p class="muted tiny">Associa le etichette corrette ai sensori per abilitarne la visualizzazione.</p>
                </div>
              </section>

              <section
                v-else-if="securityView === 'cameras'"
                class="security-panel card"
                aria-label="Telecamere tvcc"
              >
                <header class="security-panel-head">
                  <div>
                    <p class="eyebrow">Telecamere</p>
                    <h3>Streaming live</h3>
                    <small class="muted tiny">{{ securityViewSubtitle('cameras') }}</small>
                  </div>
                  <div
                    class="security-panel-meta"
                    v-if="!shouldShowSecurityToolbar"
                  >
                    <div class="alarm-chip" :class="alarmStatusChip.tone">
                      <span class="icon" aria-hidden="true" v-html="iconMarkup(alarmStatusChip.icon)"></span>
                      <div class="alarm-chip-body">
                        <strong>{{ alarmStatusChip.label }}</strong>
                        <small v-if="alarmStatusChip.details">{{ alarmStatusChip.details }}</small>
                      </div>
                    </div>
                  </div>
                </header>
                <div class="rooms-grid camera-rooms-grid">
                  <article
                    v-for="room in cameraRoomsGrid"
                    :key="room.id"
                    class="room-card card"
                    :class="{ focused: room.id === currentRoomId && !room.isGlobal, 'has-bg': !!room.background }"
                    :style="roomBackgroundStyle(room)"
                  >
                    <header class="room-head">
                      <div>
                        <p class="eyebrow" v-if="room.isGlobal">Sicurezza</p>
                        <h3>{{ room.name }}</h3>
                        <small class="muted tiny">
                          {{ room.cameras.length }} {{ room.cameras.length === 1 ? 'telecamera' : 'telecamere' }}
                        </small>
                      </div>
                      <div class="room-actions" v-if="!room.isGlobal && room.id !== currentRoomId">
                        <button class="pill ghost" type="button" @click="focusRoom(room.id)">
                          Apri stanza
                        </button>
                      </div>
                    </header>

                    <div class="camera-mosaic">
                      <article
                        v-for="camera in room.cameras"
                        :key="room.id + '-' + cameraKey(camera)"
                        :class="['camera-card', 'camera-card--mosaic', cameraFrameState(camera), { 'camera-card--no-preview': skipCameraPreviews }]"
                      >
                        <div
                          class="camera-media"
                          :class="['camera-frame', cameraFrameState(camera)]"
                          role="button"
                          tabindex="0"
                          :aria-label="`Apri ${camera.name}`"
                          @click="handleCameraPrimaryClick(camera)"
                          @keydown.enter.prevent="handleCameraPrimaryClick(camera)"
                          @keydown.space.prevent="handleCameraPrimaryClick(camera)"
                        >
                          <span class="camera-state-chip" :class="cameraStateChip(camera).tone">
                            {{ cameraStateChip(camera).label }}
                          </span>
                          <span
                            v-if="isAdmin"
                            class="camera-stream-chip"
                            :class="cameraPreviewStreamLabel(camera) === 'HLS' ? 'camera-stream-chip--hls' : 'camera-stream-chip--mjpeg'"
                          >
                            {{ cameraPreviewStreamLabel(camera) }}
                          </span>
                          <div v-if="skipCameraPreviews" class="camera-preview-name">
                            <div class="camera-preview-name-inner">
                              <strong>{{ camera.name }}</strong>
                            </div>
                          </div>
                          <img
                            v-else-if="!cameraHasError(camera)"
                            :src="cameraPreviewSrc(camera)"
                            :alt="`Diretta ${camera.name}`"
                            loading="lazy"
                            @error="handleCameraError(camera, $event)"
                            @load="handleCameraFrameLoaded(camera)"
                            draggable="false"
                          />
                          <img
                            v-else-if="cameraHasFallback(camera)"
                            :src="cameraFallbackEntry(camera)?.url"
                            :alt="`Istantanea ${camera.name}`"
                            loading="lazy"
                            draggable="false"
                            @error="refreshCameraFallback(camera)"
                          />
                          <div v-else class="camera-media-placeholder">
                            <span class="icon" aria-hidden="true" v-html="iconMarkup('cameraOff')"></span>
                            <p class="muted tiny">Streaming non disponibile</p>
                          </div>
                          <div
                            v-if="cameraHasFallback(camera) && cameraHasError(camera)"
                            class="camera-fallback-chip"
                          >
                            <small>Istantanea · {{ fallbackTimestampLabel(camera) }}</small>
                          </div>
                          <div v-if="cameraHasError(camera) && !cameraHasFallback(camera)" class="camera-media-overlay">
                            <p class="muted tiny">{{ cameraErrorMessage(camera) }}</p>
                            <div class="camera-media-actions">
                              <button class="pill ghost tiny" type="button" @click="openCameraSnapshot(camera)">
                                Istantanea
                              </button>
                            </div>
                          </div>
                          <!-- Play overlay + quick snapshot refresh -->
                          <div class="camera-play-overlay">
                            <button class="play-btn" type="button" @click.stop="playCameraViewer(camera)" :title="`Riproduci ${camera.name}`">
                              <span class="icon" aria-hidden="true" v-html="iconMarkup('play')"></span>
                            </button>
                            <button class="snapshot-refresh small" type="button" @click.stop="refreshCameraFallback(camera)" :title="`Aggiorna istantanea ${camera.name}`">
                              <span class="sr-only">Aggiorna istantanea</span>
                              <span class="icon" aria-hidden="true" v-html="iconMarkup('refresh')"></span>
                            </button>
                          </div>
                        </div>
                        <div class="camera-meta">
                          <div>
                            <strong>{{ camera.name }}</strong>
                            <small class="muted tiny">
                              {{ cameraLocationLabel(camera, room.isGlobal ? '' : room.name) }}
                            </small>
                          </div>
                          <div class="camera-meta-actions">
                            <button
                              class="ghost-icon"
                              type="button"
                              :title="`Istantanea ${camera.name}`"
                              @click.stop="openCameraSnapshot(camera)"
                            >
                              <span class="sr-only">Mostra istantanea</span>
                              <span class="icon" aria-hidden="true" v-html="iconMarkup('camera')"></span>
                            </button>
                          </div>
                        </div>
                      </article>
                    </div>
                  </article>
                </div>
              </section>
            </template>

            <div v-else class="empty-state card">
              <div class="empty-icon" aria-hidden="true" v-html="iconMarkup('shield')"></div>
              <h3>Nessun dispositivo di sicurezza</h3>
              <p class="muted">Associa telecamere, zone o partizioni per abilitare questa vista.</p>
            </div>
          </div>
        </template>

        <template v-else-if="activeCategory === 'comfort'">
          <section v-if="hasComfortDevices" class="comfort-rooms">
            <article
              v-for="room in comfortRooms"
              :key="room.id"
              class="room-panel card"
            >
              <header class="room-panel-header">
                <div class="room-header-inline">
                  <span class="room-icon" aria-hidden="true" v-html="iconMarkup('home')"></span>
                  <div>
                    <h3>{{ room.name }}</h3>
                    <p class="muted tiny">{{ comfortDeviceCount(room) }}</p>
                  </div>
                </div>
                <div v-if="room.temperatures && room.temperatures.length > 0" class="room-temp-banner">
                  <span class="temp-icon" v-html="iconMarkup('thermo')"></span>
                  <div class="temp-values">
                    <span 
                      v-for="(sensor, index) in room.temperatures" 
                      :key="sensor.id"
                      class="temp-reading"
                    >
                      {{ sensor.value !== null ? sensor.value : '--' }}{{ sensor.unit || '°C' }}<span v-if="index < room.temperatures.length - 1" class="temp-separator"> • </span>
                    </span>
                  </div>
                </div>
              </header>

              <!-- Sezione Oscuranti (Covers) -->
              <div v-if="room.covers && room.covers.length > 0" class="comfort-section">
                <h4 class="comfort-section-title">
                  <span class="icon" aria-hidden="true" v-html="iconMarkup('blinds')"></span>
                  Oscuranti
                </h4>
                <div class="comfort-devices-grid">
                  <article
                    v-for="cover in room.covers"
                    :key="cover.id"
                    class="cover-card-modern"
                    :class="{
                      'is-open': isCoverFullyOpen(cover),
                      'is-closed': isCoverFullyClosed(cover),
                      'is-moving': isCoverMoving(cover)
                    }"
                  >
                    <div class="cover-header">
                      <div class="cover-info">
                        <h5 class="cover-name">{{ cover.name }}</h5>
                        <span class="cover-state-badge" :class="coverStateBadgeClass(cover)">
                          {{ coverStateLabel(cover) }}
                        </span>
                      </div>
                      <div class="cover-position-display">
                        <span class="position-number">{{ getCoverPosition(cover) }}</span>
                        <span class="position-unit">%</span>
                      </div>
                    </div>

                    <div class="cover-visual">
                      <div class="cover-window">
                        <div class="cover-blind" :style="{ height: `${100 - getCoverPosition(cover)}%` }">
                          <div class="blind-slats"></div>
                        </div>
                      </div>
                    </div>

                    <div class="cover-slider-container">
                      <input
                        type="range"
                        min="0"
                        max="100"
                        :value="getCoverPosition(cover)"
                        @input="updateCoverPositionOptimistic(cover, $event.target.value)"
                        @change="setCoverPosition(cover, $event.target.value)"
                        class="cover-slider-modern"
                        :disabled="isCoverMoving(cover)"
                      />
                      <div class="slider-markers">
                        <span>0%</span>
                        <span>50%</span>
                        <span>100%</span>
                      </div>
                    </div>

                    <div class="cover-controls-modern">
                      <button 
                        class="cover-btn cover-btn-up" 
                        type="button" 
                        @click="openCover(cover)" 
                        :disabled="isCoverMoving(cover) || isCoverFullyOpen(cover)"
                        title="Apri completamente"
                      >
                        <span v-html="iconMarkup('chevronUp')"></span>
                        <span class="btn-label">Apri</span>
                      </button>
                      <button 
                        class="cover-btn cover-btn-stop" 
                        type="button" 
                        @click="stopCover(cover)" 
                        :disabled="!isCoverMoving(cover)"
                        title="Ferma"
                      >
                        <span v-html="iconMarkup('pause')"></span>
                        <span class="btn-label">Stop</span>
                      </button>
                      <button 
                        class="cover-btn cover-btn-down" 
                        type="button" 
                        @click="closeCover(cover)" 
                        :disabled="isCoverMoving(cover) || isCoverFullyClosed(cover)"
                        title="Chiudi completamente"
                      >
                        <span v-html="iconMarkup('chevronDown')"></span>
                        <span class="btn-label">Chiudi</span>
                      </button>
                    </div>
                  </article>
                </div>
              </div>

              <!-- Sezione Clima -->
              <div v-if="room.climate && room.climate.length > 0" class="comfort-section">
                <h4 class="comfort-section-title">
                  <span class="icon" aria-hidden="true" v-html="iconMarkup('thermo')"></span>
                  Clima
                </h4>
                <div class="climate-grid">
                  <article
                    v-for="climate in room.climate"
                    :key="climate.id"
                    class="climate-card"
                    :class="{ 
                      'is-on': isClimateOn(climate),
                      'is-heating': climate.hvac_action === 'heating',
                      'is-cooling': climate.hvac_action === 'cooling',
                      'mode-heat': climate.hvac_mode === 'heat',
                      'mode-cool': climate.hvac_mode === 'cool',
                      'mode-auto': climate.hvac_mode === 'auto',
                      'mode-dry': climate.hvac_mode === 'dry',
                      'mode-fan': climate.hvac_mode === 'fan_only'
                    }"
                  >
                    <!-- Header compatto con nome e toggle -->
                    <div class="climate-header">
                      <div class="climate-title-group">
                        <h5 class="climate-name">{{ climate.name }}</h5>
                        <span v-if="climate.hvac_action" class="climate-state-badge">
                          {{ formatHvacAction(climate.hvac_action) }}
                        </span>
                      </div>
                      <button 
                        class="climate-toggle"
                        :class="{ active: isClimateOn(climate) }"
                        @click="toggleClimate(climate)"
                        type="button"
                        :title="isClimateOn(climate) ? 'Spegni' : 'Accendi'"
                      >
                        <span v-html="iconMarkup('power')"></span>
                      </button>
                    </div>

                    <!-- Corpo con temperatura e controlli -->
                    <div v-if="isClimateOn(climate)" class="climate-body">
                      <!-- Temperatura attuale grande e visibile -->
                      <div class="climate-temp-display">
                        <div class="current-temp">
                          <span class="temp-value">{{ climate.current_temperature || '--' }}</span>
                          <span class="temp-unit">°C</span>
                        </div>
                        <div v-if="climate.humidity" class="humidity-info">
                          <span v-html="iconMarkup('droplet')"></span>
                          <span>{{ climate.humidity }}%</span>
                        </div>
                      </div>

                      <!-- Controlli target temperatura inline -->
                      <div class="climate-target-controls">
                        <button 
                          class="temp-btn temp-down"
                          @click="decreaseTemp(climate)"
                          type="button"
                          title="Diminuisci temperatura"
                        >
                          <span v-html="iconMarkup('minus')"></span>
                        </button>
                        <div class="target-temp-display">
                          <span class="target-label">Target</span>
                          <span class="target-value">{{ climate.temperature || '--' }}°C</span>
                        </div>
                        <button 
                          class="temp-btn temp-up"
                          @click="increaseTemp(climate)"
                          type="button"
                          title="Aumenta temperatura"
                        >
                          <span v-html="iconMarkup('plus')"></span>
                        </button>
                      </div>

                      <!-- Modalità HVAC compatte -->
                      <div v-if="climate.hvac_modes && climate.hvac_modes.length > 1" class="climate-modes">
                        <button
                          v-for="mode in climate.hvac_modes.filter(m => m !== 'off')"
                          :key="mode"
                          class="mode-btn"
                          :class="{ active: climate.hvac_mode === mode }"
                          @click="setHvacMode(climate, mode)"
                          type="button"
                          :title="formatHvacMode(mode)"
                        >
                          <span class="mode-icon" v-html="getHvacModeIcon(mode)"></span>
                          <span class="mode-text">{{ formatHvacMode(mode) }}</span>
                        </button>
                      </div>
                    </div>

                    <!-- Stato spento con controlli base -->
                    <div v-else class="climate-off">
                      <div class="climate-off-temp">
                        <div class="off-temp-value">{{ climate.temperature || climate.target_temperature || '--' }}°C</div>
                        <p class="off-temp-label">Temperatura impostata</p>
                      </div>
                      <button 
                        class="climate-turn-on-btn"
                        @click="toggleClimate(climate)"
                        type="button"
                      >
                        <span v-html="iconMarkup('power')"></span>
                        <span>Accendi</span>
                      </button>
                    </div>
                  </article>
                </div>
              </div>
            </article>
          </section>
          <div v-else class="empty-state card">
            <div class="empty-icon" aria-hidden="true" v-html="iconMarkup('thermo')"></div>
            <h3>Nessun dispositivo comfort</h3>
            <p class="muted">Tapparelle e dispositivi clima verranno visualizzati qui quando disponibili.</p>
          </div>
        </template>
      </div>

      <aside class="right rail card" v-if="isAdmin">
        <h3>Stato sistema</h3>
        <div class="connection-status-card" :class="connectionStatusChip.tone" aria-live="polite">
          <span class="icon" aria-hidden="true" v-html="iconMarkup(connectionStatusChip.icon)"></span>
          <div class="meta">
            <p class="tiny muted">Percorso rete</p>
            <strong>{{ connectionStatusChip.label }}</strong>
            <small>{{ connectionStatusChip.details }}</small>
          </div>
        </div>
        <div class="system-pills">
          <div v-for="pill in systemPills" :key="pill.id" class="system-pill" :class="pill.accent">
            <p>{{ pill.label }}</p>
            <small>{{ pill.value }}</small>
          </div>
        </div>
        <div class="telemetry">
          <div class="telemetry-item">
            <div>
              <p class="tiny muted">Connessione HA</p>
              <strong>{{ hasLights ? 'Operativa' : 'In attesa' }}</strong>
            </div>
            <span class="status-dot" :class="{ on: hasLights }"></span>
          </div>
          <div class="telemetry-item">
            <div>
              <p class="tiny muted">Ultimo comando</p>
              <strong>{{ lastCommandLabel }}</strong>
            </div>
            <button class="tag compact" type="button" @click="refreshNow">Aggiorna</button>
          </div>
          <div class="telemetry-item">
            <div>
              <p class="tiny muted">Ultimo aggiornamento</p>
              <strong>{{ lastRefreshLabel }}</strong>
            </div>
          </div>
        </div>
        <div class="support-card">
          <p class="eyebrow">Suggerimenti</p>
          <p class="muted">Usa questa vista per monitorare rapidamente lo stato generale del sistema.</p>
          <button class="ghost-btn" type="button" @click="$emit('open-settings')">
            Centro impostazioni
          </button>
        </div>
      </aside>
    </section>

    <transition name="fade">
      <div v-if="lightsModalOpen" class="lights-overlay" role="dialog" aria-modal="true">
        <div class="lights-panel card">
          <header class="panel-head">
            <div>
              <p class="eyebrow">Illuminazione</p>
              <h3>Luci attive</h3>
            </div>
            <button class="ghost-btn icon-only" type="button" @click="closeLightsModal" aria-label="Chiudi">
              <span class="icon" aria-hidden="true" v-html="iconMarkup('close')"></span>
            </button>
          </header>
          <div class="panel-controls">
            <div class="filter-toggle" role="group" aria-label="Filtro luci">
              <button
                class="pill"
                type="button"
                :class="{ on: !showAllLightsInModal }"
                @click="setLightsModalFilter(false)"
              >
                Solo accese
              </button>
              <button
                class="pill ghost"
                type="button"
                :class="{ on: showAllLightsInModal }"
                @click="setLightsModalFilter(true)"
              >
                Tutte
              </button>
            </div>
            <button
              class="pill danger tiny"
              type="button"
              :disabled="!canTurnOffVisibleLights"
              @click="turnOffVisibleLights"
            >
              Spegni tutte
            </button>
          </div>
          <div v-if="modalLightDevices.length" class="active-lights-list">
            <article
              v-for="device in modalLightDevices"
              :key="device.id"
              class="active-light-card"
              :style="lightCardStyle(device.ref)"
              @click="tryOpenDevicePanel(device.ref, device.roomRef)"
            >
              <div class="active-light-body">
                <button
                  class="device-icon-btn sm"
                  type="button"
                  :aria-pressed="true"
                  :style="deviceIconStyle(device.ref)"
                  @click.stop="toggle(device.ref)"
                >
                  <span class="device-icon" aria-hidden="true" v-html="iconMarkup(deviceIcon(device.ref))"></span>
                </button>
                <div class="active-light-text">
                  <p class="light-label">{{ device.name }}</p>
                  <p class="muted tiny">{{ device.stateLabel }}</p>
                  <small class="muted">{{ device.roomName }}</small>
                </div>
                <button class="pill ghost tiny" type="button" @click.stop="toggle(device.ref)">Spegni</button>
              </div>
            </article>
          </div>
          <p v-else class="muted">
            {{ showAllLightsInModal ? 'Nessuna luce disponibile.' : 'Nessuna luce risulta accesa.' }}
          </p>
        </div>
      </div>

      <div v-if="coversModalOpen" class="lights-overlay" role="dialog" aria-modal="true">
        <div class="lights-panel card">
          <header class="panel-head">
            <div>
              <p class="eyebrow">Tapparelle</p>
              <h3>Gestione tapparelle</h3>
            </div>
            <button class="ghost-btn icon-only" type="button" @click="closeCoversModal" aria-label="Chiudi">
              <span class="icon" aria-hidden="true" v-html="iconMarkup('close')"></span>
            </button>
          </header>
          <div class="panel-controls">
            <div class="filter-toggle" role="group" aria-label="Filtro tapparelle">
              <button
                class="pill"
                type="button"
                :class="{ on: !showAllCoversInModal }"
                @click="setCoversModalFilter(false)"
              >
                Solo aperte
              </button>
              <button
                class="pill ghost"
                type="button"
                :class="{ on: showAllCoversInModal }"
                @click="setCoversModalFilter(true)"
              >
                Mostra tutte
              </button>
            </div>
            <button
              class="pill primary tiny"
              type="button"
              @click="openAllCovers"
            >
              Apri tutte
            </button>
            <button
              class="pill danger tiny"
              type="button"
              @click="closeAllCovers"
            >
              Chiudi tutte
            </button>
          </div>
          <div v-if="modalCoverDevices.length" class="active-lights-list">
            <article
              v-for="cover in modalCoverDevices"
              :key="cover.id"
              class="active-light-card cover-card"
            >
              <div class="active-light-body">
                <div class="cover-info">
                  <p class="light-label">{{ cover.name }}</p>
                  <p class="muted tiny">{{ coverStateLabel(cover.ref) }}</p>
                  <small class="muted">{{ cover.roomName }}</small>
                </div>
                <div class="cover-controls">
                  <button class="pill ghost tiny" type="button" @click="openCover(cover.ref)">Apri</button>
                  <button class="pill ghost tiny" type="button" @click="stopCover(cover.ref)">Stop</button>
                  <button class="pill ghost tiny" type="button" @click="closeCover(cover.ref)">Chiudi</button>
                </div>
              </div>
              <div class="cover-slider">
                <input
                  type="range"
                  min="0"
                  max="100"
                  :value="getCoverPosition(cover.ref)"
                  @input="setCoverPosition(cover.ref, $event.target.value)"
                  class="slider"
                />
                <span class="slider-value">{{ getCoverPosition(cover.ref) }}%</span>
              </div>
            </article>
          </div>
          <p v-else class="muted">
            {{ showAllCoversInModal ? 'Nessuna tapparella disponibile.' : 'Nessuna tapparella risulta aperta.' }}
          </p>
        </div>
      </div>
    </transition>

    <!-- Gates Modal -->
    <transition name="fade">
      <div v-if="gatesModalOpen" class="lights-overlay" role="dialog" aria-modal="true">
        <div class="lights-panel card" @click.stop>
          <header class="panel-head">
            <div>
              <p class="eyebrow">Controllo</p>
              <h3>Cancelli e Portoni</h3>
              <small class="muted tiny" v-if="gatesList.length">{{ gatesList.length }} {{ gatesList.length === 1 ? 'cancello' : 'cancelli' }}</small>
            </div>
            <button class="ghost-btn icon-only" type="button" @click="closeGatesModal" aria-label="Chiudi">
              <span class="icon" aria-hidden="true" v-html="iconMarkup('close')"></span>
            </button>
          </header>
          <div v-if="gatesList.length" class="active-lights-list">
            <article
              v-for="gate in gatesList"
              :key="gate.id"
              class="active-light-card"
              @click="activateGate(gate)"
              style="cursor: pointer;"
            >
              <div class="active-light-head">
                <div class="active-light-info">
                  <h5 class="active-light-name">{{ gate.name }}</h5>
                  <p v-if="gate.state && gate.state !== 'unknown'" class="muted tiny">{{ gate.state }}</p>
                </div>
                <button
                  class="pill primary"
                  type="button"
                  @click.stop="activateGate(gate)"
                >
                  Apri
                </button>
              </div>
            </article>
          </div>
          <p v-else class="muted">Nessun cancello disponibile.</p>
        </div>
      </div>
    </transition>

    <transition name="fade">
      <div
        v-if="doorbellPickerOpen"
        class="doorbell-picker-overlay"
        role="dialog"
        aria-modal="true"
        @click.self="closeDoorbellPicker"
      >
        <div class="doorbell-picker-panel card">
          <header class="panel-head">
            <div>
              <p class="eyebrow">Campanelli</p>
              <h3>Apri manualmente</h3>
              <small class="muted tiny" v-if="doorbellSources.length">{{ doorbellSources.length }} disponibili</small>
            </div>
            <button class="ghost-btn icon-only" type="button" @click="closeDoorbellPicker" aria-label="Chiudi selezione campanello">
              <span class="icon" aria-hidden="true" v-html="iconMarkup('close')"></span>
            </button>
          </header>
          <div v-if="doorbellSources.length" class="doorbell-picker-grid">
            <button
              v-for="entry in doorbellSources"
              :key="entry.id"
              class="doorbell-picker-btn"
              type="button"
              @click="triggerDoorbellFromPicker(entry)"
            >
              <div class="doorbell-picker-btn-head">
                <span class="icon" aria-hidden="true" v-html="iconMarkup('doorbell')"></span>
                <div>
                  <strong>{{ entry.label }}</strong>
                  <small class="muted tiny">{{ formatDoorbellPickerMeta(entry) }}</small>
                </div>
              </div>
              <p class="muted tiny" v-if="entry.gates.length">
                {{ entry.gates.length }} cancello{{ entry.gates.length > 1 ? 'i' : '' }} collegato{{ entry.gates.length > 1 ? 'i' : '' }}
              </p>
            </button>
          </div>
          <p v-else class="muted">Nessun campanello configurato.</p>
        </div>
      </div>
    </transition>

    <transition name="fade">
      <div
        v-if="weatherDetailsOpen"
        class="weather-overlay"
        role="dialog"
        aria-modal="true"
        @click.self="closeWeatherDetails"
      >
        <div class="weather-panel card">
          <header class="panel-head">
            <div>
              <p class="eyebrow">Meteo</p>
              <h3>{{ weatherSnapshot.condition }}</h3>
              <small class="muted">{{ weatherDetails.location || 'Stazione locale' }}</small>
            </div>
            <button class="ghost-btn icon-only" type="button" @click="closeWeatherDetails" aria-label="Chiudi dettagli meteo">
              <span class="icon" aria-hidden="true" v-html="iconMarkup('close')"></span>
            </button>
          </header>

          <div class="weather-current">
            <div class="current-temp">
              <span class="temp-display">{{ weatherSnapshot.temperature }}</span>
              <span class="muted tiny" v-if="weatherDetails.feelsLike">
                Percepita {{ weatherDetails.feelsLike }}
              </span>
            </div>
            <div class="weather-metrics">
              <div v-for="metric in weatherDetails.metrics" :key="metric.label" class="metric-chip">
                <p class="tiny muted">{{ metric.label }}</p>
                <strong>{{ metric.value }}</strong>
                <small v-if="metric.meta" class="muted">{{ metric.meta }}</small>
              </div>
            </div>
          </div>

          <section class="forecast-section" v-if="weatherDetails.forecast.length">
            <div class="section-head">
              <p>Previsioni</p>
              <span class="muted tiny">Prossime ore</span>
            </div>
            <div class="forecast-scroll">
              <article v-for="entry in weatherDetails.forecast" :key="entry.key" class="forecast-chip">
                <p class="tiny muted">{{ entry.label }}</p>
                <span class="icon" aria-hidden="true" v-html="iconMarkup(entry.icon)"></span>
                <strong>{{ entry.temperature }}</strong>
                <small>{{ entry.condition }}</small>
              </article>
            </div>
          </section>

          <section class="forecast-section" v-if="weatherDetails.dailyForecast.length">
            <div class="section-head">
              <p>Prossimi giorni</p>
              <span class="muted tiny">Panoramica giornaliera</span>
            </div>
            <div class="forecast-grid">
              <article v-for="entry in weatherDetails.dailyForecast" :key="`daily-${entry.key}`" class="forecast-day">
                <p class="tiny muted">{{ entry.label }}</p>
                <span class="icon" aria-hidden="true" v-html="iconMarkup(entry.icon)"></span>
                <div class="day-temps">
                  <strong>{{ entry.high }}</strong>
                  <small v-if="entry.low">{{ entry.low }}</small>
                </div>
                <small>{{ entry.condition }}</small>
              </article>
            </div>
          </section>

          <p v-if="!weatherDetails.forecast.length && !weatherDetails.dailyForecast.length" class="muted tiny no-forecast">
            Nessuna previsione disponibile dal servizio HA configurato.
          </p>

          <p class="muted tiny updated-at" v-if="weatherDetails.updatedAt">
            Aggiornato {{ weatherDetails.updatedAt }}
          </p>
        </div>
      </div>
    </transition>

    <transition name="fade">
      <div
        v-if="snapshotPreview.open"
        class="snapshot-overlay"
        role="dialog"
        aria-modal="true"
        @click.self="closeSnapshotModal"
      >
        <div class="snapshot-panel card">
          <header class="panel-head">
            <div>
              <p class="eyebrow">Istantanea</p>
              <h3>{{ (snapshotPreview.camera && snapshotPreview.camera.name) || 'Telecamera' }}</h3>
              <small class="muted" v-if="snapshotPreview.fetchedAt">
                {{ formatSnapshotTimestamp(snapshotPreview.fetchedAt) }}
              </small>
            </div>
            <div class="snapshot-actions">
              <button class="ghost-btn tiny" type="button" @click="refreshSnapshotModal">Aggiorna</button>
              <button class="ghost-btn icon-only" type="button" @click="closeSnapshotModal" aria-label="Chiudi istantanea">
                <span class="icon" aria-hidden="true" v-html="iconMarkup('close')"></span>
              </button>
            </div>
          </header>
          <div class="snapshot-body">
            <p v-if="snapshotPreview.error" class="snapshot-error">{{ snapshotPreview.error }}</p>
            <div v-else class="snapshot-media">
              <img
                v-if="snapshotPreview.url"
                :src="snapshotPreview.url"
                :alt="`Istantanea ${(snapshotPreview.camera && snapshotPreview.camera.name) || ''}`"
                @load="handleSnapshotLoaded"
                @error="handleSnapshotError"
                draggable="false"
              />
              <div v-if="snapshotPreview.loading" class="snapshot-placeholder overlay">Caricamento in corso…</div>
            </div>
          </div>
          <footer class="snapshot-footer">
            <button
              class="pill ghost tiny"
              type="button"
              @click="openCameraSnapshot(snapshotPreview.camera, { external: true })"
            >
              Apri in nuova scheda
            </button>
          </footer>
        </div>
      </div>
    </transition>

    <transition name="fade">
      <div
        v-if="cameraViewer.open"
        class="camera-viewer-overlay"
        role="dialog"
        aria-modal="true"
        @click.self="closeCameraViewer"
      >
        <div class="camera-viewer-panel card">
          <header class="panel-head">
            <div>
              <p class="eyebrow">Telecamera live</p>
              <h3>{{ (cameraViewer.camera && cameraViewer.camera.name) || 'Telecamera' }}</h3>
              <small class="muted" v-if="cameraViewer.lastRefresh">
                Agg. {{ formatTime(cameraViewer.lastRefresh) }}
              </small>
            </div>
            <div class="snapshot-actions">
              <button
                v-if="cameraViewerCanForceHls"
                class="ghost-btn tiny"
                type="button"
                @click="forceCameraViewerHls"
                title="Prova la riproduzione HLS (sperimentale)"
              >
                Prova HLS
              </button>
              <button class="ghost-btn tiny" type="button" @click="refreshCameraViewer">Aggiorna ora</button>
              <button class="ghost-btn icon-only" type="button" @click="closeCameraViewer" aria-label="Chiudi telecamera">
                <span class="icon" aria-hidden="true" v-html="iconMarkup('close')"></span>
              </button>
            </div>
          </header>
          <div class="camera-viewer-body">
            <div class="camera-viewer-media" :class="{ loading: cameraViewer.loading }">
              <span
                v-if="isAdmin && cameraViewer.camera"
                class="camera-stream-chip camera-stream-chip--viewer"
                :class="cameraViewerStreamLabel() === 'HLS' ? 'camera-stream-chip--hls' : 'camera-stream-chip--mjpeg'"
              >
                {{ cameraViewerStreamLabel() }}
              </span>
              <div v-if="skipCameraPreviews && !cameraViewer.open" class="camera-viewer-name">
                <div class="camera-viewer-name-inner">
                  <strong>{{ (cameraViewer.camera && cameraViewer.camera.name) || 'Telecamera' }}</strong>
                </div>
              </div>
              <template v-if="cameraViewerRenderMode === 'hls' && cameraViewerHlsUrl">
                <video
                  :key="cameraViewerElementKey"
                  ref="cameraViewerVideo"
                  v-show="cameraViewerHlsBuffered && cameraViewerNativePlaying"
                  class="camera-viewer-video"
                  autoplay
                  muted
                  playsinline
                  controlslist="nodownload nofullscreen noremoteplayback"
                  disablepictureinpicture
                  @error="handleCameraViewerVideoError"
                  :aria-label="`Live ${(cameraViewer.camera && cameraViewer.camera.name) || ''}`"
                ></video>
                <!-- show snapshot / frozen frame while HLS is not yet playing -->
                <img
                  v-if="cameraViewerRenderMode === 'hls' && cameraViewerHlsUrl && !cameraViewerHlsBuffered"
                  ref="cameraViewerFallbackImg"
                  :src="cameraViewerFrozenFrame || (cameraViewer.camera ? cameraSnapshotUrl(cameraViewer.camera) : '')"
                  :alt="`Anteprima ${(cameraViewer.camera && cameraViewer.camera.name) || ''}`"
                  @load="handleCameraViewerLoaded"
                  @error="handleCameraViewerError($event)"
                  draggable="false"
                />
                <div v-if="cameraViewer.loading || (cameraViewerRenderMode === 'hls' && !cameraViewerHlsBuffered)" class="camera-viewer-placeholder overlay">
                  Connessione alla telecamera…
                  <div class="viewer-play-action" v-if="cameraViewerRenderMode === 'hls' && !cameraViewerHlsBuffered">
                    <button class="ghost-btn" type="button" @click.stop="playCameraViewer()">
                      <span class="icon" aria-hidden="true" v-html="iconMarkup('play')"></span>
                      <span>Riproduci</span>
                    </button>
                  </div>
                </div>
              </template>
              <img
                v-else-if="cameraViewer.url"
                :key="cameraViewerElementKey"
                :src="cameraViewer.url"
                :alt="`Live ${(cameraViewer.camera && cameraViewer.camera.name) || ''}`"
                @load="handleCameraViewerLoaded"
                @error="handleCameraViewerError($event)"
                draggable="false"
              />
              <div v-if="cameraViewer.loading" class="camera-viewer-placeholder overlay">
                Connessione alla telecamera…
              </div>
            </div>
            <p v-if="cameraViewer.error" class="snapshot-error">{{ cameraViewer.error }}</p>
          </div>
          <footer class="snapshot-footer">
            <small class="muted tiny">La diretta si aggiorna automaticamente mentre questa finestra è aperta.</small>
          </footer>
        </div>
      </div>
    </transition>

    <transition name="fade">
      <div
        v-if="doorbellAlert.open"
        class="doorbell-overlay"
        role="dialog"
        aria-modal="true"
        @click.self="closeDoorbellAlert"
      >
        <div class="doorbell-panel card">
          <header class="panel-head doorbell-head">
            <div>
              <p class="eyebrow">Campanello</p>
              <h3>{{ doorbellAlert.doorbellLabel || 'Campanello' }}</h3>
              <small class="muted" v-if="doorbellAlert.triggeredAt">
                {{ formatTime(doorbellAlert.triggeredAt) }}
              </small>
            </div>
            <div class="doorbell-head-actions">
              <span class="muted tiny" v-if="activeDoorbellVideo && activeDoorbellVideo.camera">
                {{ activeDoorbellVideo.camera.name }}
              </span>
              <button class="ghost-btn icon-only" type="button" @click="closeDoorbellAlert" aria-label="Chiudi campanello">
                <span class="icon" aria-hidden="true" v-html="iconMarkup('close')"></span>
              </button>
            </div>
          </header>

          <section class="doorbell-body">
            <div
              v-if="doorbellAlert.videos && doorbellAlert.videos.length"
              class="doorbell-media"
              aria-live="polite"
            >
              <button
                v-if="doorbellAlert.videos.length > 1"
                class="doorbell-video-arrow doorbell-video-arrow--left"
                type="button"
                aria-label="Telecamera precedente"
                @click="stepDoorbellVideo(-1)"
              >
                <span class="icon" aria-hidden="true" v-html="iconMarkup('arrowLeft')"></span>
              </button>
              <div class="doorbell-video-frame" :class="{ 'is-hls': doorbellVideoRenderMode === 'hls' }">
                <template v-if="doorbellVideoRenderMode === 'hls'">
                  <video
                    :key="doorbellVideoElementKey"
                    ref="doorbellVideoEl"
                    class="doorbell-video"
                    autoplay
                    muted
                    playsinline
                    controlslist="nodownload nofullscreen noremoteplayback"
                    disablepictureinpicture
                    v-show="doorbellHlsBuffered"
                    @playing="handleDoorbellPlaying"
                    @error="handleDoorbellVideoError"
                    :aria-label="`Live ${doorbellAlert.doorbellLabel || 'campanello'}`"
                  ></video>
                  <div v-if="doorbellHlsLoading || (doorbellVideoRenderMode === 'hls' && !doorbellHlsBuffered)" class="doorbell-video-placeholder overlay">
                    Connessione al flusso…
                  </div>
                  <p v-if="doorbellHlsError" class="doorbell-video-error">{{ doorbellHlsError }}</p>
                </template>
                <template v-else>
                  <img
                    :key="doorbellVideoElementKey"
                    :src="activeDoorbellVideoUrl"
                    :alt="`Live ${doorbellAlert.doorbellLabel || 'campanello'}`"
                    loading="eager"
                    draggable="false"
                    @load="handleDoorbellFallbackLoaded"
                    @error="handleDoorbellFallbackError"
                  />
                  <div v-if="doorbellFallbackError" class="doorbell-video-placeholder overlay">
                    {{ doorbellFallbackError }}
                  </div>
                </template>
                <div
                  v-if="doorbellAlert.videos.length > 1"
                  class="doorbell-video-controls"
                >
                  <button class="ghost-btn tiny" type="button" @click="stepDoorbellVideo(-1)">
                    Precedente
                  </button>
                  <button class="ghost-btn tiny" type="button" @click="stepDoorbellVideo(1)">
                    Successivo
                  </button>
                </div>
              </div>
              <button
                v-if="doorbellAlert.videos.length > 1"
                class="doorbell-video-arrow doorbell-video-arrow--right"
                type="button"
                aria-label="Telecamera successiva"
                @click="stepDoorbellVideo(1)"
              >
                <span class="icon" aria-hidden="true" v-html="iconMarkup('arrowRight')"></span>
              </button>
            </div>

            <div
              v-if="doorbellAlert.videos && doorbellAlert.videos.length > 1"
              class="doorbell-video-selector"
              role="tablist"
              aria-label="Telecamere disponibili"
            >
              <button
                v-for="(video, index) in doorbellAlert.videos"
                :key="video.camera?.id || video.tag || index"
                type="button"
                class="doorbell-video-chip"
                :class="{ active: index === doorbellAlert.videoIndex }"
                role="tab"
                :aria-selected="index === doorbellAlert.videoIndex"
                @click="setDoorbellVideo(index)"
              >
                {{ (video.camera && video.camera.name) || `Video ${index + 1}` }}
              </button>
            </div>

            <section v-if="doorbellAlert.gates && doorbellAlert.gates.length" class="doorbell-gates">
              <div class="section-head compact">
                <p>Comandi cancello</p>
                <span class="muted tiny">{{ doorbellAlert.gates.length }} disponibili</span>
              </div>
              <div class="doorbell-gate-grid">
                <button
                  v-for="gate in doorbellAlert.gates"
                  :key="gate.device?.id || gate.label"
                  class="pill doorbell-gate-btn"
                  type="button"
                  :disabled="!gate.device"
                  @click="triggerGateDevice(gate.device)"
                >
                  {{ gate.label || 'Cancello' }}
                </button>
              </div>
            </section>
          </section>
        </div>
      </div>
    </transition>

    <transition name="fade">
      <div
        v-if="devicePanel.open"
        class="device-overlay"
        role="dialog"
        aria-modal="true"
        @click.self="closeDevicePanel"
      >
        <div class="device-panel card">
          <header class="panel-head">
            <div>
              <p class="eyebrow">{{ devicePanel.roomName || 'Illuminazione' }}</p>
              <h3>{{ devicePanel.device?.name }}</h3>
              <span class="state-chip" :class="{ on: isOn(devicePanel.device) }">
                {{ isOn(devicePanel.device) ? 'Accesa' : 'Spenta' }}
              </span>
            </div>
            <button class="ghost-btn icon-only" type="button" @click="closeDevicePanel" aria-label="Chiudi pannello luce">
              <span class="icon" aria-hidden="true" v-html="iconMarkup('close')"></span>
            </button>
          </header>

          <section v-if="panelSupportsBrightness" class="panel-section">
            <div class="section-head">
              <p>Luminosità</p>
              <span>{{ panelBrightnessPercent }}%</span>
            </div>
            <div class="slider-row">
              <input
                type="range"
                min="1"
                max="255"
                :value="devicePanel.brightness"
                @input="previewPanelBrightness($event.target.value)"
                @change="commitPanelBrightness"
              />
            </div>
          </section>

          <section v-if="panelSupportsColorTemp" class="panel-section">
            <div class="section-head">
              <p>Tonalità</p>
              <span>{{ panelColorTempLabel }}</span>
            </div>
            <div class="slider-row">
              <input
                type="range"
                :min="panelColorTempRange.min"
                :max="panelColorTempRange.max"
                :value="devicePanel.colorTemp || panelColorTempRange.min"
                @input="previewPanelColorTemp($event.target.value)"
                @change="commitPanelColorTemp"
              />
            </div>
          </section>

          <section v-if="panelSupportsColor" class="panel-section">
            <div class="section-head">
              <p>Colore</p>
              <span>{{ devicePanel.color }}</span>
            </div>
            <div class="color-palette">
              <button
                v-for="preset in colorPresets"
                :key="preset"
                type="button"
                class="swatch"
                :class="{ active: preset === devicePanel.color }"
                :style="{ '--swatch-color': preset }"
                @click="applyPanelColor(preset)"
                :aria-label="`Imposta colore ${preset}`"
              ></button>
            </div>
            <div class="hue-slider">
              <input
                type="range"
                min="0"
                max="360"
                :value="devicePanel.hue"
                @input="previewPanelHue($event.target.value)"
                @change="commitPanelHue"
              />
              <div class="hue-track" :style="{ background: hueGradient }"></div>
            </div>
          </section>

          <p v-if="devicePanel.open && !panelHasControls" class="muted no-controls">Nessun controllo aggiuntivo disponibile per questa luce.</p>
        </div>
      </div>
    </transition>
  </div>
</template>

<script>
import axios from 'axios'
import Hls from 'hls.js'
import {
  callLightService,
  extractBrightness,
  extractRgb,
  rgbToHex,
  hexToRgb,
  normalizeBrightness,
  isValidHexColor
} from '../utils/lightControl'
import brandLogoImg from '../assets/logos/e-face_nobg.png'

const ICONS = {
  default: '<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M3 10.5 12 4l9 6.5V20a1 1 0 0 1-1 1h-5v-5H9v5H4a1 1 0 0 1-1-1Z"/></svg>',
  sun: '<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="4.5"/><path d="M12 2v2M12 20v2M4 12H2M22 12h-2M5.64 5.64 4.22 4.22M19.78 19.78l-1.42-1.42M19.78 4.22l-1.42 1.42M4.22 19.78l1.42-1.42"/></svg>',
  cloud: '<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M7 18a4 4 0 0 1 0-8h.5A5.5 5.5 0 0 1 17 7.5a4.5 4.5 0 0 1 .5 9H7Z"/></svg>',
  rain: '<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M6 15a4 4 0 0 1 .5-8A5.5 5.5 0 0 1 17 7.5a4.5 4.5 0 0 1 .5 9H6Z"/><path d="m8 19-1 3M12 19l-1 3M16 19l-1 3"/></svg>',
  storm: '<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M6 15a4 4 0 0 1 .5-8A5.5 5.5 0 0 1 17 7.5a4.5 4.5 0 0 1 .5 9H6Z"/><path d="M10 13h3l-2 4h3l-3 5"/></svg>',
  snow: '<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/XMLSchema" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="2"/><path d="M12 4v4M12 16v4M4 12h4M16 12h4M7 7l2.5 2.5M14.5 14.5 17 17M17 7l-2.5 2.5M9.5 14.5 7 17"/></svg>',
  wind: '<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M4 12h9a2 2 0 1 0-2-2"/><path d="M2 16h13a3 3 0 1 1-3 3"/></svg>',
  settings: '<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" strokeLinejoin="round"><path d="M10.343 3.94c.09-.54.56-.94 1.11-.94h1.093c.55 0 1.02.4 1.11.94l.15.894c.07.424.383.764.78.93.398.164.855.142 1.204-.108l.738-.527a1.125 1.125 0 0 1 1.45.12l.773.774c.39.39.44 1.002.12 1.45l-.527.737c-.25.35-.272.806-.107 1.204.165.397.505.71.93.78l.894.15c.54.09.94.56.94 1.109v1.094c0 .55-.4 1.02-.94 1.109l-.894.15c-.425.07-.765.383-.93.78-.165.398-.143.854.107 1.204l.527.738c.32.448.27 1.06-.12 1.45l-.774.774a1.125 1.125 0 0 1-1.449.12l-.738-.527c-.35-.25-.806-.272-1.204-.107-.397.165-.71.505-.78.93l-.15.894c-.09.54-.56.94-1.11.94h-1.093c-.55 0-1.02-.4-1.11-.94l-.15-.894c-.07-.425-.383-.765-.78-.93-.398-.165-.854-.143-1.204.107l-.737.527a1.125 1.125 0 0 1-1.45-.12l-.773-.774a1.125 1.125 0 0 1-.12-1.45l.527-.737c.25-.35.272-.806.107-1.204-.165-.397-.505-.71-.93-.78l-.894-.15c-.54-.09-.94-.56-.94-1.109v-1.094c0-.55.4-1.019.94-1.108l.894-.15c.424-.07.765-.383.93-.78.165-.398.143-.854-.107-1.204l-.527-.738a1.125 1.125 0 0 1 .12-1.449l.773-.774a1.125 1.125 0 0 1 1.45-.12l.737.527c.35.25.807.272 1.204.107.397-.165.71-.505.78-.93l.15-.894Z"/><path d="M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z"/></svg>',
  doorbell: '<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><rect x="7" y="2.5" width="10" height="19" rx="2"/><circle cx="12" cy="8" r="1.5"/><path d="M10 13h4v5a2 2 0 0 1-2 2 2 2 0 0 1-2-2Z"/><path d="M5.5 8c0-3 2-5 4-5.5"/><path d="M18.5 8c0-3-2-5-4-5.5"/></svg>',
  bulb: '<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" strokeLinejoin="round"><path d="M12 3a5 5 0 0 1 5 5c0 1.9-.9 3.2-2 4.2-.5.4-.8.9-.8 1.5V16H9.8v-2.3c0-.6-.3-1.1-.8-1.5-1.1-1-2-2.3-2-4.2a5 5 0 0 1 5-5Z"/><path d="M9 20h6"/><path d="M10 22h4"/></svg>',
  shield: '<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" strokeLinejoin="round"><path d="M12 3 20 6v6c0 4.6-3.2 8.8-8 10-4.8-1.2-8-5.4-8-10V6l8-3Z"/></svg>',
  play: '<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" strokeLinecap="round" strokeLinejoin="round"><path d="M9 7v10l8-5-8-5Z"/></svg>',
  thermo: '<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" strokeLinecap="round" strokeLinejoin="round"><path d="M12 3a2 2 0 0 0-2 2v9.76a4 4 0 1 0 4 0V5a2 2 0 0 0-2-2Z"/></svg>',
  home: '<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" strokeLinecap="round" strokeLinejoin="round"><path d="M3 10.5 12 4l9 6.5V20a1 1 0 0 1-1 1h-5v-5H9v5H4a1 1 0 0 1-1-1Z"/></svg>',
  bed: '<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/XMLSchema" fill="none" stroke="currentColor" stroke-width="1.5" strokeLinecap="round" strokeLinejoin="round"><path d="M3 11h18v9H3z"/><path d="M3 16h18"/></svg>',
  bath: '<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" strokeLinecap="round" strokeLinejoin="round"><path d="M5 7a2 2 0 0 1 2-2h1"/><path d="M3 13h18v2a4 4 0 0 1-4 4H7a4 4 0 0 1-4-4v-2Z"/><path d="M6 19v2M18 19v2"/></svg>',
  desk: '<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" strokeLinecap="round" strokeLinejoin="round"><path d="M4 10h16v7H4z"/><path d="M8 17v4M16 17v4"/></svg>',
  sofa: '<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" strokeLinecap="round" strokeLinejoin="round"><path d="M4 12a3 3 0 0 1 3-3h10a3 3 0 0 1 3 3v4H4Z"/><path d="M6 16v3M18 16v3"/></svg>',
  plug: '<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" strokeLinecap="round" strokeLinejoin="round"><path d="M9 2v6m6-6v6"/><path d="M7 12h10v4a4 4 0 0 1-4 4h-2a4 4 0 0 1-4-4v-4Z"/></svg>',
  power: '<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2v10"/><path d="M18.36 6.64A9 9 0 1 1 5.64 6.64"/></svg>',
  minus: '<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="5" y1="12" x2="19" y2="12"/></svg>',
  plus: '<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>',
  droplet: '<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2.69l5.66 5.66a8 8 0 1 1-11.31 0z"/></svg>',
  blinds: '<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18M3 15h18"/></svg>',
  chevronUp: '<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="18 15 12 9 6 15"/></svg>',
  chevronDown: '<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"/></svg>',
  pause: '<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="6" y="4" width="4" height="16"/><rect x="14" y="4" width="4" height="16"/></svg>',
  close: '<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" strokelinecap="round" strokeLinejoin="round"><path d="m6 6 12 12M18 6 6 18"/></svg>',
  cloud: '<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M17.5 19H7a4 4 0 0 1-.5-8A5.5 5.5 0 0 1 17 7.5a4.5 4.5 0 0 1 .5 9Z"/></svg>',
  cloudOff: '<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="m3 3 18 18"/><path d="M18 18H7a4 4 0 0 1-.5-8 5.5 5.5 0 0 1 9.22-4"/></svg>',
  lan: '<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><rect x="6" y="3" width="12" height="6" rx="1.5"/><path d="M12 9v4"/><rect x="4" y="15" width="6" height="6" rx="1"/><rect x="14" y="15" width="6" height="6" rx="1"/></svg>',
  refresh: '<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M3 12a9 9 0 0 1 15.36-6.36L21 8"/><path d="M21 4v4h-4"/><path d="M21 12a9 9 0 0 1-15.36 6.36L3 16"/><path d="M3 20v-4h4"/></svg>',
  camera: '<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M4 7h4.5L10 5h4l1.5 2H20a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V9a2 2 0 0 1 2-2Z"/><circle cx="12" cy="13" r="3.5"/></svg>',
  cameraOff: '<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M10.5 5h3l1.5 2H20a2 2 0 0 1 2 2v6.5"/><path d="M3 7h4.5"/><path d="M2 2l20 20"/><path d="M6 19h12a2 2 0 0 0 2-2v-1"/><path d="M9.5 13a2.5 2.5 0 0 0 3.5 3.5"/></svg>',
  grid: '<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>',
  rows: '<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M4 6h16"/><path d="M4 12h16"/><path d="M4 18h16"/></svg>',
  arrowLeft: '<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M15 5l-7 7 7 7"/><path d="M5 12h14"/></svg>',
  arrowRight: '<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="m9 5 7 7-7 7"/><path d="M19 12H5"/></svg>',
  gate: '<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><rect x="4" y="6" width="16" height="14" rx="1"/><path d="M12 6V20"/><path d="M8 6v14"/><path d="M16 6v14"/><circle cx="15" cy="13" r="1" fill="currentColor"/></svg>'
}

const defaultSnapshotState = () => ({
  open: false,
  camera: null,
  url: '',
  fetchedAt: null,
  loading: false,
  error: null
})

const CAMERA_VIEWER_REFRESH_INTERVAL = 15000
// Increased timeout to tolerate slower playlist proxy responses
const CAMERA_VIEWER_HLS_TIMEOUT = 20000
const CAMERA_VIEWER_HLS_BLACKLIST_TTL = 2 * 60 * 1000
const CAMERA_VIEWER_HLS_MAX_RETRIES = 3
// require this many fragments/parts buffered before showing video to avoid flash
const CAMERA_VIEWER_HLS_BUFFERED_FRAGMENTS = 4
// require at least this many buffered seconds before showing video
const CAMERA_VIEWER_HLS_MIN_BUFFERED_SECONDS = 1.0
const CAMERA_VIEWER_SNAPSHOT_INTERVAL = 4000
const CAMERA_STREAM_SESSION_TIMEOUTS = Object.freeze({
  auto: 6000,
  doorbell: 10000,
  manual: 12000
})
const DOORBELL_HLS_TIMEOUT = 6000
const CAMERA_HLS_SCOPE_VIEWER = 'viewer'
const CAMERA_HLS_SCOPE_DOORBELL = 'doorbell'
const CAMERA_RESUME_STAGGER_DELAY = 400 // spread camera restarts to avoid hammering HA
const CAMERA_RESUME_BATCH_SIZE = 3

const defaultCameraViewerState = () => ({
  open: false,
  camera: null,
  url: '',
  loading: false,
  error: null,
  lastRefresh: null
})

const defaultDoorbellAlertState = () => ({
  open: false,
  doorbellId: null,
  doorbellLabel: '',
  triggeredAt: null,
  videoIndex: 0,
  videos: [],
  gates: []
})

const STREAM_SUSPEND_PRIORITY = {
  manual: 1,
  'visibility-hidden': 2,
  pagehide: 3,
  beforeunload: 4,
  unmount: 5
}

const STREAM_RESUME_RULES = {
  manual: new Set(['manual']),
  'visibility-hidden': new Set(['visibility-visible', 'pageshow', 'manual']),
  pagehide: new Set(['pageshow', 'visibility-visible', 'manual']),
  beforeunload: new Set(['manual']),
  unmount: new Set()
}

export default {
  name: 'Dashboard',
  props: {
    rooms: {
      type: Array,
      default: () => []
    },
    devices: {
      type: Array,
      default: () => []
    },
    securityDevices: {
      type: Array,
      default: () => []
    },
    roomName: {
      type: String,
      default: ''
    },
    currentRoom: {
      type: [String, Number, null],
      default: null
    },
    isAdmin: {
      type: Boolean,
      default: false
    },
    connMode: {
      type: String,
      default: 'unknown'
    },
    haConnected: {
      type: Boolean,
      default: false
    },
    backendConnected: {
      type: Boolean,
      default: false
    },
    weather: {
      type: Object,
      default: null
    },
    meta: {
      type: Object,
      default: () => ({})
    }
  },
  emits: ['open-settings', 'refresh-room', 'room-selected'],
  data() {
    return {
      brandLogo: brandLogoImg,
      categories: [
        { id: 'overview', label: 'Panoramica', icon: 'grid' },
        { id: 'lights', label: 'Illuminazione', icon: 'bulb' },
        { id: 'media', label: 'Media', icon: 'play' },
        { id: 'security', label: 'Sicurezza', icon: 'shield' },
        { id: 'comfort', label: 'Comfort', icon: 'thermo' }
      ],
      activeCategory: 'overview',
      currentRoomId: this.currentRoom ?? null,
      lastCommand: null,
      lastRefresh: Date.now(),
      lightsModalOpen: false,
      showAllLightsInModal: false,
      coversModalOpen: false,
      showAllCoversInModal: false,
      gatesModalOpen: false,
      haWeather: null,
      weatherDetailsOpen: false,
      sceneTriggering: null,
      devicePanel: {
        open: false,
        device: null,
        roomName: '',
        brightness: 0,
        color: '#ffffff',
        hue: 0,
        colorTemp: null,
        supportsBrightness: false,
        supportsColor: false,
        supportsColorTemp: false
      },
      colorPresets: ['#ffffff', '#ffe1c4', '#ffd369', '#ffb3c6', '#f7aef8', '#cdb4ff', '#9bf6ff', '#a7ff83'],
      pendingRoomRefresh: null,
      optimisticStates: {},
      optimisticTimers: {},
      doorbellPickerOpen: false,
      cameraErrors: {},
      cameraStreamSeeds: {},
      cameraFallbacks: {},
      cameraRefreshing: {},
      cameraRefreshTimers: {},
      cameraResumeTimeouts: [],
      snapshotPreview: defaultSnapshotState(),
      cameraViewer: defaultCameraViewerState(),
      cameraViewerRefreshTimer: null,
      cameraViewerHlsTimeout: null,
      cameraViewerHlsBlacklist: {},
      securityView: null,
      doorbellStateCache: {},
      doorbellAlert: defaultDoorbellAlertState(),
      doorbellVideoRefreshTimer: null,
      doorbellFallbackStreaming: false,
      doorbellHlsBuffered: false,
      cameraHlsSessions: {},
      doorbellHlsController: null,
      doorbellHlsSourceUrl: '',
      doorbellHlsLoading: false,
      doorbellHlsError: null,
      doorbellHlsDisabled: false,
      doorbellHlsRetryTimer: null,
      doorbellHlsRetryAttempts: 0,
      doorbellHlsMaxRetries: 3,
      doorbellVideoElementKey: 0,
      doorbellVideoRefreshInFlight: false,
      doorbellHlsTimeout: null,
      doorbellHlsErrorCount: 0,
      doorbellFallbackError: null,
      cameraViewerHlsController: null,
      cameraViewerHlsUrl: '',
      cameraViewerHlsDisabled: false,
      cameraViewerHlsBuffered: false,
      cameraViewerNativePlaying: false,
      cameraViewerHlsFragBufferedCount: 0,
      cameraViewerHlsErrorCount: 0,
      cameraViewerHlsStallCount: 0,
      cameraViewerHlsNetworkFailCount: 0,
      cameraViewerHlsBufferedCandidateAt: 0,
      cameraViewerHlsBufferedConfirmTimer: null,
      cameraViewerElementKey: 0,
      // TEST FLAG: when true, do not load MJPEG/HLS previews — show names only
      skipCameraPreviews: true,
      // When false, mosaic preview images are disabled. Automatically set false when opening viewer.
      mosaicPreviewsEnabled: true,
      // Stati ottimistici per le tapparelle
      coverOptimisticStates: new Map(),
      coverMovingStates: new Map(),
      cameraViewerHlsRetryTimer: null,
      cameraViewerHlsRetryAttempts: 0,
      cameraViewerSnapshotTimer: null,
      cameraViewerSnapshotMode: false,
      cameraViewerHlsProbeEnabled: true,
      cameraViewerAutoHlsEnabled: true,
      streamsSuspended: false,
      streamSuspendReason: null,
      streamGuardHandlers: {
        visibility: null,
        pageHide: null,
        pageShow: null,
        beforeUnload: null
      }
    }
  },
  computed: {
    roomNameLabel() {
      if (this.roomName) return this.roomName
      return this.currentRoomObj?.name || 'Ambiente'
    },
    structuredRooms() {
      const rooms = Array.isArray(this.rooms) ? this.rooms : []
      const looseDevices = Array.isArray(this.devices) ? this.devices : []
      if (rooms.length) {
        const devicesByRoomId = new Map()
        const devicesByRoomSlug = new Map()
        const registerDevice = (bucket, key, device) => {
          if (key === null || typeof key === 'undefined') return
          if (typeof key === 'string' && !key.trim()) return
          if (!bucket.has(key)) bucket.set(key, [])
          bucket.get(key).push(device)
        }
        looseDevices.forEach((device) => {
          if (!device) return
          const roomIdCandidate =
            device.room_id ??
            device.area_id ??
            device.roomId ??
            device.areaId ??
            device.attributes?.room_id ??
            device.attributes?.area_id
          const normalizedRoomId =
            typeof roomIdCandidate === 'undefined' ? null : this.normalizeRoomId(roomIdCandidate)
          if (normalizedRoomId !== null) {
            registerDevice(devicesByRoomId, normalizedRoomId, device)
          }
          const slugSource =
            device.area_name ||
            device.room_name ||
            device.attributes?.room_name ||
            device.attributes?.area ||
            ''
          const slug = this.normalizeRoomSlug(slugSource)
          if (slug) {
            registerDevice(devicesByRoomSlug, slug, device)
          }
        })
        return rooms.map((room) => {
          const roomId = this.normalizeRoomId(room.id)
          const slug = this.normalizeRoomSlug(room.name)
          const primaryDevices = Array.isArray(room.devices) ? room.devices : []
          const supplemental = [
            ...(roomId !== null && devicesByRoomId.has(roomId) ? devicesByRoomId.get(roomId) : []),
            ...(slug && devicesByRoomSlug.has(slug) ? devicesByRoomSlug.get(slug) : [])
          ]
          return {
            ...room,
            devices: this.mergeDeviceLists(primaryDevices, supplemental),
            cameras: Array.isArray(room.cameras) ? room.cameras : []
          }
        })
      }
      if (looseDevices.length) {
        const label = this.roomName || 'Ambiente'
        return [{ id: this.currentRoom || 'default-room', name: label, devices: looseDevices, cameras: [] }]
      }
      return []
    },
    connectionStatusChip() {
      const normalizedMode = (this.connMode || '').toLowerCase()
      if (!this.haConnected) {
        if (normalizedMode === 'cloud') {
          return { label: 'Cloud', details: 'Connessione…', icon: 'cloud', tone: 'cloud' }
        }
        if (normalizedMode === 'local') {
          return { label: 'Locale', details: 'Connessione…', icon: 'lan', tone: 'local' }
        }
        return { label: 'Offline', details: 'In attesa', icon: 'cloudOff', tone: 'offline' }
      }
      if (normalizedMode === 'cloud') {
        return { label: 'Cloud', details: 'Tunnel remoto', icon: 'cloud', tone: 'cloud' }
      }
      return { label: 'Locale', details: 'Rete interna', icon: 'lan', tone: 'local' }
    },
    currentRoomObj() {
      if (!this.currentRoomId) return null
      return this.structuredRooms.find((room) => room.id === this.currentRoomId) || null
    },
    visibleRooms() {
      if (!this.structuredRooms.length) return []
      if (!this.currentRoomId) return this.structuredRooms
      const focused = this.structuredRooms.filter((room) => room.id === this.currentRoomId)
      const rest = this.structuredRooms.filter((room) => room.id !== this.currentRoomId)
      return [...focused, ...rest]
    },
    hasLights() {
      return this.totalLights > 0
    },
    totalLights() {
      return this.structuredRooms.reduce((acc, room) => acc + (room.devices?.length || 0), 0)
    },
    activeLights() {
      return this.structuredRooms.reduce((acc, room) => acc + this.roomActiveLights(room), 0)
    },
    activeCategoryLabel() {
      return this.categories.find((cat) => cat.id === this.activeCategory)?.label || ''
    },
    placeholderTiles() {
      const base = {
        media: [
          { title: 'Cinema', desc: 'Scene Dolby Atmos' },
          { title: 'Playlist', desc: 'Audio multi-room' },
          { title: 'Streaming', desc: 'Ingressi HDMI e ARC' }
        ],
        security: [
          { title: 'Ingressi', desc: 'Sensori porte/finestre' },
          { title: 'Telecamere', desc: 'Dirette IP H.265' },
          { title: 'Automazioni', desc: 'Inserimento intelligente' }
        ],
        comfort: [
          { title: 'Clima', desc: 'Temperatura e qualità aria' },
          { title: 'Tende', desc: 'Scene sunrise/sunset' },
          { title: 'Qualità aria', desc: 'PM2.5 e umidità' }
        ]
      }
      return base[this.activeCategory] || []
    },
    uniqueCameraList() {
      const map = new Map()
      const source = Array.isArray(this.rooms) && this.rooms.length ? this.rooms : this.structuredRooms
      source.forEach((room) => {
        const entries = Array.isArray(room?.cameras) ? room.cameras : []
        entries.forEach((camera) => {
          const key = this.cameraKey(camera)
          if (!key || map.has(key)) return
          map.set(key, camera)
        })
      })
      this.flattenedDevices().forEach(({ device }) => {
        if (!this.isCameraDevice(device)) return
        if (!this.hasTvccTag(device)) return
        const key = this.cameraKey(device)
        if (!key || map.has(key)) return
        map.set(key, device)
      })
      return Array.from(map.values())
    },
    globalCameraList() {
      return this.uniqueCameraList.filter((camera) => this.isGlobalCamera(camera))
    },
    totalCameraCount() {
      return this.uniqueCameraList.length
    },
    assignedCameraRooms() {
      return this.structuredRooms
        .map((room) => {
          const scoped = (room.cameras || []).filter((camera) => this.cameraBelongsToRoom(camera, room))
          if (!scoped.length) return null
          return { ...room, cameras: scoped }
        })
        .filter(Boolean)
    },
    cameraRoomsGrid() {
      const scopedRooms = this.assignedCameraRooms
      const entries = scopedRooms.length ? [...scopedRooms] : []

      if (this.globalCameraList.length) {
        entries.push({
          id: 'global-cameras',
          name: 'Accesso globale',
          isGlobal: true,
          background: null,
          cameras: this.globalCameraList
        })
      }

      if (!entries.length && this.uniqueCameraList.length) {
        return [
          {
            id: 'all-cameras',
            name: 'Telecamere',
            isGlobal: true,
            background: null,
            cameras: this.uniqueCameraList
          }
        ]
      }

      return entries
    },
    doorbellSources() {
      const entries = new Map()
      const ensureEntry = (slot) => {
        const id = slot || 'default'
        if (!entries.has(id)) {
          entries.set(id, {
            id,
            label: this.formatDoorbellLabel(id),
            triggers: [],
            videos: [],
            gates: []
          })
        }
        return entries.get(id)
      }
      const registerGate = (device, slot) => {
        const entry = ensureEntry(slot)
        entry.gates.push({
          device,
          label: this.gateLabelForDevice(device, slot)
        })
      }
      const registerDoorbellTag = (device, tag) => {
        const meta = this.parseDoorbellToken(tag)
        if (!meta) return
        const roles = this.doorbellRolesForDevice(device, meta)
        roles.forEach((role) => {
          const entry = ensureEntry(meta.slot)
          if (role === 'video' && this.isCameraDevice(device)) {
            entry.videos.push({ camera: device, priority: meta.priority ?? 1, tag })
          } else if (role === 'gate') {
            registerGate(device, meta.slot)
          } else if (role === 'trigger') {
            entry.triggers.push(device)
          }
        })
      }
      const processDevice = (device) => {
        if (!device) return
        const tags = this.extractDeviceTags(device)
        tags.forEach((tag) => {
          registerDoorbellTag(device, tag)
          const gate = this.parseGateTag(tag)
          if (gate) {
            registerGate(device, gate.slot)
          }
        })
      }
      this.flattenedDevices().forEach(({ device }) => processDevice(device))
      ;(this.uniqueCameraList || []).forEach((camera) => processDevice(camera))
      const dedupeByKey = (list, keyFn) => {
        const seen = new Set()
        return list.filter((item) => {
          const key = keyFn(item)
          if (!key) return true
          if (seen.has(key)) return false
          seen.add(key)
          return true
        })
      }
      return Array.from(entries.values()).map((entry) => {
        const videos = dedupeByKey(entry.videos, (video) => this.cameraKey(video.camera)).sort((a, b) => {
          if (a.priority !== b.priority) return a.priority - b.priority
          const aName = (a.camera?.name || '').toLowerCase()
          const bName = (b.camera?.name || '').toLowerCase()
          if (aName && bName) return aName.localeCompare(bName)
          return 0
        })
        const triggers = dedupeByKey(entry.triggers, (device) =>
          this.normalizeEntityIdKey(this.deviceEntityId(device))
        )
        const gates = dedupeByKey(entry.gates, (gate) =>
          this.normalizeEntityIdKey(this.deviceEntityId(gate.device))
        )
        return {
          ...entry,
          videos,
          triggers,
          gates
        }
      })
    },
    doorbellMap() {
      return this.doorbellSources.reduce((acc, entry) => {
        acc[entry.id] = entry
        return acc
      }, {})
    },
    doorbellTriggerIndex() {
      const map = {}
      this.doorbellSources.forEach((entry) => {
        entry.triggers.forEach((device) => {
          const entityId = this.normalizeEntityIdKey(this.deviceEntityId(device))
          if (!entityId) return
          map[entityId] = { entry, device }
        })
      })
      return map
    },
    activeDoorbellVideo() {
      if (!this.doorbellAlert.open) return null
      const list = Array.isArray(this.doorbellAlert.videos) ? this.doorbellAlert.videos : []
      if (!list.length) return null
      const index = Math.max(0, Math.min(list.length - 1, this.doorbellAlert.videoIndex || 0))
      return list[index]
    },
    activeDoorbellVideoUrl() {
      if (this.streamsSuspended) return ''
      const feed = this.activeDoorbellVideo
      if (!feed) return ''
      if (this.doorbellVideoRenderMode === 'hls') return ''
      const source = feed.camera || feed.device
      if (!source) return ''
      const rawUrl = this.cameraStreamSrc(source)
      if (!rawUrl) return ''
      return this.appendCacheBust(rawUrl, `doorbell-${this.doorbellAlert.doorbellId || 'feed'}`)
    },
    doorbellVideoRenderMode() {
      if (this.doorbellHlsSourceUrl) return 'hls'
      if (this.doorbellHlsDisabled) return 'mjpeg'
      const feed = this.activeDoorbellVideo
      if (feed?.camera && this.cameraSupportsHls(feed.camera)) {
        return 'hls'
      }
      return 'mjpeg'
    },
    cameraViewerRenderMode() {
      if (this.cameraViewerHlsUrl) return 'hls'
      if (this.cameraViewerHlsDisabled) return 'mjpeg'
      if (!this.cameraViewer.camera) return 'mjpeg'
      return this.cameraViewerSupportsHls(this.cameraViewer.camera) ? 'hls' : 'mjpeg'
    },
    cameraViewerCanForceHls() {
      if (!this.cameraViewer.open) return false
      if (!this.cameraViewer.camera) return false
      if (this.cameraViewerRenderMode === 'hls') return false
      if (this.cameraForcesMjpeg(this.cameraViewer.camera)) return false
      const key = this.cameraKey(this.cameraViewer.camera)
      if (!key) return false
      if (this.isCameraViewerHlsBlacklisted(key)) return true
      if (this.cameraSupportsHls(this.cameraViewer.camera)) return true
      return this.cameraViewerHlsProbeEnabled
    },
    securityHeroStats() {
      const stats = this.alarmInventoryStats
      return [
        { id: 'partitions', label: 'Partizioni', value: stats.partitions },
        { id: 'zones', label: 'Zone', value: stats.zones },
        { id: 'cameras', label: 'Telecamere', value: stats.cameras }
      ]
    },
    panelSupportsBrightness() {
      if (!this.devicePanel.device) return false
      if (typeof this.devicePanel.supportsBrightness === 'boolean') return this.devicePanel.supportsBrightness
      return this.supportsBrightness(this.devicePanel.device)
    },
    panelSupportsColor() {
      if (!this.devicePanel.device) return false
      if (typeof this.devicePanel.supportsColor === 'boolean') return this.devicePanel.supportsColor
      return this.supportsColor(this.devicePanel.device)
    },
    panelSupportsColorTemp() {
      if (!this.devicePanel.device) return false
      if (typeof this.devicePanel.supportsColorTemp === 'boolean') return this.devicePanel.supportsColorTemp
      return this.supportsColorTemperature(this.devicePanel.device)
    },
    panelHasControls() {
      return this.panelSupportsBrightness || this.panelSupportsColor || this.panelSupportsColorTemp
    },
    panelColorTempRange() {
      if (!this.devicePanel.device || !this.panelSupportsColorTemp) return { min: 153, max: 500 }
      return this.colorTempBounds(this.devicePanel.device)
    },
    panelColorTempLabel() {
      if (!this.panelSupportsColorTemp || !this.devicePanel.colorTemp) return '-- K'
      const kelvin = Math.round(1000000 / this.devicePanel.colorTemp)
      return `${kelvin} K`
    },
    lastRefreshLabel() {
      return new Intl.DateTimeFormat('it-IT', { hour: '2-digit', minute: '2-digit' }).format(this.lastRefresh)
    },
    lastCommandLabel() {
      if (!this.lastCommand) return '—'
      return new Intl.DateTimeFormat('it-IT', { hour: '2-digit', minute: '2-digit', second: '2-digit' }).format(this.lastCommand)
    },
    // Computed properties per la vista Overview
    currentRoomObject() {
      if (!this.currentRoomId) return null
      return this.structuredRooms.find(room => room.id === this.currentRoomId) || null
    },
    currentRoomDevices() {
      if (!this.currentRoomObject) return []
      return this.currentRoomObject.devices || []
    },
    currentRoomCameras() {
      if (!this.currentRoomObject) return []
      return this.currentRoomObject.cameras || []
    },
    isCurrentRoomEmpty() {
      if (!this.currentRoomObject) return true
      const hasDevices = this.currentRoomDevices.length > 0
      const hasCovers = this.currentRoomObject.covers && this.currentRoomObject.covers.length > 0
      const hasClimate = this.currentRoomObject.climate && this.currentRoomObject.climate.length > 0
      const hasCameras = this.currentRoomCameras.length > 0
      return !hasDevices && !hasCovers && !hasClimate && !hasCameras
    },
    overviewDevicesSummary() {
      if (!this.currentRoomObject) return ''
      const counts = []
      const deviceCount = this.currentRoomDevices.length
      if (deviceCount > 0) counts.push(`${deviceCount} ${deviceCount === 1 ? 'luce' : 'luci'}`)
      
      const coverCount = this.currentRoomObject.covers?.length || 0
      if (coverCount > 0) counts.push(`${coverCount} ${coverCount === 1 ? 'oscurante' : 'oscuranti'}`)
      
      const climateCount = this.currentRoomObject.climate?.length || 0
      if (climateCount > 0) counts.push(`${climateCount} ${climateCount === 1 ? 'dispositivo clima' : 'dispositivi clima'}`)
      
      const cameraCount = this.currentRoomCameras.length
      if (cameraCount > 0) counts.push(`${cameraCount} ${cameraCount === 1 ? 'telecamera' : 'telecamere'}`)
      
      return counts.length > 0 ? counts.join(' • ') : 'Nessun dispositivo'
    },
    systemPills() {
      return [
        { id: 'ha', label: 'Home Assistant', value: this.hasLights ? 'Operativo' : 'In attesa', accent: this.hasLights ? 'positive' : 'warning' },
        { id: 'devices', label: 'Dispositivi', value: `${this.totalLights} luci`, accent: 'neutral' },
        { id: 'command', label: 'Ultimo comando', value: this.lastCommandLabel, accent: 'neutral' }
      ]
    },
    allLightDevices() {
      return this.flattenedDevices().map(({ device, room }) => ({
        id: device.id,
        name: device.name,
        roomName: room.name,
        roomRef: room,
        ref: device,
        stateLabel: this.deviceStateLabel(device),
        isOn: this.isOn(device)
      }))
    },
    modalLightDevices() {
      const list = this.allLightDevices
      return this.showAllLightsInModal ? list : list.filter((entry) => entry.isOn)
    },
    modalCoverDevices() {
      const list = []
      for (const room of this.rooms) {
        if (room.covers && room.covers.length > 0) {
          for (const cover of room.covers) {
            list.push({
              id: cover.id,
              name: cover.friendly_name || cover.name || cover.id,
              ref: cover,
              roomName: room.name,
              isOpen: this.isCoverOpen(cover)
            })
          }
        }
      }
      return this.showAllCoversInModal ? list : list.filter(entry => entry.isOpen)
    },
    gatesList() {
      if (!this.meta || !this.meta.gates) return []
      return this.meta.gates.map(gate => ({
        id: gate.id,
        entity_id: gate.entity_id,
        name: gate.name || gate.entity_id,
        state: gate.state,
        domain: gate.domain,
        icon: gate.icon,
        device_class: gate.device_class
      }))
    },
    canTurnOffVisibleLights() {
      return this.modalLightDevices.some((entry) => entry.isOn)
    },
    weatherSnapshot() {
      const fallback = { icon: 'sun', temperature: '--°', condition: 'In attesa dati HA' }
      const source = this.haWeather || this.findWeatherDevice()
      if (!source) return fallback
      const resolved = this.normalizeHaWeather(source)
      return resolved || fallback
    },
    weatherDetails() {
      const source = this.haWeather || this.findWeatherDevice()
      const base = {
        location: source?.attributes?.friendly_name || source?.friendly_name || '',
        feelsLike: null,
        metrics: [],
        forecast: [],
        dailyForecast: [],
        updatedAt: null
      }
      if (!source) {
        return base
      }
      const attrs = source.attributes || source.a || {}
      const feelsLike = this.formatTemperatureValue(
        attrs.apparent_temperature ?? attrs.feels_like ?? attrs.apparentTemperature
      )
      const metrics = []
      const humidityValue = this.formatPercentage(attrs.humidity ?? attrs.current_humidity)
      if (humidityValue) {
        metrics.push({ label: 'Umidità', value: humidityValue })
      }
      const pressureValue = this.formatWeatherMeasurement(attrs.pressure, attrs.pressure_unit || 'hPa')
      if (pressureValue) {
        metrics.push({ label: 'Pressione', value: pressureValue })
      }
      const windValue = this.formatWeatherMeasurement(
        attrs.wind_speed ?? attrs.wind_speed_avg ?? attrs.windSpeed,
        attrs.wind_speed_unit || attrs.speed_unit || 'km/h'
      )
      if (windValue) {
        metrics.push({
          label: 'Vento',
          value: windValue,
          meta: this.formatWindBearing(attrs.wind_bearing ?? attrs.windBearing)
        })
      }
      const visibilityValue = this.formatWeatherMeasurement(
        attrs.visibility,
        attrs.visibility_unit || 'km'
      )
      if (visibilityValue) {
        metrics.push({ label: 'Visibilità', value: visibilityValue })
      }
      const hourlySource = this.pickForecastArray(attrs, ['forecast_hourly', 'forecast', 'hourly_forecast'])
      const dailySource = this.pickForecastArray(attrs, ['forecast_daily', 'daily_forecast', 'forecast_twice_daily'])
      const fallbackSource = hourlySource.length ? hourlySource : dailySource
      const forecast = this.normalizeForecastEntries(fallbackSource, 12)
      const dailyForecast = dailySource.length
        ? this.buildDailyForecast(dailySource)
        : this.buildDailyForecast(fallbackSource)
      return {
        ...base,
        location: base.location || attrs.attribution || attrs.location_name || '',
        feelsLike,
        metrics,
        forecast,
        dailyForecast,
        updatedAt: this.formatWeatherTimestamp(
          attrs.observation_time || attrs.datetime || source.last_changed || source.last_updated
        )
      }
    },
    alarmSnapshot() {
      const devices = this.flattenedDevices().map(({ device }) => device)
      if (!devices.length) return null
      const taggedDevices = devices.filter((dev) =>
        this.extractDeviceTags(dev).some((tag) => this.isAlarmStatusTag(tag))
      )
      if (!taggedDevices.length) {
        return null
      }
      const device = this.pickPreferredAlarmStatusDevice(taggedDevices)
      if (!device) return null
      const attrs = device.attributes || {}
      const tagOverride = this.alarmStatusValueFromTags(device)
      const attributeState =
        tagOverride ||
        attrs.alarm_status ||
        attrs.alarmStatus ||
        attrs.status ||
        attrs.state ||
        device.state ||
        ''
      const meta = this.describeAlarmPanelState(attributeState)
      const label = meta.label || this.formatCondition(attributeState || 'Allarme')
      const timestamp = device.last_changed || device.last_updated || attrs.updated_at
      const details = this.formatAlarmStatusTimestamp(timestamp)
      return { icon: 'shield', label, details, tone: meta.tone }
    },
    alarmStatusChip() {
      const snapshot = this.alarmSnapshot
      if (snapshot) {
        return snapshot
      }
      if (this.alarmPartitions.length) {
        const partition = this.alarmPartitions[0]
        return {
          icon: 'shield',
          label: partition.label,
          details: this.formatAlarmStatusTimestamp(partition.updatedAt) || '',
          tone: partition.tone
        }
      }
      return {
        icon: 'shield',
        label: 'Allarme',
        details: 'Non configurato',
        tone: 'idle'
      }
    },
    shouldShowSecurityToolbar() {
      return Boolean(this.securityView && this.securityViewOptions.length > 1)
    },
    alarmPartitions() {
      const entries = new Map()
      this.flattenedDevices().forEach(({ device, room }) => {
        if (!this.isAlarmPartitionDevice(device)) return
        const entry = this.buildAlarmPartitionEntry(device, room)
        if (entry && entry.id) {
          entries.set(entry.id, entry)
        }
      })
      return Array.from(entries.values()).sort((a, b) => {
        const toneDiff = this.alarmToneRank(a.tone) - this.alarmToneRank(b.tone)
        if (toneDiff !== 0) return toneDiff
        return a.name.localeCompare(b.name)
      })
    },
    alarmZones() {
      const entries = new Map()
      this.flattenedDevices().forEach(({ device, room }) => {
        if (!this.isAlarmZoneDevice(device)) return
        const entry = this.buildAlarmZoneEntry(device, room)
        if (entry && entry.id) {
          entries.set(entry.id, entry)
        }
      })
      return Array.from(entries.values()).sort((a, b) => {
        const toneDiff = this.alarmToneRank(a.tone) - this.alarmToneRank(b.tone)
        if (toneDiff !== 0) return toneDiff
        return a.name.localeCompare(b.name)
      })
    },
    alarmInventoryStats() {
      return {
        partitions: this.alarmPartitions.length,
        zones: this.alarmZones.length,
        cameras: this.totalCameraCount
      }
    },
    groupedAlarmZones() {
      const groups = new Map()
      this.alarmZones.forEach((zone) => {
        const hasRoom = Boolean(zone.roomName && zone.roomName.trim())
        const label = hasRoom ? zone.roomName.trim() : 'Area principale'
        const mapKey = label.toLowerCase()
        if (!groups.has(mapKey)) {
          groups.set(mapKey, {
            roomKey: mapKey,
            roomLabel: hasRoom ? 'Stanza' : 'Area',
            displayName: label,
            zones: []
          })
        }
        groups.get(mapKey).zones.push(zone)
      })
      return Array.from(groups.values())
        .map((group) => ({
          ...group,
          zones: group.zones.slice().sort((a, b) => a.name.localeCompare(b.name))
        }))
        .sort((a, b) => a.displayName.localeCompare(b.displayName))
    },
    securityViewOptions() {
      const options = []
      if (this.alarmPartitions.length) {
        options.push({ id: 'partitions', label: 'Partizioni', icon: 'shield', count: this.alarmPartitions.length })
      }
      if (this.alarmZones.length) {
        options.push({ id: 'zones', label: 'Zone', icon: 'rows', count: this.alarmZones.length })
      }
      if (this.totalCameraCount > 0) {
        options.push({ id: 'cameras', label: 'Telecamere', icon: 'camera', count: this.totalCameraCount })
      }
      return options
    },
    showSecurityHub() {
      return this.securityViewOptions.length > 0 && !this.securityView
    },
    canShowSecurityBack() {
      return Boolean(this.securityView && this.securityViewOptions.length > 1)
    },
    activeSecurityOption() {
      if (!this.securityView) return null
      return this.securityViewOptions.find((opt) => opt.id === this.securityView) || null
    },
    panelBrightnessPercent() {
      const value = Number(this.devicePanel.brightness) || 0
      return Math.round((value / 255) * 100)
    },
    hueGradient() {
      return 'linear-gradient(90deg, #ff0000 0%, #ff9900 16%, #ffff00 32%, #00ff00 48%, #00ffff 64%, #0055ff 80%, #ff00ff 100%)'
    },
    hasComfortDevices() {
      return this.comfortRooms.length > 0
    },
    comfortRooms() {
      // Filtra solo la stanza corrente se selezionata
      const rooms = this.currentRoomId 
        ? this.structuredRooms.filter(room => room.id === this.currentRoomId)
        : this.structuredRooms
      
      return rooms.filter(room => {
        const hasCovers = room.covers && room.covers.length > 0
        const hasClimate = room.climate && room.climate.length > 0
        return hasCovers || hasClimate
      })
    }
  },
  watch: {
    currentRoom(value) {
      if (typeof value === 'undefined') return
      this.currentRoomId = value === null ? null : this.normalizeRoomId(value)
    },
    rooms: {
      handler(newRooms) {
        if (!this.currentRoomId && Array.isArray(newRooms) && newRooms.length) {
          this.currentRoomId = this.normalizeRoomId(newRooms[0].id)
        }
        this.syncDevicePanel()
        this.updateWeatherFromDevices()
        this.reconcileOptimisticStates()
        this.pruneCameraCaches(newRooms)
        this.scanDoorbellTriggers()
      },
      deep: true,
      immediate: true
    },
    devices: {
      handler() {
        this.lastRefresh = Date.now()
        if (!this.currentRoomId && this.currentRoom !== null) {
          this.currentRoomId = this.normalizeRoomId(this.currentRoom)
        }
        this.syncDevicePanel()
        this.updateWeatherFromDevices()
        this.reconcileOptimisticStates()
        this.pruneCameraCaches(this.rooms)
        this.scanDoorbellTriggers()
      },
      deep: true,
      immediate: true
    },
    weather: {
      handler(value) {
        if (value) {
          this.haWeather = value
        } else if (!this.haWeather) {
          this.haWeather = null
        }
      },
      immediate: true
    },
    securityViewOptions: {
      handler(options) {
        if (!Array.isArray(options) || !options.length) {
          this.securityView = null
          return
        }
        if (options.length === 1) {
          this.securityView = options[0].id
          return
        }
        if (this.securityView && options.some((opt) => opt.id === this.securityView)) {
          return
        }
        this.securityView = null
      },
      immediate: true,
      deep: false
    }
  },
  mounted() {
    if (!this.currentRoomId && this.structuredRooms.length) {
      this.currentRoomId = this.normalizeRoomId(this.structuredRooms[0].id)
    }
    if (typeof window !== 'undefined') {
      window.addEventListener('ha_event', this.handleHaEvent)
    }
    this.fetchHaWeather()
    this.scanDoorbellTriggers()
    this.bindForegroundStreamGuards()
  },
  beforeUnmount() {
    if (typeof window !== 'undefined') {
      window.removeEventListener('ha_event', this.handleHaEvent)
    }
    this.clearQueuedRoomRefresh()
    this.clearAllOptimisticTimers()
    this.unbindForegroundStreamGuards()
    this.suspendAllStreams('unmount')
  },
  methods: {
    getDirectHaCaller() {
      if (typeof window === 'undefined') return null
      const fn = window.__efaceHaCallService
      return typeof fn === 'function' ? fn : null
    },
    entityDomain(entityId) {
      if (typeof entityId !== 'string') return ''
      return entityId.includes('.') ? entityId.split('.', 1)[0] : ''
    },
    normalizeEntityIdKey(entityId) {
      if (entityId === null || typeof entityId === 'undefined') return ''
      return entityId.toString().trim().toLowerCase()
    },
    deviceDomain(device) {
      if (!device) return ''
      const direct = device.domain || device.type || device.platform
      if (typeof direct === 'string' && direct.trim()) {
        return direct.toLowerCase()
      }
      const entityId = this.deviceEntityId(device)
      if (entityId) {
        const fromId = this.entityDomain(entityId)
        if (fromId) return fromId.toLowerCase()
      }
      if (typeof device.id === 'string' && device.id.includes('.')) {
        const fromRaw = this.entityDomain(device.id)
        if (fromRaw) return fromRaw.toLowerCase()
      }
      return ''
    },
    isMomentaryDoorbellDevice(device) {
      const domain = this.deviceDomain(device)
      return domain === 'button' || domain === 'input_button' || domain === 'event'
    },
    setCategory(id) {
      this.activeCategory = id
    },
    setSecurityView(viewId) {
      if (!viewId) return
      const option = this.securityViewOptions.find((opt) => opt.id === viewId)
      if (!option) return
      this.securityView = option.id
    },
    resetSecurityView() {
      if (this.securityViewOptions.length > 1) {
        this.securityView = null
      }
    },
    suspendAllStreams(reason = 'manual') {
      this.clearCameraResumeQueue()
      const nextPriority = STREAM_SUSPEND_PRIORITY[reason] || STREAM_SUSPEND_PRIORITY.manual
      const currentPriority = STREAM_SUSPEND_PRIORITY[this.streamSuspendReason] || 0
      if (this.streamsSuspended) {
        if (nextPriority > currentPriority) {
          this.streamSuspendReason = reason
        }
        return
      }
      this.streamsSuspended = true
      this.streamSuspendReason = reason
      const resetOverlays = ['unmount', 'pagehide', 'beforeunload'].includes(reason)
      this.clearAllCameraRefreshTimers()
      this.stopCameraViewerAutorefresh()
      this.clearCameraViewerHlsTimeout()
      this.teardownCameraViewerHls()
      if (resetOverlays) {
        this.cameraViewer = defaultCameraViewerState()
        this.cameraViewerHlsDisabled = false
      } else if (this.cameraViewer.open) {
        this.cameraViewer = {
          ...this.cameraViewer,
          url: '',
          loading: false,
          error: null
        }
        this.cameraViewerHlsUrl = ''
        this.cameraViewerHlsDisabled = false
      }
      this.stopDoorbellVideoAutorefresh()
      this.teardownDoorbellHls({ resetDisable: true })
      if (resetOverlays) {
        this.doorbellAlert = defaultDoorbellAlertState()
      }
      this.doorbellFallbackError = null
    },
    resumeAllStreams(reason = 'manual') {
      if (!this.streamsSuspended) return
      const lastReason = this.streamSuspendReason
      if (lastReason) {
        const allowed = STREAM_RESUME_RULES[lastReason]
        if (allowed instanceof Set) {
          if (allowed.size === 0) {
            return
          }
          if (!allowed.has(reason)) {
            return
          }
        }
      }
      this.streamsSuspended = false
      this.streamSuspendReason = null
      if (Array.isArray(this.uniqueCameraList) && this.uniqueCameraList.length) {
        this.refreshScopedCameras(this.uniqueCameraList, {
          stagger: true,
          batchSize: CAMERA_RESUME_BATCH_SIZE,
          delay: CAMERA_RESUME_STAGGER_DELAY
        })
      }
      if (this.cameraViewer.open && this.cameraViewer.camera) {
        if (this.cameraViewerRenderMode === 'hls') {
          this.startCameraViewerHls(true, 'auto')
        } else {
          this.refreshCameraViewer()
        }
      }
      if (this.doorbellAlert.open) {
        this.refreshActiveDoorbellVideo()
      } else {
        this.stopDoorbellVideoAutorefresh()
      }
    },
    // Pause/resume MJPEG and HLS streams when the browser tab visibility changes.
    bindForegroundStreamGuards() {
      if (typeof document !== 'undefined' && !this.streamGuardHandlers.visibility) {
        const onVisibilityChange = () => {
          if (document.hidden) {
            this.suspendAllStreams('visibility-hidden')
          } else {
            this.resumeAllStreams('visibility-visible')
          }
        }
        document.addEventListener('visibilitychange', onVisibilityChange)
        this.streamGuardHandlers.visibility = onVisibilityChange
      }
      if (typeof window !== 'undefined') {
        if (!this.streamGuardHandlers.pageHide) {
          const onPageHide = () => this.suspendAllStreams('pagehide')
          window.addEventListener('pagehide', onPageHide)
          this.streamGuardHandlers.pageHide = onPageHide
        }
        if (!this.streamGuardHandlers.pageShow) {
          const onPageShow = (event) => {
            if (event?.persisted || this.streamsSuspended) {
              this.resumeAllStreams('pageshow')
            }
          }
          window.addEventListener('pageshow', onPageShow)
          this.streamGuardHandlers.pageShow = onPageShow
        }
        if (!this.streamGuardHandlers.beforeUnload) {
          const onBeforeUnload = () => this.suspendAllStreams('beforeunload')
          window.addEventListener('beforeunload', onBeforeUnload)
          this.streamGuardHandlers.beforeUnload = onBeforeUnload
        }
      }
    },
    unbindForegroundStreamGuards() {
      if (typeof document !== 'undefined' && this.streamGuardHandlers.visibility) {
        document.removeEventListener('visibilitychange', this.streamGuardHandlers.visibility)
        this.streamGuardHandlers.visibility = null
      }
      if (typeof window !== 'undefined') {
        if (this.streamGuardHandlers.pageHide) {
          window.removeEventListener('pagehide', this.streamGuardHandlers.pageHide)
          this.streamGuardHandlers.pageHide = null
        }
        if (this.streamGuardHandlers.pageShow) {
          window.removeEventListener('pageshow', this.streamGuardHandlers.pageShow)
          this.streamGuardHandlers.pageShow = null
        }
        if (this.streamGuardHandlers.beforeUnload) {
          window.removeEventListener('beforeunload', this.streamGuardHandlers.beforeUnload)
          this.streamGuardHandlers.beforeUnload = null
        }
      }
    },
    securityViewSubtitle(viewId) {
      switch (viewId) {
        case 'cameras': {
          const count = this.totalCameraCount
          return `${count} ${count === 1 ? 'telecamera' : 'telecamere'}`
        }
        case 'zones': {
          const count = this.alarmZones.length
          return `${count} ${count === 1 ? 'zona' : 'zone'}`
        }
        case 'partitions': {
          const count = this.alarmPartitions.length
          return `${count} ${count === 1 ? 'partizione' : 'partizioni'}`
        }
        default:
          return ''
      }
    },
    pickPreferredAlarmStatusDevice(devices = []) {
      if (!Array.isArray(devices) || !devices.length) return null
      const ranked = devices
        .map((device) => ({ device, rank: this.alarmStatusDeviceRank(device) }))
        .sort((a, b) => a.rank - b.rank)
      return ranked[0]?.device || null
    },
    alarmStatusDeviceRank(device) {
      const domain = this.deviceDomain(device)
      if (domain === 'sensor') return 0
      if (domain === 'binary_sensor') return 1
      if (domain === 'select' || domain === 'input_select' || domain === 'text') return 2
      if (domain === 'switch' || domain === 'button') return 3
      if (domain === 'alarm_control_panel') return 4
      return 5
    },
    alarmStatusCandidateDevices(devices = []) {
      if (!Array.isArray(devices) || !devices.length) return []
      const keywords = ['alarm', 'allarme', 'scenario', 'sicurezza', 'security', 'ksenia', 'status']
      const allowed = new Set(['sensor', 'binary_sensor', 'select', 'switch', 'input_select', 'text', 'button'])
      return devices.filter((device) => {
        const entityId = this.deviceEntityId(device)
        const normalizedId = (entityId || '').toLowerCase()
        const name = (device?.name || device?.attributes?.friendly_name || '').toLowerCase()
        const domain = this.deviceDomain(device)
        if (domain === 'alarm_control_panel') return true
        if (!allowed.has(domain)) return false
        if (!normalizedId && !name) return false
        return keywords.some((token) => normalizedId.includes(token) || name.includes(token))
      })
    },
    refreshScopedCameras(cameras, options = {}) {
      const list = Array.isArray(cameras) ? [...cameras] : []
      if (!list.length) {
        this.clearCameraResumeQueue()
        return
      }
      const {
        stagger = false,
        batchSize = CAMERA_RESUME_BATCH_SIZE,
        delay = CAMERA_RESUME_STAGGER_DELAY
      } = options
      if (!stagger) {
        this.clearCameraResumeQueue()
        list.forEach((camera) => this.refreshCameraFeed(camera))
        return
      }
      this.clearCameraResumeQueue()
      const safeBatch = Math.max(1, Math.floor(batchSize))
      const safeDelay = Math.max(50, Math.floor(delay))
      for (let offset = 0, wave = 0; offset < list.length; offset += safeBatch, wave += 1) {
        const chunk = list.slice(offset, offset + safeBatch)
        const timer = setTimeout(() => {
          if (this.streamsSuspended) return
          chunk.forEach((camera) => this.refreshCameraFeed(camera))
          this.cameraResumeTimeouts = this.cameraResumeTimeouts.filter((handle) => handle !== timer)
        }, wave * safeDelay)
        this.cameraResumeTimeouts = [...this.cameraResumeTimeouts, timer]
      }
    },
    refreshNow() {
      this.lastRefresh = Date.now()
      this.clearQueuedRoomRefresh()
      this.$emit('refresh-room')
      this.fetchHaWeather()
    },

    toggleSkipCameraPreviews() {
      this.skipCameraPreviews = !this.skipCameraPreviews
      // small debug log so you can see card count in console
      try {
        const count = document.querySelectorAll('.camera-card--mosaic').length
        console.log('[debug] skipCameraPreviews', this.skipCameraPreviews, 'camera cards:', count)
      } catch (err) {
        console.log('[debug] skipCameraPreviews toggled', this.skipCameraPreviews)
      }
    },
    openWeatherDetails() {
      this.weatherDetailsOpen = true
    },
    closeWeatherDetails() {
      this.weatherDetailsOpen = false
    },
    focusRoom(roomId) {
      if (roomId === undefined || roomId === null) return
      const normalized = this.normalizeRoomId(roomId)
      this.currentRoomId = normalized
      this.$emit('room-selected', normalized)
    },
    normalizeRoomId(value) {
      if (value === null || value === undefined) return null
      if (typeof this.currentRoomId === 'number' || typeof value === 'number') {
        const num = Number(value)
        return Number.isNaN(num) ? value : num
      }
      return value
    },
    normalizeRoomSlug(value) {
      if (value === null || typeof value === 'undefined') return ''
      const text = String(value)
      const base = typeof text.normalize === 'function' ? text.normalize('NFD') : text
      return base
        .replace(/[\u0300-\u036f]/g, '')
        .toLowerCase()
        .replace(/&/g, 'e')
        .replace(/[^a-z0-9]+/g, '-')
        .replace(/^-+|-+$/g, '')
    },
    mergeDeviceLists(primary = [], supplemental = []) {
      const merged = []
      const seen = new Set()
      const pushUnique = (device) => {
        if (!device) return
        const key = this.deviceEntityId(device)
        if (key) {
          if (seen.has(key)) return
          seen.add(key)
        }
        merged.push(device)
      }
      primary.forEach(pushUnique)
      supplemental.forEach(pushUnique)
      return merged
    },
    roomIcon(room) {
      const name = (room?.name || '').toLowerCase()
      if (name.includes('living') || name.includes('salotto') || name.includes('soggiorno')) return 'sofa'
      if (name.includes('studio') || name.includes('office')) return 'desk'
      if (name.includes('camera') || name.includes('bed')) return 'bed'
      if (name.includes('bagno') || name.includes('bath')) return 'bath'
      return 'home'
    },
    normalizeDoorbellSlot(value) {
      if (value === null || typeof value === 'undefined') return 'default'
      const normalized = String(value).trim().toLowerCase()
      return normalized || 'default'
    },
    formatDoorbellLabel(slot) {
      const normalized = this.normalizeDoorbellSlot(slot)
      if (!normalized || normalized === 'default') {
        return 'Campanello'
      }
      const numeric = Number(normalized)
      if (!Number.isNaN(numeric)) {
        return `Campanello ${numeric}`
      }
      return `Campanello ${normalized.toUpperCase()}`
    },
    parseDoorbellToken(tag) {
      if (!tag) return null
      const normalized = tag.toString().trim().toLowerCase()
      const match = normalized.match(/^doorbell(?:[-_\s]?([a-z0-9]+))?(?:[-_\s]*(video|gate|trigger)(?:[-_\s]*(p))?)?$/)
      if (!match) return null
      const slot = this.normalizeDoorbellSlot(match[1])
      const role = match[2] ? match[2].toLowerCase() : null
      const priority = role === 'video' ? (match[3] ? 0 : 1) : null
      return { slot, role, priority }
    },
    parseGateTag(tag) {
      if (!tag) return null
      const normalized = tag.toString().trim().toLowerCase()
      const match = normalized.match(/^gate(?:[-_\s]?([a-z0-9]+))$/)
      if (!match) return null
      return { slot: this.normalizeDoorbellSlot(match[1]) }
    },
    hasTvccTag(device) {
      const tags = this.extractDeviceTags(device, { includeLabels: true })
      if (!tags.length) return false
      return tags.some((tag) => {
        if (tag === null || typeof tag === 'undefined') return false
        const normalized = tag.toString().trim().toLowerCase()
        if (!normalized) return false
        const slug = normalized.replace(/\s+/g, '-')
        return normalized === 'tvcc' || slug.startsWith('tvcc:') || slug.startsWith('tvcc-')
      })
    },
    normalizeCameraTagValue(tag) {
      if (tag === null || typeof tag === 'undefined') return ''
      const normalized = tag.toString().trim().toLowerCase()
      if (!normalized) return ''
      return normalized.replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '')
    },
    cameraHasTagSlug(camera, slug) {
      if (!camera || !slug) return false
      const target = this.normalizeCameraTagValue(slug)
      if (!target) return false
      const tags = this.extractDeviceTags(camera, { includeLabels: true })
      if (!tags.length) return false
      return tags.some((tag) => this.normalizeCameraTagValue(tag) === target)
    },
    cameraForcesHls(camera) {
      if (!camera) return false
      if (this.cameraForcesMjpeg(camera)) return false
      return this.cameraHasTagSlug(camera, 'tvcc-hls') || this.cameraHasTagSlug(camera, 'tvcc')
    },
    cameraForcesMjpeg(camera) {
      if (!camera) return false
      return this.cameraHasTagSlug(camera, 'tvcc-mjpeg')
    },
    isCameraDevice(device) {
      return this.deviceDomain(device) === 'camera'
    },
    cameraSupportsHls(camera) {
      if (!camera) return false
      if (this.cameraForcesMjpeg(camera)) return false
      if (this.cameraForcesHls(camera)) return true
      const type = camera?.attributes?.frontend_stream_type || camera?.attributes?.stream_type
      if (typeof type === 'string' && type.toLowerCase() === 'hls') {
        return true
      }
      return false
    },
    cameraViewerSupportsHls(camera) {
      if (!camera || !this.cameraViewerAutoHlsEnabled) return false
      const key = this.cameraKey(camera)
      if (!key) return false
      if (this.isCameraViewerHlsBlacklisted(key)) return false
      if (this.cameraForcesMjpeg(camera)) return false
      if (this.cameraForcesHls(camera)) return true
      if (this.cameraSupportsHls(camera)) return true
      return this.cameraViewerHlsProbeEnabled
    },
    cameraPreferredStreamType(camera) {
      if (!camera) return 'mjpeg'
      if (this.cameraForcesMjpeg(camera)) return 'mjpeg'
      if (this.cameraForcesHls(camera)) return 'hls'
      if (this.cameraSupportsHls(camera)) return 'hls'
      return 'mjpeg'
    },
    cameraPreviewStreamLabel(camera) {
      const type = this.cameraPreferredStreamType(camera)
      return type === 'hls' ? 'HLS' : 'MJPEG'
    },
    cameraViewerStreamLabel() {
      if (!this.cameraViewer.camera) return ''
      if (this.cameraViewerHlsUrl) return 'HLS'
      return 'MJPEG'
    },
    isCameraViewerHlsBlacklisted(key) {
      if (!key) return false
      const stamp = this.cameraViewerHlsBlacklist[key]
      if (!stamp) return false
      if (Date.now() - stamp > CAMERA_VIEWER_HLS_BLACKLIST_TTL) {
        const next = { ...this.cameraViewerHlsBlacklist }
        delete next[key]
        this.cameraViewerHlsBlacklist = next
        return false
      }
      return true
    },
    extractCameraViewerStreamErrorDetail(error) {
      if (!error) return ''
      if (typeof error === 'string') return error
      const responseData = error?.response?.data
      if (typeof responseData === 'string') return responseData
      if (responseData && typeof responseData.detail === 'string') {
        return responseData.detail
      }
      if (typeof error.message === 'string') {
        return error.message
      }
      return ''
    },
    isFatalCameraViewerHlsError(error) {
      const detail = this.extractCameraViewerStreamErrorDetail(error)
      if (!detail) return false
      const normalized = detail.toString().toLowerCase()
      if (normalized.includes('does not support play stream service')) {
        return true
      }
      if (normalized.includes('camera_stream_request_failed')) {
        return true
      }
      if (normalized.includes('camera_stream_url_unavailable')) {
        return true
      }
      return false
    },
    markCameraViewerHlsFailure(camera) {
      const key = this.cameraKey(camera)
      if (!key) return
      this.invalidateCameraHlsSession(camera, CAMERA_HLS_SCOPE_VIEWER)
      if (this.cameraViewerHlsBlacklist[key]) return
      this.cameraViewerHlsBlacklist = {
        ...this.cameraViewerHlsBlacklist,
        [key]: Date.now()
      }
    },
    clearCameraViewerHlsBlacklist(camera) {
      const key = this.cameraKey(camera)
      if (!key) return
      if (!this.cameraViewerHlsBlacklist[key]) return
      const next = { ...this.cameraViewerHlsBlacklist }
      delete next[key]
      this.cameraViewerHlsBlacklist = next
    },
    invalidateCameraHlsSession(camera, scope = null) {
      const key = this.cameraKey(camera)
      if (!key || !this.cameraHlsSessions[key]) return
      const entry = this.cameraHlsSessions[key]
      if (!scope) {
        const next = { ...this.cameraHlsSessions }
        delete next[key]
        this.cameraHlsSessions = next
        return
      }
      if (!entry[scope]) return
      const scoped = { ...entry }
      delete scoped[scope]
      const next = { ...this.cameraHlsSessions }
      if (Object.keys(scoped).length) {
        next[key] = scoped
      } else {
        delete next[key]
      }
      this.cameraHlsSessions = next
    },
    isGateControllerDevice(device) {
      if (!device) return false
      const domain = this.deviceDomain(device)
      if (!domain) return false
      const gateDomains = new Set(['cover', 'lock', 'garage_door', 'door', 'gate'])
      if (gateDomains.has(domain)) return true
      const tags = this.extractDeviceTags(device, { includeLabels: false })
      if (tags.some((tag) => this.parseGateTag(tag))) return true
      return tags.some((tag) => {
        const parsed = this.parseDoorbellToken(tag)
        return parsed?.role === 'gate'
      })
    },
    isDoorbellTriggerCandidate(device) {
      if (!device) return false
      if (this.isCameraDevice(device)) return false
      if (this.isGateControllerDevice(device)) return false
      if (this.isMomentaryDoorbellDevice(device)) return true
      const domain = this.deviceDomain(device)
      const allowed = new Set([
        'binary_sensor',
        'sensor',
        'switch',
        'input_boolean',
        'input_text',
        'input_number',
        'button',
        'input_button',
        'device_tracker',
        'event'
      ])
      if (allowed.has(domain)) return true
      return false
    },
    doorbellRolesForDevice(device, tagMeta = {}) {
      const roles = new Set()
      const explicitRole = tagMeta.role
      if (explicitRole === 'video' && this.isCameraDevice(device)) {
        roles.add('video')
      } else if (explicitRole === 'gate') {
        roles.add('gate')
      } else if (explicitRole === 'trigger') {
        roles.add('trigger')
      }
      if (!explicitRole) {
        if (this.isCameraDevice(device)) {
          roles.add('video')
        } else if (this.isGateControllerDevice(device)) {
          roles.add('gate')
        } else if (this.isDoorbellTriggerCandidate(device)) {
          roles.add('trigger')
        }
      }
      if (explicitRole === 'video' && !roles.has('video')) {
        roles.add('trigger')
      }
      if (explicitRole === 'gate' && !roles.has('gate')) {
        roles.add('trigger')
      }
      if (!roles.size) {
        roles.add('trigger')
      }
      return Array.from(roles)
    },
    gateLabelForDevice(device, slot) {
      if (device?.name) return device.name
      if (device?.attributes?.friendly_name) return device.attributes.friendly_name
      const normalized = this.normalizeDoorbellSlot(slot)
      if (!normalized || normalized === 'default') return 'Cancello'
      return `Cancello ${normalized}`
    },
    normalizeDoorbellState(source) {
      if (source === null || typeof source === 'undefined') {
        return ''
      }
      if (typeof source === 'object' && !Array.isArray(source)) {
        const candidate =
          source.state ??
          source.value ??
          source.status ??
          source.current_state ??
          source.currentState ??
          null
        if (candidate === null || typeof candidate === 'undefined') {
          return ''
        }
        if (typeof candidate === 'number' || typeof candidate === 'boolean') {
          return String(candidate).trim().toLowerCase()
        }
        return candidate.toString().trim().toLowerCase()
      }
      return source.toString().trim().toLowerCase()
    },
    isDoorbellActiveState(value) {
      const normalized = (value || '').toString().trim().toLowerCase()
      if (!normalized) return false
      const activeStates = ['on', 'pressed', 'ringing', 'triggered', 'detected', 'open', '1', 'true']
      if (activeStates.includes(normalized)) return true
      return /^press|^ring|^attivo|^attiva/.test(normalized)
    },
    preferredGateService(domain) {
      switch (domain) {
        case 'button':
        case 'input_button':
          return { domain, service: 'press' }
        case 'switch':
        case 'input_boolean':
        case 'scene':
          return { domain: domain === 'scene' ? 'scene' : domain, service: 'turn_on' }
        case 'lock':
          return { domain: 'lock', service: 'unlock' }
        case 'cover':
          return { domain: 'cover', service: 'open_cover' }
        default:
          return null
      }
    },
    async triggerGateDevice(device) {
      if (!device) return
      const entityId = this.deviceEntityId(device)
      const domain = this.deviceDomain(device) || (entityId ? this.entityDomain(entityId) : null)
      const preferred = domain ? this.preferredGateService(domain) : null
      const directCaller = this.getDirectHaCaller()
      if (preferred && entityId && directCaller) {
        try {
          await directCaller(preferred.domain, preferred.service, { entity_id: entityId })
          return
        } catch (err) {
          console.warn('Direct gate trigger failed, falling back to toggleDevice', err)
        }
      }
      this.toggleDevice(device, true)
    },
    scanDoorbellTriggers() {
      if (!this.doorbellSources.length) {
        return
      }
      const nextCache = { ...this.doorbellStateCache }
      this.doorbellSources.forEach((entry) => {
        entry.triggers.forEach((triggerDevice) => {
          if (!triggerDevice) return
          if (this.isMomentaryDoorbellDevice(triggerDevice)) {
            // Momentary entities (button/input_button) do not expose a stable state, rely on HA events instead.
            return
          }
          const entityId = this.normalizeEntityIdKey(this.deviceEntityId(triggerDevice))
          if (!entityId) return
          const currentState = this.normalizeDoorbellState(triggerDevice)
          const previousState = nextCache[entityId]?.state
          nextCache[entityId] = { state: currentState }
          if (this.isDoorbellActiveState(currentState) && !this.isDoorbellActiveState(previousState)) {
            this.presentDoorbellAlert(entry, triggerDevice)
          }
        })
      })
      this.doorbellStateCache = nextCache
    },
    presentDoorbellAlert(entry) {
      if (!entry) return
      const alert = defaultDoorbellAlertState()
      alert.open = true
      alert.doorbellId = entry.id
      alert.doorbellLabel = entry.label || this.formatDoorbellLabel(entry.id)
      alert.triggeredAt = Date.now()
      alert.videos = entry.videos || []
      alert.gates = (entry.gates || []).map((gate) => ({
        ...gate,
        label: gate.label || this.gateLabelForDevice(gate.device, entry.id)
      }))
      if (alert.videos.length) {
        alert.videoIndex = 0
      }
      this.releaseActiveDoorbellSession()
      this.teardownDoorbellHls({ resetDisable: true })
      this.doorbellFallbackStreaming = false
      this.doorbellAlert = alert
      this.doorbellFallbackError = null
      this.$nextTick(() => {
        this.refreshActiveDoorbellVideo()
      })
    },
    releaseActiveDoorbellSession() {
      const feed = this.activeDoorbellVideo
      if (feed?.camera) {
        this.invalidateCameraHlsSession(feed.camera, CAMERA_HLS_SCOPE_DOORBELL)
      }
    },
    openDoorbellPicker() {
      this.doorbellPickerOpen = true
    },
    closeDoorbellPicker() {
      this.doorbellPickerOpen = false
    },
    triggerDoorbellFromPicker(entry) {
      if (!entry) return
      this.closeDoorbellPicker()
      this.presentDoorbellAlert(entry)
    },
    formatDoorbellPickerMeta(entry) {
      if (!entry) return 'Nessun flusso collegato'
      const videos = Array.isArray(entry.videos) ? entry.videos.length : 0
      const triggers = Array.isArray(entry.triggers) ? entry.triggers.length : 0
      const parts = []
      if (videos) {
        parts.push(`${videos} video`)
      }
      if (triggers) {
        parts.push(`${triggers} trigger`)
      }
      if (!parts.length) {
        return 'Nessun flusso collegato'
      }
      return parts.join(' / ')
    },
    closeDoorbellAlert() {
      this.stopDoorbellVideoAutorefresh()
      this.releaseActiveDoorbellSession()
      this.teardownDoorbellHls({ resetDisable: true })
      this.doorbellFallbackStreaming = false
      this.doorbellAlert = defaultDoorbellAlertState()
      this.doorbellFallbackError = null
    },
    stepDoorbellVideo(direction = 1) {
      const videos = this.doorbellAlert.videos || []
      if (!videos.length) return
      const nextIndex = (this.doorbellAlert.videoIndex + direction + videos.length) % videos.length
      this.releaseActiveDoorbellSession()
      this.teardownDoorbellHls({ resetDisable: true })
      this.doorbellFallbackStreaming = false
      this.doorbellAlert = {
        ...this.doorbellAlert,
        videoIndex: nextIndex
      }
      this.doorbellFallbackError = null
      this.$nextTick(() => {
        this.refreshActiveDoorbellVideo()
      })
    },
    setDoorbellVideo(index) {
      const videos = this.doorbellAlert.videos || []
      if (!videos.length) return
      const safeIndex = Math.max(0, Math.min(index, videos.length - 1))
      this.releaseActiveDoorbellSession()
      this.teardownDoorbellHls({ resetDisable: true })
      this.doorbellFallbackStreaming = false
      this.doorbellAlert = {
        ...this.doorbellAlert,
        videoIndex: safeIndex
      }
      this.doorbellFallbackError = null
      this.$nextTick(() => {
        this.refreshActiveDoorbellVideo()
      })
    },
    async refreshActiveDoorbellVideo() {
      if (this.doorbellVideoRefreshInFlight) return
      if (this.streamsSuspended) {
        this.stopDoorbellVideoAutorefresh()
        return
      }
      this.doorbellVideoRefreshInFlight = true
      try {
        this.doorbellFallbackError = null
        const feed = this.activeDoorbellVideo
        if (!feed?.camera) {
          this.teardownDoorbellHls({ resetDisable: true })
          this.stopDoorbellVideoAutorefresh()
          return
        }
        if (this.streamsSuspended) return
        const prefersHls = this.cameraSupportsHls(feed.camera)
        if (prefersHls && !this.doorbellHlsDisabled) {
          const usedHls = await this.prepareDoorbellHlsFeed(feed.camera, { silentOnFailure: true })
          if (usedHls) {
            this.doorbellFallbackStreaming = false
            this.stopDoorbellVideoAutorefresh()
            return
          }
        }
        if (this.doorbellFallbackStreaming) {
          this.stopDoorbellVideoAutorefresh()
          return
        }
        this.refreshCameraFeed(feed.camera)
        this.doorbellFallbackStreaming = true
        this.stopDoorbellVideoAutorefresh()
      } finally {
        this.doorbellVideoRefreshInFlight = false
      }
    },
    async prepareDoorbellHlsFeed(camera, options = {}) {
      if (!camera || this.streamsSuspended) return false
      const { silentOnFailure = false } = options
      this.doorbellHlsLoading = true
      this.doorbellHlsBuffered = false
      this.doorbellHlsError = null
      this.doorbellHlsSourceUrl = ''
      try {
        this.doorbellHlsDisabled = false
        this.doorbellHlsErrorCount = 0
        this.invalidateCameraHlsSession(camera, CAMERA_HLS_SCOPE_DOORBELL)
        const session = await this.fetchCameraStreamSession(camera, {
          force: true,
          scope: CAMERA_HLS_SCOPE_DOORBELL,
          priority: 'doorbell'
        })
        if (this.streamsSuspended) {
          return false
        }
        this.doorbellHlsSourceUrl = session.playlistUrl
        this.doorbellVideoElementKey += 1
        this.mountDoorbellHlsPlayer(session.playlistUrl)
        this.setDoorbellHlsTimeout()
        return true
      } catch (err) {
        console.warn('doorbell hls failed', err)
        if (!silentOnFailure) {
          this.doorbellHlsError = 'Streaming non disponibile'
        }
        this.invalidateCameraHlsSession(camera, CAMERA_HLS_SCOPE_DOORBELL)
        this.doorbellHlsDisabled = true
        this.doorbellHlsErrorCount = 0
        this.teardownDoorbellHls({ resetError: silentOnFailure })
        return false
      } finally {
        this.doorbellHlsLoading = false
      }
    },
    mountDoorbellHlsPlayer(url) {
      this.$nextTick(() => {
        if (this.streamsSuspended) return
        const el = this.$refs.doorbellVideoEl
        if (!el) return
          if (Hls.isSupported()) {
          if (this.doorbellHlsController) {
            try { this.doorbellHlsController.destroy() } catch (_) {}
          }
          // Use conservative Hls.js defaults for stability (A/B test)
          // Avoid forcing crossOrigin here; let the proxy handle same-origin delivery.
          const hls = new Hls({
            enableWorker: true,
            autoStartLoad: true,
            startFragPrefetch: true,
            lowLatencyMode: false,
            liveSyncDurationCount: 3,
            maxBufferLength: 60,
            maxMaxBufferLength: 120,
            maxBufferHole: 0.5,
            fragLoadingTimeOut: 60000,
            levelLoadingTimeOut: 60000,
            manifestLoadingTimeOut: 60000
          })
          hls.attachMedia(el)
          hls.on(Hls.Events.MEDIA_ATTACHED, () => {
            console.log('[hls] DOORBELL MEDIA_ATTACHED, loading source', url)
            try { hls.loadSource(url) } catch (e) { console.warn('[hls] loadSource failed', e) }
          })
          hls.on(Hls.Events.MANIFEST_PARSED, () => {
            this.clearDoorbellHlsTimeout()
            this.doorbellHlsLoading = false
            this.doorbellHlsErrorCount = 0
            this.clearDoorbellHlsRetry()
            try { el.play().catch(() => {}) } catch (_) {}
          })
          // mark buffered when fragments/parts appended
          hls.on(Hls.Events.FRAG_BUFFERED, () => {
            if (!this.doorbellHlsBuffered) {
              this.doorbellHlsBuffered = true
              this.clearDoorbellHlsTimeout()
              this.doorbellHlsLoading = false
              this.clearDoorbellHlsRetry()
            }
          })
          hls.on(Hls.Events.BUFFER_APPENDED, () => {
            if (!this.doorbellHlsBuffered) {
              this.doorbellHlsBuffered = true
              this.clearDoorbellHlsTimeout()
              this.doorbellHlsLoading = false
              this.clearDoorbellHlsRetry()
            }
          })
          // also listen for native playing to mark first buffer
          try {
            el.removeEventListener && el.removeEventListener('playing', this.handleDoorbellPlaying)
            el.addEventListener && el.addEventListener('playing', this.handleDoorbellPlaying)
          } catch (_) {}
          hls.on(Hls.Events.ERROR, (_, data = {}) => {
            if (!this.doorbellAlert.open) return
            console.warn('[hls] DOORBELL ERROR', data)
            this.doorbellHlsErrorCount += 1
            try { console.debug('[hls] DOORBELL ERROR detail', JSON.parse(JSON.stringify(data))) } catch (_) {}
            if (data.type === Hls.ErrorTypes.MEDIA_ERROR) {
              try { hls.recoverMediaError(); return } catch (err) { console.warn('[hls] recoverMediaError failed', err) }
            }
            const fatalNetwork = Boolean(data.fatal) || data.type === Hls.ErrorTypes.NETWORK_ERROR
            const tooManyErrors = this.doorbellHlsErrorCount >= 3
            // attempt retry/backoff for network/fatal errors before forcing fallback
            if (fatalNetwork || tooManyErrors) {
              if (this.doorbellHlsRetryAttempts < this.doorbellHlsMaxRetries) {
                this.doorbellHlsRetryAttempts += 1
                const backoff = Math.min(20000, 1000 * Math.pow(2, this.doorbellHlsRetryAttempts - 1))
                console.warn(`[hls] scheduling doorbell hls retry #${this.doorbellHlsRetryAttempts} in ${backoff}ms`)
                this.clearDoorbellHlsRetry()
                this.doorbellHlsRetryTimer = setTimeout(async () => {
                  try {
                    const feed = this.activeDoorbellVideo
                    if (!feed?.camera) {
                      this.forceDoorbellFallback()
                      return
                    }
                    // re-request a fresh session and reload
                    const session = await this.fetchCameraStreamSession(feed.camera, { force: true, scope: CAMERA_HLS_SCOPE_DOORBELL, priority: 'doorbell' })
                    if (session?.playlistUrl) {
                      this.doorbellHlsSourceUrl = session.playlistUrl
                      try {
                        hls.loadSource(session.playlistUrl)
                        hls.startLoad()
                      } catch (err) {
                        console.warn('[hls] retry loadSource/startLoad failed', err)
                      }
                      return
                    }
                  } catch (err) {
                    console.warn('[hls] retry failed', err)
                  }
                  // if retry didn’t produce success, either schedule another retry or fallback
                  if (this.doorbellHlsRetryAttempts >= this.doorbellHlsMaxRetries) {
                    console.warn('[hls] doorbell hls retries exhausted, forcing fallback')
                    this.forceDoorbellFallback()
                  }
                }, backoff)
                return
              }
              console.warn('doorbell hls fatal/too-many error', data)
              this.forceDoorbellFallback()
            }
          })
          this.doorbellHlsController = hls
        } else if (el.canPlayType('application/vnd.apple.mpegurl')) {
          el.src = url
          this.clearDoorbellHlsTimeout()
          this.doorbellHlsLoading = false
          try {
            el.removeEventListener && el.removeEventListener('playing', this.handleDoorbellPlaying)
            el.addEventListener && el.addEventListener('playing', this.handleDoorbellPlaying)
          } catch (_) {}
          try { el.play().catch(() => {}) } catch (_) {}
        } else {
          this.doorbellHlsError = 'Streaming non supportato dal browser'
          this.clearDoorbellHlsTimeout()
        }
      })
    },
    teardownDoorbellHls({ resetError = true, resetDisable = false } = {}) {
      if (this.doorbellHlsController) {
        try { this.doorbellHlsController.destroy() } catch (_) {}
        this.doorbellHlsController = null
      }
      this.clearDoorbellHlsTimeout()
      const el = this.$refs.doorbellVideoEl
      if (el && typeof el.pause === 'function') {
        try { el.pause() } catch (_) {}
        el.removeAttribute('src')
        if (typeof el.load === 'function') {
          try { el.load() } catch (_) {}
        }
      }
      // reset buffered flag
      this.doorbellHlsBuffered = false
      this.doorbellHlsSourceUrl = ''
      this.doorbellHlsErrorCount = 0
      if (resetError) {
        this.doorbellHlsError = null
      }
      if (resetDisable) {
        this.doorbellHlsDisabled = false
      }
      this.doorbellHlsLoading = false
      this.clearDoorbellHlsRetry()
    },

    clearDoorbellHlsRetry() {
      if (this.doorbellHlsRetryTimer) {
        try { clearTimeout(this.doorbellHlsRetryTimer) } catch (_) {}
        this.doorbellHlsRetryTimer = null
      }
      this.doorbellHlsRetryAttempts = 0
    },
    // Hold a short confirmation window before revealing viewer video
    scheduleCameraViewerBufferedConfirm(delay = 700) {
      try { this.clearCameraViewerBufferedConfirm() } catch (_) {}
      this.cameraViewerHlsBufferedConfirmTimer = setTimeout(() => {
        try {
          const video = this.$refs.cameraViewerVideo
          let bufferedSeconds = 0
          try {
            const b = video && video.buffered
            const now = (video && (video.currentTime || 0)) || 0
            if (b && b.length) bufferedSeconds = b.end(b.length - 1) - now
          } catch (_) { bufferedSeconds = 0 }
          if (this.cameraViewerHlsFragBufferedCount >= CAMERA_VIEWER_HLS_BUFFERED_FRAGMENTS && bufferedSeconds >= (CAMERA_VIEWER_HLS_MIN_BUFFERED_SECONDS || 0)) {
            this.cameraViewerHlsBuffered = true
            if (this.cameraViewerNativePlaying) {
              this.cameraViewer = { ...this.cameraViewer, loading: false, error: null }
              try { this.clearCameraViewerFrozenFrame() } catch (_) {}
            }
            try { this.cameraViewerHlsStallCount = 0 } catch (_) {}
            try { this.cameraViewerHlsNetworkFailCount = 0 } catch (_) {}
            this.clearCameraViewerHlsTimeout()
            this.clearCameraViewerHlsRetry()
          } else {
            this.cameraViewerHlsBufferedCandidateAt = 0
          }
        } catch (_) {}
        try { this.cameraViewerHlsBufferedConfirmTimer = null } catch (_) {}
      }, Math.max(150, Number(delay) || 700))
    },

    clearCameraViewerBufferedConfirm() {
      if (this.cameraViewerHlsBufferedConfirmTimer) {
        try { clearTimeout(this.cameraViewerHlsBufferedConfirmTimer) } catch (_) {}
        this.cameraViewerHlsBufferedConfirmTimer = null
      }
      try { this.cameraViewerHlsBufferedCandidateAt = 0 } catch (_) {}
    },
    startDoorbellVideoAutorefresh(intervalMs = 5000) {
      if (this.streamsSuspended) {
        this.stopDoorbellVideoAutorefresh()
        return
      }
      if (!this.doorbellAlert.videos?.length) {
        this.stopDoorbellVideoAutorefresh()
        return
      }
      if (this.doorbellVideoRenderMode === 'hls') {
        this.stopDoorbellVideoAutorefresh()
        return
      }
      if (this.doorbellVideoRefreshTimer) {
        return
      }
      this.doorbellVideoRefreshTimer = setInterval(() => {
        if (this.streamsSuspended) {
          this.stopDoorbellVideoAutorefresh()
          return
        }
        if (this.doorbellVideoRenderMode === 'hls' || !this.doorbellAlert.open) {
          this.stopDoorbellVideoAutorefresh()
          return
        }
        this.refreshActiveDoorbellVideo()
      }, intervalMs)
    },
    stopDoorbellVideoAutorefresh() {
      if (this.doorbellVideoRefreshTimer) {
        clearInterval(this.doorbellVideoRefreshTimer)
        this.doorbellVideoRefreshTimer = null
      }
    },
    setDoorbellHlsTimeout() {
      this.clearDoorbellHlsTimeout()
      this.doorbellHlsTimeout = setTimeout(() => {
        if (!this.doorbellAlert.open || this.streamsSuspended) return
        if (this.doorbellVideoRenderMode === 'hls' && !this.doorbellHlsDisabled) {
          console.warn('doorbell hls timeout, forcing fallback')
          this.forceDoorbellFallback()
        }
      }, DOORBELL_HLS_TIMEOUT)
    },
    clearDoorbellHlsTimeout() {
      if (this.doorbellHlsTimeout) {
        clearTimeout(this.doorbellHlsTimeout)
        this.doorbellHlsTimeout = null
      }
    },
    resolveDoorbellPayloadState(payload) {
      if (payload === null || typeof payload === 'undefined') return null
      if (typeof payload === 'string' || typeof payload === 'number' || typeof payload === 'boolean') {
        return payload
      }
      if (typeof payload !== 'object') {
        return null
      }
      if (Object.prototype.hasOwnProperty.call(payload, 'state')) {
        return payload.state
      }
      if (Object.prototype.hasOwnProperty.call(payload, 's')) {
        return payload.s
      }
      if (Object.prototype.hasOwnProperty.call(payload, 'value')) {
        return payload.value
      }
      if (Object.prototype.hasOwnProperty.call(payload, 'status')) {
        return payload.status
      }
      if (payload.new_state !== undefined) {
        return this.resolveDoorbellPayloadState(payload.new_state)
      }
      if (payload.newState !== undefined) {
        return this.resolveDoorbellPayloadState(payload.newState)
      }
      if (payload.payload !== undefined) {
        return this.resolveDoorbellPayloadState(payload.payload)
      }
      return null
    },
    applyDoorbellEventState(entityId, payload) {
      const key = this.normalizeEntityIdKey(entityId)
      if (!key) return false
      const mapping = this.doorbellTriggerIndex[key]
      if (!mapping) return false
      const resolvedState = this.resolveDoorbellPayloadState(payload)
      const isMomentary = this.isMomentaryDoorbellDevice(mapping.device)
      const rawState = resolvedState === null || typeof resolvedState === 'undefined' ? mapping.device : resolvedState
      const normalizedState = isMomentary ? 'pressed' : this.normalizeDoorbellState(rawState)
      const previousEntry = this.doorbellStateCache[key] || {}
      const previousState = previousEntry.state
      const nextStamp = Date.now()
      this.doorbellStateCache = {
        ...this.doorbellStateCache,
        [key]: {
          state: normalizedState,
          updatedAt: nextStamp
        }
      }
      const triggered = isMomentary
        ? nextStamp - (previousEntry.updatedAt || 0) > 300
        : this.isDoorbellActiveState(normalizedState) && !this.isDoorbellActiveState(previousState)
      if (triggered) {
        console.log('[doorbell] trigger ricevuto', {
          entityId: key,
          slot: mapping.entry?.id,
          label: mapping.entry?.label || this.formatDoorbellLabel(mapping.entry?.id),
          momentary: isMomentary
        })
        this.presentDoorbellAlert(mapping.entry, mapping.device)
      }
      return true
    },
    processDoorbellEvent(detail) {
      if (!detail) return false
      let handled = false
      const mapPayload = detail.event?.a || detail.a
      if (mapPayload && typeof mapPayload === 'object') {
        Object.entries(mapPayload).forEach(([entityId, payload]) => {
          handled = this.applyDoorbellEventState(entityId, payload) || handled
        })
      }
      const data = detail.event?.data || detail.data || detail
      const entityId = data?.entity_id || detail.entity_id
      if (entityId) {
        const newStatePayload = data?.new_state ?? detail.new_state ?? data
        handled = this.applyDoorbellEventState(entityId, newStatePayload) || handled
      }
      return handled
    },
    sanitizeCssUrl(value) {
      if (!value) return ''
      return String(value)
        .replace(/"/g, '\\"')
        .replace(/\n|\r/g, '')
        .trim()
    },
    roomBackgroundStyle(room) {
      const sanitized = this.sanitizeCssUrl(room?.background)
      if (!sanitized) return {}
      return {
        backgroundImage: `linear-gradient(135deg, rgba(8,10,16,0.82), rgba(8,10,16,0.72)), url("${sanitized}")`,
        backgroundSize: 'cover',
        backgroundPosition: 'center'
      }
    },
    cameraEntityId(camera) {
      if (!camera) return ''
      if (typeof camera === 'string') return camera
      const candidate =
        camera.entity_id ||
        camera.id ||
        camera.entityId ||
        camera.device_id ||
        camera.deviceId ||
        camera.attributes?.entity_id ||
        camera.attributes?.entityId ||
        camera.attributes?.camera_entity ||
        camera.attributes?.cameraEntity ||
        ''
      if (typeof candidate === 'number') return String(candidate)
      if (typeof candidate === 'string') return candidate
      return ''
    },
    cameraKey(camera) {
      return this.cameraEntityId(camera)
    },
    cameraFrameState(camera) {
      const key = this.cameraKey(camera)
      if (!key) return ''
      if (!this.cameraErrors[key]) return 'is-live'
      return this.cameraFallbacks[key] ? 'has-fallback' : 'has-error'
    },
    cameraHasError(camera) {
      const key = this.cameraKey(camera)
      if (!key) return false
      return Boolean(this.cameraErrors[key])
    },
    cameraErrorMessage(camera) {
      const key = this.cameraKey(camera)
      if (!key) return 'Streaming non disponibile'
      return this.cameraErrors[key] || 'Streaming non disponibile'
    },
    cameraHasFallback(camera) {
      return Boolean(this.cameraFallbackEntry(camera))
    },
    cameraStateChip(camera) {
      if (this.isCameraRefreshing(camera)) {
        return { label: 'Aggiorno', tone: 'pending' }
      }
      if (this.cameraHasError(camera)) {
        if (this.cameraHasFallback(camera)) {
          return { label: 'Snapshot', tone: 'pending' }
        }
        return { label: 'Offline', tone: 'alert' }
      }
      if (this.isCameraPreviewThrottled(camera)) {
        return { label: 'Anteprima limitata', tone: 'pending' }
      }
      return { label: 'Live', tone: 'live' }
    },
    cameraLocationLabel(camera, roomName = '') {
      if (this.isGlobalCamera(camera)) return 'Accesso globale'
      if (roomName) return roomName
      return 'Stanza dedicata'
    },
    isGlobalCamera(camera) {
      return !camera?.room_id
    },
    cameraBelongsToRoom(camera, room) {
      if (!camera || !room || !camera.room_id || typeof room.id === 'undefined' || room.id === null) {
        return false
      }
      return String(camera.room_id) === String(room.id)
    },
    cameraFallbackEntry(camera) {
      const key = this.cameraKey(camera)
      if (!key) return null
      return this.cameraFallbacks[key] || null
    },
    fallbackTimestampLabel(camera) {
      const entry = this.cameraFallbackEntry(camera)
      if (!entry?.fetchedAt) return 'Ultimo tentativo'
      const stamp = this.formatTime(entry.fetchedAt)
      return stamp ? `Agg. ${stamp}` : 'Aggiornamento in corso'
    },
    collectCameraIds(roomSource) {
      const ids = new Set()
      const rooms = Array.isArray(roomSource) ? roomSource : []
      rooms.forEach((room) => {
        const list = Array.isArray(room?.cameras) ? room.cameras : []
        list.forEach((camera) => {
          const key = this.cameraKey(camera)
          if (key) ids.add(key)
        })
      })
      return ids
    },
    pruneCameraCaches(roomSource) {
      const fallback = Array.isArray(this.rooms) ? this.rooms : []
      const ids = this.collectCameraIds(roomSource && roomSource.length ? roomSource : fallback)
      if (!ids.size) {
        if (Object.keys(this.cameraErrors).length) this.cameraErrors = {}
        if (Object.keys(this.cameraStreamSeeds).length) this.cameraStreamSeeds = {}
        if (Object.keys(this.cameraFallbacks).length) this.cameraFallbacks = {}
        this.clearAllCameraRefreshTimers()
        return
      }
      let errorsChanged = false
      const nextErrors = { ...this.cameraErrors }
      Object.keys(nextErrors).forEach((key) => {
        if (!ids.has(key)) {
          delete nextErrors[key]
          errorsChanged = true
        }
      })
      if (errorsChanged) {
        this.cameraErrors = nextErrors
      }
      let seedsChanged = false
      const nextSeeds = { ...this.cameraStreamSeeds }
      Object.keys(nextSeeds).forEach((key) => {
        if (!ids.has(key)) {
          delete nextSeeds[key]
          seedsChanged = true
        }
      })
      if (seedsChanged) {
        this.cameraStreamSeeds = nextSeeds
      }
      let fallbackChanged = false
      const nextFallbacks = { ...this.cameraFallbacks }
      Object.keys(nextFallbacks).forEach((key) => {
        if (!ids.has(key)) {
          delete nextFallbacks[key]
          fallbackChanged = true
        }
      })
      if (fallbackChanged) {
        this.cameraFallbacks = nextFallbacks
      }
      const nextRefreshing = { ...this.cameraRefreshing }
      let refreshingChanged = false
      Object.keys(nextRefreshing).forEach((key) => {
        if (!ids.has(key)) {
          delete nextRefreshing[key]
          refreshingChanged = true
        }
      })
      const nextTimers = { ...this.cameraRefreshTimers }
      Object.keys(nextTimers).forEach((key) => {
        if (!ids.has(key)) {
          clearTimeout(nextTimers[key])
          delete nextTimers[key]
        }
      })
      if (refreshingChanged) {
        this.cameraRefreshing = nextRefreshing
      }
      if (Object.keys(this.cameraViewerHlsBlacklist).length) {
        const nextBlacklist = { ...this.cameraViewerHlsBlacklist }
        let blacklistChanged = false
        Object.keys(nextBlacklist).forEach((key) => {
          if (!ids.has(key)) {
            delete nextBlacklist[key]
            blacklistChanged = true
          }
        })
        if (blacklistChanged) {
          this.cameraViewerHlsBlacklist = nextBlacklist
        }
      }
      this.cameraRefreshTimers = nextTimers
    },
    formatTime(timestamp) {
      if (!timestamp) return ''
      const date = new Date(timestamp)
      if (Number.isNaN(date.getTime())) return ''
      return new Intl.DateTimeFormat('it-IT', { hour: '2-digit', minute: '2-digit' }).format(date)
    },
    formatAlarmStatusTimestamp(timestamp) {
      const label = this.formatTime(timestamp)
      return label ? `Agg. ${label}` : ''
    },
    formatSnapshotTimestamp(timestamp) {
      const label = this.formatTime(timestamp)
      return label ? `Aggiornato alle ${label}` : ''
    },
    ensureCameraSeed(cameraId) {
      if (!cameraId) return Date.now()
      const current = this.cameraStreamSeeds[cameraId]
      if (current) return current
      const seed = Date.now()
      this.cameraStreamSeeds = { ...this.cameraStreamSeeds, [cameraId]: seed }
      return seed
    },
    refreshCameraSeed(cameraId) {
      if (!cameraId) return
      const seed = Date.now()
      this.cameraStreamSeeds = { ...this.cameraStreamSeeds, [cameraId]: seed }
    },
    getAuthToken() {
      if (typeof window === 'undefined') return ''
      try {
        return localStorage.getItem('eface_token') || ''
      } catch (err) {
        return ''
      }
    },
    buildCameraUrl(camera, variant = 'stream') {
      const entityId = this.cameraEntityId(camera)
      if (!entityId) return ''
      const params = new URLSearchParams()
      params.set('seed', this.ensureCameraSeed(entityId))
      const token = this.getAuthToken()
      if (token) {
        params.set('token', token)
      }
      return `/api/devices/cameras/${encodeURIComponent(entityId)}/${variant}?${params.toString()}`
    },
    appendCacheBust(url, label = 'cb') {
      if (!url) return ''
      const connector = url.includes('?') ? '&' : '?'
      return `${url}${connector}${label}=${Date.now()}`
    },
    cameraPreviewSrc(camera) {
      if (this.streamsSuspended) return ''
      // If mosaic previews are disabled, don't provide any preview src to avoid MJPEG loads
      if (!this.mosaicPreviewsEnabled) return ''
      if (this.isCameraPreviewThrottled(camera)) {
        return this.cameraSnapshotUrl(camera)
      }
      // Prefer continuous MJPEG stream for previews (even for HLS-capable cameras)
      // unless throttled above. This provides live mosaic previews instead of a single snapshot.
      return this.cameraStreamSrc(camera)
    },
    cameraStreamSrc(camera) {
      if (this.streamsSuspended) return ''
      return this.buildCameraUrl(camera, 'stream')
    },
    cameraSnapshotUrl(camera) {
      if (this.streamsSuspended) return ''
      return this.buildCameraUrl(camera, 'snapshot')
    },
    cameraViewerConsumesMjpegSlot() {
      if (!this.cameraViewer.open) return false
      if (!this.cameraViewer.camera) return false
      if (this.cameraViewerSnapshotMode) return false
      return this.cameraViewerRenderMode === 'mjpeg'
    },
    isCameraPreviewThrottled(camera) {
      if (!this.cameraViewerConsumesMjpegSlot()) return false
      if (!camera) return false
      if (this.cameraSupportsHls(camera)) return false
      const viewerKey = this.cameraKey(this.cameraViewer.camera)
      const cameraKey = this.cameraKey(camera)
      if (viewerKey && cameraKey && viewerKey === cameraKey) {
        return false
      }
      return true
    },
    async fetchCameraStreamSession(camera, options = {}) {
      const key = this.cameraKey(camera)
      if (!key) {
        throw new Error('missing_camera_id')
      }
      const {
        force = false,
        signal = null,
        scope = CAMERA_HLS_SCOPE_VIEWER,
        priority: priorityOption = 'auto'
      } = options
      const scopedCache = this.cameraHlsSessions[key] || {}
      const cached = !force ? scopedCache[scope] : null
      if (cached && cached.expiresAt && cached.expiresAt > Date.now() + 5000) {
        return cached
      }
      const encoded = encodeURIComponent(key)
      const priorityKey = typeof priorityOption === 'string' ? priorityOption.trim().toLowerCase() : 'auto'
      const priority = Object.prototype.hasOwnProperty.call(CAMERA_STREAM_SESSION_TIMEOUTS, priorityKey)
        ? priorityKey
        : 'auto'
      const timeoutMs = CAMERA_STREAM_SESSION_TIMEOUTS[priority]
      let timeoutId = null
      let relayCleanup = null
      const supportsAbort = typeof AbortController !== 'undefined'
      const abortController = supportsAbort ? new AbortController() : null
      if (signal && abortController) {
        const relay = () => abortController.abort()
        signal.addEventListener('abort', relay, { once: true })
        relayCleanup = () => signal.removeEventListener('abort', relay)
      }
      const requestConfig = abortController ? { signal: abortController.signal } : {}
      const endpointParams = new URLSearchParams()
      endpointParams.set('mode', priority)
      const endpoint = `/api/devices/cameras/${encoded}/stream_session?${endpointParams.toString()}`
      console.log('[hls] fetchCameraStreamSession starting', { camera: key, endpoint, priority })
      const responsePromise = axios.post(endpoint, null, requestConfig)
      responsePromise.catch(() => {})
      const timeoutPromise = new Promise((_, reject) => {
        timeoutId = setTimeout(() => {
          const timeoutError = new Error('stream_session_timeout')
          timeoutError.code = 'stream_session_timeout'
          reject(timeoutError)
        }, timeoutMs)
      })
      try {
        const response = await Promise.race([responsePromise, timeoutPromise])
        const payload = (response?.data) || {}
        console.log('[hls] fetchCameraStreamSession success', { camera: key, payload })
        if (!payload.playlist) {
          throw new Error('stream_session_unavailable')
        }
        const session = {
          sessionId: payload.session,
          playlistUrl: payload.playlist,
          expiresAt: Date.now() + Math.max(5000, (payload.expires_in || 60) * 1000)
        }
        const existing = this.cameraHlsSessions[key] || {}
        this.cameraHlsSessions = {
          ...this.cameraHlsSessions,
          [key]: {
            ...existing,
            [scope]: session
          }
        }
        return session
      } catch (err) {
        console.warn('[hls] fetchCameraStreamSession error', { camera: key, err: err && (err.message || err.code) ? (err.message || err.code) : err })
        if (err?.code === 'stream_session_timeout') {
          throw err
        }
        if (axios.isCancel?.(err) || err?.code === 'ERR_CANCELED') {
          const timeoutError = new Error('stream_session_timeout')
          timeoutError.code = 'stream_session_timeout'
          throw timeoutError
        }
        throw err
      } finally {
        if (timeoutId) {
          clearTimeout(timeoutId)
        }
        if (relayCleanup) {
          relayCleanup()
        }
      }
    },
    refreshCameraFeed(camera) {
      const key = this.cameraKey(camera)
      if (!key) return
      this.clearCameraError(key)
      this.clearCameraFallback(key)
      this.refreshCameraSeed(key)
      this.flagCameraRefreshing(key)
    },
    handleCameraPrimaryClick(camera) {
      // open snapshot-first viewer; user can explicitly start HLS playback
      this.openCameraViewerSnapshot(camera)
    },
    handleCameraError(camera, event) {
      const key = this.cameraKey(camera)
      if (!key) return
      const reason = this.describeCameraError(event)
      this.cameraErrors = { ...this.cameraErrors, [key]: reason }
      this.primeCameraFallback(camera)
      this.clearCameraRefreshing(key)
    },
    handleCameraFrameLoaded(camera) {
      const key = this.cameraKey(camera)
      if (!key) return
      this.clearCameraRefreshing(key)
    },
    clearCameraError(cameraId) {
      if (!cameraId || !this.cameraErrors[cameraId]) return
      const next = { ...this.cameraErrors }
      delete next[cameraId]
      this.cameraErrors = next
    },
    clearCameraFallback(cameraId) {
      if (!cameraId || !this.cameraFallbacks[cameraId]) return
      const next = { ...this.cameraFallbacks }
      delete next[cameraId]
      this.cameraFallbacks = next
    },
    describeCameraError(event) {
      if (event && event.message) return event.message
      return 'Streaming non disponibile'
    },
    openCameraSnapshot(camera, options = {}) {
      if (!camera) return
      const baseUrl = this.cameraSnapshotUrl(camera)
      if (!baseUrl) return
      const finalUrl = this.appendCacheBust(baseUrl, options.external ? 'download' : 'modal')
      if (options.external) {
        if (typeof window !== 'undefined') {
          window.open(finalUrl, '_blank', 'noopener,noreferrer')
        }
        return
      }
      this.snapshotPreview = {
        ...defaultSnapshotState(),
        open: true,
        camera,
        url: finalUrl,
        fetchedAt: Date.now(),
        loading: true
      }
    },
    closeSnapshotModal() {
      if (!this.snapshotPreview.open) return
      this.snapshotPreview = defaultSnapshotState()
    },
    handleSnapshotLoaded() {
      if (!this.snapshotPreview.open) return
      this.snapshotPreview = { ...this.snapshotPreview, loading: false, error: null }
    },
    handleSnapshotError() {
      if (!this.snapshotPreview.open) return
      this.snapshotPreview = { ...this.snapshotPreview, loading: false, error: 'Impossibile caricare l\'istantanea' }
    },
    openCameraViewer(camera) {
      if (!camera) return
      const key = this.cameraKey(camera)
      if (!key) return
      // Disable mosaic previews while viewer is open to free MJPEG slots
      try { this.mosaicPreviewsEnabled = false } catch (_) {}
      this.refreshCameraFeed(camera)
      this.teardownCameraViewerHls()
      this.cameraViewerHlsDisabled = false
      this.clearCameraViewerHlsRetry()
      this.cameraViewerHlsRetryAttempts = 0
      this.stopCameraViewerSnapshotLoop()
      this.invalidateCameraHlsSession(camera, CAMERA_HLS_SCOPE_VIEWER)
      this.clearCameraViewerHlsBlacklist(camera)
      const rawUrl = this.cameraStreamSrc(camera)
      if (!rawUrl) {
        this.cameraViewer = {
          ...defaultCameraViewerState(),
          open: true,
          camera,
          error: 'Streaming non configurato'
        }
        return
      }
      // NOTE: mosaic preview disabling should not prevent opening the viewer.
      // We still want to load the viewer stream even when `skipCameraPreviews` is true.
      const streamUrl = this.appendCacheBust(rawUrl, 'viewer')
      const baseState = {
        ...defaultCameraViewerState(),
        open: true,
        camera,
        url: streamUrl,
        loading: true,
        lastRefresh: Date.now()
      }
      this.cameraViewer = baseState
      this.bumpCameraViewerElementKey()
      this.stopCameraViewerAutorefresh()
      this.startCameraViewerAutorefresh()
      this.scheduleCameraViewerReady()
      const shouldProbeHls =
        this.cameraViewerAutoHlsEnabled &&
        !this.streamsSuspended &&
        !this.cameraForcesMjpeg(camera)
      if (shouldProbeHls) {
        this.startCameraViewerHls(true, 'auto')
      }
    },
    openCameraViewerSnapshot(camera) {
      if (!camera) return
      const key = this.cameraKey(camera)
      if (!key) return
      // show a snapshot/fallback image in the viewer instead of immediately starting HLS
      try { this.mosaicPreviewsEnabled = false } catch (_) {}
      this.refreshCameraFeed(camera)
      this.teardownCameraViewerHls()
      this.clearCameraViewerHlsRetry()
      this.stopCameraViewerAutorefresh()
      this.cameraViewerSnapshotMode = true
      const base = this.cameraSnapshotUrl(camera)
      const snapshotUrl = base ? this.appendCacheBust(base, 'viewer-snap') : (this.cameraFallbackEntry(camera)?.url || '')
      this.cameraViewer = {
        ...defaultCameraViewerState(),
        open: true,
        camera,
        url: snapshotUrl,
        loading: false,
        lastRefresh: Date.now()
      }
      this.bumpCameraViewerElementKey()
      this.startCameraViewerSnapshotLoop()
      this.startCameraViewerAutorefresh()
    },
    playCameraViewer(camera) {
      // start HLS playback for current viewer or a provided camera
      const target = camera || (this.cameraViewer && this.cameraViewer.camera)
      if (!target) return
      if (!this.cameraViewer.open) {
        // open viewer in HLS mode
        this.openCameraViewer(target)
        return
      }
      // if snapshot mode active, clear it and start HLS
      this.cameraViewerSnapshotMode = false
      this.clearCameraViewerHlsRetry()
      this.startCameraViewerHls(true, 'manual')
    },
    closeCameraViewer() {
      if (!this.cameraViewer.open) return
      const camera = this.cameraViewer.camera
      this.stopCameraViewerAutorefresh()
      this.teardownCameraViewerHls()
      this.clearCameraViewerHlsRetry()
      this.cameraViewerHlsRetryAttempts = 0
      this.stopCameraViewerSnapshotLoop()
      this.cameraViewer = defaultCameraViewerState()
      this.cameraViewerHlsDisabled = false
      if (camera) {
        this.invalidateCameraHlsSession(camera, CAMERA_HLS_SCOPE_VIEWER)
        this.clearCameraViewerHlsBlacklist(camera)
      }
      // Re-enable mosaic previews when viewer is closed and refresh visible cameras
      try {
        this.mosaicPreviewsEnabled = true
        // refresh previews for visible cameras (staggered)
        const visible = Array.isArray(this.uniqueCameraList) ? this.uniqueCameraList : []
        if (visible.length) {
          this.refreshScopedCameras(visible, { stagger: true, batchSize: CAMERA_RESUME_BATCH_SIZE, delay: CAMERA_RESUME_STAGGER_DELAY })
        }
      } catch (_) {}
    },
    refreshCameraViewer() {
      if (!this.cameraViewer.open || !this.cameraViewer.camera) return
      if (this.streamsSuspended) return
      const key = this.cameraKey(this.cameraViewer.camera)
      if (!key) return
      if (this.cameraViewerRenderMode === 'hls') {
        this.startCameraViewerHls(true, 'auto')
        return
      }
      if (this.cameraViewerAutoHlsEnabled && !this.cameraForcesMjpeg(this.cameraViewer.camera)) {
        this.clearCameraViewerHlsBlacklist(this.cameraViewer.camera)
        this.startCameraViewerHls(true, 'auto')
        return
      }
      this.refreshCameraSeed(key)
      const rawUrl = this.cameraStreamSrc(this.cameraViewer.camera)
      if (!rawUrl) return
      const nextUrl = this.appendCacheBust(rawUrl, 'viewer')
      this.cameraViewer = {
        ...this.cameraViewer,
        url: nextUrl,
        loading: true,
        error: null,
        lastRefresh: Date.now()
      }
      this.bumpCameraViewerElementKey()
      this.startCameraViewerAutorefresh()
      this.scheduleCameraViewerReady()
    },
    handleCameraViewerLoaded() {
      if (!this.cameraViewer.open) return
      this.cameraViewer = { ...this.cameraViewer, loading: false, error: null }
    },
    handleCameraViewerError(event) {
      if (!this.cameraViewer.open) return
      const message = event?.message || 'Impossibile caricare lo streaming'
      this.cameraViewer = { ...this.cameraViewer, loading: false, error: message }
      this.startCameraViewerAutorefresh()
    },
    handleCameraViewerVideoError(event) {
      if (!this.cameraViewer.open) return
      console.warn('camera viewer video error', event)
      if (this.cameraViewerHlsDisabled) {
        this.cameraViewer = { ...this.cameraViewer, loading: false, error: 'Streaming non disponibile' }
        return
      }
      this.startCameraViewerFallback()
    },
    handleDoorbellVideoError(event) {
      console.warn('doorbell video error', event)
      this.forceDoorbellFallback()
    },
    handleDoorbellPlaying() {
      // mark that HLS has started playing for doorbell and hide placeholder
      if (!this.doorbellAlert.open) return
      this.doorbellHlsBuffered = true
      this.doorbellHlsLoading = false
      this.doorbellHlsError = null
    },
    handleCameraViewerPlaying() {
      if (!this.cameraViewer.open) return
      // mark native playback observed; only clear loading when buffered probe also satisfied
      try { this.cameraViewerNativePlaying = true } catch (_) {}
      if (this.cameraViewerHlsBuffered) {
        this.cameraViewer = { ...this.cameraViewer, loading: false, error: null }
        this.clearCameraViewerHlsTimeout()
        this.clearCameraViewerHlsRetry()
      }
    },
    handleDoorbellFallbackLoaded() {
      this.doorbellFallbackError = null
    },
    handleDoorbellFallbackError(event) {
      console.warn('doorbell fallback error', event)
      this.doorbellFallbackError = 'Streaming non disponibile'
      this.doorbellFallbackStreaming = false
      if (!this.doorbellVideoRefreshInFlight) {
        this.refreshActiveDoorbellVideo()
      }
    },
    forceDoorbellFallback() {
      if (!this.doorbellAlert.open) return
      const video = this.activeDoorbellVideo
      if (video?.camera) {
        this.invalidateCameraHlsSession(video.camera, CAMERA_HLS_SCOPE_DOORBELL)
      }
      this.doorbellHlsDisabled = true
      this.doorbellHlsError = null
      this.doorbellHlsErrorCount = 0
      this.doorbellHlsLoading = false
      this.doorbellFallbackError = null
      this.doorbellFallbackStreaming = false
      this.teardownDoorbellHls({ resetError: true })
      this.$nextTick(() => {
        this.refreshActiveDoorbellVideo()
      })
    },
    startCameraViewerAutorefresh() {
      if (!this.cameraViewer.open) return
      if (this.cameraViewerSnapshotMode) {
        this.stopCameraViewerAutorefresh()
        return
      }
      if (this.cameraViewerRenderMode === 'hls') {
        this.stopCameraViewerAutorefresh()
        return
      }
      this.stopCameraViewerAutorefresh()
      this.cameraViewerRefreshTimer = setTimeout(() => {
        this.refreshCameraViewer()
      }, CAMERA_VIEWER_REFRESH_INTERVAL)
    },
    stopCameraViewerAutorefresh() {
      if (this.cameraViewerRefreshTimer) {
        clearTimeout(this.cameraViewerRefreshTimer)
        this.cameraViewerRefreshTimer = null
      }
    },
    scheduleCameraViewerReady() {
      if (!this.cameraViewer.open) return
      const run = () => {
        if (!this.cameraViewer.open) return
        if (this.cameraViewerRenderMode === 'hls') return
        this.cameraViewer = { ...this.cameraViewer, loading: false, error: null }
      }
      const raf = typeof window !== 'undefined' ? window.requestAnimationFrame : null
      if (typeof raf === 'function') {
        raf(run)
      } else {
        setTimeout(run, 0)
      }
    },
    bumpCameraViewerElementKey() {
      this.cameraViewerElementKey = (this.cameraViewerElementKey + 1) % Number.MAX_SAFE_INTEGER
    },
    setCameraViewerHlsTimeout() {
      this.clearCameraViewerHlsTimeout()
      this.cameraViewerHlsTimeout = setTimeout(() => {
        if (!this.cameraViewer.open) return
        if (this.cameraViewerRenderMode === 'hls') {
          console.warn('camera viewer hls timeout, falling back to mjpeg')
          this.startCameraViewerFallback()
        }
      }, CAMERA_VIEWER_HLS_TIMEOUT)
    },
    clearCameraViewerHlsTimeout() {
      if (this.cameraViewerHlsTimeout) {
        clearTimeout(this.cameraViewerHlsTimeout)
        this.cameraViewerHlsTimeout = null
      }
    },
    clearCameraViewerHlsRetry() {
      if (this.cameraViewerHlsRetryTimer) {
        clearTimeout(this.cameraViewerHlsRetryTimer)
        this.cameraViewerHlsRetryTimer = null
      }
    },
    queueCameraViewerHlsRetry(priority = 'manual', delay = 2500) {
      if (!this.cameraViewer.open) return
      if (this.cameraViewerHlsRetryTimer) return
      if (this.cameraViewerHlsRetryAttempts >= CAMERA_VIEWER_HLS_MAX_RETRIES) {
        return
      }
      this.cameraViewerHlsRetryAttempts += 1
      this.cameraViewerHlsRetryTimer = setTimeout(() => {
        this.cameraViewerHlsRetryTimer = null
        if (!this.cameraViewer.open) return
        this.cameraViewerHlsDisabled = false
        this.startCameraViewerHls(true, priority)
      }, Math.max(250, delay))
    },
    startCameraViewerSnapshotLoop() {
      if (!this.cameraViewer.open || !this.cameraViewer.camera) return
      this.stopCameraViewerSnapshotLoop()
      const tick = () => {
        if (!this.cameraViewer.open) {
          this.stopCameraViewerSnapshotLoop()
          return
        }
        const snapshotUrl = this.cameraSnapshotUrl(this.cameraViewer.camera)
        if (!snapshotUrl) {
          this.stopCameraViewerSnapshotLoop()
          this.cameraViewer = { ...this.cameraViewer, loading: false, error: 'Istantanea non disponibile' }
          return
        }
        const finalUrl = this.appendCacheBust(snapshotUrl, 'viewer-snap')
        this.cameraViewer = {
          ...this.cameraViewer,
          url: finalUrl,
          loading: false,
          error: null,
          lastRefresh: Date.now()
        }
        this.bumpCameraViewerElementKey()
      }
      tick()
      this.cameraViewerSnapshotTimer = setInterval(tick, CAMERA_VIEWER_SNAPSHOT_INTERVAL)
    },
    stopCameraViewerSnapshotLoop() {
      if (this.cameraViewerSnapshotTimer) {
        clearInterval(this.cameraViewerSnapshotTimer)
        this.cameraViewerSnapshotTimer = null
      }
      this.cameraViewerSnapshotMode = false
    },
    async startCameraViewerHls(force = false, priority = 'auto') {
      if (!this.cameraViewer.open || !this.cameraViewer.camera) return
      if (this.cameraForcesMjpeg(this.cameraViewer.camera)) return
      if (this.streamsSuspended) return
      this.clearCameraViewerHlsTimeout()
      this.cameraViewerHlsDisabled = false
      this.cameraViewerHlsErrorCount = 0
      this.stopCameraViewerSnapshotLoop()
      this.cameraViewerSnapshotMode = false
      this.cameraViewer = { ...this.cameraViewer, loading: true, error: null }
      if (force) {
        this.invalidateCameraHlsSession(this.cameraViewer.camera, CAMERA_HLS_SCOPE_VIEWER)
      }
      try {
        const session = await this.fetchCameraStreamSession(this.cameraViewer.camera, {
          force,
          scope: CAMERA_HLS_SCOPE_VIEWER,
          priority
        })
        if (!this.cameraViewer.open || this.streamsSuspended) {
          return
        }
        this.cameraViewerHlsUrl = session.playlistUrl
        this.bumpCameraViewerElementKey()
        this.mountCameraViewerHls(session.playlistUrl)
        this.cameraViewer = { ...this.cameraViewer, loading: false, error: null, lastRefresh: Date.now() }
        this.clearCameraViewerHlsBlacklist(this.cameraViewer.camera)
        this.clearCameraViewerHlsRetry()
        this.cameraViewerHlsRetryAttempts = 0
        this.setCameraViewerHlsTimeout()
      } catch (err) {
        console.warn('camera viewer hls failed', err)
        this.invalidateCameraHlsSession(this.cameraViewer.camera, CAMERA_HLS_SCOPE_VIEWER)
        this.cameraViewerHlsUrl = ''
        this.cameraViewer = { ...this.cameraViewer, loading: false, error: null }
        this.clearCameraViewerHlsTimeout()
        const fatalHlsError = this.isFatalCameraViewerHlsError(err)
        const shouldBlacklist = fatalHlsError || priority !== 'auto'
        const disableHlsUi = shouldBlacklist || fatalHlsError
        this.startCameraViewerFallback({ disableHls: disableHlsUi, blacklist: shouldBlacklist })
        if (!shouldBlacklist && !fatalHlsError) {
          this.queueCameraViewerHlsRetry('manual')
        } else {
          this.clearCameraViewerHlsRetry()
          this.cameraViewerHlsRetryAttempts = 0
        }
      }
    },
    startCameraViewerFallback(options = {}) {
      const { disableHls = true, blacklist = disableHls } = options
      if (!this.cameraViewer.open || !this.cameraViewer.camera) return
      if (this.streamsSuspended) return
      const preferSnapshots = this.cameraSupportsHls(this.cameraViewer.camera)
      if (!disableHls) {
        this.cameraViewerHlsUrl = ''
        this.cameraViewerHlsErrorCount = 0
      }
      if (blacklist) {
        this.markCameraViewerHlsFailure(this.cameraViewer.camera)
      }
      this.teardownCameraViewerHls()
      this.clearCameraViewerHlsTimeout()
      if (preferSnapshots) {
        this.cameraViewerSnapshotMode = true
        this.cameraViewerHlsUrl = ''
        this.cameraViewerHlsDisabled = true
        this.cameraViewer = {
          ...this.cameraViewer,
          url: '',
          loading: true,
          error: null,
          lastRefresh: Date.now()
        }
        this.stopCameraViewerAutorefresh()
        this.startCameraViewerSnapshotLoop()
        return
      }
      this.cameraViewerSnapshotMode = false
      this.stopCameraViewerSnapshotLoop()
      const rawUrl = this.cameraStreamSrc(this.cameraViewer.camera)
      if (!rawUrl) {
        this.cameraViewer = { ...this.cameraViewer, error: 'Streaming non disponibile' }
        return
      }
      const streamUrl = this.appendCacheBust(rawUrl, 'viewer')
      this.cameraViewerHlsUrl = ''
      this.cameraViewerHlsDisabled = disableHls
      if (disableHls) {
        this.cameraViewerHlsErrorCount = 0
      }
      this.cameraViewer = {
        ...this.cameraViewer,
        url: streamUrl,
        loading: true,
        error: null,
        lastRefresh: Date.now()
      }
      this.bumpCameraViewerElementKey()
      this.stopCameraViewerAutorefresh()
      this.startCameraViewerAutorefresh()
      this.scheduleCameraViewerReady()
    },
    forceCameraViewerHls() {
      if (!this.cameraViewer.open || !this.cameraViewer.camera) return
      if (this.cameraForcesMjpeg(this.cameraViewer.camera)) {
        this.cameraViewer = {
          ...this.cameraViewer,
          loading: false,
          error: 'Questa telecamera è configurata solo MJPEG'
        }
        return
      }
      this.clearCameraViewerHlsBlacklist(this.cameraViewer.camera)
      this.invalidateCameraHlsSession(this.cameraViewer.camera, CAMERA_HLS_SCOPE_VIEWER)
      this.cameraViewerHlsDisabled = false
      this.cameraViewerHlsUrl = ''
      this.clearCameraViewerHlsRetry()
      this.cameraViewerHlsRetryAttempts = 0
      this.stopCameraViewerSnapshotLoop()
      this.cameraViewer = { ...this.cameraViewer, loading: true, error: null }
      this.startCameraViewerHls(true, 'manual')
    },
    mountCameraViewerHls(url) {
      this.$nextTick(() => {
        const video = this.$refs.cameraViewerVideo
        if (!video) return
        try { this.clearCameraViewerBufferedConfirm() } catch (_) {}
          if (Hls.isSupported()) {
          if (this.cameraViewerHlsController) {
            try { this.cameraViewerHlsController.destroy() } catch (_) {}
          }
          // Use conservative Hls.js defaults for stability (A/B test)
          // Avoid forcing crossOrigin here; let the proxy handle same-origin delivery.
          const hls = new Hls({
            enableWorker: true,
            autoStartLoad: true,
            startFragPrefetch: true,
            lowLatencyMode: false,
            liveSyncDurationCount: 3,
            maxBufferLength: 60,
            maxMaxBufferLength: 120,
            maxBufferHole: 0.5,
            fragLoadingTimeOut: 60000,
            levelLoadingTimeOut: 60000,
            manifestLoadingTimeOut: 60000
          })
          hls.attachMedia(video)
          hls.on(Hls.Events.MEDIA_ATTACHED, () => {
            console.log('[hls] MEDIA_ATTACHED, loading source', url)
            try { hls.loadSource(url) } catch (e) { console.warn('[hls] loadSource failed', e) }
          })
          hls.on(Hls.Events.MANIFEST_PARSED, () => {
            this.cameraViewer = { ...this.cameraViewer, loading: false, error: null }
            this.clearCameraViewerHlsTimeout()
            // clear transient failure counters on successful manifest
            try { this.cameraViewerHlsStallCount = 0 } catch (_) {}
            try { this.cameraViewerHlsNetworkFailCount = 0 } catch (_) {}
            try { video.play().catch(() => {}) } catch (_) {}
          })
          // increment buffered-frag counter and mark buffered only after threshold
          hls.on(Hls.Events.FRAG_BUFFERED, () => {
            try {
              this.cameraViewerHlsFragBufferedCount = (this.cameraViewerHlsFragBufferedCount || 0) + 1
            } catch (_) { this.cameraViewerHlsFragBufferedCount = 1 }
            // compute buffered seconds if possible
            let bufferedSeconds = 0
            try {
              const b = video && video.buffered
              const now = (video && (video.currentTime || 0)) || 0
              if (b && b.length) bufferedSeconds = b.end(b.length - 1) - now
            } catch (_) { bufferedSeconds = 0 }
            if (!this.cameraViewerHlsBuffered && this.cameraViewerHlsFragBufferedCount >= CAMERA_VIEWER_HLS_BUFFERED_FRAGMENTS && bufferedSeconds >= (CAMERA_VIEWER_HLS_MIN_BUFFERED_SECONDS || 0)) {
              // mark a candidate and require a short sustain window before revealing video
              if (!this.cameraViewerHlsBufferedCandidateAt) {
                this.cameraViewerHlsBufferedCandidateAt = Date.now()
                this.scheduleCameraViewerBufferedConfirm(700)
              }
            } else {
              console.debug('[hls] FRAG_BUFFERED probe', { count: this.cameraViewerHlsFragBufferedCount, bufferedSeconds })
            }
          })
          hls.on(Hls.Events.BUFFER_APPENDED, () => {
            try {
              this.cameraViewerHlsFragBufferedCount = (this.cameraViewerHlsFragBufferedCount || 0) + 1
            } catch (_) { this.cameraViewerHlsFragBufferedCount = 1 }
            let bufferedSeconds = 0
            try {
              const b = video && video.buffered
              const now = (video && (video.currentTime || 0)) || 0
              if (b && b.length) bufferedSeconds = b.end(b.length - 1) - now
            } catch (_) { bufferedSeconds = 0 }
            if (!this.cameraViewerHlsBuffered && this.cameraViewerHlsFragBufferedCount >= CAMERA_VIEWER_HLS_BUFFERED_FRAGMENTS && bufferedSeconds >= (CAMERA_VIEWER_HLS_MIN_BUFFERED_SECONDS || 0)) {
              if (!this.cameraViewerHlsBufferedCandidateAt) {
                this.cameraViewerHlsBufferedCandidateAt = Date.now()
                this.scheduleCameraViewerBufferedConfirm(700)
              }
            } else {
              console.debug('[hls] BUFFER_APPENDED probe', { count: this.cameraViewerHlsFragBufferedCount, bufferedSeconds })
            }
          })
          // also listen for native playing to mark first buffer (safety)
          try {
            video.removeEventListener && video.removeEventListener('playing', this.handleCameraViewerPlaying)
            video.addEventListener && video.addEventListener('playing', this.handleCameraViewerPlaying)
          } catch (_) {}
          hls.on(Hls.Events.ERROR, (_, data = {}) => {
            if (!this.cameraViewer.open) return
            try { this.clearCameraViewerBufferedConfirm() } catch (_) {}
            console.warn('[hls] CAMERA_VIEWER ERROR', data)
            this.cameraViewerHlsErrorCount += 1
            try { console.debug('[hls] CAMERA_VIEWER ERROR detail', JSON.parse(JSON.stringify(data))) } catch (_) {}
            const type = data.type
            const fatal = Boolean(data.fatal)

            // Detect repeated buffer stalls and force fallback/blacklist
            try {
              const details = data && data.details ? data.details.toString().toLowerCase() : ''
              if (details && details.includes('bufferstal') || details.includes('buffer_stalled') || details.includes('bufferstallederror')) {
                this.cameraViewerHlsStallCount = (this.cameraViewerHlsStallCount || 0) + 1
                console.warn('[hls] buffer stalled count', this.cameraViewerHlsStallCount)
                if (this.cameraViewerHlsStallCount >= 3) {
                  console.warn('[hls] too many buffer stalls, forcing fallback and blacklisting camera')
                  try { this.markCameraViewerHlsFailure(this.cameraViewer.camera) } catch (_) {}
                  try { this.startCameraViewerFallback({ disableHls: true, blacklist: true }) } catch (_) {}
                  return
                }
              }
            } catch (_) {}

            // Detect repeated upstream 502/503 network failures and fallback
            try {
              const status = data?.response?.code || data?.response?.status || null
              if (status === 502 || status === 503) {
                this.cameraViewerHlsNetworkFailCount = (this.cameraViewerHlsNetworkFailCount || 0) + 1
                console.warn('[hls] server returned', status, 'network fail count', this.cameraViewerHlsNetworkFailCount)
                if (this.cameraViewerHlsNetworkFailCount >= 3) {
                  console.warn('[hls] repeated network errors, blacklisting and falling back')
                  try { this.markCameraViewerHlsFailure(this.cameraViewer.camera) } catch (_) {}
                  try { this.startCameraViewerFallback({ disableHls: true, blacklist: true }) } catch (_) {}
                  return
                }
              }
            } catch (_) {}

            // Try to recover from media errors first
            if (type === Hls.ErrorTypes.MEDIA_ERROR) {
              try {
                console.warn('[hls] attempting media error recovery')
                hls.recoverMediaError()
                return
              } catch (err) { console.warn('[hls] recoverMediaError failed', err) }
            }

            // For fatal errors prefer a short retry/backoff before falling back to MJPEG.
            if (fatal) {
              // If UI-level HLS disabled, show error immediately
              if (this.cameraViewerHlsDisabled) {
                this.cameraViewer = { ...this.cameraViewer, loading: false, error: 'Streaming non disponibile' }
                return
              }

              // If we still have retry budget, teardown and schedule a retry with backoff
              if (this.cameraViewerHlsRetryAttempts < CAMERA_VIEWER_HLS_MAX_RETRIES) {
                console.warn('[hls] fatal error, scheduling retry attempt', this.cameraViewerHlsRetryAttempts + 1)
                try { hls.destroy() } catch (_) {}
                try { this.teardownCameraViewerHls() } catch (_) {}
                const delay = 1000 * (1 + this.cameraViewerHlsRetryAttempts) // 1s, 2s, ...
                this.queueCameraViewerHlsRetry('auto', delay)
                return
              }

              // Out of retries -> fallback
              console.warn('[hls] fatal error, out of retries, falling back', data)
              this.startCameraViewerFallback()
            }
          })
          this.cameraViewerHlsController = hls
        } else if (video.canPlayType('application/vnd.apple.mpegurl')) {
          video.src = url
          this.cameraViewer = { ...this.cameraViewer, loading: false, error: null }
          this.clearCameraViewerHlsTimeout()
          try { video.play().catch(() => {}) } catch (_) {}
        } else {
          this.cameraViewer = { ...this.cameraViewer, error: 'Streaming non supportato dal browser' }
        }
      })
    },
    teardownCameraViewerHls() {
      if (this.cameraViewerHlsController) {
        try { this.cameraViewerHlsController.destroy() } catch (_) {}
        this.cameraViewerHlsController = null
      }
      this.clearCameraViewerHlsTimeout()
      this.cameraViewerHlsUrl = ''
      this.cameraViewerHlsErrorCount = 0
      // reset buffered state and frag count
      try { this.cameraViewerHlsBuffered = false } catch (_) {}
      try { this.cameraViewerHlsFragBufferedCount = 0 } catch (_) {}
      try { this.clearCameraViewerBufferedConfirm() } catch (_) {}
      const video = this.$refs.cameraViewerVideo
      if (video && typeof video.pause === 'function') {
        try { video.pause() } catch (_) {}
        video.removeAttribute('src')
        if (typeof video.load === 'function') {
          try { video.load() } catch (_) {}
        }
      }
    },
    refreshSnapshotModal() {
      if (!this.snapshotPreview.open || !this.snapshotPreview.camera) return
      const baseUrl = this.cameraSnapshotUrl(this.snapshotPreview.camera)
      if (!baseUrl) return
      this.snapshotPreview = {
        ...this.snapshotPreview,
        url: this.appendCacheBust(baseUrl, 'modal'),
        fetchedAt: Date.now(),
        loading: true,
        error: null
      }
    },
    primeCameraFallback(camera) {
      const key = this.cameraKey(camera)
      if (!key) return
      const baseUrl = this.cameraSnapshotUrl(camera)
      if (!baseUrl) return
      const entry = { url: this.appendCacheBust(baseUrl, 'fallback'), fetchedAt: Date.now() }
      this.cameraFallbacks = { ...this.cameraFallbacks, [key]: entry }
    },
    refreshCameraFallback(camera) {
      this.primeCameraFallback(camera)
    },
    flagCameraRefreshing(cameraId) {
      if (!cameraId) return
      const timer = setTimeout(() => this.clearCameraRefreshing(cameraId), 6000)
      if (this.cameraRefreshTimers[cameraId]) {
        clearTimeout(this.cameraRefreshTimers[cameraId])
      }
      this.cameraRefreshTimers = { ...this.cameraRefreshTimers, [cameraId]: timer }
      this.cameraRefreshing = { ...this.cameraRefreshing, [cameraId]: true }
    },
    clearCameraRefreshing(cameraId) {
      if (!cameraId) return
      if (this.cameraRefreshTimers[cameraId]) {
        clearTimeout(this.cameraRefreshTimers[cameraId])
        const nextTimers = { ...this.cameraRefreshTimers }
        delete nextTimers[cameraId]
        this.cameraRefreshTimers = nextTimers
      }
      if (!this.cameraRefreshing[cameraId]) return
      const nextRefreshing = { ...this.cameraRefreshing }
      delete nextRefreshing[cameraId]
      this.cameraRefreshing = nextRefreshing
    },
    isCameraRefreshing(camera) {
      const key = this.cameraKey(camera)
      if (!key) return false
      return Boolean(this.cameraRefreshing[key])
    },
    clearCameraResumeQueue() {
      if (!this.cameraResumeTimeouts.length) return
      this.cameraResumeTimeouts.forEach((timer) => {
        clearTimeout(timer)
      })
      this.cameraResumeTimeouts = []
    },
    clearAllCameraRefreshTimers() {
      Object.values(this.cameraRefreshTimers).forEach((timer) => clearTimeout(timer))
      this.cameraRefreshTimers = {}
      this.cameraRefreshing = {}
    },
    flattenedDevices() {
      const entries = new Map()
      const pushEntry = (device, roomHint = null) => {
        if (!device) return
        const key = this.deviceEntityId(device)
        if (!key || entries.has(key)) return
        const fallbackName = device.area_name || device.attributes?.room_name || device.attributes?.area || 'Area principale'
        const resolvedRoom = roomHint || { id: `device-room-${key}`, name: fallbackName }
        entries.set(key, { room: resolvedRoom, device })
      }
      this.structuredRooms.forEach((room) => {
        (room.devices || []).forEach((device) => pushEntry(device, room))
      })
      const looseDevices = Array.isArray(this.devices) ? this.devices : []
      looseDevices.forEach((device) => pushEntry(device))
      const securityDevices = Array.isArray(this.securityDevices) ? this.securityDevices : []
      securityDevices.forEach((device) => pushEntry(device))
      return Array.from(entries.values())
    },
    deviceEntityId(device) {
      if (!device) return ''
      if (typeof device === 'string') return device
      return device.entity_id || device.id || device.entityId || device.attributes?.entity_id || ''
    },
    extractDeviceTags(device, options = {}) {
      if (!device) return []
      const includeLabels = options.includeLabels !== false
      const tags = new Set()
      const pushValue = (value) => {
        if (value === null || typeof value === 'undefined') return
        if (Array.isArray(value) || value instanceof Set) {
          value.forEach((entry) => pushValue(entry))
          return
        }
        if (value instanceof Map) {
          value.forEach((entryValue, entryKey) => {
            pushValue(entryKey)
            pushValue(entryValue)
          })
          return
        }
        if (typeof value === 'object') {
          const named = value.name || value.tag || value.key || value.id
          const val = value.value || value.label || value.text || value.display
          if (named && val) {
            const combo = `${named}:${val}`
            pushValue(combo)
          }
          Object.entries(value).forEach(([key, entry]) => {
            pushValue(key)
            pushValue(entry)
          })
          return
        }
        if (typeof value === 'number' || typeof value === 'boolean') {
          pushValue(String(value))
          return
        }
        if (typeof value === 'string') {
          const trimmed = value.trim()
          if (!trimmed) return
          if (/^[\[{]/.test(trimmed)) {
            try {
              const parsed = JSON.parse(trimmed)
              pushValue(parsed)
              return
            } catch (err) {
              // ignore malformed json
            }
          }
          trimmed.split(',').forEach((token) => {
            const normalized = token.trim().toLowerCase()
            if (normalized) {
              tags.add(normalized)
            }
          })
        }
      }
      const attrs = device.attributes || {}
      pushValue(device.labels)
      pushValue(device.tags)
      pushValue(attrs.labels)
      pushValue(attrs.tags)
      pushValue(attrs.eface_tags)
      pushValue(attrs.custom_tags)
      pushValue(attrs.alarm_status)
      pushValue(attrs.alarmStatus)
      if (includeLabels) {
        pushValue(attrs.label)
        pushValue(attrs.tag)
      }
      return Array.from(tags)
    },
    isAlarmStatusTag(tag) {
      if (!tag) return false
      const normalized = tag.toString().trim().toLowerCase()
      if (!normalized) return false
      const scrubbed = normalized.replace(/[_]+/g, ' ')
      return /^alarm[\s-]*status(?:[:=\s-]|$)/.test(scrubbed)
    },
    alarmStatusValueFromTags(device) {
      if (!device) return ''
      const tags = this.extractDeviceTags(device, { includeLabels: false })
      for (const tag of tags) {
        const value = this.parseAlarmStatusTagValue(tag)
        if (value) return value
      }
      return ''
    },
    parseAlarmStatusTagValue(tag) {
      if (!this.isAlarmStatusTag(tag)) return ''
      const normalized = tag.toString().trim().toLowerCase()
      const scrubbed = normalized.replace(/[_]+/g, ' ')
      const match = scrubbed.match(/^alarm[\s-]*status(?:[:=\s-]+(.+))?$/)
      if (!match) return ''
      const value = (match[1] || '').trim()
      return value.toLowerCase()
    },
    deviceHasAlarmZoneTag(device) {
      return this.extractDeviceTags(device).some((tag) => {
        const hasAlarm = tag.includes('alarm') || tag.includes('allarme')
        const hasZone = tag.includes('zone') || tag.includes('zona') || tag.includes('sensor')
        return hasAlarm && hasZone
      })
    },
    deviceHasAlarmPartitionTag(device) {
      return this.extractDeviceTags(device).some((tag) => {
        const hasAlarm = tag.includes('alarm') || tag.includes('allarme')
        const hasPartition = tag.includes('part') || tag.includes('partition') || tag.includes('partizione')
        return hasAlarm && hasPartition
      })
    },
    isAlarmPartitionDevice(device) {
      if (!device) return false
      if (this.deviceHasAlarmPartitionTag(device)) return true
      const domain = this.deviceDomain(device)
      return domain === 'alarm_control_panel'
    },
    isAlarmZoneDevice(device) {
      if (!device) return false
      if (this.deviceHasAlarmZoneTag(device)) return true
      const domain = this.deviceDomain(device)
      if (domain !== 'binary_sensor' && domain !== 'sensor') {
        return false
      }
      const deviceClass = (device.device_class || device.attributes?.device_class || '').toLowerCase()
      const allowed = ['door', 'window', 'opening', 'motion', 'occupancy', 'garage_door', 'safety', 'lock', 'vibration', 'tamper']
      return allowed.includes(deviceClass)
    },
    buildAlarmPartitionEntry(device, room) {
      const id = this.deviceEntityId(device)
      if (!id) return null
      const stateMeta = this.describeAlarmPanelState(device.state || device.attributes?.state || '')
      const location = this.formatLocationLabel(
        room?.name || device.area_name || device.attributes?.room_name || device.attributes?.area || ''
      )
      const timestamp = device.last_changed || device.last_updated
      const formattedTime = timestamp ? this.formatTime(timestamp) : ''
      const detailParts = []
      if (location) detailParts.push(location)
      if (formattedTime) detailParts.push(`Agg. ${formattedTime}`)
      return {
        id,
        name: device.name || device.attributes?.friendly_name || this.formatCondition(id),
        label: stateMeta.label,
        tone: stateMeta.tone,
        detail: this.joinDetailParts(detailParts) || 'Monitoraggio attivo',
        detailParts,
        location,
        updatedAt: timestamp || null
      }
    },
    buildAlarmZoneEntry(device, room) {
      const id = this.deviceEntityId(device)
      if (!id) return null
      const meta = this.describeAlarmZoneState(device)
      const location = this.formatLocationLabel(
        room?.name || device.area_name || device.attributes?.room_name || device.attributes?.area || ''
      )
      const deviceClass = this.formatCondition(device.device_class || device.attributes?.device_class || '')
      const timestamp = device.last_changed || device.last_updated
      const formattedTime = timestamp ? this.formatTime(timestamp) : ''
      const detailParts = []
      if (deviceClass) detailParts.push(deviceClass)
      if (formattedTime) detailParts.push(`Agg. ${formattedTime}`)
      return {
        id,
        name: device.name || device.attributes?.friendly_name || this.formatCondition(id),
        label: meta.label,
        tone: meta.tone,
        detail: this.joinDetailParts(detailParts) || 'Monitoraggio attivo',
        roomName: location
      }
    },
    formatLocationLabel(value) {
      if (!value) return ''
      const label = String(value).trim()
      if (!label) return ''
      const spaced = label.replace(/([a-zà-öø-ÿ0-9])([A-ZÀ-ÖØ-Ý])/g, '$1 $2')
      return spaced.replace(/\s{2,}/g, ' ').trim()
    },
    joinDetailParts(parts) {
      if (!Array.isArray(parts)) return ''
      const normalized = parts
        .map((part) => (typeof part === 'string' ? part.trim() : part))
        .filter(Boolean)
        .map((part) => (typeof part === 'string' ? part.replace(/\s{2,}/g, ' ') : part))
      return normalized.join(' · ')
    },
    describeAlarmPanelState(stateValue) {
      const state = (stateValue || '').toString().toLowerCase()
      const mapping = {
        disarmed: { label: 'Disinserito', tone: 'idle' },
        armed_home: { label: 'Inserito casa', tone: 'armed' },
        armed_away: { label: 'Inserito totale', tone: 'armed' },
        armed_night: { label: 'Inserito notte', tone: 'armed' },
        armed_custom_bypass: { label: 'Inserito parziale', tone: 'armed' },
        arming: { label: 'Inserimento', tone: 'pending' },
        pending: { label: 'In attesa', tone: 'pending' },
        triggered: { label: 'Allarme attivo', tone: 'alert' }
      }
      if (mapping[state]) {
        return mapping[state]
      }
      if (!state) {
        return { label: 'Allarme', tone: 'idle' }
      }
      if (state.includes('trigger')) {
        return { label: this.formatCondition(state), tone: 'alert' }
      }
      if (state.includes('armed')) {
        return { label: this.formatCondition(state), tone: 'armed' }
      }
      return { label: this.formatCondition(state), tone: 'idle' }
    },
    describeAlarmZoneState(device) {
      const raw = ((device?.state ?? device?.attributes?.state) || '').toString().toLowerCase()
      if (!raw) {
        return { label: 'Sconosciuto', tone: 'pending' }
      }
      if (raw === 'a') {
        return { label: 'Aperta', tone: 'alert' }
      }
      if (raw === 'r') {
        return { label: 'Chiusa', tone: 'idle' }
      }
      if (['off', 'closed', 'clear', 'idle', 'normal', 'false', 'standby'].includes(raw)) {
        return { label: 'Chiusa', tone: 'idle' }
      }
      if (raw === 'pending') {
        return { label: 'In verifica', tone: 'pending' }
      }
      if (['unavailable', 'unknown'].includes(raw)) {
        return { label: 'Offline', tone: 'pending' }
      }
      if (['on', 'open', 'triggered', 'detected', 'true', 'alarm', 'problem', 'tamper'].includes(raw)) {
        const label = raw === 'open' ? 'Aperta' : raw === 'detected' ? 'Rilevata' : 'Allarme'
        return { label, tone: 'alert' }
      }
      return { label: this.formatCondition(raw), tone: 'idle' }
    },
    alarmToneRank(tone) {
      switch (tone) {
        case 'alert':
          return 0
        case 'pending':
          return 1
        case 'armed':
          return 2
        default:
          return 3
      }
    },
    deviceState(device) {
      if (!device) return null
      const entityId = device.id
      if (entityId && this.optimisticStates[entityId]) {
        return this.optimisticStates[entityId]
      }
      return (
        this.normalizeStateValue(device.state) ||
        this.normalizeStateValue(device?.attributes?.state) ||
        null
      )
    },
    normalizeStateValue(value) {
      if (typeof value === 'string') {
        const normalized = value.trim().toLowerCase()
        if (normalized === 'on' || normalized === 'off') return normalized
        return null
      }
      if (typeof value === 'boolean') {
        return value ? 'on' : 'off'
      }
      return null
    },
    isOn(device) {
      return this.deviceState(device) === 'on'
    },
    zoneStateLabel(zone) {
      if (!zone) return 'Sconosciuto'
      const label = (zone.label || '').trim()
      if (!label) return 'Sconosciuto'
      if (label.length === 1) {
        return label.toUpperCase() === 'A' ? 'Aperta' : 'Chiusa'
      }
      return label
    },
    partitionLocationLabel(partition) {
      const location = this.formatLocationLabel(partition?.location || '')
      if (!location) return ''
      if (location.toLowerCase() === 'impianto') {
        return ''
      }
      return location
    },
    roomActiveLights(room) {
      return (room.devices || []).filter((device) => this.isOn(device)).length
    },
    deviceStateLabel(device) {
      if (!device) return 'Stato sconosciuto'
      if (device.brightness)
      {
        const brightness = extractBrightness(device)
        const percent = Math.round((brightness / 255) * 100)
        return this.isOn(device) ? `Accesa al ${percent}%` : 'Spenta'
      }
      return this.isOn(device) ? 'Accesa' : 'Spenta'
    },
    deviceIcon() {
      return 'bulb'
    },
    colorModes(device) {
      const attrs = device?.attributes || {}
      const modes = new Set()
      const candidates = [
        attrs.supported_color_modes,
        attrs.capabilities?.supported_color_modes,
        device?.supported_color_modes,
        device?.capabilities?.supported_color_modes
      ]
      const pushCandidate = (value) => {
        if (!value) return
        if (Array.isArray(value)) {
          value.forEach((mode) => {
            const normalized = (mode ?? '').toString().trim()
            if (normalized) modes.add(normalized)
          })
          return
        }
        if (typeof value === 'string') {
          value.split(',').forEach((mode) => {
            const normalized = mode.trim()
            if (normalized) modes.add(normalized)
          })
        }
      }
      candidates.forEach(pushCandidate)
      const singleMode = attrs.color_mode || device?.color_mode
      if (singleMode) modes.add(singleMode)
      return Array.from(modes)
    },
    supportedFeatures(device) {
      const attrs = device?.attributes || {}
      const raw = attrs.supported_features ?? device?.supported_features
      if (typeof raw === 'number') return raw
      if (typeof raw === 'string' && raw.trim().length) {
        const parsed = Number(raw)
        return Number.isNaN(parsed) ? null : parsed
      }
      return null
    },
    supportsBrightness(device) {
      const attrs = device?.attributes || {}
      if (typeof device?.brightness === 'number' || typeof attrs.brightness === 'number') return true
      const modes = this.colorModes(device)
      if (modes.some((mode) => ['brightness', 'hs', 'xy', 'rgb', 'rgbw', 'rgbww', 'color_temp'].includes((mode || '').toString().trim().toLowerCase()))) {
        return true
      }
      const features = this.supportedFeatures(device)
      return typeof features === 'number' && (features & 1) === 1
    },
    supportsColor(device) {
      const attrs = device?.attributes || {}
      if (Array.isArray(device?.rgb_color) || Array.isArray(attrs.rgb_color)) return true
      if (Array.isArray(attrs.xy_color) || Array.isArray(attrs.hs_color)) return true
      const modes = this.colorModes(device)
      const colorTokens = ['hs', 'rgb', 'rgbw', 'rgbww', 'xy', 'xy_color', 'rgb_color']
      if (modes.some((mode) => colorTokens.includes((mode || '').toString().trim().toLowerCase()))) {
        return true
      }
      const features = this.supportedFeatures(device)
      if (typeof features === 'number') {
        const COLOR_FLAG = 16
        const WHITE_VALUE_FLAG = 128
        if ((features & COLOR_FLAG) === COLOR_FLAG || (features & WHITE_VALUE_FLAG) === WHITE_VALUE_FLAG) {
          return true
        }
      }
      return false
    },
    supportsColorTemperature(device) {
      const attrs = device?.attributes || {}
      if (typeof attrs.color_temp === 'number' || typeof device?.color_temp === 'number') return true
      const modes = this.colorModes(device)
      if (modes.some((mode) => ['color_temp', 'ct'].includes((mode || '').toString().trim().toLowerCase()))) {
        return true
      }
      const features = this.supportedFeatures(device)
      const COLOR_TEMP_FLAG = 2
      return typeof features === 'number' && (features & COLOR_TEMP_FLAG) === COLOR_TEMP_FLAG
    },
    supportsAdvancedControls(device) {
      return this.supportsBrightness(device) || this.supportsColor(device) || this.supportsColorTemperature(device)
    },
    brightnessValue(device) {
      if (!device) return 0
      return extractBrightness(device)
    },
    colorValue(device) {
      if (!device) return '#ffffff'
      const rgb = extractRgb(device)
      return rgb ? rgbToHex(rgb) : '#ffffff'
    },
    colorFromMireds(mireds) {
      const kelvin = 1000000 / Math.max(1, Number(mireds) || 1)
      const clamped = Math.min(6500, Math.max(2000, kelvin))
      const ratio = (clamped - 2000) / (6500 - 2000)
      return this.mixHex('#ffb347', '#8ab4ff', ratio)
    },
    mixHex(start, end, t = 0.5) {
      const a = hexToRgb(this.ensureHexFormat(start)) || [255, 255, 255]
      const b = hexToRgb(this.ensureHexFormat(end)) || [255, 255, 255]
      const mix = a.map((val, idx) => Math.round(val + (b[idx] - val) * Math.min(1, Math.max(0, t))))
      return rgbToHex(mix)
    },
    hexWithAlpha(hex, alpha = 1) {
      const rgb = hexToRgb(this.ensureHexFormat(hex)) || [255, 255, 255]
      return `rgba(${rgb[0]}, ${rgb[1]}, ${rgb[2]}, ${Math.min(1, Math.max(0, alpha))})`
    },
    deviceActiveColor(device) {
      if (!this.isOn(device)) return null
      if (this.supportsColor(device)) return this.colorValue(device)
      if (this.supportsColorTemperature(device)) {
        const temp = this.colorTempValue(device)
        if (temp) return this.colorFromMireds(temp)
      }
      return '#ffd54f'
    },
    async triggerScene(scene) {
      if (!scene || !scene.id) return
      if (this.sceneTriggering === scene.id) return
      const domain = scene.domain || this.entityDomain(scene.id) || 'button'
      const service = scene.service || (domain === 'button' ? 'press' : 'turn_on')
      const payload = { entity_id: scene.id }
      const direct = this.getDirectHaCaller()
      this.sceneTriggering = scene.id
      try {
        if (direct) {
          try {
            await direct(domain, service, payload)
            this.lastCommand = Date.now()
            return
          } catch (err) {
            console.warn('Direct HA scene trigger failed, falling back to backend', err)
          }
        }
        await axios.post(`/api/devices/${scene.id}/trigger`, { domain, service })
        this.lastCommand = Date.now()
      } catch (err) {
        console.error('Scene trigger failed', err)
      } finally {
        this.sceneTriggering = null
      }
    },
    lightCardStyle(device) {
      const color = this.deviceActiveColor(device)
      if (!color) return {}
      return {
        '--light-accent': color,
        borderColor: this.hexWithAlpha(color, 0.55),
        background: `linear-gradient(140deg, ${this.hexWithAlpha(color, 0.28)}, rgba(5, 7, 20, 0.82))`,
        boxShadow: `0 18px 32px ${this.hexWithAlpha(color, 0.28)}`
      }
    },
    deviceIconStyle(device) {
      const color = this.deviceActiveColor(device)
      if (!color) return {}
      return {
        background: this.hexWithAlpha(color, 0.32),
        borderColor: this.hexWithAlpha(color, 0.65)
      }
    },
    colorTempBounds(device) {
      const attrs = device?.attributes || {}
      const min = Number(attrs.min_mireds ?? 153)
      const max = Number(attrs.max_mireds ?? 500)
      return {
        min: Math.max(100, Math.min(600, min)),
        max: Math.max(200, Math.min(600, Math.max(min + 1, max)))
      }
    },
    colorTempValue(device) {
      if (!device) return null
      const attrs = device?.attributes || {}
      if (typeof attrs.color_temp === 'number') return attrs.color_temp
      if (typeof device?.color_temp === 'number') return device.color_temp
      const bounds = this.colorTempBounds(device)
      return Math.round((bounds.min + bounds.max) / 2)
    },
    async toggleDevice(device, forceState) {
      if (!device) return
      const shouldTurnOn = typeof forceState === 'boolean' ? forceState : !this.isOn(device)
      const previousState = this.isOn(device)
      this.applyOptimisticState(device, shouldTurnOn)
      try {
        if (device.type === 'light') {
          await callLightService(device, shouldTurnOn ? 'turn_on' : 'turn_off')
        } else {
          await axios.post('/api/device/toggle', { id: device.id, state: shouldTurnOn })
        }
        this.lastCommand = Date.now()
        this.queueRoomRefresh()
      } catch (error) {
        console.error(error)
        alert('Impossibile eseguire il comando')
        this.applyOptimisticState(device, previousState)
        this.reconcileOptimisticStates()
        this.queueRoomRefresh(200, { force: true })
      }
    },
    toggle(device) {
      this.toggleDevice(device)
    },
    toggleRoom(room) {
      if (!room?.devices?.length) return
      const shouldTurnOn = this.roomActiveLights(room) === 0
      room.devices.forEach((device) => this.toggleDevice(device, shouldTurnOn))
    },
    openLightsModal() {
      this.lightsModalOpen = true
    },
    closeLightsModal() {
      this.lightsModalOpen = false
    },
    openCoversModal() {
      this.coversModalOpen = true
    },
    closeCoversModal() {
      this.coversModalOpen = false
    },
    openGatesModal() {
      this.gatesModalOpen = true
    },
    closeGatesModal() {
      this.gatesModalOpen = false
    },
    async activateGate(gate) {
      try {
        let service = ''
        switch (gate.domain) {
          case 'cover':
            // Toggle cover: se chiuso apre, se aperto chiude
            if (gate.state === 'closed' || gate.state === 'closing') {
              service = 'open_cover'
            } else if (gate.state === 'open' || gate.state === 'opening') {
              service = 'close_cover'
            } else {
              service = 'toggle'
            }
            break
          case 'switch':
          case 'light':
            service = 'turn_on'
            break
          case 'button':
            service = 'press'
            break
          case 'scene':
            service = 'turn_on'
            break
          default:
            service = 'turn_on'
        }
        console.log(`Activating gate ${gate.entity_id} (domain: ${gate.domain}, state: ${gate.state}, service: ${service})`)
        
        const integration = await axios.get('/api/integration/ws-info')
        const haUrl = integration.data?.host || 'http://homeassistant.local:8123'
        const haToken = integration.data?.token || ''
        
        await axios.post(`${haUrl}/api/services/${gate.domain}/${service}`, {
          entity_id: gate.entity_id
        }, {
          headers: { Authorization: `Bearer ${haToken}` }
        })
        // Refresh state after 1 second
        setTimeout(() => {
          this.$emit('refresh-room')
        }, 1000)
      } catch (err) {
        console.error('Errore attivazione gate:', err)
      }
    },
    async openAllCovers() {
      const targets = this.modalCoverDevices
      if (!targets.length) return
      await Promise.allSettled(targets.map((entry) => this.openCover(entry.ref)))
    },
    async closeAllCovers() {
      const targets = this.modalCoverDevices
      if (!targets.length) return
      await Promise.allSettled(targets.map((entry) => this.closeCover(entry.ref)))
    },
    setLightsModalFilter(showAll) {
      this.showAllLightsInModal = !!showAll
    },
    setCoversModalFilter(showAll) {
      this.showAllCoversInModal = !!showAll
    },
    async turnOffVisibleLights() {
      const targets = this.modalLightDevices.filter((entry) => entry.isOn)
      if (!targets.length) return
      await Promise.allSettled(targets.map((entry) => this.toggleDevice(entry.ref, false)))
    },
    hasRoomLightsOn(room) {
      if (!room || !room.devices) return false
      return room.devices.some(device => device.state === 'on')
    },
    async turnOffRoomLights(room) {
      if (!room || !room.devices) return
      const onDevices = room.devices.filter(device => device.state === 'on')
      if (!onDevices.length) return
      await Promise.allSettled(onDevices.map(device => this.toggleDevice(device, false)))
    },
    openScenesPanel(room) {
      // TODO: implement scenes panel if needed
      console.log('Open scenes for room:', room.name)
    },
    tryOpenDevicePanel(device, room) {
      if (!device) return
      const supportsBrightness = this.supportsBrightness(device)
      const supportsColor = this.supportsColor(device)
      const supportsColorTemp = this.supportsColorTemperature(device)
      if (!supportsBrightness && !supportsColor && !supportsColorTemp) {
        this.toggle(device)
        return
      }
      const color = this.colorValue(device)
      this.devicePanel = {
        open: true,
        device,
        roomName: room?.name || this.roomNameLabel,
        brightness: this.brightnessValue(device) || 0,
        color,
        hue: this.hexToHue(color),
        colorTemp: supportsColorTemp ? this.colorTempValue(device) : null,
        supportsBrightness,
        supportsColor,
        supportsColorTemp
      }
    },
    closeDevicePanel() {
      this.devicePanel = {
        ...this.devicePanel,
        open: false
      }
    },
    syncDevicePanel() {
      if (!this.devicePanel.open || !this.devicePanel.device) return
      const entry = this.flattenedDevices().find(({ device }) => device.id === this.devicePanel.device.id)
      if (!entry) return
      const prevDevice = this.devicePanel.device || {}
      const nextDevice = entry.device || {}
      const mergedAttributes = {
        ...(prevDevice.attributes || {}),
        ...(nextDevice.attributes || {})
      }
      const mergedDevice = {
        ...prevDevice,
        ...nextDevice,
        attributes: mergedAttributes
      }
      const color = this.colorValue(mergedDevice)
      const supportsTemp = this.supportsColorTemperature(mergedDevice)
      this.devicePanel = {
        ...this.devicePanel,
        device: mergedDevice,
        roomName: entry.room?.name || this.devicePanel.roomName,
        brightness: this.brightnessValue(mergedDevice) || 0,
        color,
        hue: this.hexToHue(color),
        colorTemp: supportsTemp ? this.colorTempValue(mergedDevice) : null,
        supportsBrightness: this.devicePanel.supportsBrightness || this.supportsBrightness(mergedDevice),
        supportsColor: this.devicePanel.supportsColor || this.supportsColor(mergedDevice),
        supportsColorTemp: this.devicePanel.supportsColorTemp || supportsTemp
      }
    },
    normalizeColorTemp(value, device = null) {
      const bounds = this.colorTempBounds(device || this.devicePanel.device || {})
      const num = Math.round(Number(value))
      if (Number.isNaN(num)) return bounds.min
      return Math.max(bounds.min, Math.min(bounds.max, num))
    },
    previewPanelBrightness(value) {
      const next = Number(value)
      this.devicePanel = { ...this.devicePanel, brightness: Number.isNaN(next) ? 0 : next }
    },
    async commitPanelBrightness() {
      if (!this.devicePanel.device || !this.panelSupportsBrightness) return
      const prevState = this.isOn(this.devicePanel.device)
      this.applyOptimisticState(this.devicePanel.device, true)
      try {
        await callLightService(this.devicePanel.device, 'turn_on', {
          brightness: normalizeBrightness(this.devicePanel.brightness)
        })
        this.lastCommand = Date.now()
        this.queueRoomRefresh()
      } catch (e) {
        console.error(e)
        alert('Impossibile aggiornare la luminosità')
        this.applyOptimisticState(this.devicePanel.device, prevState)
        this.reconcileOptimisticStates()
        this.queueRoomRefresh(200, { force: true })
      }
    },
    previewPanelColorTemp(value) {
      const normalized = this.normalizeColorTemp(value)
      this.devicePanel = { ...this.devicePanel, colorTemp: normalized }
    },
    async commitPanelColorTemp() {
      if (!this.devicePanel.device || !this.panelSupportsColorTemp || !this.devicePanel.colorTemp) return
      const prevState = this.isOn(this.devicePanel.device)
      this.applyOptimisticState(this.devicePanel.device, true)
      try {
        await callLightService(this.devicePanel.device, 'turn_on', { color_temp: this.devicePanel.colorTemp })
        this.lastCommand = Date.now()
        this.queueRoomRefresh()
      } catch (e) {
        console.error(e)
        alert('Impossibile aggiornare la tonalità')
        this.applyOptimisticState(this.devicePanel.device, prevState)
        this.reconcileOptimisticStates()
        this.queueRoomRefresh(200, { force: true })
      }
    },
    previewPanelHue(value) {
      const hue = Number(value)
      const normalizedHue = Number.isNaN(hue) ? 0 : Math.max(0, Math.min(360, hue))
      this.devicePanel = { ...this.devicePanel, hue: normalizedHue, color: this.hueToHex(normalizedHue) }
    },
    async commitPanelHue() {
      if (!this.devicePanel.device || !this.panelSupportsColor) return
      const prevState = this.isOn(this.devicePanel.device)
      this.applyOptimisticState(this.devicePanel.device, true)
      try {
        const rgb = hexToRgb(this.ensureHexFormat(this.devicePanel.color))
        await callLightService(this.devicePanel.device, 'turn_on', { rgb_color: rgb })
        this.lastCommand = Date.now()
        this.queueRoomRefresh()
      } catch (e) {
        console.error(e)
        alert('Impossibile aggiornare la tonalità colore')
        this.applyOptimisticState(this.devicePanel.device, prevState)
        this.reconcileOptimisticStates()
        this.queueRoomRefresh(200, { force: true })
      }
    },
    async applyPanelColor(color) {
      if (!this.devicePanel.device || !this.supportsColor(this.devicePanel.device)) return
      const normalized = this.ensureHexFormat(color)
      if (!isValidHexColor(normalized)) return
      const rgb = hexToRgb(normalized)
      if (!rgb) return
      const payload = { rgb_color: rgb }
      if (this.supportsBrightness(this.devicePanel.device)) {
        payload.brightness = normalizeBrightness(this.devicePanel.brightness)
      }
      const prevState = this.isOn(this.devicePanel.device)
      this.applyOptimisticState(this.devicePanel.device, true)
      try {
        await callLightService(this.devicePanel.device, 'color', payload)
        this.devicePanel = { ...this.devicePanel, color: normalized, hue: this.hexToHue(normalized) }
        this.lastCommand = Date.now()
        this.queueRoomRefresh()
      } catch (e) {
        console.error(e)
        alert('Impossibile aggiornare il colore')
        this.applyOptimisticState(this.devicePanel.device, prevState)
        this.reconcileOptimisticStates()
        this.queueRoomRefresh(200, { force: true })
      }
    },
    applyOptimisticState(device, stateValue) {
      if (!device?.id) return
      if (typeof stateValue !== 'boolean') {
        this.clearOptimisticState(device.id)
        return
      }
      const next = stateValue ? 'on' : 'off'
      const updated = { ...this.optimisticStates, [device.id]: next }
      this.optimisticStates = updated
      this.scheduleOptimisticExpiry(device.id)
    },
    clearOptimisticState(entityId) {
      if (!entityId) return
      if (this.optimisticStates[entityId]) {
        const clone = { ...this.optimisticStates }
        delete clone[entityId]
        this.optimisticStates = clone
      }
      this.clearOptimisticTimer(entityId)
    },
    scheduleOptimisticExpiry(entityId, ttl = 7000) {
      if (!entityId) return
      this.clearOptimisticTimer(entityId)
      this.optimisticTimers[entityId] = setTimeout(() => {
        this.clearOptimisticState(entityId)
      }, ttl)
    },
    clearOptimisticTimer(entityId) {
      if (!entityId) return
      const timer = this.optimisticTimers[entityId]
      if (timer) {
        clearTimeout(timer)
        delete this.optimisticTimers[entityId]
      }
    },
    clearAllOptimisticTimers() {
      Object.keys(this.optimisticTimers).forEach((key) => this.clearOptimisticTimer(key))
    },
    reconcileOptimisticStates() {
      const entries = Object.keys(this.optimisticStates || {})
      if (!entries.length) return
      const snapshot = new Map()
      this.flattenedDevices().forEach(({ device }) => {
        if (device?.id) {
          snapshot.set(device.id, this.normalizeStateValue(device.state) || this.normalizeStateValue(device?.attributes?.state))
        }
      })
      let mutated = false
      const clone = { ...this.optimisticStates }
      entries.forEach((entityId) => {
        const optimistic = clone[entityId]
        const actual = snapshot.get(entityId)
        if (!optimistic || optimistic === actual) {
          delete clone[entityId]
          this.clearOptimisticTimer(entityId)
          mutated = true
        }
      })
      if (mutated) {
        this.optimisticStates = clone
      }
    },
    queueRoomRefresh(delay = 500, options = {}) {
      const { force = false } = options
      const optimisticCount = Object.keys(this.optimisticStates || {}).length
      const hasOptimisticState = optimisticCount > 0
      const relyOnRealtime = this.haConnected === true || this.backendConnected === true
      if (!force && hasOptimisticState && relyOnRealtime) {
        return
      }
      let effectiveDelay = delay
      if (!force && hasOptimisticState && !relyOnRealtime) {
        // fallback to backend refresh so optimistic state settles for remote panels
        effectiveDelay = Math.max(delay, 900)
      }
      if (this.pendingRoomRefresh) {
        clearTimeout(this.pendingRoomRefresh)
      }
      this.pendingRoomRefresh = setTimeout(() => {
        this.$emit('refresh-room')
        this.pendingRoomRefresh = null
      }, effectiveDelay)
    },
    clearQueuedRoomRefresh() {
      if (this.pendingRoomRefresh) {
        clearTimeout(this.pendingRoomRefresh)
        this.pendingRoomRefresh = null
      }
    },
    handleHaEvent(evt) {
      const payload = evt?.detail
      const weatherPayload = this.extractWeatherPayload(payload)
      if (weatherPayload) {
        this.haWeather = weatherPayload
      }
      const handledDoorbell = this.processDoorbellEvent(payload)
      if (!handledDoorbell) {
        this.scanDoorbellTriggers()
      }
    },
    extractWeatherPayload(detail) {
      if (!detail) return null
      const mapPayload = detail.event?.a || detail.a
      if (mapPayload) {
        const found = this.findWeatherInMap(mapPayload)
        if (found) return found
      }
      const data = detail.event?.data || detail.data || detail
      const entityId = data?.entity_id || detail.entity_id
      if (this.isWeatherEntity(entityId)) {
        const newState = data?.new_state || detail.new_state || detail.state || {}
        const attrs = newState?.attributes || data?.attributes || detail.attributes || {}
        const stateVal = newState?.state ?? data?.state ?? detail.state ?? null
        return { state: stateVal, attributes: attrs }
      }
      return null
    },
    findWeatherInMap(collection) {
      if (!collection || typeof collection !== 'object') return null
      for (const [entityId, payload] of Object.entries(collection)) {
        if (this.isWeatherEntity(entityId)) {
          const attrs = payload?.a || payload?.attributes || {}
          const stateVal = payload?.s ?? payload?.state ?? null
          return { state: stateVal, attributes: attrs }
        }
      }
      return null
    },
    isWeatherEntity(entityId) {
      return typeof entityId === 'string' && entityId.toLowerCase().startsWith('weather.')
    },
    findWeatherDevice() {
      const dataset = Array.isArray(this.devices) ? this.devices : []
      return dataset.find((dev) => {
        const entity = (dev?.id || dev?.entity_id || '').toLowerCase()
        return entity.startsWith('weather.')
      }) || null
    },
    updateWeatherFromDevices() {
      const deviceWeather = this.findWeatherDevice()
      if (deviceWeather) {
        this.haWeather = deviceWeather
      } else if (!this.haWeather && this.weather) {
        this.haWeather = this.weather
      }
    },
    async fetchHaWeather() {
      this.updateWeatherFromDevices()
    },
    normalizeHaWeather(payload) {
      if (!payload) return null
      const attrs = payload.attributes || payload.a || {}
      const tempSource = attrs.temperature ?? attrs.current_temperature ?? payload.temperature
      const temperature = typeof tempSource === 'number'
        ? `${Math.round(tempSource)}°`
        : (typeof tempSource === 'string' && tempSource.trim() ? tempSource : '--°')
      const stateValue = payload.state ?? payload.s ?? ''
      const conditionRaw = stateValue || attrs.condition || payload.condition || ''
      return {
        icon: this.matchWeatherIcon(conditionRaw),
        temperature,
        condition: this.formatCondition(conditionRaw) || 'In attesa'
      }
    },
    hueToHex(hue) {
      return this.hslToHex(Number(hue) || 0, 0.85, 0.55)
    },
    hslToHex(hue, saturation = 0.85, lightness = 0.55) {
      const h = (((hue % 360) + 360) % 360) / 360
      const s = Math.min(1, Math.max(0, saturation))
      const l = Math.min(1, Math.max(0, lightness))
      const c = (1 - Math.abs(2 * l - 1)) * s
      const x = c * (1 - Math.abs(((h * 6) % 2) - 1))
      const m = l - c / 2
      const segment = Math.floor(h * 6)
      let r = 0
      let g = 0
      let b = 0
      switch (segment) {
        case 0:
          r = c; g = x; b = 0
          break
        case 1:
          r = x; g = c; b = 0
          break
        case 2:
          r = 0; g = c; b = x
          break
        case 3:
          r = 0; g = x; b = c
          break
        case 4:
          r = x; g = 0; b = c
          break
        default:
          r = c; g = 0; b = x
      }
      const rgb = [r + m, g + m, b + m].map((val) => Math.round(val * 255))
      return rgbToHex(rgb)
    },
    hexToHue(hex) {
      const rgb = hexToRgb(this.ensureHexFormat(hex))
      if (!rgb) return 0
      const [r, g, b] = rgb.map((val) => val / 255)
      const max = Math.max(r, g, b)
      const min = Math.min(r, g, b)
      if (max === min) return 0
      let h
      if (max === r) {
        h = (60 * ((g - b) / (max - min)) + 360) % 360
      } else if (max === g) {
        h = (60 * ((b - r) / (max - min)) + 120) % 360
      } else {
        h = (60 * ((r - g) / (max - min)) + 240) % 360
      }
      return Math.round(h)
    },
    ensureHexFormat(color) {
      if (!color) return '#ffffff'
      return color.startsWith('#') ? color : `#${color}`
    },
    coerceNumber(value) {
      if (typeof value === 'number' && Number.isFinite(value)) return value
      if (typeof value === 'string' && value.trim() === '') return null
      const parsed = Number(value)
      return Number.isFinite(parsed) ? parsed : null
    },
    formatTemperatureValue(value) {
      const numeric = this.coerceNumber(value)
      if (numeric === null) {
        return typeof value === 'string' && value.trim() ? value.trim() : null
      }
      return `${Math.round(numeric)}°`
    },
    formatPercentage(value) {
      const numeric = this.coerceNumber(value)
      if (numeric === null) return null
      return `${Math.round(numeric)}%`
    },
    formatWeatherMeasurement(value, unit = '') {
      const numeric = this.coerceNumber(value)
      if (numeric === null) return null
      const rounded = Math.round(numeric * 10) / 10
      const normalized = Number.isInteger(rounded) ? Math.round(rounded) : rounded
      const suffix = unit && typeof unit === 'string' ? unit.trim() : ''
      return `${normalized}${suffix ? ` ${suffix}` : ''}`
    },
    formatWindBearing(value) {
      const numeric = this.coerceNumber(value)
      if (numeric === null) return null
      const normalized = ((numeric % 360) + 360) % 360
      const dirs = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW']
      const idx = Math.round(normalized / 45) % dirs.length
      return `${dirs[idx]} (${Math.round(normalized)}°)`
    },
    formatForecastLabel(value, fallbackIndex = 0) {
      if (!value) {
        const baseDate = new Date(Date.now() + fallbackIndex * 60 * 60 * 1000)
        return new Intl.DateTimeFormat('it-IT', { weekday: 'short', hour: '2-digit' }).format(baseDate)
      }
      const date = new Date(value)
      if (Number.isNaN(date.getTime())) return String(value)
      const now = new Date()
      const sameDay = date.toDateString() === now.toDateString()
      const formatter = new Intl.DateTimeFormat('it-IT', sameDay ? { hour: '2-digit', minute: '2-digit' } : { weekday: 'short', hour: '2-digit' })
      return formatter.format(date)
    },
    formatWeatherTimestamp(value) {
      if (!value) return null
      const date = value instanceof Date ? value : new Date(value)
      if (Number.isNaN(date.getTime())) return null
      return new Intl.DateTimeFormat('it-IT', { weekday: 'short', hour: '2-digit', minute: '2-digit' }).format(date)
    },
    pickForecastArray(attrs = {}, keys = []) {
      if (!attrs || typeof attrs !== 'object') return []
      for (const key of keys) {
        if (!key) continue
        const candidate = attrs[key]
        if (Array.isArray(candidate) && candidate.length) {
          return candidate
        }
      }
      return []
    },
    normalizeForecastEntries(source = [], limit = 8) {
      if (!Array.isArray(source) || !source.length) return []
      return source.slice(0, limit).map((entry, index) => {
        const conditionRaw = entry.condition || entry.summary || entry.precipitation || entry.icon || ''
        const temperatureValue = entry.temperature
          ?? entry.temphi
          ?? entry.high_temperature
          ?? entry.temperature_high
          ?? entry.templow
          ?? entry.low_temperature
          ?? entry.temperature_low
        const labelValue = entry.datetime || entry.time || entry.daytime || entry.dt || entry.timestamp
        return {
          key: labelValue || `slot-${index}`,
          label: this.formatForecastLabel(labelValue, index),
          temperature: this.formatTemperatureValue(temperatureValue) || '--°',
          condition: this.formatCondition(conditionRaw) || '—',
          icon: this.matchWeatherIcon(conditionRaw || entry.icon || '')
        }
      })
    },
    resolveForecastDate(value, fallbackIndex = 0) {
      if (value) {
        const dt = new Date(value)
        if (!Number.isNaN(dt.getTime())) return dt
      }
      const fallback = new Date(Date.now() + fallbackIndex * 60 * 60 * 1000)
      return fallback
    },
    formatDailyLabel(dateLike) {
      if (!dateLike) return '—'
      const date = dateLike instanceof Date ? dateLike : new Date(dateLike)
      if (Number.isNaN(date.getTime())) return String(dateLike)
      return new Intl.DateTimeFormat('it-IT', { weekday: 'short', day: '2-digit', month: '2-digit' }).format(date)
    },
    buildDailyForecast(source = []) {
      if (!Array.isArray(source) || !source.length) return []
      const buckets = new Map()
      source.forEach((entry, index) => {
        const dt = this.resolveForecastDate(entry.datetime || entry.time || entry.daytime, index)
        const key = dt.toISOString().slice(0, 10)
        if (!buckets.has(key)) {
          buckets.set(key, {
            key,
            date: dt,
            high: null,
            low: null,
            samples: []
          })
        }
        const bucket = buckets.get(key)
        const highs = [entry.temperature, entry.temphi, entry.high_temperature]
        const lows = [entry.templow, entry.low_temperature, entry.apparent_temperature_low]
        highs.forEach((val) => {
          const num = this.coerceNumber(val)
          if (num === null) return
          bucket.high = bucket.high === null ? num : Math.max(bucket.high, num)
          bucket.low = bucket.low === null ? num : Math.min(bucket.low, num)
        })
        lows.forEach((val) => {
          const num = this.coerceNumber(val)
          if (num === null) return
          bucket.low = bucket.low === null ? num : Math.min(bucket.low, num)
        })
        bucket.samples.push({
          dt,
          condition: entry.condition || entry.summary || '',
          icon: entry.icon
        })
      })
      return Array.from(buckets.values())
        .sort((a, b) => (a.date?.getTime() || 0) - (b.date?.getTime() || 0))
        .map((bucket) => {
          const targetHour = 13
          const preferredSample = bucket.samples.reduce((best, sample) => {
            const hours = sample.dt instanceof Date ? sample.dt.getHours() : targetHour
            const diff = Math.abs(hours - targetHour)
            if (!best) return { sample, diff }
            return diff < best.diff ? { sample, diff } : best
          }, null)?.sample
          return {
            key: bucket.key,
            label: this.formatDailyLabel(bucket.date),
            high: bucket.high === null ? '--°' : this.formatTemperatureValue(bucket.high),
            low: bucket.low === null ? null : this.formatTemperatureValue(bucket.low),
            condition: this.formatCondition(preferredSample?.condition || '') || '—',
            icon: this.matchWeatherIcon(preferredSample?.condition || preferredSample?.icon || '')
          }
        })
        .slice(0, 5)
    },
    iconMarkup(key) {
      return ICONS[key] || ICONS.default
    },
    getCoverPosition(cover) {
      // Sempre usa la posizione reale da HA, anche durante il movimento
      // L'unico caso in cui usiamo l'ottimistica è quando l'utente muove lo slider manualmente
      const optimistic = this.coverOptimisticStates.get(cover.id)
      if (optimistic !== undefined) return optimistic
      return cover.current_position ?? 0
    },
    isCoverMoving(cover) {
      // Considera in movimento se lo stato locale è true OPPURE se HA dice che si sta muovendo
      return this.coverMovingStates.get(cover.id) || cover.state === 'opening' || cover.state === 'closing'
    },
    isCoverFullyOpen(cover) {
      return this.getCoverPosition(cover) >= 100
    },
    isCoverFullyClosed(cover) {
      return this.getCoverPosition(cover) <= 0
    },
    coverStateBadgeClass(cover) {
      if (this.isCoverMoving(cover)) return 'badge-moving'
      if (this.isCoverFullyOpen(cover)) return 'badge-open'
      if (this.isCoverFullyClosed(cover)) return 'badge-closed'
      return 'badge-partial'
    },
    updateCoverPositionOptimistic(cover, position) {
      this.coverOptimisticStates.set(cover.id, parseInt(position))
    },
    matchWeatherIcon(condition) {
      const value = (condition || '').toLowerCase()
      if (value.includes('storm') || value.includes('temporale')) return 'storm'
      if (value.includes('rain') || value.includes('pioggia')) return 'rain'
      if (value.includes('snow') || value.includes('neve')) return 'snow'
      if (value.includes('cloud') || value.includes('nuvol')) return 'cloud'
      if (value.includes('wind') || value.includes('vento')) return 'wind'
      return 'sun'
    },
    formatTag(tag) {
      if (tag === null || typeof tag === 'undefined') return ''
      const normalized = String(tag).replace(/[_-]+/g, ' ').trim()
      if (!normalized) return ''
      return normalized.charAt(0).toUpperCase() + normalized.slice(1)
    },
    formatCondition(value) {
      if (!value) return ''
      return String(value)
        .replace(/_/g, ' ')
        .replace(/\b\w/g, (match) => match.toUpperCase())
        .trim()
    },
    // Comfort devices methods
    comfortDeviceCount(room) {
      const coverCount = room.covers?.length || 0
      const climateCount = room.climate?.length || 0
      const total = coverCount + climateCount
      if (total === 0) return 'Nessun dispositivo'
      const parts = []
      if (coverCount > 0) parts.push(`${coverCount} ${coverCount === 1 ? 'tapparella' : 'tapparelle'}`)
      if (climateCount > 0) parts.push(`${climateCount} ${climateCount === 1 ? 'dispositivo clima' : 'dispositivi clima'}`)
      return parts.join(', ')
    },
    // Cover methods
    isCoverOpen(cover) {
      return cover.state !== 'closed' && cover.current_position > 0
    },
    coverStateLabel(cover) {
      // Usa prima lo stato locale di movimento
      if (this.isCoverMoving(cover)) {
        const targetPos = this.coverOptimisticStates.get(cover.id)
        if (targetPos === 100) return 'Apertura in corso…'
        if (targetPos === 0) return 'Chiusura in corso…'
        return 'In movimento…'
      }
      // Poi usa lo stato da Home Assistant
      if (cover.state === 'opening') return 'Apertura in corso…'
      if (cover.state === 'closing') return 'Chiusura in corso…'
      if (cover.state === 'closed') return 'Chiuso'
      if (cover.state === 'open') return 'Aperto'
      // Mostra posizione parziale
      const pos = this.getCoverPosition(cover)
      if (pos >= 100) return 'Completamente aperto'
      if (pos <= 0) return 'Completamente chiuso'
      return `Aperto al ${pos}%`
    },
    coverIconStyle(cover) {
      const isActive = this.isCoverOpen(cover)
      return {
        backgroundColor: isActive ? 'rgba(255, 165, 0, 0.15)' : 'rgba(0, 0, 0, 0.05)',
        color: isActive ? '#ffa500' : '#666'
      }
    },
    getCoverPosition(cover) {
      const optimistic = this.coverOptimisticStates.get(cover.id)
      if (optimistic !== undefined) return optimistic
      return cover.current_position ?? 0
    },
    isCoverMoving(cover) {
      return this.coverMovingStates.get(cover.id) || false
    },
    isCoverFullyOpen(cover) {
      return this.getCoverPosition(cover) >= 100
    },
    isCoverFullyClosed(cover) {
      return this.getCoverPosition(cover) <= 0
    },
    coverStateBadgeClass(cover) {
      if (this.isCoverMoving(cover)) return 'badge-moving'
      if (this.isCoverFullyOpen(cover)) return 'badge-open'
      if (this.isCoverFullyClosed(cover)) return 'badge-closed'
      return 'badge-partial'
    },
    updateCoverPositionOptimistic(cover, position) {
      this.coverOptimisticStates.set(cover.id, parseInt(position))
    },
    async openCover(cover) {
      try {
        // Segna solo come "in movimento", NON impostare posizione ottimistica
        // Lascia che sia HA a fornire la posizione reale progressivamente
        this.coverMovingStates.set(cover.id, true)
        
        await axios.post(`/api/comfort/covers/${cover.id}/open`)
        
        // Refresh periodico per sincronizzare durante il movimento
        const refreshInterval = setInterval(() => {
          if (!this.coverMovingStates.get(cover.id)) {
            clearInterval(refreshInterval)
            return
          }
          this.$emit('trigger-refresh', { delay: 100 })
        }, 500) // Più frequente per animazione fluida
        
        // Timeout massimo (tapparella media impiega ~20-30s)
        setTimeout(() => {
          clearInterval(refreshInterval)
          this.coverMovingStates.set(cover.id, false)
          this.coverOptimisticStates.delete(cover.id)
          this.$emit('trigger-refresh', { delay: 100 })
        }, 30000)
      } catch (err) {
        console.error('Failed to open cover:', err)
        this.coverOptimisticStates.delete(cover.id)
        this.coverMovingStates.set(cover.id, false)
      }
    },
    async closeCover(cover) {
      try {
        // Segna solo come "in movimento", NON impostare posizione ottimistica
        // Lascia che sia HA a fornire la posizione reale progressivamente
        this.coverMovingStates.set(cover.id, true)
        
        await axios.post(`/api/comfort/covers/${cover.id}/close`)
        
        // Refresh periodico per sincronizzare durante il movimento
        const refreshInterval = setInterval(() => {
          if (!this.coverMovingStates.get(cover.id)) {
            clearInterval(refreshInterval)
            return
          }
          this.$emit('trigger-refresh', { delay: 100 })
        }, 500) // Più frequente per animazione fluida
        
        // Timeout massimo
        setTimeout(() => {
          clearInterval(refreshInterval)
          this.coverMovingStates.set(cover.id, false)
          this.coverOptimisticStates.delete(cover.id)
          this.$emit('trigger-refresh', { delay: 100 })
        }, 30000)
      } catch (err) {
        console.error('Failed to close cover:', err)
        this.coverOptimisticStates.delete(cover.id)
        this.coverMovingStates.set(cover.id, false)
      }
    },
    async stopCover(cover) {
      try {
        // Ferma immediatamente lo stato locale
        this.coverMovingStates.set(cover.id, false)
        this.coverOptimisticStates.delete(cover.id)
        
        await axios.post(`/api/comfort/covers/${cover.id}/stop`)
        
        // Refresh immediato per ottenere posizione reale
        setTimeout(() => {
          this.$emit('trigger-refresh', { delay: 0 })
        }, 500)
      } catch (err) {
        console.error('Failed to stop cover:', err)
      }
    },
    async setCoverPosition(cover, position) {
      try {
        const pos = parseInt(position)
        this.coverOptimisticStates.set(cover.id, pos)
        this.coverMovingStates.set(cover.id, true)
        await axios.post(`/api/comfort/covers/${cover.id}/position`, { position: pos })
        setTimeout(() => {
          this.coverMovingStates.set(cover.id, false)
          this.coverOptimisticStates.delete(cover.id)
          this.$emit('trigger-refresh', { delay: 100 })
        }, 2000)
      } catch (err) {
        console.error('Failed to set cover position:', err)
        this.coverOptimisticStates.delete(cover.id)
        this.coverMovingStates.set(cover.id, false)
      }
    },
    // Climate methods
    isClimateOn(climate) {
      return climate.state !== 'off' && climate.hvac_mode !== 'off'
    },
    climateStateLabel(climate) {
      if (!this.isClimateOn(climate)) return 'Spento'
      if (climate.hvac_mode === 'heat') return 'Riscaldamento'
      if (climate.hvac_mode === 'cool') return 'Raffrescamento'
      if (climate.hvac_mode === 'auto') return 'Automatico'
      if (climate.hvac_mode === 'fan_only') return 'Solo ventilazione'
      if (climate.hvac_mode === 'dry') return 'Deumidificazione'
      return 'Attivo'
    },
    climateIconStyle(climate) {
      const isActive = this.isClimateOn(climate)
      return {
        backgroundColor: isActive ? 'rgba(255, 69, 0, 0.15)' : 'rgba(0, 0, 0, 0.05)',
        color: isActive ? '#ff4500' : '#666'
      }
    },
    async toggleClimate(climate) {
      try {
        const isOn = this.isClimateOn(climate)
        if (isOn) {
          // Spegni impostando hvac_mode a 'off'
          await this.callClimateService(climate.id, 'set_hvac_mode', { hvac_mode: 'off' })
        } else {
          // Riaccendi usando l'ultima modalità valida o 'heat' come default
          const validModes = climate.hvac_modes?.filter(m => m !== 'off') || ['heat']
          // Cerca una modalità preferita (heat > auto > cool > altro)
          const preferredMode = validModes.includes('heat') ? 'heat' 
            : validModes.includes('auto') ? 'auto'
            : validModes.includes('cool') ? 'cool'
            : validModes[0]
          
          await this.callClimateService(climate.id, 'set_hvac_mode', { hvac_mode: preferredMode })
          
          // Se c'è una temperatura salvata, impostala
          if (climate.temperature || climate.target_temperature) {
            const temp = climate.temperature || climate.target_temperature
            await this.callClimateService(climate.id, 'set_temperature', { temperature: temp })
          }
        }
      } catch (err) {
        console.error('Failed to toggle climate:', err)
      }
    },
    async setTemperature(climate, temperature) {
      try {
        await this.callClimateService(climate.id, 'set_temperature', { temperature })
      } catch (err) {
        console.error('Failed to set temperature:', err)
      }
    },
    async decreaseTemp(climate) {
      const current = climate.temperature || 20
      const newTemp = Math.max(10, current - 0.5)
      await this.setTemperature(climate, newTemp)
    },
    async increaseTemp(climate) {
      const current = climate.temperature || 20
      const newTemp = Math.min(30, current + 0.5)
      await this.setTemperature(climate, newTemp)
    },
    async setHvacMode(climate, mode) {
      try {
        await this.callClimateService(climate.id, 'set_hvac_mode', { hvac_mode: mode })
      } catch (err) {
        console.error('Failed to set HVAC mode:', err)
      }
    },
    async callClimateService(entityId, service, data = {}) {
      const directFn = this.getDirectHaCaller()
      const serviceData = { entity_id: entityId, ...data }
      
      if (directFn) {
        try {
          await directFn('climate', service, serviceData)
          return true
        } catch (err) {
          console.warn('Direct HA call failed for climate', err)
        }
      }
      
      // Fallback to backend API if WebSocket unavailable
      console.warn('No direct HA connection, using backend fallback')
      const endpoint = service === 'turn_on' ? 'turn_on' : service === 'turn_off' ? 'turn_off' : service === 'set_temperature' ? 'temperature' : 'hvac_mode'
      await axios.post(`/api/comfort/climate/${entityId}/${endpoint}`, data)
      return true
    },
    formatHvacMode(mode) {
      const modes = {
        off: 'Spento',
        heat: 'Riscaldamento',
        cool: 'Raffrescamento',
        auto: 'Auto',
        heat_cool: 'Auto',
        fan_only: 'Ventilazione',
        dry: 'Deumidificazione'
      }
      return modes[mode] || mode
    },
    formatHvacAction(action) {
      const labels = {
        heating: 'Riscaldamento',
        cooling: 'Raffrescamento',
        idle: 'Inattivo',
        off: 'Spento'
      }
      return labels[action] || action
    },
    getHvacModeIcon(mode) {
      const icons = {
        heat: '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8zm-1-13h2v6h-2zm0 8h2v2h-2z"/></svg>',
        cool: '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M19.78 17.51l-2.67-1.54 1.83-1.06c.26-.15.33-.49.18-.75s-.49-.33-.75-.18l-2.83 1.63V12l2.83 1.63c.08.05.16.07.24.07.18 0 .36-.1.45-.25.15-.26.08-.6-.18-.75l-1.83-1.06 2.67-1.54c.26-.15.33-.49.18-.75s-.49-.33-.75-.18l-2.67 1.54.33-2.12c.06-.29-.12-.58-.4-.64-.29-.07-.58.12-.64.4l-.54 3.44L14.6 12v-3.6l2.82-2.82c.2-.2.2-.51 0-.71s-.51-.2-.71 0L14.6 7v-2.6c0-.29-.24-.53-.53-.53s-.53.24-.53.53V7l-2.11-2.11c-.2-.2-.51-.2-.71 0s-.2.51 0 .71L13.54 8.4V12l-2.83-1.63-.54-3.44c-.06-.29-.35-.47-.64-.4-.29.06-.47.35-.4.64l.33 2.12-2.67-1.54c-.26-.15-.6-.08-.75.18s-.08.6.18.75l2.67 1.54-1.83 1.06c-.26.15-.33.49-.18.75.09.16.27.25.45.25.08 0 .17-.02.24-.07L10.46 12v3.61L7.63 17.2c-.08.05-.16.07-.24.07-.18 0-.36-.1-.45-.25-.15-.26-.08-.6.18-.75l1.83-1.06-2.67-1.54c-.26-.15-.6-.08-.75.18s-.08.6.18.75l2.67 1.54-.33 2.12c-.06.29.12.58.4.64.04.01.07.01.11.01.25 0 .47-.18.53-.42l.54-3.44L11.46 15v3.6l-2.11 2.11c-.2.2-.2.51 0 .71.1.1.23.15.35.15s.26-.05.35-.15l2.11-2.11v2.6c0 .29.24.53.53.53s.53-.24.53-.53v-2.6l2.11 2.11c.1.1.23.15.35.15s.26-.05.35-.15c.2-.2.2-.51 0-.71L13.54 18.4V15l2.83 1.63.54 3.44c.05.24.27.42.53.42.04 0 .07 0 .11-.01.29-.06.47-.35.4-.64l-.33-2.12 2.67 1.54c.08.05.16.07.24.07.18 0 .36-.1.45-.25.15-.25.08-.59-.18-.74z"/></svg>',
        auto: '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8zm-5.5-2.5l7.51-3.49L17.5 6.5 9.99 9.99 6.5 17.5zm5.5-6.6c.61 0 1.1.49 1.1 1.1s-.49 1.1-1.1 1.1-1.1-.49-1.1-1.1.49-1.1 1.1-1.1z"/></svg>',
        heat_cool: '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8zm-5.5-2.5l7.51-3.49L17.5 6.5 9.99 9.99 6.5 17.5zm5.5-6.6c.61 0 1.1.49 1.1 1.1s-.49 1.1-1.1 1.1-1.1-.49-1.1-1.1.49-1.1 1.1-1.1z"/></svg>',
        dry: '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 2.69l5.66 5.66c3.12 3.12 3.12 8.19 0 11.31C15.52 21.8 13.76 22.5 12 22.5s-3.52-.7-5.66-2.83c-3.12-3.12-3.12-8.19 0-11.31L12 2.69m0 2.83l-4.25 4.24c-2.34 2.34-2.34 6.14 0 8.49 1.17 1.17 2.7 1.76 4.25 1.76s3.08-.59 4.25-1.76c2.34-2.34 2.34-6.14 0-8.49L12 5.52z"/></svg>',
        fan_only: '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M17 11c.34 0 .67.04 1 .09V6.27L10.5 3L3 6.27v4.91c0 4.54 3.2 8.79 7.5 9.82.55-.13 1.08-.32 1.6-.55C11.41 19.47 11 18.28 11 17c0-3.31 2.69-6 6-6z"/></svg>'
      }
      return icons[mode] || icons.auto
    },
    getThermostatColor(climate) {
      if (climate.hvac_action === 'heating') return '#ff6b35'
      if (climate.hvac_action === 'cooling') return '#4a90e2'
      if (climate.hvac_mode === 'heat') return '#ff8c42'
      if (climate.hvac_mode === 'cool') return '#6ab0f3'
      return '#00d4ff'
    },
    getThermostatProgress(climate) {
      const minTemp = climate.attributes?.min_temp || 10
      const maxTemp = climate.attributes?.max_temp || 30
      const currentTemp = climate.current_temperature || minTemp
      const range = maxTemp - minTemp
      const progress = ((currentTemp - minTemp) / range) * 100
      const circumference = 2 * Math.PI * 85
      return `${circumference} ${circumference}`
    }
  }
}
</script>

<style scoped>
:global(body) {
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

.control4-shell {
  display: flex;
  flex-direction: column;
  gap: clamp(16px, 2vw, 28px);
  min-height: calc(100vh - 40px);
  width: 100%;
  box-sizing: border-box;
  color: #f4f7ff;
  --text: #f4f7ff;
  --muted: rgba(255, 255, 255, 0.74);
  --primary: #6c8cff;
  --accent: #22c1c3;
  --card: rgba(9, 12, 24, 0.85);
  padding-bottom: clamp(200px, 24vh, 260px);
  scroll-padding-bottom: 140px;
}

.card {
  border-radius: 22px;
  background: rgba(9, 12, 24, 0.85);
  border: 1px solid rgba(255, 255, 255, 0.05);
  padding: clamp(18px, 1.8vw, 28px);
  backdrop-filter: blur(18px);
  width: 100%;
  box-sizing: border-box;
}


.dashboard-header {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
  gap: 12px;
}

.compact-header {
  padding: clamp(10px, 1.1vw, 18px) clamp(12px, 1.6vw, 22px);
}

.header-inline {
  display: flex;
  align-items: center;
  gap: 12px;
}

.status-inline {
  display: flex;
  align-items: center;
  gap: 8px;
}

.connection-chip {
  display: flex;
  align-items: center;
  gap: 8px;
  border-radius: 16px;
  border: 1px solid rgba(255, 255, 255, 0.18);
  padding: 6px 12px;
  min-height: 34px;
  background: rgba(255, 255, 255, 0.05);
  box-shadow: 0 10px 22px rgba(0, 0, 0, 0.28);
}

.connection-chip.compact {
  padding: 4px 10px;
  min-height: 28px;
  border-radius: 12px;
  box-shadow: none;
  border-color: rgba(255, 255, 255, 0.12);
  background: rgba(255, 255, 255, 0.04);
}

.connection-chip > div {
  display: flex;
  flex-direction: column;
  line-height: 1.1;
}

.connection-chip strong {
  font-size: 11px;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.connection-chip.compact strong {
  font-size: 10px;
}

.connection-chip small {
  font-size: 9px;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: rgba(255, 255, 255, 0.75);
}

.connection-chip.compact small {
  font-size: 8px;
  letter-spacing: 0.04em;
}

.connection-chip .icon {
  width: 26px;
  height: 26px;
  border-radius: 12px;
  background: rgba(5, 7, 20, 0.4);
  border: 1px solid rgba(255, 255, 255, 0.18);
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.connection-chip.compact .icon {
  width: 20px;
  height: 20px;
  border-radius: 10px;
}

.connection-chip.local {
  border-color: rgba(111, 223, 190, 0.8);
  background: rgba(92, 217, 178, 0.18);
}

.connection-chip.cloud {
  border-color: rgba(142, 189, 255, 0.8);
  background: linear-gradient(135deg, rgba(142, 189, 255, 0.18), rgba(97, 125, 255, 0.24));
}

.connection-chip.offline {
  border-color: rgba(255, 255, 255, 0.12);
  background: rgba(255, 255, 255, 0.04);
  opacity: 0.85;
}

.connection-dot {
  width: 18px;
  height: 18px;
  border-radius: 999px;
  border: 1px solid rgba(255, 255, 255, 0.3);
  background: rgba(0, 0, 0, 0.3);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 3px;
  margin-right: 6px;
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.35);
  transition: box-shadow var(--transition-base), transform var(--transition-fast);
}

.connection-dot .dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.6);
  animation: pulse-glow 2.4s ease-in-out infinite;
}

.connection-dot.tone-local .dot {
  background: #34c759;
  box-shadow: 0 0 6px rgba(52, 199, 89, 0.8);
}

.connection-dot.tone-cloud .dot {
  background: #ffd60a;
  box-shadow: 0 0 6px rgba(255, 214, 10, 0.8);
}

.connection-dot.tone-offline .dot {
  background: #ff453a;
  box-shadow: 0 0 6px rgba(255, 69, 58, 0.7);
}

.connection-status-card {
  display: flex;
  align-items: center;
  gap: 14px;
  margin: 6px 0 18px;
  padding: 16px 18px;
  border-radius: 22px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(255, 255, 255, 0.04);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.05);
  transition: transform var(--transition-base), box-shadow var(--transition-base), border-color var(--transition-fast);
}

.connection-status-card .icon {
  width: 42px;
  height: 42px;
  border-radius: 16px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: rgba(5, 7, 20, 0.4);
  border: 1px solid rgba(255, 255, 255, 0.15);
}

.connection-status-card .meta {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.connection-status-card .meta strong {
  font-size: 18px;
  letter-spacing: 0.04em;
}

.connection-status-card .meta small {
  font-size: 12px;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: rgba(255, 255, 255, 0.78);
}

.connection-status-card.local {
  border-color: rgba(111, 223, 190, 0.4);
  background: linear-gradient(135deg, rgba(92, 217, 178, 0.18), rgba(11, 16, 30, 0.85));
}

.connection-status-card.cloud {
  border-color: rgba(142, 189, 255, 0.45);
  background: linear-gradient(135deg, rgba(142, 189, 255, 0.16), rgba(12, 18, 36, 0.88));
}

.connection-status-card.offline {
  border-color: rgba(255, 255, 255, 0.08);
  opacity: 0.9;
}

.connection-status-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.35);
}


.brand-logo {
  width: 78px;
  height: 78px;
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.08);
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 15px 35px rgba(4, 7, 20, 0.45);
  transition: transform var(--transition-base), box-shadow var(--transition-base);
  padding: 8px;
  overflow: hidden;
}

.brand-logo img {
  width: 100%;
  height: 100%;
  object-fit: contain;
  display: block;
}

.brand-logo:hover {
  transform: translateY(-2px) rotate(-1.5deg);
  box-shadow: 0 24px 38px rgba(4, 7, 20, 0.6);
}

.brand-logo.tiny {
  width: 64px;
  height: 64px;
  border-radius: 20px;
}

.muted {
  color: rgba(255, 255, 255, 0.94);
}

.tiny {
  font-size: 12px;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: rgba(255, 255, 255, 0.92);
}

.eyebrow {
  margin: 0;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  font-size: 12px;
  color: var(--muted);
}

.dashboard-header h1 {
  margin: 4px 0;
}

h3 {
  color: rgba(255, 255, 255, 0.97);
  letter-spacing: 0.01em;
}

.weather-chip,
.alarm-chip {
  border-radius: 18px;
  border: 1px solid rgba(255, 255, 255, 0.16);
  padding: 10px 14px;
  background: rgba(255, 255, 255, 0.07);
  transition: transform var(--transition-fast), box-shadow var(--transition-base), border-color var(--transition-fast);
}

.weather-chip {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 190px;
  padding: 12px 18px;
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.08), rgba(49, 85, 255, 0.18));
  box-shadow: 0 12px 28px rgba(0, 0, 0, 0.35);
}

.weather-chip.interactive {
  cursor: pointer;
}

.weather-chip.interactive:focus-visible {
  outline: 2px solid rgba(255, 255, 255, 0.8);
  outline-offset: 2px;
}

.alarm-chip {
  display: flex;
  align-items: center;
  gap: 6px;
  min-height: 32px;
  padding: 6px 10px;
  max-width: 220px;
  background: rgba(255, 255, 255, 0.07);
}

.alarm-chip strong {
  font-size: 0.95rem;
  letter-spacing: 0.02em;
  display: block;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.alarm-chip small {
  font-size: 0.68rem;
  letter-spacing: 0.02em;
  display: block;
  margin-top: 2px;
}

.alarm-chip-body {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.alarm-chip.armed {
  border-color: rgba(137, 227, 255, 0.5);
}

.alarm-chip.alert {
  border-color: rgba(255, 107, 107, 0.7);
  background: rgba(255, 87, 87, 0.15);
}
.weather-chip:hover,
.alarm-chip:hover {
  transform: translateY(-2px);
  box-shadow: 0 16px 32px rgba(0, 0, 0, 0.35);
}

.weather-chip .icon {
  width: 34px;
  height: 34px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 14px;
  background: rgba(5, 7, 20, 0.45);
  border: 1px solid rgba(255, 255, 255, 0.2);
}

.room-chip strong {
  color: #ffffff;
  font-weight: 600;
}

.weather-meta {
  display: flex;
  flex-direction: column;
  line-height: 1.1;
}

.weather-meta strong {
  font-size: clamp(20px, 2.2vw, 30px);
  color: #ffffff;
}

.diag-row>strong{
  color: #ffffff;
}

.weather-meta small {
  margin-top: 2px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  font-size: 11px;
  color: rgba(255, 255, 255, 0.78);
}

.forecast-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 12px;
}

.forecast-day {
  border-radius: 18px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(0, 0, 0, 0.3);
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  align-items: flex-start;
}

.forecast-day .icon {
  width: 30px;
  height: 30px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.04);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.day-temps {
  display: flex;
  align-items: center;
  gap: 6px;
}

.day-temps strong {
  font-size: 22px;
}

.day-temps small {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.78);
}

.no-forecast {
  margin-top: 8px;
}
.weather-chip.compact {
  padding: 6px 10px;
  min-width: auto;
  gap: 8px;
  min-height: 34px;
}


.header-actions {
  display: flex;
  gap: 10px;
  justify-self: flex-end;
}

.header-actions .connection-chip {
  margin-right: 4px;
}

.header-actions.compact .ghost-btn {
  width: 44px;
  height: 44px;
}

.ghost-btn {
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.2);
  background: rgba(255, 255, 255, 0.05);
  color: var(--text);
  padding: 8px 14px;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  transition: background var(--transition-fast), border var(--transition-fast), box-shadow var(--transition-base), transform var(--transition-fast);
}

.ghost-btn.tiny {
  padding: 6px 10px;
  font-size: 12px;
  height: 34px;
  border-radius: 10px;
}

.ghost-btn:hover {
  background: rgba(255, 255, 255, 0.08);
  transform: translateY(-2px);
  box-shadow: 0 12px 24px rgba(4, 7, 20, 0.4);
}

.ghost-btn:active {
  transform: translateY(0) scale(0.97);
}

.ghost-btn:focus-visible {
  outline: 2px solid var(--primary);
  outline-offset: 2px;
}

.icon-only {
  width: 48px;
  height: 48px;
  justify-content: center;
  padding: 0;
  border-radius: 16px;
}

.ghost-btn .icon {
  width: 20px;
  height: 20px;
  color: inherit;
  transition: transform var(--transition-fast);
}

.ghost-btn:hover .icon {
  transform: scale(1.06);
}

.icon :deep(svg),
.nav-icon :deep(svg),
.device-icon :deep(svg) {
  width: 100%;
  height: 100%;
  display: block;
}

.console {
  display: grid;
  grid-template-columns: clamp(96px, 10vw, 120px) minmax(0, 1fr) clamp(190px, 22vw, 280px);
  grid-template-areas: 'nav content right';
  gap: clamp(16px, 2vw, 28px);
  align-items: flex-start;
  padding-bottom: 40px;
}

.console--compact {
  grid-template-columns: clamp(96px, 10vw, 120px) minmax(0, 1fr);
  grid-template-areas: 'nav content';
}

.nav.rail {
  grid-area: nav;
  display: flex;
  flex-direction: column;
  gap: 12px;
  position: sticky;
  top: 32px;
  align-items: center;
  justify-content: flex-start;
  padding: 12px 10px;
  background: rgba(5, 7, 20, 0.8);
  border: 1px solid rgba(255, 255, 255, 0.04);
  border-radius: 22px;
  box-shadow: 0 25px 45px rgba(0, 0, 0, 0.45);
  backdrop-filter: blur(18px);
  width: clamp(70px, 7vw, 92px);
  z-index: 6;
}

.nav-btn {
  text-align: center;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 20px;
  padding: 5px;
  background: transparent;
  color: var(--text);
  display: flex;
  align-items: center;
  justify-content: center;
  width: 50px;
  height: 50px;
  flex: 0 0 50px;
  cursor: pointer;
  transition: border var(--transition-fast), background var(--transition-fast), transform var(--transition-fast), box-shadow var(--transition-base);
  box-shadow: 0 6px 18px rgba(0, 0, 0, 0.25);
}

.nav-btn:hover {
  transform: translateY(-2px);
  border-color: rgba(255, 255, 255, 0.2);
}

.nav-btn.active {
  background: linear-gradient(120deg, var(--primary), var(--accent));
  color: #050714;
  border-color: transparent;
  box-shadow: 0 16px 28px rgba(11, 16, 32, 0.55);
}

.nav-icon {
  width: 30px;
  height: 30px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.12);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.content {
  grid-area: content;
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 20px;
  padding-bottom: clamp(140px, 20vh, 200px);
}

.right.rail {
  grid-area: right;
  position: sticky;
  top: 12px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.room-selector {
  display: flex;
  min-height: 180px;
  width: auto;
  min-width: 0;
  box-sizing: border-box;
  flex-direction: column;
  gap: 16px;
  position: sticky;
  top: calc(env(safe-area-inset-top, 0px) + 8px);
  z-index: 8;
}

.room-selector.card {
  background: rgba(9, 12, 24, 0.95);
  min-height: 50px;
}

.room-select-mobile {
  display: none;
  flex-direction: column;
  gap: 4px;
}

.room-select-mobile select {
  border-radius: 16px;
  border: 1px solid rgba(255, 255, 255, 0.14);
  background: rgba(7, 10, 20, 0.85);
  color: var(--text);
  padding: 10px 14px;
}

.room-chip-row {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 10px;
}

.room-chip {
  border-radius: 18px;
  padding: 14px 16px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  background: rgba(10, 13, 26, 0.65);
  display: flex;
  align-items: center;
  gap: 12px;
  cursor: pointer;
  transition: border var(--transition-fast), transform var(--transition-fast), box-shadow var(--transition-base), background var(--transition-fast);
  box-shadow: 0 8px 22px rgba(4, 7, 18, 0.4);
}

.room-chip strong {
  color: #ffffff;
  font-weight: 600;
}

.room-chip:hover {
  border-color: rgba(108, 140, 255, 0.45);
  transform: translateY(-2px);
  box-shadow: 0 18px 32px rgba(4, 7, 18, 0.55);
}

.room-chip.active {
  border-color: transparent;
  background: linear-gradient(135deg, rgba(108, 140, 255, 0.18), rgba(34, 193, 195, 0.3));
  transform: translateY(-2px);
  box-shadow: 0 24px 40px rgba(4, 7, 18, 0.65);
}

.chip-icon {
  width: 44px;
  height: 44px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.08);
  display: flex;
  align-items: center;
  justify-content: center;
}

.security-stack {
  display: flex;
  flex-direction: column;
  gap: clamp(18px, 2vw, 30px);
}

.security-hub {
  padding: 18px;
  background: rgba(5, 8, 18, 0.82);
  border: 1px solid rgba(255, 255, 255, 0.04);
  border-radius: 22px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.security-hero {
  display: flex;
  flex-wrap: wrap;
  gap: 20px;
  align-items: center;
  justify-content: space-between;
}

.security-hero-main {
  flex: 1 1 240px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.security-hero-main h2 {
  font-size: clamp(1.4rem, 2vw, 2rem);
  margin: 0;
}

.security-hero-stats {
  flex: 1 1 220px;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: 12px;
}

.security-hero-stats article {
  border-radius: 16px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  padding: 12px 14px;
  background: rgba(10, 13, 26, 0.5);
}

.security-hub-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 16px;
}

.security-hub-btn {
  border-radius: 18px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(255, 255, 255, 0.04);
  padding: clamp(20px, 2vw, 28px);
  min-height: 140px;
  display: flex;
  gap: 20px;
  align-items: center;
  text-align: left;
  transition: border var(--transition-fast), background var(--transition-fast), transform var(--transition-fast);
  cursor: pointer;
}

.security-hub-btn .icon {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.08);
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.security-hub-btn-copy {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.security-hub-btn-copy strong {
  font-size: 1.05rem;
}

.security-hub-btn-copy small {
  font-size: 0.82rem;
}

.security-hub-btn:hover {
  border-color: rgba(108, 140, 255, 0.5);
  background: linear-gradient(135deg, rgba(108, 140, 255, 0.18), rgba(34, 193, 195, 0.25));
  transform: translateY(-2px);
}

.security-view-toolbar {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: flex-start;
  gap: 16px 20px;
  padding: clamp(16px, 1.6vw, 22px);
  border-radius: 18px;
  background: rgba(5, 8, 18, 0.82);
  border: 1px solid rgba(255, 255, 255, 0.04);
}

.security-view-toolbar-left {
  display: flex;
  align-items: center;
  gap: 14px;
  min-width: 0;
}

.security-view-toolbar-badge {
  display: flex;
  justify-content: flex-end;
  align-items: flex-start;
}

.security-view-toolbar-badge .alarm-chip {
  width: auto;
  max-width: 200px;
}

.security-panel-head {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
}

.security-view-toolbar .back-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  border-radius: 999px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  background: transparent;
  color: var(--text);
  padding: 6px 16px;
  cursor: pointer;
  transition: border var(--transition-fast), transform var(--transition-fast);
}

.security-view-toolbar .back-btn .icon {
  width: 20px;
  height: 20px;
}

.security-view-toolbar .back-btn:hover {
  border-color: rgba(108, 140, 255, 0.6);
  transform: translateX(-2px);
}

.security-view-title {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

@media (max-width: 900px) {
  .security-view-toolbar {
    grid-template-columns: minmax(0, 1fr);
  }

  .security-view-toolbar-badge {
    width: 100%;
    margin-top: 6px;
    justify-content: flex-start;
  }

  .security-view-toolbar-badge .alarm-chip {
    max-width: none;
  }
}

.security-panel-meta {
  display: flex;
  align-items: center;
  gap: 10px;
}

.security-panel-meta .alarm-chip {
  max-width: 220px;
}

.alarm-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-radius: 18px;
  padding: 14px 18px;
  border: 1px solid rgba(255, 255, 255, 0.05);
  background: rgba(255, 255, 255, 0.02);
}

.alarm-zone-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 14px;
}

.alarm-zone-card {
  border-radius: 20px;
  padding: 18px;
  border: 1px solid rgba(255, 255, 255, 0.05);
  background: rgba(255, 255, 255, 0.02);
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.zone-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.security-rooms-grid {
  gap: 18px;
}

.security-room-card {
  border-radius: 20px;
  padding: 18px;
  background: rgba(7, 10, 20, 0.8);
  border: 1px solid rgba(255, 255, 255, 0.04);
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.security-zone-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.zone-row {
  border-radius: 14px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  padding: 14px 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  background: rgba(12, 16, 30, 0.7);
}

.zone-row.alert {
  border-color: rgba(255, 99, 132, 0.6);
  background: linear-gradient(135deg, rgba(255, 99, 132, 0.25), rgba(78, 17, 35, 0.65));
  box-shadow: 0 12px 30px rgba(255, 99, 132, 0.35);
}

.zone-row.alert .zone-row-meta strong {
  color: #fff1f4;
}

.zone-row.alert .zone-row-meta small {
  color: rgba(255, 240, 244, 0.8);
}

.zone-row.pending {
  border-color: rgba(255, 193, 7, 0.4);
  background: linear-gradient(135deg, rgba(255, 193, 7, 0.18), rgba(51, 38, 4, 0.5));
}

.zone-row-meta {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.zone-state-chip {
  border-radius: 999px;
  padding: 8px 18px;
  font-size: 0.95rem;
  font-weight: 600;
  border: 1px solid rgba(255, 255, 255, 0.18);
}

.zone-state-chip.alert {
  background: rgba(255, 99, 132, 0.2);
  border-color: rgba(255, 99, 132, 0.5);
  color: #ffbac8;
}

.zone-state-chip.idle {
  background: rgba(34, 193, 195, 0.15);
  border-color: rgba(34, 193, 195, 0.35);
  color: #b8ffe7;
}

.zone-state-chip.pending {
  background: rgba(255, 193, 7, 0.15);
  border-color: rgba(255, 193, 7, 0.4);
  color: #ffe9b0;
}

.alarm-state {
  border-radius: 999px;
  padding: 6px 16px;
  font-size: 0.9rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: #f4f7ff;
}

.alarm-row.alert,
.alarm-zone-card.alert {
  border-color: rgba(255, 138, 128, 0.5);
  background: rgba(255, 61, 86, 0.08);
  box-shadow: 0 10px 24px rgba(255, 61, 86, 0.18);
}

.alarm-row.armed,
.alarm-zone-card.armed {
  border-color: rgba(255, 193, 7, 0.3);
  background: rgba(255, 193, 7, 0.08);
}

.alarm-row.pending,
.alarm-zone-card.pending {
  border-color: rgba(255, 255, 255, 0.2);
  background: rgba(255, 255, 255, 0.04);
}

.alarm-state.alert {
  background: rgba(255, 61, 86, 0.2);
  border-color: rgba(255, 61, 86, 0.4);
  color: #ffb4b4;
}

.alarm-state.armed {
  background: rgba(255, 193, 7, 0.2);
  border-color: rgba(255, 193, 7, 0.4);
  color: #ffeaa7;
}

.alarm-state.pending {
  background: rgba(255, 255, 255, 0.12);
  border-color: rgba(255, 255, 255, 0.24);
}

.alarm-state.idle {
  background: rgba(108, 140, 255, 0.2);
  border-color: rgba(108, 140, 255, 0.35);
  color: #d7deff;
}

.rooms-grid {
  display: flex;
  flex-direction: column;
  gap: 22px;
  padding-bottom: 40px;
}

.rooms-grid.camera-rooms-grid {
  display: flex;
  flex-direction: column;
}

.rooms-grid.camera-rooms-grid .room-card {
  min-height: 0;
}

.rooms-grid.camera-rooms-grid .camera-mosaic {
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 12px;
}

.rooms-grid.camera-rooms-grid .camera-card {
  min-height: 0;
}

.rooms-grid.camera-rooms-grid .camera-card .camera-media {
  aspect-ratio: 4 / 3;
}

.room-card {
  position: relative;
  overflow: hidden;
  min-height: 320px;
  width: 100%;
}

.room-card.has-bg::after {
  content: '';
  position: absolute;
  inset: 1px;
  border-radius: inherit;
  background: rgba(5, 7, 15, 0.45);
  pointer-events: none;
}

.room-card.focused {
  border-color: rgba(108, 140, 255, 0.6);
  box-shadow: 0 20px 50px rgba(0, 0, 0, 0.45);
}

.room-card > * {
  position: relative;
  z-index: 2;
}

.room-head {
  display: flex;
  justify-content: space-between;
  gap: 18px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.room-title-group {
  display: flex;
  align-items: center;
  gap: 16px;
  flex: 1;
  min-width: 0;
}

.room-temp-banner {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 14px;
  border-radius: 20px;
  background: linear-gradient(135deg, rgba(108, 140, 255, 0.12), rgba(92, 124, 250, 0.06));
  border: 1px solid rgba(108, 140, 255, 0.25);
  backdrop-filter: blur(10px);
  margin-left: auto;
}

.room-temp-banner .temp-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 18px;
  height: 18px;
  color: var(--primary);
  flex-shrink: 0;
}

.room-temp-banner .temp-values {
  display: flex;
  align-items: center;
  gap: 2px;
}

.room-temp-banner .temp-reading {
  font-size: 0.95rem;
  font-weight: 600;
  color: var(--text);
  white-space: nowrap;
}

.room-temp-banner .temp-separator {
  color: rgba(255, 255, 255, 0.3);
  margin: 0 4px;
}

.room-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: flex-end;
  align-items: center;
  width: 100%;
}

.primary-actions {
  display: inline-flex;
  gap: 8px;
  align-items: center;
}

.scene-actions {
  display: inline-flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
  justify-content: flex-start;
}

.pill {
  border-radius: 999px;
  padding: 8px 14px;
  border: 1px solid rgba(255, 255, 255, 0.18);
  background: rgba(255, 255, 255, 0.05);
  color: var(--text);
  cursor: pointer;
  font-size: 13px;
  transition: background var(--transition-fast), border var(--transition-fast), transform var(--transition-fast), box-shadow var(--transition-base);
}

.pill.on {
  background: linear-gradient(135deg, rgba(108, 140, 255, 0.4), rgba(34, 193, 195, 0.4));
  border-color: transparent;
}

.pill.ghost {
  background: transparent;
}

.pill.danger {
  background: linear-gradient(135deg, rgba(255, 99, 132, 0.85), rgba(255, 138, 101, 0.8));
  border-color: transparent;
  color: #fff;
}

.pill.scene {
  background: rgba(255, 255, 255, 0.08);
  border-color: rgba(255, 255, 255, 0.12);
  font-size: 12px;
  padding-inline: 12px;
}

.pill.tiny {
  padding: 6px 12px;
  font-size: 12px;
}

.pill:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.pill.scene:disabled {
  opacity: 0.5;
  cursor: wait;
}

.pill:not(:disabled):hover {
  transform: translateY(-1px);
  box-shadow: 0 10px 18px rgba(0, 0, 0, 0.3);
}

.lights-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 10px;
}

.light-card {
  border-radius: 18px;
  padding: 14px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(0, 0, 0, 0.35);
  display: flex;
  flex-direction: column;
  gap: 12px;
  cursor: pointer;
  transition: border var(--transition-fast), transform var(--transition-base), box-shadow var(--transition-base), background var(--transition-fast);
  color: rgba(255, 255, 255, 0.95);
  width: auto;
  min-width: 0;
  animation: float-in 420ms cubic-bezier(0.22, 1, 0.36, 1);
}

.light-card.active {
  border-color: rgba(138, 180, 255, 0.6);
  box-shadow: 0 18px 32px rgba(0, 0, 0, 0.4);
  transform: translateY(-2px);
}

.light-card:hover {
  transform: translateY(-4px) scale(1.01);
  box-shadow: 0 22px 40px rgba(0, 0, 0, 0.4);
  border-color: rgba(138, 180, 255, 0.35);
}

.light-card:nth-child(2n) {
  animation-delay: 60ms;
}

.light-card:nth-child(3n) {
  animation-delay: 120ms;
}

.light-head {
  display: flex;
  justify-content: space-between;
  gap: 14px;
}

.device-chip {
  display: flex;
  gap: 10px;
}

.room-cameras {
  margin-top: 20px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.camera-inline-actions {
  display: flex;
  gap: 8px;
  align-items: center;
}

.cameras-board {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.camera-board-head {
  display: flex;
  justify-content: space-between;
  gap: 18px;
  flex-wrap: wrap;
}

.camera-board-head.minimal {
  align-items: flex-start;
  gap: 16px;
}

.camera-board-title {
  flex: 1;
  min-width: 200px;
}

.camera-toolbar {
  display: flex;
  gap: 10px;
  align-items: center;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.camera-metrics {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  align-items: center;
}

.camera-metric {
  min-width: 96px;
  border-radius: 18px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  padding: 10px 14px;
  background: rgba(0, 0, 0, 0.25);
  text-align: left;
}

.camera-metric strong {
  font-size: 22px;
  display: block;
}

.camera-hero {
  min-width: 220px;
}

.camera-actions {
  display: flex;
  gap: 12px;
  align-items: center;
  flex-wrap: wrap;
}

.layout-toggle {
  display: inline-flex;
  gap: 6px;
  border-radius: 999px;
  padding: 4px;
  background: rgba(255, 255, 255, 0.08);
}

.layout-toggle.compact {
  border-radius: 14px;
  padding: 4px;
}

.camera-summary-pills {
  display: flex;
  gap: 10px;
  align-items: center;
}

.camera-pill {
  min-width: 90px;
  border-radius: 14px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  padding: 10px 14px;
  text-align: center;
  background: rgba(0, 0, 0, 0.25);
}

.camera-pill strong {
  font-size: 20px;
}

.camera-groups {
  display: flex;
  flex-direction: column;
  gap: 22px;
}

.camera-group {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.camera-mosaic {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 14px;
}

.camera-mosaic.list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.cameras-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 12px;
}

.cameras-grid.list {
  grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
}

.camera-card {
  border-radius: 18px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(0, 0, 0, 0.32);
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.camera-card--mosaic {
  padding: 0;
  gap: 14px;
}

.camera-card--list {
  padding: 14px 18px;
  background: linear-gradient(135deg, rgba(7, 9, 20, 0.85), rgba(3, 4, 12, 0.92));
  border: 1px solid rgba(255, 255, 255, 0.1);
  box-shadow: 0 12px 28px rgba(5, 7, 20, 0.38);
  display: flex;
  align-items: center;
  gap: 18px;
}

.camera-card--list .camera-media {
  flex: 0 0 190px;
  border-radius: 16px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  min-height: 120px;
  aspect-ratio: 4 / 3;
  overflow: hidden;
  background: rgba(0, 0, 0, 0.45);
}

.camera-card--list .camera-media img {
  height: 100%;
}

.camera-card--list .camera-meta {
  padding: 0;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  gap: 12px;
}

.camera-card--list .camera-meta > div:first-child {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.camera-card--list .camera-meta strong {
  font-size: 1.05rem;
}

.camera-card--list .camera-meta-actions {
  justify-content: flex-start;
  gap: 10px;
  flex-wrap: wrap;
}

.camera-card--list .ghost-icon {
  width: 40px;
  height: 40px;
  border-radius: 16px;
}

.camera-card--list .camera-fallback-chip {
  right: 12px;
  bottom: 12px;
}

@media (max-width: 1024px) {
  .camera-card--list {
    flex-direction: column;
    align-items: stretch;
  }

  .camera-card--list .camera-media {
    width: 100%;
    min-height: 180px;
  }

  .doorbell-overlay {
    align-items: flex-end;
  }

  .doorbell-panel {
    width: 100%;
  }
}

@media (max-width: 640px) {
  .camera-card--list {
    padding: 14px;
    gap: 14px;
    box-shadow: 0 8px 18px rgba(5, 7, 20, 0.28);
  }

  .camera-card--list .camera-meta {
    padding: 0;
    gap: 12px;
  }
}

.camera-card--global {
  border-color: rgba(138, 180, 255, 0.28);
}

.camera-head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
}

.camera-head-meta {
  display: flex;
  align-items: center;
  gap: 8px;
}

.camera-head-actions {
  display: inline-flex;
  gap: 6px;
}

.camera-tag {
  border-radius: 999px;
  border: 1px solid rgba(255, 255, 255, 0.14);
  padding: 2px 10px;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.camera-frame {
  position: relative;
  border-radius: 16px;
  overflow: hidden;
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(0, 0, 0, 0.4);
  min-height: 180px;
  aspect-ratio: 16 / 9;
}

.camera-frame.has-error {
  border-color: rgba(255, 120, 120, 0.4);
}

.camera-frame.has-fallback {
  border-color: rgba(138, 180, 255, 0.4);
}

.camera-frame img {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: cover;
  filter: saturate(1.05);
  transition: transform var(--transition-base), filter var(--transition-base);
}

.camera-card--mosaic .camera-media {
  position: relative;
  border-radius: 18px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(5, 7, 20, 0.5);
  overflow: hidden;
  aspect-ratio: 16 / 9;
}

.camera-card--mosaic .camera-media img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.camera-state-chip {
  position: absolute;
  top: 12px;
  left: 12px;
  z-index: 2;
  border-radius: 999px;
  padding: 4px 10px;
  font-size: 11px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  border: 1px solid rgba(255, 255, 255, 0.2);
  background: rgba(0, 0, 0, 0.45);
}

.camera-state-chip.live {
  border-color: rgba(102, 255, 166, 0.4);
  color: #8dffce;
}

.camera-state-chip.pending {
  border-color: rgba(255, 211, 99, 0.5);
  color: #ffe29a;
}

.camera-state-chip.alert {
  border-color: rgba(255, 122, 122, 0.5);
  color: #ff9f9f;
}

.camera-play-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  pointer-events: none;
}
.camera-play-overlay .play-btn,
.camera-play-overlay .snapshot-refresh {
  pointer-events: auto;
}
.camera-play-overlay .play-btn {
  background: rgba(0,0,0,0.55);
  border: 1px solid rgba(255,255,255,0.06);
  color: var(--text);
  padding: 10px 14px;
  border-radius: 999px;
  display: inline-flex;
  align-items: center;
  gap: 8px;
}
.camera-play-overlay .snapshot-refresh.small {
  position: absolute;
  top: 8px;
  right: 8px;
  background: rgba(0,0,0,0.45);
  border-radius: 8px;
  width: 34px;
  height: 34px;
  padding: 6px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.viewer-play-action {
  margin-top: 12px;
  display: flex;
  gap: 8px;
  justify-content: center;
}

.camera-stream-chip {
  position: absolute;
  top: 12px;
  right: 12px;
  z-index: 2;
  border-radius: 10px;
  padding: 3px 8px;
  font-size: 10px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  font-weight: 600;
  background: rgba(15, 18, 35, 0.72);
  border: 1px solid rgba(255, 255, 255, 0.18);
  color: rgba(255, 255, 255, 0.8);
}

.camera-stream-chip--hls {
  border-color: rgba(87, 244, 177, 0.6);
  color: #9bffd1;
}

.camera-stream-chip--mjpeg {
  border-color: rgba(121, 178, 255, 0.6);
  color: #d6e8ff;
}

.camera-stream-chip--viewer {
  top: 16px;
  right: 16px;
}

.camera-media-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.camera-media-overlay {
  position: absolute;
  inset: 0;
  background: rgba(5, 7, 18, 0.82);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 18px;
  text-align: center;
}

.camera-media-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: center;
}

.camera-fallback-chip {
  position: absolute;
  right: 12px;
  bottom: 12px;
  padding: 6px 12px;
  border-radius: 14px;
  background: rgba(5, 7, 16, 0.72);
  border: 1px solid rgba(255, 255, 255, 0.12);
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 11px;
}

.camera-preview-name {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(8,10,16,0.45);
}
.camera-preview-name-inner {
  padding: 12px 18px;
  border-radius: 12px;
  background: rgba(0,0,0,0.35);
  border: 1px solid rgba(255,255,255,0.06);
}

.camera-viewer-name {
  width: 100%;
  height: 360px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(8,10,16,0.6);
}
.camera-viewer-name-inner {
  padding: 18px 24px;
  border-radius: 14px;
  background: rgba(0,0,0,0.45);
  border: 1px solid rgba(255,255,255,0.06);
}

/* hide the bottom meta strip when previews are disabled to avoid duplicate labels */
.camera-card--no-preview .camera-meta {
  display: none;
}

.camera-meta {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 0 14px 14px;
}

.camera-meta > div > strong {
  display: block;
  font-size: 14px;
}

.camera-meta-actions {
  display: inline-flex;
  gap: 8px;
  align-items: center;
}

.ghost-icon {
  width: 38px;
  height: 38px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.14);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: transform var(--transition-fast), border var(--transition-fast), background var(--transition-fast);
}

.ghost-icon:hover {
  transform: translateY(-1px);
  border-color: rgba(138, 180, 255, 0.5);
  background: rgba(138, 180, 255, 0.15);
}

.ghost-btn.compact {
  gap: 6px;
  padding-inline: 14px;
  border-radius: 14px;
  height: 40px;
}

.camera-card--mosaic.is-live {
  border-color: rgba(102, 255, 166, 0.28);
}

.camera-card--mosaic.has-fallback {
  border-color: rgba(255, 211, 99, 0.25);
}

.camera-card--mosaic.has-error {
  border-color: rgba(255, 122, 122, 0.25);
}

.camera-card--list.is-live {
  border-color: rgba(102, 255, 166, 0.4);
  box-shadow: 0 18px 44px rgba(4, 10, 20, 0.45);
}

.camera-card--list.has-fallback {
  border-color: rgba(255, 211, 99, 0.38);
}

.camera-card--list.has-error {
  border-color: rgba(255, 122, 122, 0.4);
  background: linear-gradient(135deg, rgba(35, 7, 16, 0.85), rgba(18, 6, 10, 0.9));
}

.camera-frame img:hover {
  transform: scale(1.01);
  filter: saturate(1.25);
}

.camera-error {
  display: flex;
  flex-direction: column;
  gap: 8px;
  align-items: flex-start;
  justify-content: center;
  padding: 18px;
  min-height: 180px;
  text-align: left;
}

.camera-error-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.camera-fallback {
  display: flex;
  flex-direction: column;
  gap: 10px;
  align-items: stretch;
}

.camera-fallback img {
  width: 100%;
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  aspect-ratio: 16 / 9;
  height: auto;
  object-fit: cover;
}

.camera-fallback-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.icon-pill {
  width: 36px;
  height: 36px;
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.18);
  background: rgba(255, 255, 255, 0.06);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: background var(--transition-fast), border var(--transition-fast), transform var(--transition-fast);
}

.icon-pill.active,
.icon-pill:hover {
  background: rgba(138, 180, 255, 0.25);
  border-color: rgba(138, 180, 255, 0.6);
  transform: translateY(-1px);
}

.icon-pill .icon {
  width: 18px;
  height: 18px;
}

.empty-state.compact {
  text-align: center;
  gap: 8px;
}

.device-icon-btn {
  border-radius: 16px;
  width: 50px;
  height: 50px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  background: rgba(255, 255, 255, 0.06);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0;
  cursor: pointer;
  transition: transform var(--transition-fast), border var(--transition-fast), background var(--transition-fast), box-shadow var(--transition-fast);
  box-shadow: 0 8px 20px rgba(5, 7, 20, 0.45);
}

.device-icon-btn.sm {
  width: 44px;
  height: 44px;
  border-radius: 14px;
}

.device-icon-btn.sm .device-icon {
  width: 32px;
  height: 32px;
}

.device-icon-btn:focus-visible {
  outline: 2px solid var(--primary);
  outline-offset: 2px;
}

.device-icon-btn:active {
  transform: scale(0.95);
}

.device-icon-btn:hover {
  transform: translateY(-2px) scale(1.03);
  box-shadow: 0 16px 26px rgba(5, 7, 20, 0.55);
}

.device-icon {
  width: 40px;
  height: 40px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.08);
  display: flex;
  align-items: center;
  justify-content: center;
}

.light-text-block {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  min-height: 54px;
  flex: 1;
}

.light-text-block .light-label,
.active-light-text .light-label {
  color: rgba(255, 255, 255, 0.98);
  font-weight: 600;
}

.light-text-block .muted,
.active-light-text .muted,
.active-light-text small {
  color: rgba(255, 255, 255, 0.82);
}

.device-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-top: 6px;
}

.device-tag {
  border-radius: 999px;
  padding: 2px 8px;
  font-size: 10px;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  border: 1px solid rgba(255, 255, 255, 0.2);
  background: rgba(255, 255, 255, 0.05);
  color: rgba(255, 255, 255, 0.8);
}

.light-label {
  margin: 0;
  font-weight: 600;
  min-height: 22px;
}

.switch {
  position: relative;
  width: 46px;
  height: 24px;
}

.switch input {
  opacity: 0;
  width: 0;
  height: 0;
}

.slider {
  position: absolute;
  cursor: pointer;
  inset: 0;
  background: rgba(255, 255, 255, 0.25);
  border-radius: 999px;
  transition: background 0.2s;
}

.slider::before {
  content: '';
  position: absolute;
  height: 18px;
  width: 18px;
  left: 3px;
  top: 3px;
  border-radius: 50%;
  background: #050714;
  transition: transform 0.2s, background 0.2s;
}

.switch input:checked + .slider {
  background: linear-gradient(120deg, var(--primary), var(--accent));
}

.switch input:checked + .slider::before {
  transform: translateX(22px);
  background: #fff;
}

.light-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: 36px;
  gap: 8px;
  flex-wrap: wrap;
}

.state-chip {
  border-radius: 999px;
  padding: 4px 12px;
  border: 1px solid rgba(255, 255, 255, 0.18);
  min-width: 96px;
  text-align: center;
}

.state-chip.on {
  border-color: transparent;
  background: rgba(255, 255, 255, 0.18);
  color: #050714;
}

.empty-state {
  text-align: center;
  padding: 48px 24px;
}

.empty-icon {
  width: 72px;
  height: 72px;
  border-radius: 22px;
  margin: 0 auto 16px;
  background: rgba(255, 255, 255, 0.1);
  display: flex;
  align-items: center;
  justify-content: center;
}

.placeholder {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.placeholder-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 12px;
}

.placeholder-card {
  border-radius: 18px;
  padding: 18px;
  border: 1px dashed rgba(255, 255, 255, 0.2);
}

.system-pills {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.system-pill {
  border-radius: 16px;
  padding: 12px 16px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.08);
  transition: transform var(--transition-fast), box-shadow var(--transition-base), border-color var(--transition-fast);
}

.system-pill:hover {
  transform: translateY(-2px);
  box-shadow: 0 14px 30px rgba(0, 0, 0, 0.35);
  border-color: rgba(255, 255, 255, 0.2);
}

.system-pill.positive {
  border-color: rgba(74, 222, 128, 0.4);
}

.system-pill.warning {
  border-color: rgba(248, 181, 0, 0.4);
}

.telemetry {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.telemetry-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  transition: transform var(--transition-fast), color var(--transition-fast);
}

.telemetry-item:hover {
  transform: translateX(4px);
}

.status-dot {
  width: 12px;
  height: 12px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.25);
}

.status-dot.on {
  background: #66ffa6;
  box-shadow: 0 0 15px rgba(102, 255, 166, 0.5);
  animation: pulse-glow 2.8s ease-in-out infinite;
}

.tag {
  border-radius: 999px;
  border: 1px solid rgba(255, 255, 255, 0.18);
  padding: 6px 14px;
  background: transparent;
  color: var(--text);
  transition: border var(--transition-fast), background var(--transition-fast), transform var(--transition-fast);
}

.tag.compact {
  padding: 4px 10px;
  font-size: 12px;
}

.tag:hover {
  background: rgba(255, 255, 255, 0.08);
  transform: translateY(-1px);
}

.support-card {
  border-radius: 18px;
  padding: 18px;
  background: rgba(5, 7, 18, 0.6);
  border: 1px solid rgba(255, 255, 255, 0.08);
  transition: transform var(--transition-base), box-shadow var(--transition-base);
  animation: float-in 520ms cubic-bezier(0.22, 1, 0.36, 1);
}

.support-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 22px 38px rgba(0, 0, 0, 0.4);
}

.lights-overlay,
.device-overlay,
.weather-overlay {
  position: fixed;
  inset: 0;
  background: rgba(3, 5, 15, 0.72);
  display: flex;
  align-items: flex-end;
  justify-content: flex-end;
  padding: clamp(16px, 3vw, 32px);
  padding-bottom: calc(clamp(16px, 3vw, 32px) + 110px + env(safe-area-inset-bottom, 0px));
  z-index: 20;
  backdrop-filter: blur(18px);
  animation: overlay-fade 220ms ease-out;
}

.lights-panel,
.device-panel,
.weather-panel,
.doorbell-picker-panel {
  width: min(480px, 100%);
  max-height: min(80vh, 760px);
  overflow-y: auto;
  animation: overlay-rise 360ms cubic-bezier(0.22, 1, 0.36, 1);
  transform-origin: bottom right;
}

.doorbell-picker-overlay {
  position: fixed;
  inset: 0;
  background: rgba(3, 5, 15, 0.76);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: clamp(16px, 4vw, 60px);
  z-index: 23;
  backdrop-filter: blur(22px);
  animation: overlay-fade 220ms ease-out;
}

.doorbell-picker-panel {
  width: min(520px, 100%);
  max-height: 80vh;
  display: flex;
  flex-direction: column;
  gap: 16px;
  animation: overlay-rise 360ms cubic-bezier(0.22, 1, 0.36, 1);
}

.doorbell-picker-grid {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.doorbell-picker-btn {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 16px;
  border-radius: 16px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(255, 255, 255, 0.04);
  text-align: left;
  transition: border-color 160ms ease, background 160ms ease;
}

.doorbell-picker-btn:hover,
.doorbell-picker-btn:focus-visible {
  border-color: rgba(255, 255, 255, 0.35);
  background: rgba(255, 255, 255, 0.08);
}

.doorbell-picker-btn-head {
  display: flex;
  align-items: center;
  gap: 12px;
}

.doorbell-picker-btn-head .icon {
  width: 40px;
  height: 40px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.08);
  display: grid;
  place-items: center;
}

.snapshot-overlay {
  position: fixed;
  inset: 0;
  background: rgba(3, 5, 15, 0.82);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: clamp(16px, 4vw, 60px);
  z-index: 25;
  backdrop-filter: blur(22px);
  animation: overlay-fade 220ms ease-out;
}

.snapshot-panel {
  width: min(900px, 100%);
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  gap: 16px;
  animation: overlay-rise 360ms cubic-bezier(0.22, 1, 0.36, 1);
}

.camera-viewer-overlay {
  position: fixed;
  inset: 0;
  background: rgba(2, 4, 12, 0.88);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: clamp(16px, 4vw, 60px);
  z-index: 24;
  backdrop-filter: blur(26px);
  animation: overlay-fade 220ms ease-out;
}

.camera-viewer-panel {
  width: min(960px, 100%);
  max-height: 92vh;
  display: flex;
  flex-direction: column;
  gap: 16px;
  animation: overlay-rise 360ms cubic-bezier(0.22, 1, 0.36, 1);
  overflow-y: auto;
}

.doorbell-overlay {
  position: fixed;
  inset: 0;
  background: rgba(2, 4, 12, 0.88);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: clamp(16px, 4vw, 60px);
  z-index: 26;
  backdrop-filter: blur(28px);
  animation: overlay-fade 220ms ease-out;
}

.doorbell-panel {
  width: min(960px, 100%);
  max-height: 92vh;
  display: flex;
  flex-direction: column;
  gap: 16px;
  animation: overlay-rise 360ms cubic-bezier(0.22, 1, 0.36, 1);
  overflow-y: auto;
}

.doorbell-body {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.doorbell-head {
  align-items: center;
}

.doorbell-head-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.doorbell-media {
  position: relative;
  border-radius: 18px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(0, 0, 0, 0.45);
  padding: 12px;
  width: 100%;
  max-width: 100%;
}

.doorbell-video-frame {
  position: relative;
  border-radius: 16px;
  overflow: hidden;
  background: #000;
  border: 1px solid rgba(255, 255, 255, 0.12);
  aspect-ratio: 16 / 9;
  width: 100%;
  max-width: 100%;
  max-height: min(70vh, 540px);
  margin: 0 auto;
}

.doorbell-video-frame img {
  width: 100%;
  height: 100%;
  object-fit: contain;
  display: block;
}

.doorbell-video-controls {
  position: absolute;
  bottom: 12px;
  right: 12px;
  display: flex;
  gap: 8px;
}

.doorbell-video-arrow {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  border: none;
  background: rgba(0, 0, 0, 0.5);
  color: currentColor;
  width: 44px;
  height: 44px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: background var(--transition-fast), transform var(--transition-fast);
}

.doorbell-video-arrow .icon {
  width: 20px;
  height: 20px;
}

.doorbell-video-arrow:hover {
  background: rgba(0, 0, 0, 0.68);
  transform: translateY(-50%) scale(1.05);
}

.doorbell-video-arrow--left {
  left: 18px;
}

.doorbell-video-arrow--right {
  right: 18px;
}

.doorbell-video-placeholder {
  min-height: 260px;
  border-radius: 16px;
  border: 1px dashed rgba(255, 255, 255, 0.18);
  background: rgba(5, 7, 16, 0.55);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  text-align: center;
}

.doorbell-video-placeholder .icon {
  width: 48px;
  height: 48px;
}

.doorbell-video-selector {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.doorbell-video-chip {
  border-radius: 14px;
  border: 1px solid rgba(255, 255, 255, 0.18);
  background: rgba(255, 255, 255, 0.04);
  padding: 6px 14px;
  font-size: 0.85rem;
  transition: border var(--transition-fast), background var(--transition-fast), transform var(--transition-fast);
}

.doorbell-video-chip.active {
  border-color: rgba(138, 180, 255, 0.6);
  background: rgba(138, 180, 255, 0.18);
  transform: translateY(-1px);
}

.doorbell-gates {
  border-radius: 16px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 14px;
  background: rgba(5, 7, 20, 0.45);
}

.doorbell-gate-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.doorbell-gate-btn {
  min-width: 140px;
}


.doorbell-video-frame.is-hls {
  background: #000;
}

.doorbell-video {
  width: 100%;
  height: 100%;
  display: block;
  object-fit: contain;
  background: #000;
  border: none;
  max-height: inherit;
}

.doorbell-video-placeholder.overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.6);
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.doorbell-video-error {
  position: absolute;
  bottom: 12px;
  left: 12px;
  right: 12px;
  background: rgba(0, 0, 0, 0.7);
  border-radius: 12px;
  padding: 8px 12px;
  color: #ffb4b4;
  font-weight: 600;
  font-size: 0.85rem;
}

.camera-viewer-body {
  flex: 1;
  border-radius: 18px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(5, 7, 16, 0.7);
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.camera-viewer-media {
  position: relative;
  width: 100%;
  border-radius: 16px;
  overflow: hidden;
  background: #000;
  min-height: 0;
  aspect-ratio: 16 / 9;
  border: 1px solid rgba(255, 255, 255, 0.12);
}

.camera-viewer-media img {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: contain;
  background: #000;
}

.camera-viewer-video {
  width: 100%;
  height: 100%;
  display: block;
  object-fit: contain;
  background: #000;
  border: none;
}

.camera-viewer-placeholder {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  color: rgba(255, 255, 255, 0.85);
  letter-spacing: 0.05em;
  text-transform: uppercase;
  background: rgba(5, 7, 20, 0.6);
}

.snapshot-actions {
  display: flex;
  gap: 8px;
  align-items: center;
}

.snapshot-body {
  flex: 1;
  min-height: 360px;
  border-radius: 18px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(5, 7, 20, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.snapshot-media {
  position: relative;
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.snapshot-body img {
  width: 100%;
  height: 100%;
  object-fit: contain;
  background: #000;
}

.snapshot-placeholder {
  color: rgba(255, 255, 255, 0.8);
  letter-spacing: 0.05em;
  text-transform: uppercase;
}

.snapshot-placeholder.overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(5, 7, 20, 0.65);
}

.snapshot-error {
  color: #ff9f9f;
  font-weight: 600;
}

.snapshot-footer {
  display: flex;
  justify-content: flex-end;
}

.panel-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
}

.active-lights-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
  margin-top: 16px;
}

.active-light-card {
  border-radius: 18px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(0, 0, 0, 0.35);
  padding: 12px 16px;
  transition: border var(--transition-fast), box-shadow var(--transition-base), transform var(--transition-base);
  cursor: pointer;
  animation: float-in 440ms cubic-bezier(0.22, 1, 0.36, 1);
}

.active-light-card:hover {
  transform: translateY(-2px);
  border-color: rgba(138, 180, 255, 0.45);
  box-shadow: 0 18px 32px rgba(0, 0, 0, 0.35);
}

.cover-card {
  cursor: default;
  display: flex;
  flex-direction: column;
}

.cover-card:hover {
  transform: none;
  border-color: rgba(255, 255, 255, 0.15);
}

.cover-info {
  flex: 1;
}

.cover-controls {
  display: flex;
  gap: 8px;
  align-items: center;
}

.cover-slider {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
  width: 100%;
  position: relative;
}

.cover-slider .slider {
  flex: 1;
  height: 4px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.15);
  outline: none;
  -webkit-appearance: none;
  appearance: none;
}

.cover-slider .slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: var(--primary);
  cursor: pointer;
  transition: transform var(--transition-fast);
}

.cover-slider .slider::-webkit-slider-thumb:hover {
  transform: scale(1.2);
}

.cover-slider .slider::-moz-range-thumb {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: var(--primary);
  cursor: pointer;
  border: none;
  transition: transform var(--transition-fast);
}

.cover-slider .slider::-moz-range-thumb:hover {
  transform: scale(1.2);
}

.slider-value {
  min-width: 45px;
  text-align: right;
  font-weight: 600;
  font-size: 0.9rem;
  color: var(--primary);
}

.weather-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.weather-current {
  display: flex;
  flex-direction: column;
  gap: 18px;
  margin-top: 8px;
}

.current-temp {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.temp-display {
  font-size: clamp(42px, 4vw, 72px);
  font-weight: 600;
  line-height: 1;
}

.weather-metrics {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
  gap: 12px;
}

.metric-chip {
  border-radius: 16px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  background: rgba(255, 255, 255, 0.04);
  padding: 10px 14px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.metric-chip strong {
  font-size: 18px;
  letter-spacing: 0.04em;
}

.forecast-section {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.forecast-scroll {
  display: flex;
  gap: 12px;
  overflow-x: auto;
  padding-bottom: 4px;
}

.forecast-scroll::-webkit-scrollbar {
  height: 6px;
}

.forecast-scroll::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.2);
  border-radius: 999px;
}

.forecast-chip {
  min-width: 120px;
  border-radius: 16px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(0, 0, 0, 0.35);
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  backdrop-filter: blur(8px);
}

.forecast-chip .icon {
  width: 28px;
  height: 28px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.05);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.forecast-chip strong {
  font-size: 20px;
}

.updated-at {
  margin-top: 4px;
  text-align: right;
}

.active-light-card:nth-child(2n) {
  animation-delay: 60ms;
}

.active-light-body {
  display: flex;
  align-items: center;
  gap: 14px;
  width: 100%;
  margin-bottom: 0;
}

.active-light-text {
  flex: 1;
  min-width: 0;
}

.active-light-text .light-label {
  margin: 0;
  font-weight: 600;
}

.device-overlay {
  align-items: center;
  justify-content: center;
}

.device-panel {
  width: min(520px, 100%);
}

.panel-section {
  margin-top: 18px;
  padding-top: 18px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
}

.section-head {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
}

.section-head.compact {
  margin-bottom: 0;
  align-items: baseline;
  gap: 8px;
}

.slider-row input[type='range'] {
  width: 100%;
}

.color-palette {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(32px, 1fr));
  gap: 10px;
  margin-bottom: 16px;
}

.swatch {
  border-radius: 12px;
  border: 2px solid transparent;
  padding: 0;
  height: 36px;
  background: var(--swatch-color);
  cursor: pointer;
  transition: transform var(--transition-fast), box-shadow var(--transition-fast), border-color var(--transition-fast);
}

.swatch.active {
  border-color: #ffffff;
}

.swatch:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 14px rgba(0, 0, 0, 0.35);
}

.hue-slider {
  position: relative;
  margin-top: 16px;
  padding-top: 12px;
  overflow: hidden;
}

.hue-slider input[type='range'] {
  width: 100%;
  appearance: none;
  background: transparent;
  position: relative;
  z-index: 2;
  height: 14px;
  border: none;
  outline: none;
}

.hue-track {
  position: absolute;
  inset: 0;
  border-radius: 999px;
  opacity: 0.35;
  pointer-events: none;
  z-index: 1;
}

.hue-slider input[type='range']::-webkit-slider-thumb {
  appearance: none;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: linear-gradient(135deg, #6c8cff, #22c1c3);
  border: 2px solid rgba(5, 7, 20, 0.6);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.25);
}

.hue-slider input[type='range']::-webkit-slider-runnable-track {
  height: 14px;
  background: transparent;
  border: none;
}

.hue-slider input[type='range']::-moz-range-thumb {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: linear-gradient(135deg, #6c8cff, #22c1c3);
  border: 2px solid rgba(5, 7, 20, 0.6);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.25);
}

.hue-slider input[type='range']::-moz-range-track {
  height: 14px;
  background: transparent;
  border: none;
}

.hue-slider input[type='range']::-moz-range-progress {
  background: transparent;
}

.hue-slider input[type='range']::-ms-track {
  height: 14px;
  background: transparent;
  border-color: transparent;
  color: transparent;
}

.hue-slider input[type='range']::-ms-fill-lower,
.hue-slider input[type='range']::-ms-fill-upper {
  background: transparent;
}

.no-controls {
  margin-top: 24px;
  text-align: center;
}

@keyframes overlay-fade {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}

@media (max-width: 1100px) {
  .console,
  .console--compact {
    display: flex;
    flex-direction: column;
    gap: 18px;
  }

  .nav.rail {
    flex-direction: row;
    width: 100%;
    max-width: none;
    justify-content: space-between;
    align-items: center;
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    transform: none;
    top: auto;
    border-radius: 0;
    padding: clamp(10px, 2vh, 14px) clamp(18px, 5vw, 32px);
    padding-bottom: calc(clamp(10px, 2vh, 14px) + env(safe-area-inset-bottom, 0px));
    min-height: 0;
    max-height: 84px;
    box-sizing: border-box;
    z-index: 30;
    gap: 6px;
    border-left: none;
    border-right: none;
    border-bottom: none;
    border-top: 1px solid rgba(255, 255, 255, 0.08);
  }

  .nav-btn {
    flex: 1 1 0;
    width: auto;
    height: 44px;
    border-radius: 16px;
    max-width: 64px;
    min-width: 44px;
  }

  .control4-shell {
    padding-bottom: 120px;
  }

  .right.rail {
    position: static;
  }
}

@media (max-width: 768px) {
  .dashboard-header {
    grid-template-columns: 1fr;
  }

  .room-actions {
    flex-direction: column;
    align-items: stretch;
    gap: 6px;
  }

  .primary-actions {
    justify-content: space-between;
  }

  .scene-actions {
    justify-content: flex-start;
  }

  .room-card {
    min-height: auto;
  }

  .nav.rail {
    border-radius: 0;
    padding: clamp(10px, 2vh, 14px) clamp(16px, 6vw, 22px);
    padding-bottom: calc(clamp(10px, 2vh, 14px) + env(safe-area-inset-bottom, 0px));
    gap: 10px;
    width: 100%;
    left: 0;
    right: 0;
    top: auto;
    bottom: 0;
  }

  .room-actions {
    justify-content: flex-start;
  }

  .room-select-mobile {
    display: flex;
  }

  .room-chip-row {
    display: none;
  }

  .rooms-grid {
    grid-template-columns: 1fr;
  }

  .lights-grid {
    grid-template-columns: 1fr;
    gap: 10px;
  }

  .cameras-grid {
    grid-template-columns: 1fr;
  }

  .camera-frame {
    min-height: 0;
    height: auto;
    aspect-ratio: 16 / 9;
  }

  .camera-frame img {
    height: 100%;
    min-height: 0;
    object-fit: contain;
  }

  .lights-overlay,
  .device-overlay {
    align-items: flex-end;
    justify-content: center;
  }

  .doorbell-panel {
    max-height: 90vh;
  }

  .doorbell-media {
    padding: 10px;
  }

  .doorbell-video-frame {
    aspect-ratio: 16 / 9;
  }

  .doorbell-meta-info {
    flex-direction: column;
  }

  .camera-board-head {
    flex-direction: column;
  }

  .camera-summary-pills {
    width: 100%;
    flex-wrap: wrap;
    justify-content: flex-start;
  }
}

.panel-controls {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  margin-top: 12px;
}

.filter-toggle {
  display: inline-flex;
  flex-wrap: wrap;
  gap: 8px;
}

@media (max-width: 520px) {
  .nav.rail {
    padding: clamp(10px, 2vh, 14px) clamp(12px, 8vw, 18px);
    padding-bottom: calc(clamp(10px, 2vh, 14px) + env(safe-area-inset-bottom, 0px));
    border-radius: 0;
    left: 0;
    right: 0;
    bottom: 0;
  }

  .light-head {
    flex-direction: row;
    align-items: center;
    gap: 12px;
  }

  .light-card {
    padding: 12px;
  }

  .lights-grid {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .light-card {
    flex-direction: row;
    align-items: center;
    width: 100%;
    max-width: 520px;
    margin: 0 auto;
    min-height: 96px;
  }

  .camera-frame {
    height: auto;
    aspect-ratio: 16 / 9;
  }

  .camera-frame img {
    height: 100%;
    object-fit: contain;
  }

  .camera-summary-pills {
    justify-content: space-between;
  }

  .doorbell-video-frame {
    min-height: 220px;
    aspect-ratio: 16 / 9;
  }

  .camera-viewer-media {
    aspect-ratio: 16 / 9;
  }

  .doorbell-video-controls {
    position: static;
    margin-top: 10px;
    justify-content: space-between;
  }

  .doorbell-video-arrow {
    display: none;
  }

  .doorbell-footer {
    justify-content: stretch;
  }

  .doorbell-footer .ghost-btn {
    width: 100%;
  }
}

/* Comfort Devices Styles */
.comfort-rooms {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.room-panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.room-header-inline {
  display: flex;
  align-items: center;
  gap: 12px;
}

.comfort-section {
  margin-top: 20px;
}

.comfort-section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 1rem;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.comfort-section-title .icon {
  width: 20px;
  height: 20px;
  opacity: 0.7;
}

.comfort-devices-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}

.comfort-card {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 16px;
  padding: 16px;
  transition: all 0.3s ease;
}

.comfort-card.active {
  border-color: rgba(255, 165, 0, 0.3);
  background: rgba(255, 165, 0, 0.05);
}

.comfort-card:hover {
  border-color: rgba(255, 255, 255, 0.15);
  transform: translateY(-2px);
}

/* Climate/Thermostat Styles - Nuovo Design Compatto */
.climate-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 16px;
}

.climate-card {
  background: rgba(255, 255, 255, 0.03);
  border-radius: 18px;
  padding: 20px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.25);
}

.climate-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.35);
}

/* Modalità Heat - Arancione/Rosso */
.climate-card.mode-heat {
  border-color: rgba(255, 107, 53, 0.4);
  background: linear-gradient(135deg, rgba(255, 107, 53, 0.08) 0%, rgba(255, 69, 0, 0.04) 100%);
  box-shadow: 0 4px 16px rgba(255, 107, 53, 0.15);
}

.climate-card.mode-heat.is-heating {
  border-color: rgba(255, 107, 53, 0.6);
  background: linear-gradient(135deg, rgba(255, 107, 53, 0.12) 0%, rgba(255, 69, 0, 0.06) 100%);
  box-shadow: 0 4px 20px rgba(255, 107, 53, 0.25), 0 0 40px rgba(255, 107, 53, 0.1);
}

/* Modalità Cool - Blu */
.climate-card.mode-cool {
  border-color: rgba(74, 144, 226, 0.4);
  background: linear-gradient(135deg, rgba(74, 144, 226, 0.08) 0%, rgba(0, 149, 255, 0.04) 100%);
  box-shadow: 0 4px 16px rgba(74, 144, 226, 0.15);
}

.climate-card.mode-cool.is-cooling {
  border-color: rgba(74, 144, 226, 0.6);
  background: linear-gradient(135deg, rgba(74, 144, 226, 0.12) 0%, rgba(0, 149, 255, 0.06) 100%);
  box-shadow: 0 4px 20px rgba(74, 144, 226, 0.25), 0 0 40px rgba(74, 144, 226, 0.1);
}

/* Modalità Auto - Verde/Turchese */
.climate-card.mode-auto {
  border-color: rgba(52, 211, 153, 0.4);
  background: linear-gradient(135deg, rgba(52, 211, 153, 0.08) 0%, rgba(16, 185, 129, 0.04) 100%);
  box-shadow: 0 4px 16px rgba(52, 211, 153, 0.15);
}

.climate-card.mode-auto.is-on {
  border-color: rgba(52, 211, 153, 0.5);
  box-shadow: 0 4px 20px rgba(52, 211, 153, 0.2);
}

/* Modalità Dry - Giallo */
.climate-card.mode-dry {
  border-color: rgba(251, 191, 36, 0.4);
  background: linear-gradient(135deg, rgba(251, 191, 36, 0.08) 0%, rgba(245, 158, 11, 0.04) 100%);
  box-shadow: 0 4px 16px rgba(251, 191, 36, 0.15);
}

/* Modalità Fan Only - Grigio/Azzurro */
.climate-card.mode-fan {
  border-color: rgba(156, 163, 175, 0.4);
  background: linear-gradient(135deg, rgba(156, 163, 175, 0.08) 0%, rgba(107, 114, 128, 0.04) 100%);
  box-shadow: 0 4px 16px rgba(156, 163, 175, 0.15);
}

/* Stato spento - tono neutro */
.climate-card:not(.is-on) {
  border-color: rgba(255, 255, 255, 0.06);
  background: rgba(255, 255, 255, 0.02);
}

.climate-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}

.climate-title-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.climate-name {
  font-size: 17px;
  font-weight: 600;
  margin: 0;
  color: var(--text);
}

.climate-state-badge {
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.8px;
  font-weight: 700;
  padding: 4px 10px;
  border-radius: 8px;
  width: fit-content;
  border: 1px solid;
  transition: all 0.2s ease;
}

.climate-card.is-heating .climate-state-badge {
  color: #ff6b35;
  background: rgba(255, 107, 53, 0.18);
  border-color: rgba(255, 107, 53, 0.3);
}

.climate-card.is-cooling .climate-state-badge {
  color: #4a90e2;
  background: rgba(74, 144, 226, 0.18);
  border-color: rgba(74, 144, 226, 0.3);
}

.climate-card.mode-auto .climate-state-badge {
  color: #34d399;
  background: rgba(52, 211, 153, 0.18);
  border-color: rgba(52, 211, 153, 0.3);
}

.climate-card.mode-dry .climate-state-badge {
  color: #fbbf24;
  background: rgba(251, 191, 36, 0.18);
  border-color: rgba(251, 191, 36, 0.3);
}

.climate-card.mode-fan .climate-state-badge {
  color: #9ca3af;
  background: rgba(156, 163, 175, 0.18);
  border-color: rgba(156, 163, 175, 0.3);
}

.climate-toggle {
  width: 40px;
  height: 40px;
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  background: rgba(255, 255, 255, 0.06);
  color: rgba(255, 255, 255, 0.5);
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
}

.climate-toggle:hover {
  background: rgba(255, 255, 255, 0.12);
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
}

.climate-toggle.active {
  background: linear-gradient(135deg, var(--primary), var(--accent));
  color: white;
  border-color: transparent;
  box-shadow: 0 4px 16px rgba(0, 212, 255, 0.4);
}

.climate-card.mode-heat .climate-toggle.active {
  background: linear-gradient(135deg, #ff6b35, #ff4500);
  box-shadow: 0 4px 16px rgba(255, 107, 53, 0.4);
}

.climate-card.mode-cool .climate-toggle.active {
  background: linear-gradient(135deg, #4a90e2, #0066cc);
  box-shadow: 0 4px 16px rgba(74, 144, 226, 0.4);
}

.climate-card.mode-auto .climate-toggle.active {
  background: linear-gradient(135deg, #34d399, #10b981);
  box-shadow: 0 4px 16px rgba(52, 211, 153, 0.4);
}

.climate-toggle svg {
  width: 20px;
  height: 20px;
}

.climate-body {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.climate-temp-display {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 12px;
}

.current-temp {
  display: flex;
  align-items: baseline;
  gap: 4px;
}

.temp-value {
  font-size: 56px;
  font-weight: 700;
  color: var(--text);
  line-height: 1;
}

.temp-unit {
  font-size: 24px;
  font-weight: 500;
  color: rgba(255, 255, 255, 0.6);
}

.humidity-info {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 15px;
  color: rgba(255, 255, 255, 0.7);
  padding: 8px 12px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 8px;
}

.humidity-info svg {
  width: 16px;
  height: 16px;
  opacity: 0.8;
}

.climate-target-controls {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px;
  background: rgba(255, 255, 255, 0.03);
  border-radius: 12px;
}

.temp-btn {
  width: 44px;
  height: 44px;
  border-radius: 50%;
  border: 1px solid rgba(255, 255, 255, 0.12);
  background: rgba(255, 255, 255, 0.08);
  color: var(--text);
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
}

.temp-btn:hover {
  border-color: var(--primary);
  background: rgba(0, 212, 255, 0.15);
  transform: scale(1.08);
  box-shadow: 0 4px 12px rgba(0, 212, 255, 0.2);
}

.climate-card.mode-heat .temp-btn:hover {
  border-color: #ff6b35;
  background: rgba(255, 107, 53, 0.15);
  box-shadow: 0 4px 12px rgba(255, 107, 53, 0.2);
}

.climate-card.mode-cool .temp-btn:hover {
  border-color: #4a90e2;
  background: rgba(74, 144, 226, 0.15);
  box-shadow: 0 4px 12px rgba(74, 144, 226, 0.2);
}

.climate-card.mode-auto .temp-btn:hover {
  border-color: #34d399;
  background: rgba(52, 211, 153, 0.15);
  box-shadow: 0 4px 12px rgba(52, 211, 153, 0.2);
}

.temp-btn:active {
  transform: scale(0.95);
}

.temp-btn svg {
  width: 20px;
  height: 20px;
}

.target-temp-display {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  flex: 1;
}

.target-label {
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: rgba(255, 255, 255, 0.5);
  font-weight: 600;
}

.target-value {
  font-size: 28px;
  font-weight: 700;
  color: var(--text);
  line-height: 1;
}

.climate-modes {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(90px, 1fr));
  gap: 8px;
}

.mode-btn {
  padding: 10px 8px;
  border-radius: 10px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(255, 255, 255, 0.05);
  color: rgba(255, 255, 255, 0.6);
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
}

.mode-btn:hover {
  background: rgba(255, 255, 255, 0.1);
  border-color: rgba(255, 255, 255, 0.2);
  transform: translateY(-2px);
}

.mode-btn.active {
  background: linear-gradient(135deg, var(--primary), var(--accent));
  border-color: transparent;
  color: white;
  box-shadow: 0 4px 12px rgba(0, 212, 255, 0.3);
}

.climate-card.mode-heat .mode-btn.active {
  background: linear-gradient(135deg, #ff6b35, #ff4500);
  box-shadow: 0 4px 12px rgba(255, 107, 53, 0.3);
}

.climate-card.mode-cool .mode-btn.active {
  background: linear-gradient(135deg, #4a90e2, #0066cc);
  box-shadow: 0 4px 12px rgba(74, 144, 226, 0.3);
}

.climate-card.mode-auto .mode-btn.active {
  background: linear-gradient(135deg, #34d399, #10b981);
  box-shadow: 0 4px 12px rgba(52, 211, 153, 0.3);
}

.climate-card.mode-dry .mode-btn.active {
  background: linear-gradient(135deg, #fbbf24, #f59e0b);
  box-shadow: 0 4px 12px rgba(251, 191, 36, 0.3);
}

.climate-card.mode-fan .mode-btn.active {
  background: linear-gradient(135deg, #9ca3af, #6b7280);
  box-shadow: 0 4px 12px rgba(156, 163, 175, 0.3);
}

.mode-btn .mode-icon {
  width: 20px;
  height: 20px;
}

.mode-btn .mode-text {
  font-size: 11px;
  font-weight: 600;
  text-align: center;
}

.climate-off {
  padding: 30px 20px;
  text-align: center;
  display: flex;
  flex-direction: column;
  gap: 20px;
  align-items: center;
}

.climate-off-temp {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.off-temp-value {
  font-size: 48px;
  font-weight: 700;
  color: rgba(255, 255, 255, 0.9);
  line-height: 1;
}

.off-temp-label {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.5);
  margin: 0;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.climate-turn-on-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 18px 40px;
  background: linear-gradient(135deg, var(--primary) 0%, #ff6b35 100%);
  color: white;
  border: none;
  border-radius: 16px;
  font-size: 17px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  width: 100%;
  max-width: 220px;
  box-shadow: 0 4px 16px rgba(255, 77, 41, 0.25);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.climate-turn-on-btn:hover {
  background: linear-gradient(135deg, #ff6b35 0%, var(--primary) 100%);
  transform: translateY(-3px);
  box-shadow: 0 6px 20px rgba(255, 77, 41, 0.4);
}

.climate-turn-on-btn:active {
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(255, 77, 41, 0.3);
}

.climate-turn-on-btn svg {
  width: 22px;
  height: 22px;
  stroke-width: 2.5;
}

.off-label {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.4);
  margin: 0;
  text-transform: uppercase;
  letter-spacing: 1px;
  font-weight: 500;
}

/* Icona room header - limitare dimensione */
.room-icon {
  width: 24px;
  height: 24px;
  flex-shrink: 0;
}

.room-icon svg {
  width: 100%;
  height: 100%;
  display: block;
}

.room-header-inline {
  display: flex;
  align-items: center;
  gap: 12px;
}

/* Vecchi stili termostati - mantenerli per compatibilità */
.thermostat-card {
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.05) 0%, rgba(255, 255, 255, 0.02) 100%);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 24px;
  padding: 24px;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.thermostat-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.3);
  border-color: rgba(255, 255, 255, 0.2);
}

.thermostat-card.thermostat-on {
  background: linear-gradient(135deg, rgba(0, 212, 255, 0.1) 0%, rgba(0, 212, 255, 0.05) 100%);
  border-color: rgba(0, 212, 255, 0.3);
}

.thermostat-card.thermostat-heating {
  background: linear-gradient(135deg, rgba(255, 107, 53, 0.15) 0%, rgba(255, 107, 53, 0.05) 100%);
  border-color: rgba(255, 107, 53, 0.4);
}

.thermostat-card.thermostat-cooling {
  background: linear-gradient(135deg, rgba(74, 144, 226, 0.15) 0%, rgba(74, 144, 226, 0.05) 100%);
  border-color: rgba(74, 144, 226, 0.4);
}

.thermostat-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.thermostat-name {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
}

.thermostat-power-btn {
  width: 44px;
  height: 44px;
  border-radius: 50%;
  border: 2px solid rgba(255, 255, 255, 0.2);
  background: rgba(255, 255, 255, 0.05);
  color: rgba(255, 255, 255, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.3s ease;
}

.thermostat-power-btn:hover {
  background: rgba(255, 255, 255, 0.1);
  border-color: rgba(255, 255, 255, 0.3);
}

.thermostat-power-btn.active {
  background: linear-gradient(135deg, #00d4ff 0%, #0099cc 100%);
  border-color: #00d4ff;
  color: white;
  box-shadow: 0 4px 12px rgba(0, 212, 255, 0.4);
}

.thermostat-power-btn .icon {
  width: 24px;
  height: 24px;
}

.thermostat-body {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.thermostat-display {
  position: relative;
  width: 200px;
  height: 200px;
  margin: 0 auto;
}

.thermostat-ring {
  width: 100%;
  height: 100%;
}

.thermostat-center {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  text-align: center;
  width: 140px;
}

.thermostat-current-temp {
  font-size: 48px;
  font-weight: 700;
  color: var(--text-primary);
  line-height: 1;
  margin-bottom: 8px;
  background: linear-gradient(135deg, #00d4ff 0%, #0099cc 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.thermostat-card.thermostat-heating .thermostat-current-temp {
  background: linear-gradient(135deg, #ff6b35 0%, #ff8c42 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.thermostat-card.thermostat-cooling .thermostat-current-temp {
  background: linear-gradient(135deg, #4a90e2 0%, #6ab0f3 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.thermostat-target-temp {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.6);
  margin-bottom: 4px;
}

.thermostat-status {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.5);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  font-weight: 600;
}

.thermostat-controls {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 20px;
  padding: 16px;
  background: rgba(255, 255, 255, 0.03);
  border-radius: 16px;
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.thermostat-btn {
  width: 52px;
  height: 52px;
  border-radius: 50%;
  border: 2px solid rgba(255, 255, 255, 0.2);
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.1) 0%, rgba(255, 255, 255, 0.05) 100%);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.3s ease;
  font-size: 20px;
}

.thermostat-btn:hover {
  background: linear-gradient(135deg, rgba(0, 212, 255, 0.3) 0%, rgba(0, 212, 255, 0.2) 100%);
  border-color: rgba(0, 212, 255, 0.5);
  transform: scale(1.05);
}

.thermostat-btn:active {
  transform: scale(0.95);
}

.thermostat-btn .icon {
  width: 24px;
  height: 24px;
}

.thermostat-temp-value {
  font-size: 32px;
  font-weight: 700;
  color: var(--text-primary);
  min-width: 100px;
  text-align: center;
}

.thermostat-modes {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.thermostat-mode-btn {
  flex: 1;
  min-width: 0;
  padding: 12px 8px;
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.15);
  background: rgba(255, 255, 255, 0.05);
  color: rgba(255, 255, 255, 0.7);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  transition: all 0.3s ease;
  font-size: 11px;
}

.thermostat-mode-btn:hover {
  background: rgba(255, 255, 255, 0.1);
  border-color: rgba(255, 255, 255, 0.25);
}

.thermostat-mode-btn.active {
  background: linear-gradient(135deg, #00d4ff 0%, #0099cc 100%);
  border-color: #00d4ff;
  color: white;
  box-shadow: 0 4px 12px rgba(0, 212, 255, 0.3);
}

.thermostat-mode-btn .mode-icon {
  width: 24px;
  height: 24px;
}

.thermostat-mode-btn .mode-label {
  font-weight: 600;
  text-transform: capitalize;
}

.thermostat-info {
  display: flex;
  justify-content: center;
  gap: 16px;
  padding-top: 12px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
}

.thermostat-info .info-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.6);
}

.thermostat-info .info-item .icon {
  width: 16px;
  height: 16px;
}

.thermostat-off-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  color: rgba(255, 255, 255, 0.3);
}

.thermostat-off-state .icon-large {
  width: 64px;
  height: 64px;
  margin-bottom: 12px;
  opacity: 0.3;
}

.thermostat-off-state p {
  font-size: 14px;
  margin: 0;
  text-transform: uppercase;
  letter-spacing: 1px;
}

.comfort-head {
  margin-bottom: 12px;
}

.comfort-text-block {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.comfort-label {
  font-weight: 600;
  font-size: 15px;
  color: var(--text);
  margin: 0;
}

/* ===================================
   COVER/BLINDS MODERN STYLES
   =================================== */

.cover-card-modern {
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.05) 0%, rgba(255, 255, 255, 0.02) 100%);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 18px;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 18px;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.25);
}

.cover-card-modern:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.35);
  border-color: rgba(255, 255, 255, 0.2);
}

.cover-card-modern.is-open {
  border-color: rgba(52, 211, 153, 0.4);
  background: linear-gradient(135deg, rgba(52, 211, 153, 0.08) 0%, rgba(16, 185, 129, 0.04) 100%);
}

.cover-card-modern.is-closed {
  border-color: rgba(107, 114, 128, 0.4);
  background: linear-gradient(135deg, rgba(107, 114, 128, 0.08) 0%, rgba(75, 85, 99, 0.04) 100%);
}

.cover-card-modern.is-moving {
  border-color: rgba(251, 191, 36, 0.5);
  background: linear-gradient(135deg, rgba(251, 191, 36, 0.1) 0%, rgba(245, 158, 11, 0.05) 100%);
  animation: pulse-cover 1.5s ease-in-out infinite;
}

@keyframes pulse-cover {
  0%, 100% { box-shadow: 0 4px 16px rgba(251, 191, 36, 0.2); }
  50% { box-shadow: 0 4px 24px rgba(251, 191, 36, 0.4); }
}

.cover-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
}

.cover-info {
  display: flex;
  flex-direction: column;
  gap: 8px;
  flex: 1;
}

.cover-name {
  font-size: 17px;
  font-weight: 600;
  margin: 0;
  color: var(--text);
}

.cover-state-badge {
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.8px;
  font-weight: 700;
  padding: 4px 10px;
  border-radius: 8px;
  width: fit-content;
  border: 1px solid;
  transition: all 0.2s ease;
}

.cover-state-badge.badge-open {
  color: #34d399;
  background: rgba(52, 211, 153, 0.15);
  border-color: rgba(52, 211, 153, 0.3);
}

.cover-state-badge.badge-closed {
  color: #9ca3af;
  background: rgba(156, 163, 175, 0.15);
  border-color: rgba(156, 163, 175, 0.3);
}

.cover-state-badge.badge-partial {
  color: #60a5fa;
  background: rgba(96, 165, 250, 0.15);
  border-color: rgba(96, 165, 250, 0.3);
}

.cover-state-badge.badge-moving {
  color: #fbbf24;
  background: rgba(251, 191, 36, 0.15);
  border-color: rgba(251, 191, 36, 0.3);
}

.cover-position-display {
  display: flex;
  align-items: baseline;
  gap: 4px;
  padding: 8px 16px;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.position-number {
  font-size: 32px;
  font-weight: 700;
  color: var(--text);
  line-height: 1;
}

.position-unit {
  font-size: 16px;
  font-weight: 500;
  color: rgba(255, 255, 255, 0.6);
}

/* Visualizzazione tapparella */
.cover-visual {
  display: flex;
  justify-content: center;
  padding: 12px 0;
}

.cover-window {
  width: 100%;
  max-width: 200px;
  height: 140px;
  background: linear-gradient(135deg, rgba(100, 116, 139, 0.2) 0%, rgba(71, 85, 105, 0.1) 100%);
  border-radius: 12px;
  border: 2px solid rgba(255, 255, 255, 0.15);
  overflow: hidden;
  position: relative;
  box-shadow: inset 0 2px 8px rgba(0, 0, 0, 0.3);
}

.cover-blind {
  width: 100%;
  background: linear-gradient(180deg, rgba(139, 92, 246, 0.6) 0%, rgba(124, 58, 237, 0.7) 100%);
  transition: height 0.6s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
}

.cover-card-modern.is-moving .cover-blind {
  transition: height 0.3s linear;
}

.blind-slats {
  width: 100%;
  height: 100%;
  background-image: repeating-linear-gradient(
    0deg,
    rgba(255, 255, 255, 0.1) 0px,
    rgba(255, 255, 255, 0.1) 2px,
    transparent 2px,
    transparent 12px
  );
}

/* Slider moderno */
.cover-slider-container {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.cover-slider-modern {
  width: 100%;
  height: 8px;
  border-radius: 4px;
  background: rgba(255, 255, 255, 0.1);
  outline: none;
  appearance: none;
  cursor: pointer;
  transition: all 0.2s ease;
}

.cover-slider-modern:hover {
  background: rgba(255, 255, 255, 0.15);
}

.cover-slider-modern:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.cover-slider-modern::-webkit-slider-thumb {
  appearance: none;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: linear-gradient(135deg, #8b5cf6, #7c3aed);
  cursor: pointer;
  border: 2px solid rgba(255, 255, 255, 0.3);
  box-shadow: 0 2px 8px rgba(139, 92, 246, 0.5);
  transition: all 0.2s ease;
}

.cover-slider-modern::-webkit-slider-thumb:hover {
  transform: scale(1.15);
  box-shadow: 0 4px 12px rgba(139, 92, 246, 0.7);
}

.cover-slider-modern::-moz-range-thumb {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: linear-gradient(135deg, #8b5cf6, #7c3aed);
  cursor: pointer;
  border: 2px solid rgba(255, 255, 255, 0.3);
  box-shadow: 0 2px 8px rgba(139, 92, 246, 0.5);
  transition: all 0.2s ease;
}

.cover-slider-modern::-moz-range-thumb:hover {
  transform: scale(1.15);
  box-shadow: 0 4px 12px rgba(139, 92, 246, 0.7);
}

.slider-markers {
  display: flex;
  justify-content: space-between;
  padding: 0 4px;
}

.slider-markers span {
  font-size: 10px;
  color: rgba(255, 255, 255, 0.4);
  font-weight: 500;
}

/* Controlli moderni */
.cover-controls-modern {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
}

.cover-btn {
  padding: 12px 8px;
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  background: rgba(255, 255, 255, 0.06);
  color: rgba(255, 255, 255, 0.8);
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  font-weight: 600;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
}

.cover-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
}

.cover-btn:active:not(:disabled) {
  transform: translateY(0);
}

.cover-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.cover-btn svg {
  width: 20px;
  height: 20px;
}

.cover-btn-up:hover:not(:disabled) {
  background: linear-gradient(135deg, rgba(52, 211, 153, 0.2), rgba(16, 185, 129, 0.15));
  border-color: rgba(52, 211, 153, 0.4);
  color: #34d399;
}

.cover-btn-stop:hover:not(:disabled) {
  background: linear-gradient(135deg, rgba(251, 191, 36, 0.2), rgba(245, 158, 11, 0.15));
  border-color: rgba(251, 191, 36, 0.4);
  color: #fbbf24;
}

.cover-btn-down:hover:not(:disabled) {
  background: linear-gradient(135deg, rgba(107, 114, 128, 0.2), rgba(75, 85, 99, 0.15));
  border-color: rgba(107, 114, 128, 0.4);
  color: #9ca3af;
}

.btn-label {
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.climate-controls {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-top: 12px;
}

.temp-display {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 12px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 12px;
}

.temp-value {
  font-size: 32px;
  font-weight: 700;
  color: #ff4500;
}

.temp-buttons {
  display: flex;
  gap: 8px;
  justify-content: center;
}

.climate-modes {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  justify-content: center;
}

/* ===================================
   OVERVIEW SECTION STYLES
   =================================== */

.overview-container {
  display: flex;
  flex-direction: column;
  gap: 20px;
  padding-bottom: 20px;
}

.overview-header {
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.06) 0%, rgba(255, 255, 255, 0.02) 100%);
  border: 1px solid rgba(255, 255, 255, 0.1);
  padding: 24px;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.overview-room-info {
  display: flex;
  align-items: center;
  gap: 20px;
}

.overview-room-icon {
  width: 64px;
  height: 64px;
  border-radius: 18px;
  border: 2px solid rgba(255, 255, 255, 0.15);
  background: linear-gradient(135deg, rgba(0, 212, 255, 0.2) 0%, rgba(138, 180, 255, 0.15) 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 8px 24px rgba(0, 212, 255, 0.15);
  flex-shrink: 0;
}

.overview-room-icon .icon {
  width: 32px;
  height: 32px;
  color: var(--primary);
}

.overview-room-name {
  font-size: 28px;
  font-weight: 700;
  margin: 0;
  color: var(--text);
}

.overview-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: 18px;
}

.overview-section {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.08);
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.overview-section:hover {
  border-color: rgba(255, 255, 255, 0.15);
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.35);
}

.overview-section-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding-bottom: 12px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}

.overview-section-header .icon {
  width: 22px;
  height: 22px;
  color: var(--primary);
  flex-shrink: 0;
  display: block;
}

.overview-section-header .icon svg {
  width: 100%;
  height: 100%;
  display: block;
}

.overview-section-header h3 {
  font-size: 17px;
  font-weight: 600;
  margin: 0;
  flex: 1;
  color: var(--text);
}

.overview-count {
  background: rgba(0, 212, 255, 0.15);
  color: var(--primary);
  padding: 4px 12px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
  border: 1px solid rgba(0, 212, 255, 0.3);
}

.overview-controls {
  display: flex;
  gap: 8px;
  margin-top: 12px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}

/* Grid dispositivi luci */
.overview-devices-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 12px;
}

.overview-device-card {
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 14px;
  padding: 14px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  cursor: pointer;
}

.overview-device-card:hover {
  border-color: rgba(255, 255, 255, 0.2);
  background: rgba(255, 255, 255, 0.06);
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.3);
}

.overview-device-card.active {
  border-color: rgba(0, 212, 255, 0.4);
  background: linear-gradient(135deg, rgba(0, 212, 255, 0.08) 0%, rgba(138, 180, 255, 0.04) 100%);
}

.overview-device-info {
  text-align: center;
  width: 100%;
}

.overview-device-name {
  font-size: 13px;
  font-weight: 600;
  margin: 0;
  color: var(--text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.overview-device-info small {
  font-size: 11px;
}

/* Controlli tapparelle in overview */
.overview-device-card.cover-overview {
  padding: 12px;
}

.overview-cover-controls {
  display: flex;
  gap: 6px;
  width: 100%;
}

.cover-control-btn {
  flex: 1;
  padding: 8px;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 10px;
  color: rgba(255, 255, 255, 0.8);
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
}

.cover-control-btn:hover {
  background: rgba(255, 255, 255, 0.12);
  border-color: var(--primary);
  color: var(--primary);
  transform: scale(1.05);
}

.cover-control-btn svg {
  width: 16px;
  height: 16px;
}

.cover-control-btn span {
  width: 16px;
  height: 16px;
  display: block;
}

/* Clima in overview */
.overview-climate-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 12px;
}

.overview-climate-card {
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 14px;
  padding: 14px;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.overview-climate-card.mode-heat {
  border-color: rgba(255, 107, 53, 0.3);
  background: linear-gradient(135deg, rgba(255, 107, 53, 0.06) 0%, rgba(255, 69, 0, 0.02) 100%);
}

.overview-climate-card.mode-cool {
  border-color: rgba(74, 144, 226, 0.3);
  background: linear-gradient(135deg, rgba(74, 144, 226, 0.06) 0%, rgba(0, 149, 255, 0.02) 100%);
}

.overview-climate-card.mode-auto {
  border-color: rgba(52, 211, 153, 0.3);
  background: linear-gradient(135deg, rgba(52, 211, 153, 0.06) 0%, rgba(16, 185, 129, 0.02) 100%);
}

.overview-climate-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 12px;
}

.climate-toggle-sm {
  width: 32px;
  height: 32px;
  border-radius: 10px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  background: rgba(255, 255, 255, 0.06);
  color: rgba(255, 255, 255, 0.5);
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.climate-toggle-sm:hover {
  background: rgba(255, 255, 255, 0.12);
  transform: scale(1.05);
}

.climate-toggle-sm.active {
  background: linear-gradient(135deg, var(--primary), var(--accent));
  color: white;
  border-color: transparent;
}

.overview-climate-card.mode-heat .climate-toggle-sm.active {
  background: linear-gradient(135deg, #ff6b35, #ff4500);
}

.overview-climate-card.mode-cool .climate-toggle-sm.active {
  background: linear-gradient(135deg, #4a90e2, #0066cc);
}

.overview-climate-card.mode-auto .climate-toggle-sm.active {
  background: linear-gradient(135deg, #34d399, #10b981);
}

.climate-toggle-sm svg {
  width: 16px;
  height: 16px;
}

.climate-toggle-sm span {
  width: 16px;
  height: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.overview-climate-body {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.overview-temp-display {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 12px;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 10px;
}

.temp-big {
  font-size: 36px;
  font-weight: 700;
  color: var(--text);
  line-height: 1;
}

.temp-target {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.6);
}

.overview-temp-controls {
  display: flex;
  gap: 8px;
  justify-content: center;
}

.temp-btn-sm {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  border: 1px solid rgba(255, 255, 255, 0.12);
  background: rgba(255, 255, 255, 0.08);
  color: var(--text);
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
}

.temp-btn-sm:hover {
  border-color: var(--primary);
  background: rgba(0, 212, 255, 0.15);
  transform: scale(1.1);
}

.overview-climate-card.mode-heat .temp-btn-sm:hover {
  border-color: #ff6b35;
  background: rgba(255, 107, 53, 0.15);
}

.overview-climate-card.mode-cool .temp-btn-sm:hover {
  border-color: #4a90e2;
  background: rgba(74, 144, 226, 0.15);
}

.temp-btn-sm svg {
  width: 16px;
  height: 16px;
}

.temp-btn-sm span {
  width: 16px;
  height: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* Telecamere in overview */
.overview-cameras-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 12px;
}

.overview-camera-card {
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 14px;
  padding: 10px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  transition: all 0.3s ease;
  cursor: pointer;
}

.overview-camera-card:hover {
  border-color: rgba(255, 255, 255, 0.2);
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.3);
}

.overview-camera-preview {
  aspect-ratio: 16 / 9;
  border-radius: 10px;
  overflow: hidden;
  background: rgba(0, 0, 0, 0.3);
}

.overview-camera-preview img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.camera-preview-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: rgba(255, 255, 255, 0.3);
}

.camera-preview-placeholder svg {
  width: 32px;
  height: 32px;
}

/* Responsive */
@media (max-width: 768px) {
  .overview-grid {
    grid-template-columns: 1fr;
  }
  
  .overview-devices-grid {
    grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
  }
  
  .overview-climate-grid {
    grid-template-columns: 1fr;
  }
  
  .overview-cameras-grid {
    grid-template-columns: repeat(auto-fill, minmax(130px, 1fr));
  }
}

.climate-modes .pill.active {
  background: rgba(255, 69, 0, 0.2);
  color: #ff4500;
  border-color: rgba(255, 69, 0, 0.4);
}

.icon-btn.tiny {
  padding: 8px;
  min-width: 36px;
  min-height: 36px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.12);
  color: var(--text);
  cursor: pointer;
  transition: all 0.2s ease;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.icon-btn.tiny:hover {
  background: rgba(255, 255, 255, 0.12);
  border-color: rgba(108, 140, 255, 0.4);
  transform: scale(1.05);
}

.icon-btn.tiny .icon {
  width: 18px;
  height: 18px;
}

@media (max-width: 768px) {
  .comfort-devices-grid {
    grid-template-columns: 1fr;
  }
}

/* Overview - Tapparelle e Clima */
.covers-section,
.climate-section {
  margin-top: 24px;
  padding-top: 20px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
}

.section-title {
  font-size: 1.1rem;
  font-weight: 600;
  margin-bottom: 16px;
  color: var(--text);
}

/* Covers in overview */
.covers-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 12px;
}

.cover-overview-card {
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  padding: 14px;
  transition: all 0.3s ease;
}

.cover-overview-card.open {
  border-color: rgba(108, 140, 255, 0.3);
  background: linear-gradient(135deg, rgba(108, 140, 255, 0.06) 0%, rgba(92, 124, 250, 0.02) 100%);
}

.cover-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 12px;
}

.cover-info {
  flex: 1;
}

.cover-name {
  font-size: 0.95rem;
  font-weight: 500;
  margin: 0 0 4px 0;
}

.cover-controls-compact {
  display: flex;
  gap: 6px;
}

.cover-control-btn-sm {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  background: rgba(255, 255, 255, 0.06);
  color: var(--text);
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0;
}

.cover-control-btn-sm:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.12);
  border-color: var(--primary);
  transform: scale(1.05);
}

.cover-control-btn-sm:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.cover-control-btn-sm span {
  width: 16px;
  height: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.cover-position-bar {
  position: relative;
  height: 6px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 3px;
  overflow: hidden;
}

.position-fill {
  position: absolute;
  left: 0;
  top: 0;
  height: 100%;
  background: linear-gradient(90deg, var(--primary), rgba(108, 140, 255, 0.7));
  transition: width 0.3s ease;
}

.position-label {
  position: absolute;
  right: 6px;
  top: 50%;
  transform: translateY(-50%);
  font-size: 0.7rem;
  font-weight: 600;
  color: var(--text);
  text-shadow: 0 1px 3px rgba(0, 0, 0, 0.5);
}

/* Climate in overview */
.climate-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 12px;
}

.climate-overview-card {
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  padding: 14px;
  transition: all 0.3s ease;
}

.climate-overview-card.on.mode-heat {
  border-color: rgba(255, 107, 53, 0.3);
  background: linear-gradient(135deg, rgba(255, 107, 53, 0.06) 0%, rgba(255, 69, 0, 0.02) 100%);
}

.climate-overview-card.on.mode-cool {
  border-color: rgba(74, 144, 226, 0.3);
  background: linear-gradient(135deg, rgba(74, 144, 226, 0.06) 0%, rgba(0, 149, 255, 0.02) 100%);
}

.climate-overview-card.on.mode-auto {
  border-color: rgba(52, 211, 153, 0.3);
  background: linear-gradient(135deg, rgba(52, 211, 153, 0.06) 0%, rgba(16, 185, 129, 0.02) 100%);
}

.climate-header-compact {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 12px;
}

.climate-header-compact h5 {
  margin: 0 0 4px 0;
  font-size: 0.95rem;
  font-weight: 500;
}

.climate-state-badge-sm {
  display: inline-block;
  font-size: 0.7rem;
  padding: 2px 8px;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.1);
  font-weight: 500;
}

.climate-toggle-sm {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  background: rgba(255, 255, 255, 0.06);
  color: var(--text);
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0;
}

.climate-toggle-sm.active {
  background: var(--primary);
  border-color: var(--primary);
  color: white;
}

.climate-toggle-sm span {
  width: 16px;
  height: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.climate-compact-display {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.climate-temps {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.current-temp-sm {
  display: flex;
  align-items: baseline;
  gap: 2px;
}

.temp-value-sm {
  font-size: 1.8rem;
  font-weight: 700;
  color: var(--text);
}

.temp-unit-sm {
  font-size: 1rem;
  color: rgba(255, 255, 255, 0.5);
}

.target-temp-sm {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
}

.target-label-sm {
  font-size: 0.7rem;
  color: rgba(255, 255, 255, 0.5);
  text-transform: uppercase;
}

.target-value-sm {
  font-size: 1rem;
  font-weight: 600;
  color: var(--text);
}

.climate-temp-controls-sm {
  display: flex;
  gap: 8px;
  justify-content: center;
}

.temp-btn-sm {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  background: rgba(255, 255, 255, 0.06);
  color: var(--text);
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0;
}

.temp-btn-sm:hover {
  background: rgba(255, 255, 255, 0.12);
  border-color: var(--primary);
  transform: scale(1.05);
}

.temp-btn-sm span {
  width: 16px;
  height: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.climate-off-sm {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 12px 0;
}

.off-temp-sm {
  font-size: 1.2rem;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.4);
}

/* Temperature Sensors */
.temperatures-section {
  margin-top: 24px;
  padding-top: 20px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
}

.temperatures-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 12px;
}

.temp-sensor-card {
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  padding: 14px;
  display: flex;
  gap: 12px;
  align-items: center;
  transition: all 0.3s ease;
}

.temp-sensor-card:hover {
  border-color: rgba(255, 255, 255, 0.15);
  background: rgba(255, 255, 255, 0.06);
}

.temp-sensor-icon {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  background: linear-gradient(135deg, rgba(108, 140, 255, 0.15), rgba(92, 124, 250, 0.05));
  border: 1px solid rgba(108, 140, 255, 0.2);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.temp-sensor-icon span {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  color: var(--primary);
}

.temp-sensor-info {
  flex: 1;
  min-width: 0;
}

.temp-sensor-name {
  font-size: 0.85rem;
  font-weight: 500;
  margin: 0 0 4px 0;
  color: rgba(255, 255, 255, 0.7);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.temp-sensor-value {
  display: flex;
  align-items: baseline;
  gap: 4px;
}

.temp-big {
  font-size: 1.8rem;
  font-weight: 700;
  color: var(--text);
  line-height: 1;
}

.temp-unit {
  font-size: 1rem;
  font-weight: 500;
  color: rgba(255, 255, 255, 0.5);
}

@media (max-width: 768px) {
  .covers-grid,
  .climate-grid,
  .temperatures-grid {
    grid-template-columns: 1fr;
  }
}
</style>