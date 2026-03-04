<template>
  <main class="page">
    <section class="hero-card">
      <div class="hero-header">
        <div>
          <p class="eyebrow">stream platform</p>
          <h1>Live Loop Channel</h1>
          <p class="subtext">Непрерывный эфир в тёмной теме с авто-воспроизведением.</p>
        </div>
        <span class="live-pill">● LIVE</span>
      </div>

      <div class="player-shell">
        <video ref="videoRef" autoplay muted playsinline class="player" />
      </div>

      <div class="meta-row">
        <div class="meta-item">
          <span class="meta-label">Source</span>
          <code>{{ playlistUrl }}</code>
        </div>
        <div class="meta-item">
          <span class="meta-label">Mode</span>
          <span>Live HLS (stable polling)</span>
        </div>
      </div>
    </section>
  </main>
</template>

<script setup lang="ts">
import Hls from 'hls.js'
import { onMounted, onUnmounted, ref } from 'vue'
import { LIVE_PLAYLIST_URL } from '../api'

const videoRef = ref<HTMLVideoElement | null>(null)
const playlistUrl = LIVE_PLAYLIST_URL
let hls: Hls | null = null

const setupHls = (video: HTMLVideoElement) => {
  hls = new Hls({
    lowLatencyMode: false,
    liveSyncDurationCount: 4,
    liveMaxLatencyDurationCount: 12,
    maxLiveSyncPlaybackRate: 1,
    backBufferLength: 30,
    manifestLoadingTimeOut: 20000,
    manifestLoadingRetryDelay: 2000,
    manifestLoadingMaxRetryTimeout: 12000,
    manifestLoadingMaxRetry: 4,
  })

  hls.on(Hls.Events.ERROR, (_, data) => {
    if (!hls || !data.fatal) {
      return
    }

    if (data.type === Hls.ErrorTypes.MEDIA_ERROR) {
      hls.recoverMediaError()
      return
    }

    hls.destroy()
    hls = null
  })

  hls.loadSource(LIVE_PLAYLIST_URL)
  hls.attachMedia(video)
}

onMounted(() => {
  const video = videoRef.value
  if (!video) {
    return
  }

  video.controls = false

  if (Hls.isSupported()) {
    setupHls(video)
    return
  }

  if (video.canPlayType('application/vnd.apple.mpegurl')) {
    video.src = LIVE_PLAYLIST_URL
  }
})

onUnmounted(() => {
  hls?.destroy()
  hls = null
})
</script>

<style scoped>
:global(body) {
  margin: 0;
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif;
  background: radial-gradient(circle at top, #1a2340, #090c16 45%);
  color: #eef2ff;
}

:global(*) {
  box-sizing: border-box;
}

.page {
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 24px;
}

.hero-card {
  width: min(1100px, 100%);
  background: rgba(13, 18, 34, 0.85);
  border: 1px solid rgba(155, 170, 255, 0.18);
  border-radius: 24px;
  box-shadow: 0 30px 80px rgba(0, 0, 0, 0.45);
  padding: 28px;
  backdrop-filter: blur(8px);
}

.hero-header {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
  margin-bottom: 18px;
}

.eyebrow {
  text-transform: uppercase;
  letter-spacing: 0.14em;
  color: #9fb0ff;
  font-size: 11px;
  margin: 0 0 8px;
}

h1 {
  margin: 0;
  font-size: clamp(26px, 4vw, 42px);
}

.subtext {
  margin: 8px 0 0;
  color: #bcc7e8;
}

.live-pill {
  flex-shrink: 0;
  background: linear-gradient(135deg, #ff375f, #ff914d);
  color: white;
  font-weight: 700;
  padding: 8px 12px;
  border-radius: 999px;
  font-size: 12px;
  letter-spacing: 0.08em;
}

.player-shell {
  border-radius: 18px;
  overflow: hidden;
  border: 1px solid rgba(170, 186, 255, 0.18);
  background: #02040a;
}

.player {
  display: block;
  width: 100%;
  max-height: 70vh;
  background: #02040a;
}

.meta-row {
  margin-top: 14px;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.meta-item {
  background: rgba(152, 168, 255, 0.08);
  border: 1px solid rgba(152, 168, 255, 0.2);
  border-radius: 12px;
  padding: 10px 12px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.meta-label {
  color: #9eafe9;
  font-size: 12px;
}

code {
  color: #e3eaff;
  word-break: break-all;
}

@media (max-width: 720px) {
  .hero-card {
    padding: 18px;
    border-radius: 18px;
  }

  .meta-row {
    grid-template-columns: 1fr;
  }
}
</style>
