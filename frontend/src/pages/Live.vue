<template>
  <div>
    <h1>Live</h1>
    <video ref="videoRef" autoplay muted playsinline style="width: 100%; max-width: 860px" />
  </div>
</template>

<script setup lang="ts">
import Hls from 'hls.js'
import { onMounted, onUnmounted, ref } from 'vue'
import { LIVE_PLAYLIST_URL } from '../api'

const videoRef = ref<HTMLVideoElement | null>(null)
let hls: Hls | null = null
let lastTime = 0

const lockSeeking = () => {
  const video = videoRef.value
  if (!video) {
    return
  }
  if (video.currentTime < lastTime - 0.3) {
    video.currentTime = lastTime
  }
}

const updateLast = () => {
  const video = videoRef.value
  if (!video) {
    return
  }
  lastTime = video.currentTime
}

const blockKeys = (event: KeyboardEvent) => {
  if (['ArrowLeft', 'ArrowRight', 'j', 'k', 'l', 'J', 'K', 'L'].includes(event.key)) {
    event.preventDefault()
  }
}

onMounted(() => {
  const video = videoRef.value
  if (!video) {
    return
  }

  video.controls = false
  video.addEventListener('seeking', lockSeeking)
  video.addEventListener('timeupdate', updateLast)
  window.addEventListener('keydown', blockKeys)

  if (video.canPlayType('application/vnd.apple.mpegurl')) {
    video.src = LIVE_PLAYLIST_URL
    return
  }

  hls = new Hls({ lowLatencyMode: true })
  hls.loadSource(LIVE_PLAYLIST_URL)
  hls.attachMedia(video)
})

onUnmounted(() => {
  const video = videoRef.value
  video?.removeEventListener('seeking', lockSeeking)
  video?.removeEventListener('timeupdate', updateLast)
  window.removeEventListener('keydown', blockKeys)
  hls?.destroy()
})
</script>
