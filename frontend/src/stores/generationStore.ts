import { create } from 'zustand'

export type AgentName =
  | 'LoreAgent'
  | 'DialogueStyleAgent'
  | 'VisualAgent'
  | 'VoiceAgent'
  | 'RelationshipDynamicsAgent'
  | 'SynthesisAgent'

export type AgentStatus = 'idle' | 'running' | 'done' | 'error'

export interface AgentStep {
  name: AgentName
  label: string
  status: AgentStatus
  artifact: string | null
  message: string | null
}

export interface CharacterResult {
  character_id: string
  name: string
  consistent: boolean
}

const AGENT_ORDER: { name: AgentName; label: string }[] = [
  { name: 'LoreAgent',               label: 'Lore & Backstory' },
  { name: 'DialogueStyleAgent',      label: 'Dialogue Style' },
  { name: 'VisualAgent',             label: 'Portrait' },
  { name: 'VoiceAgent',              label: 'Voice' },
  { name: 'RelationshipDynamicsAgent', label: 'Relationships' },
  { name: 'SynthesisAgent',          label: 'Synthesis' },
]

function freshSteps(): AgentStep[] {
  return AGENT_ORDER.map(a => ({
    name: a.name, label: a.label,
    status: 'idle', artifact: null, message: null,
  }))
}

interface GenerationState {
  phase: 'idle' | 'generating' | 'done' | 'error'
  steps: AgentStep[]
  result: CharacterResult | null
  error: string | null
  generate: (prompt: string, secondPrompt?: string) => Promise<void>
  reset: () => void
}

export const useGenerationStore = create<GenerationState>((set, get) => ({
  phase: 'idle',
  steps: freshSteps(),
  result: null,
  error: null,

  reset: () => set({ phase: 'idle', steps: freshSteps(), result: null, error: null }),

  generate: async (prompt, secondPrompt) => {
    set({ phase: 'generating', steps: freshSteps(), result: null, error: null })

    const res = await fetch('/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ prompt, second_prompt: secondPrompt ?? null }),
    })
    const { job_id } = await res.json()

    const ws = new WebSocket(`/ws/generate/${job_id}`)

    ws.onmessage = (e) => {
      const event = JSON.parse(e.data)
      const { steps } = get()

      if (event.event === 'agent_start') {
        set({
          steps: steps.map(s =>
            s.name === event.agent ? { ...s, status: 'running', message: event.message } : s
          ),
        })
      } else if (event.event === 'agent_complete') {
        set({
          steps: get().steps.map(s =>
            s.name === event.agent ? { ...s, status: 'done', artifact: event.artifact } : s
          ),
        })
      } else if (event.event === 'generation_complete') {
        set({
          phase: 'done',
          result: {
            character_id: event.character_id,
            name: event.name,
            consistent: event.consistent,
          },
          steps: get().steps.map(s => s.status === 'running' ? { ...s, status: 'done' } : s),
        })
        ws.close()
      } else if (event.event === 'error') {
        set({
          phase: 'error',
          error: event.message,
          steps: get().steps.map(s =>
            s.status === 'running' ? { ...s, status: 'error' } : s
          ),
        })
        ws.close()
      }
    }

    ws.onerror = () => {
      set({ phase: 'error', error: 'WebSocket connection failed' })
    }
  },
}))
