import { useGenerationStore, AgentStep } from '../stores/generationStore'

const icons: Record<string, string> = {
  LoreAgent: '📜',
  DialogueStyleAgent: '🗣',
  VisualAgent: '🎨',
  VoiceAgent: '🎙',
  RelationshipDynamicsAgent: '🕸',
  SynthesisAgent: '✦',
}

function Step({ step }: { step: AgentStep }) {
  const colors = {
    idle:    'border-void-500 text-zinc-600',
    running: 'border-crimson-600 text-zinc-100 shadow-[0_0_12px_rgba(185,28,28,0.4)]',
    done:    'border-zinc-600 text-zinc-400',
    error:   'border-red-700 text-red-400',
  }

  const dot = {
    idle:    'bg-void-500',
    running: 'bg-crimson-500 animate-pulse',
    done:    'bg-zinc-500',
    error:   'bg-red-600',
  }

  return (
    <div className={`flex items-center gap-3 border rounded-lg px-4 py-3 transition-all duration-500 ${colors[step.status]}`}>
      <span className="text-lg">{icons[step.name]}</span>
      <div className="flex-1 min-w-0">
        <div className="text-sm font-medium">{step.label}</div>
        {step.status === 'running' && step.message && (
          <div className="text-xs text-zinc-500 truncate mt-0.5">{step.message}</div>
        )}
        {step.status === 'done' && step.artifact && (
          <div className="text-xs text-zinc-600 mt-0.5">{step.artifact}</div>
        )}
      </div>
      <span className={`w-2 h-2 rounded-full flex-shrink-0 ${dot[step.status]}`} />
    </div>
  )
}

export default function GenerationProgress() {
  const { steps, phase, error } = useGenerationStore()

  if (phase === 'idle') return null

  return (
    <div className="w-full max-w-2xl mx-auto space-y-2 animate-fade-in">
      <p className="text-xs uppercase tracking-widest text-zinc-600 mb-3">
        {phase === 'generating' ? 'Agents at work…' : phase === 'done' ? 'Complete' : 'Failed'}
      </p>
      {steps.map(s => <Step key={s.name} step={s} />)}
      {error && (
        <div className="text-sm text-red-400 bg-red-950/30 border border-red-900 rounded-lg px-4 py-3">
          {error}
        </div>
      )}
    </div>
  )
}
