import { useEffect, useState } from 'react'
import { useCompanionStore } from '../stores/companionStore'

interface Bio {
  id: string
  name: string
  archetype: string
  age: string
  origin: string
  appearance: string
  personality: string[]
  backstory: string
  fears: string[]
  desires: string[]
  speech_era: string
}

export default function CharacterCard({ characterId }: { characterId: string }) {
  const [bio, setBio] = useState<Bio | null>(null)
  const { activate, active, characterId: activeId } = useCompanionStore()

  useEffect(() => {
    fetch(`/characters/${characterId}`)
      .then(r => r.json())
      .then(setBio)
  }, [characterId])

  if (!bio) return (
    <div className="w-full max-w-2xl mx-auto h-64 bg-void-800 rounded-xl animate-pulse" />
  )

  const isActive = active && activeId === characterId

  return (
    <div className="w-full max-w-2xl mx-auto animate-fade-in">
      <div className="bg-void-800 border border-void-600 rounded-xl overflow-hidden">
        {/* Portrait + header */}
        <div className="flex gap-5 p-5">
          <div className="flex-shrink-0">
            <img
              src={`/characters/${characterId}/portrait`}
              alt={bio.name}
              className="w-36 h-36 rounded-lg object-cover border border-void-500"
              onError={e => { (e.target as HTMLImageElement).style.display = 'none' }}
            />
          </div>

          <div className="flex-1 min-w-0">
            <h2 className="font-serif text-2xl text-zinc-100">{bio.name}</h2>
            <p className="text-crimson-500 text-sm mt-0.5">{bio.archetype}</p>
            <p className="text-zinc-500 text-xs mt-1">{bio.age} · {bio.origin}</p>

            <div className="flex flex-wrap gap-1.5 mt-3">
              {bio.personality.map(t => (
                <span key={t} className="px-2 py-0.5 text-xs rounded-full bg-void-600 text-zinc-400 border border-void-500">
                  {t}
                </span>
              ))}
            </div>

            <div className="mt-3">
              <audio
                controls
                src={`/characters/${characterId}/voice`}
                className="w-full h-8 accent-crimson-600"
              />
            </div>
          </div>
        </div>

        {/* Backstory */}
        <div className="px-5 pb-4 border-t border-void-600">
          <p className="text-sm text-zinc-400 leading-relaxed mt-4">{bio.backstory}</p>
        </div>

        {/* Fears + desires */}
        <div className="grid grid-cols-2 gap-px bg-void-600">
          <div className="bg-void-800 px-5 py-4">
            <p className="text-xs uppercase tracking-widest text-zinc-600 mb-2">Fears</p>
            <ul className="space-y-1">
              {bio.fears.map(f => (
                <li key={f} className="text-xs text-zinc-500 flex gap-2">
                  <span className="text-crimson-700 flex-shrink-0">✦</span>{f}
                </li>
              ))}
            </ul>
          </div>
          <div className="bg-void-800 px-5 py-4">
            <p className="text-xs uppercase tracking-widest text-zinc-600 mb-2">Desires</p>
            <ul className="space-y-1">
              {bio.desires.map(d => (
                <li key={d} className="text-xs text-zinc-500 flex gap-2">
                  <span className="text-crimson-700 flex-shrink-0">✦</span>{d}
                </li>
              ))}
            </ul>
          </div>
        </div>

        {/* Activate button */}
        <div className="px-5 py-4 border-t border-void-600">
          {isActive ? (
            <div className="text-center text-sm text-crimson-400 animate-pulse-slow">
              ● Companion active — scroll down to speak
            </div>
          ) : (
            <button
              onClick={() => activate(bio.id, bio.name)}
              className="w-full py-2.5 rounded-lg text-sm font-semibold tracking-wide uppercase
                         border border-crimson-700 text-crimson-400 hover:bg-crimson-700/20
                         transition-colors"
            >
              Activate Companion
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
