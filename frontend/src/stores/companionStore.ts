import { create } from 'zustand'

export interface Message {
  role: 'user' | 'character'
  text: string
  streaming?: boolean
}

interface CompanionState {
  active: boolean
  characterId: string | null
  characterName: string | null
  sessionId: string | null
  messages: Message[]
  ws: WebSocket | null
  audioQueue: string[]   // base64 MP3 chunks accumulated per turn
  speaking: boolean

  activate: (characterId: string, characterName: string) => Promise<void>
  sendMessage: (text: string) => void
  deactivate: () => void
}

export const useCompanionStore = create<CompanionState>((set, get) => ({
  active: false,
  characterId: null,
  characterName: null,
  sessionId: null,
  messages: [],
  ws: null,
  audioQueue: [],
  speaking: false,

  activate: async (characterId, characterName) => {
    const res = await fetch('/activate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ character_id: characterId }),
    })
    const { session_id } = await res.json()

    const ws = new WebSocket(`/ws/companion/${session_id}`)
    let currentText = ''
    const audioChunks: string[] = []

    ws.onmessage = (e) => {
      const msg = JSON.parse(e.data)
      const { messages } = get()

      if (msg.type === 'text') {
        currentText += msg.data
        const last = messages[messages.length - 1]
        if (last?.role === 'character' && last.streaming) {
          set({ messages: [...messages.slice(0, -1), { ...last, text: currentText }] })
        } else {
          set({ messages: [...messages, { role: 'character', text: currentText, streaming: true }] })
        }
      } else if (msg.type === 'audio') {
        audioChunks.push(msg.data)
      } else if (msg.type === 'done') {
        // Finalize text
        set({
          messages: get().messages.map((m, i) =>
            i === get().messages.length - 1 ? { ...m, streaming: false } : m
          ),
        })
        currentText = ''

        // Play accumulated audio
        if (audioChunks.length > 0) {
          playAudio(audioChunks.splice(0))
        }
      }
    }

    set({ active: true, characterId, characterName, sessionId: session_id, ws, messages: [] })
  },

  sendMessage: (text) => {
    const { ws, messages } = get()
    if (!ws || ws.readyState !== WebSocket.OPEN) return
    set({ messages: [...messages, { role: 'user', text }] })
    ws.send(JSON.stringify({ type: 'user_message', text }))
  },

  deactivate: () => {
    get().ws?.close()
    set({ active: false, characterId: null, characterName: null, sessionId: null, ws: null, messages: [] })
  },
}))

function playAudio(chunks: string[]) {
  const binary = chunks.map(b64 => {
    const bin = atob(b64)
    const bytes = new Uint8Array(bin.length)
    for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i)
    return bytes
  })
  const total = binary.reduce((n, b) => n + b.length, 0)
  const merged = new Uint8Array(total)
  let offset = 0
  for (const b of binary) { merged.set(b, offset); offset += b.length }

  const blob = new Blob([merged], { type: 'audio/mpeg' })
  const url = URL.createObjectURL(blob)
  const audio = new Audio(url)
  audio.onended = () => URL.revokeObjectURL(url)
  audio.play().catch(() => {})
}
