import { useEffect, useState } from 'react'
import { NEWSROOM_API, splitSentences } from '../data/newsroom.js'

// Finds a Telugu voice installed in the browser (Chrome/Edge/Android usually
// have one; many desktop browsers do not).
function pickTeluguVoice(gender) {
  const voices = window.speechSynthesis?.getVoices?.() || []
  const te = voices.filter((v) => v.lang?.toLowerCase().startsWith('te'))
  if (!te.length) return null
  const want = gender === 'male' ? /mohan|male|man/i : /shruti|female|woman/i
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

// Reads one rundown segment. Returns a cancel() function.
//   • server MP3 (edge-tts neural voice) when the agent server recorded one
//   • otherwise the browser's Telugu voice, sentence by sentence
//   • otherwise a silent timed preview, so the graphics still run
export function speakSegment(segment, { gender = 'female', onSentence, onEnd, onMode }) {
  const sentences = splitSentences(segment.script)
  const totalChars = sentences.reduce((a, s) => a + s.length, 0) || 1
  let cancelled = false
  const finish = () => {
    if (!cancelled) onEnd?.()
  }

  // 1) Server-recorded audio
  if (segment.audio_url) {
    const audio = new Audio(NEWSROOM_API + segment.audio_url)
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
    audio.onended = finish
    audio.onerror = () => {
      if (cancelled || fellBack) return
      fellBack = true
      cancelFallback = speakSegment({ ...segment, audio_url: null }, { gender, onSentence, onEnd, onMode })
    }
    onMode?.('server')
    onSentence?.(0)
    audio.play().catch(() => audio.onerror?.())
    return () => {
      cancelled = true
      audio.pause()
      audio.src = ''
      cancelFallback?.()
    }
  }

  // 2) Browser voice / 3) silent preview
  const synth = window.speechSynthesis
  const voice = synth ? pickTeluguVoice(gender) : null
  onMode?.(voice ? 'browser' : 'silent')
  let timer = null

  const sayFrom = (i) => {
    if (cancelled) return
    if (i >= sentences.length) return finish()
    onSentence?.(i)
    if (voice) {
      const u = new SpeechSynthesisUtterance(sentences[i])
      u.voice = voice
      u.lang = voice.lang
      u.rate = 1
      u.onend = () => sayFrom(i + 1)
      u.onerror = () => sayFrom(i + 1)
      synth.speak(u)
    } else {
      timer = setTimeout(() => sayFrom(i + 1), Math.max(1800, sentences[i].length * 75))
    }
  }
  sayFrom(0)

  return () => {
    cancelled = true
    clearTimeout(timer)
    if (voice) synth.cancel()
  }
}
