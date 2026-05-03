import { useState } from 'react'
import { useGenerationStore } from '../stores/generationStore'

export default function InputForm() {
  const [prompt, setPrompt] = useState('')
  const [secondPrompt, setSecondPrompt] = useState('')
  const [dual, setDual] = useState(false)
  const { generate, phase } = useGenerationStore()

  const busy = phase === 'generating'

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!prompt.trim()) return
    generate(prompt.trim(), dual && secondPrompt.trim() ? secondPrompt.trim() : undefined)
  }

  return (
    <form onSubmit={handleSubmit} className="w-full max-w-2xl mx-auto space-y-4">
      <div>
        <label className="block text-xs uppercase tracking-widest text-zinc-500 mb-2">
          Character Description
        </label>
        <textarea
          value={prompt}
          onChange={e => setPrompt(e.target.value)}
          disabled={busy}
          rows={3}
          placeholder="Count Dracula — ancient Romanian vampire lord, aristocratic and predatory, 500+ years old…"
          className="w-full bg-void-700 border border-void-500 rounded-lg px-4 py-3 text-zinc-100
                     placeholder-zinc-600 focus:outline-none focus:border-crimson-600 resize-none
                     disabled:opacity-40 transition-colors"
        />
      </div>

      <button
        type="button"
        onClick={() => setDual(d => !d)}
        className="text-xs text-zinc-500 hover:text-crimson-400 transition-colors"
      >
        {dual ? '− Remove second character' : '+ Add second character (dual mode)'}
      </button>

      {dual && (
        <div>
          <label className="block text-xs uppercase tracking-widest text-zinc-500 mb-2">
            Second Character
          </label>
          <textarea
            value={secondPrompt}
            onChange={e => setSecondPrompt(e.target.value)}
            disabled={busy}
            rows={3}
            placeholder="Professor Van Helsing — obsessive Dutch vampire hunter, 60s, encyclopedic knowledge…"
            className="w-full bg-void-700 border border-void-500 rounded-lg px-4 py-3 text-zinc-100
                       placeholder-zinc-600 focus:outline-none focus:border-crimson-600 resize-none
                       disabled:opacity-40 transition-colors"
          />
        </div>
      )}

      <button
        type="submit"
        disabled={busy || !prompt.trim()}
        className="w-full py-3 rounded-lg font-semibold tracking-wide uppercase text-sm
                   bg-crimson-600 hover:bg-crimson-500 disabled:opacity-40 disabled:cursor-not-allowed
                   transition-colors"
      >
        {busy ? 'Generating…' : 'Generate Character'}
      </button>
    </form>
  )
}
