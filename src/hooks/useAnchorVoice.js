import { useEffect, useState } from 'react'
import { NEWSROOM_API, splitSentences } from '../data/newsroom.js'

// Finds a Telugu voice installed in the browser (Chrome/Edge/Android usually
// have one; many desktop browsers do not).
function pickTeluguVoice(gender) {
  const voices = window.speechSynthesis?.getVoices?.() || []
  const te = voices.filter((v) => v.lang?.toLowerCase().startsWith('te'))
  if (!te.length) return null
  const want = gender === 'male' ? /mohan|(?<!fe)male/i : /shruti|female|woman/i
  return te.find((v) => want.test(v.name)) || te[0]
}

export function useBrowserTeluguVoice() {
  const [available, setAvailable] = useState(() => !!pickTeluguVoice())
  useEffect(() => {
    const synth = window.speechSynthesis
    if (!synth) return undefined
    const update = () => setAvailable(!!pickTeluguVoice())
    update()
    synth.addEventListener?.('voiceschanged', update)
    return () => synth.removeEventListener?.('voiceschanged', update)
  }, [])
  return available
}

// Live loudness of whatever the anchor is saying, read every frame by the
// stage to move the anchor's jaw and head.
//   source 'audio'     → value is the real level of the server MP3 (0..1)
//   source 'synthetic' → browser/silent voice: no audio access, so the stage
//                        animates a speech rhythm while `active` is true
export const voiceLevel = { value: 0, source: 'none', active: false }

let audioCtx = null
function attachAnalyser(audio) {
  try {
    const Ctx = window.AudioContext || window.webkitAudioContext
    if (!Ctx) return null
    audioCtx = audioCtx || new Ctx()
    if (audioCtx.state === 'suspended') audioCtx.resume()
    const src = audioCtx.createMediaElementSource(audio)
    const analyser = audioCtx.createAnalyser()
    analyser.fftSize = 1024
    src.connect(analyser)
    analyser.connect(audioCtx.destination)
    const buf = new Uint8Array(analyser.fftSize)
    let raf = 0
    const tick = () => {
      analyser.getByteTimeDomainData(buf)
      let sum = 0
      for (let i = 0; i < buf.length; i++) {
        const v = (buf[i] - 128) / 128
        sum += v * v
      }
      voiceLevel.value = Math.min(1, Math.sqrt(sum / buf.length) * 4.5)
      raf = requestAnimationFrame(tick)
    }
    tick()
    return () => {
      cancelAnimationFrame(raf)
      src.disconnect()
      analyser.disconnect()
    }
  } catch {
    return null
  }
}

// Reads one rundown segment. Returns a cancel() function.
//   • server MP3 (edge-tts neural voice) when the agent server recorded one
//   • otherwise the browser's Telugu voice, sentence by sentence
//   • otherwise a silent timed preview, so the graphics still run
export function speakSegment(segment, { gender = 'male', onSentence, onEnd, onMode }) {
  const sentences = splitSentences(segment.script)
  const totalChars = sentences.reduce((a, s) => a + s.length, 0) || 1
  let cancelled = false
  const finish = () => {
    if (!cancelled) onEnd?.()
  }

  // 1) Server-recorded audio
  if (segment.audio_url) {
    const audio = new Audio()
    audio.crossOrigin = 'anonymous' // lets the analyser read the level (server sends CORS headers)
    audio.src = NEWSROOM_API + segment.audio_url
    const detach = attachAnalyser(audio)
    voiceLevel.source = detach ? 'audio' : 'synthetic'
    voiceLevel.value = 0
    audio.onplay = () => (voiceLevel.active = true)
    audio.onpause = () => (voiceLevel.active = false)
    let fellBack = false
    let cancelFallback = null
    audio.ontimeupdate = () => {
      if (!audio.duration) return
      const target = (audio.currentTime / audio.duration) * totalChars
      let acc = 0
      let idx = 0
      for (; idx < sentences.length - 1; idx++) {
        acc += sentences[idx].length
        if (acc > target) break
      }
      onSentence?.(idx)
    }
    audio.onended = () => {
      voiceLevel.active = false
      voiceLevel.value = 0
      finish()
    }
    audio.onerror = () => {
      if (cancelled || fellBack) return
      fellBack = true
      detach?.()
      cancelFallback = speakSegment({ ...segment, audio_url: null }, { gender, onSentence, onEnd, onMode })
    }
    onMode?.('server')
    onSentence?.(0)
    audio.play().catch(() => audio.onerror?.())
    return () => {
      cancelled = true
      audio.pause()
      audio.src = ''
      detach?.()
      voiceLevel.active = false
      voiceLevel.value = 0
      cancelFallback?.()
    }
  }

  // 2) Browser voice / 3) silent preview
  const synth = window.speechSynthesis
  const voice = synth ? pickTeluguVoice(gender) : null
  onMode?.(voice ? 'browser' : 'silent')
  voiceLevel.source = 'synthetic'
  voiceLevel.value = 0
  let timer = null

  const sayFrom = (i) => {
    if (cancelled) return
    if (i >= sentences.length) {
      voiceLevel.active = false
      return finish()
    }
    onSentence?.(i)
    if (voice) {
      const u = new SpeechSynthesisUtterance(sentences[i])
      u.voice = voice
      u.lang = voice.lang
      u.rate = 1
      u.onstart = () => (voiceLevel.active = true)
      u.onend = () => {
        voiceLevel.active = false // short closed-mouth pause between sentences
        sayFrom(i + 1)
      }
      u.onerror = u.onend
      synth.speak(u)
    } else {
      const ms = Math.max(1800, sentences[i].length * 75)
      voiceLevel.active = true
      timer = setTimeout(() => {
        voiceLevel.active = false
        timer = setTimeout(() => sayFrom(i + 1), 280)
      }, ms)
    }
  }
  sayFrom(0)

  return () => {
    cancelled = true
    clearTimeout(timer)
    voiceLevel.active = false
    if (voice) synth.cancel()
  }
}
