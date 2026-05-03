import { useGenerationStore } from './stores/generationStore'
import InputForm from './components/InputForm'
import GenerationProgress from './components/GenerationProgress'
import CharacterCard from './components/CharacterCard'
import CompanionChat from './components/CompanionChat'

export default function App() {
  const { phase, result, reset } = useGenerationStore()

  return (
    <div className="min-h-full flex flex-col">
      {/* Header */}
      <header className="border-b border-void-700 px-6 py-4 flex items-center justify-between flex-shrink-0">
        <div>
          <h1 className="font-serif text-xl text-zinc-100 tracking-wide">Companion</h1>
          <p className="text-xs text-zinc-600 mt-0.5">Multi-Agent Character Studio</p>
        </div>
        {phase !== 'idle' && (
          <button
            onClick={reset}
            className="text-xs text-zinc-600 hover:text-zinc-400 transition-colors"
          >
            New character
          </button>
        )}
      </header>

      {/* Main content */}
      <main className="flex-1 px-6 py-8 space-y-8 max-w-3xl w-full mx-auto">
        {/* Always show input unless generating or done */}
        {phase === 'idle' && (
          <div className="space-y-6">
            <div className="text-center space-y-2">
              <h2 className="font-serif text-3xl text-zinc-100">
                Describe a character.
              </h2>
              <p className="text-zinc-600 text-sm">
                Six agents will build their portrait, voice, backstory, and soul.
              </p>
            </div>
            <InputForm />
          </div>
        )}

        {/* Progress during generation */}
        {(phase === 'generating' || phase === 'error') && (
          <GenerationProgress />
        )}

        {/* Result */}
        {phase === 'done' && result && (
          <div className="space-y-6">
            <CharacterCard characterId={result.character_id} />
            <CompanionChat />
          </div>
        )}
      </main>
    </div>
  )
}
