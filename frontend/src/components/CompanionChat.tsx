import { useEffect, useRef, useState } from 'react'
import { useCompanionStore } from '../stores/companionStore'

export default function CompanionChat() {
  const { active, characterName, messages, sendMessage, deactivate } = useCompanionStore()
  const [input, setInput] = useState('')
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  if (!active) return null

  const handleSend = (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim()) return
    sendMessage(input.trim())
    setInput('')
  }

  return (
    <div className="w-full max-w-2xl mx-auto animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between mb-3 px-1">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-crimson-500 animate-pulse" />
          <span className="text-sm text-zinc-400">Speaking with <span className="text-zinc-200 font-medium">{characterName}</span></span>
        </div>
        <button
          onClick={deactivate}
          className="text-xs text-zinc-600 hover:text-zinc-400 transition-colors"
        >
          End session
        </button>
      </div>

      {/* Messages */}
      <div className="bg-void-800 border border-void-600 rounded-xl overflow-hidden">
        <div className="h-80 overflow-y-auto p-4 space-y-4">
          {messages.length === 0 && (
            <p className="text-center text-zinc-700 text-sm mt-8">
              Say something to {characterName}…
            </p>
          )}
          {messages.map((msg, i) => (
            <div
              key={i}
              className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-[80%] rounded-xl px-4 py-2.5 text-sm leading-relaxed
                  ${msg.role === 'user'
                    ? 'bg-void-600 text-zinc-300'
                    : 'bg-void-700 border border-void-500 text-zinc-200 font-serif'
                  }
                  ${msg.streaming ? 'after:content-["▌"] after:animate-pulse after:text-crimson-500 after:ml-0.5' : ''}
                `}
              >
                {msg.text}
              </div>
            </div>
          ))}
          <div ref={bottomRef} />
        </div>

        {/* Input */}
        <form onSubmit={handleSend} className="border-t border-void-600 flex">
          <input
            value={input}
            onChange={e => setInput(e.target.value)}
            placeholder="Speak…"
            className="flex-1 bg-transparent px-4 py-3 text-sm text-zinc-200 placeholder-zinc-700
                       focus:outline-none"
          />
          <button
            type="submit"
            disabled={!input.trim()}
            className="px-5 text-crimson-500 hover:text-crimson-400 disabled:opacity-30
                       transition-colors text-sm font-medium"
          >
            Send
          </button>
        </form>
      </div>
    </div>
  )
}
