import React, { useState, useEffect, useRef } from 'react'
import { Send, Bot, User, Sparkles } from 'lucide-react'
import { chatCopilot, getCopilotSuggestions } from '../services/api'

function Message({ msg }) {
  const isUser = msg.role === 'user'
  return (
    <div className={`flex gap-3 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>
      <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
        isUser ? 'bg-saffron-500/30' : 'bg-blue-500/20'
      }`}>
        {isUser ? <User size={16} className="text-saffron-400" /> : <Bot size={16} className="text-blue-400" />}
      </div>
      <div className={isUser ? 'bubble-user' : 'bubble-assistant'}>
        {isUser ? (
          <p className="text-sm">{msg.content}</p>
        ) : (
          <div className="text-sm whitespace-pre-wrap leading-relaxed">
            {msg.content.split('\n').map((line, i) => {
              if (line.startsWith('**') && line.endsWith('**')) {
                return <p key={i} className="font-bold text-saffron-400">{line.slice(2, -2)}</p>
              }
              if (line.startsWith('• ')) {
                return <p key={i} className="pl-2">{line}</p>
              }
              return line ? <p key={i}>{line}</p> : <br key={i} />
            })}
          </div>
        )}
      </div>
    </div>
  )
}

export default function AICopilot() {
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content: `**Welcome to the AI Copilot!**

I'm your intelligent sales assistant for two-wheeler dispatch planning.

I can help you with:
• Dispatch recommendations and planning
• Festival demand analysis (Diwali, Navratri, Onam…)
• Marriage season stock planning
• Colour and variant performance
• YoY/MoM growth trends
• Slow-moving stock alerts
• What-if scenario analysis

Try asking me anything about your sales or inventory!`,
    }
  ])
  const [input, setInput] = useState('')
  const [suggestions, setSuggestions] = useState([])
  const [loading, setLoading] = useState(false)
  const [showSuggestions, setShowSuggestions] = useState(true)
  const bottomRef = useRef(null)

  useEffect(() => {
    getCopilotSuggestions().then(d => setSuggestions(d.questions || [])).catch(() => {})
  }, [])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  const send = async (text) => {
    const msg = text || input.trim()
    if (!msg) return
    setInput('')
    setShowSuggestions(false)
    setMessages(prev => [...prev, { role: 'user', content: msg }])
    setLoading(true)

    try {
      const history = messages.slice(-6).map(m => ({ role: m.role, content: m.content }))
      const result = await chatCopilot({ message: msg, history })
      setMessages(prev => [...prev, { role: 'assistant', content: result.answer }])
      if (result.suggested_followups?.length > 0) {
        setSuggestions(result.suggested_followups.slice(0, 4))
        setShowSuggestions(true)
      }
    } catch {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: 'Sorry, I encountered an error. Please try again.',
      }])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex flex-col h-[calc(100vh-140px)] max-h-[800px]">
      {/* Header */}
      <div className="flex items-center gap-3 pb-4 mb-4 border-b border-brand-border">
        <div className="w-10 h-10 rounded-xl bg-blue-500/20 flex items-center justify-center">
          <Sparkles size={20} className="text-blue-400" />
        </div>
        <div>
          <h2 className="font-semibold text-brand-text">AI Sales Copilot</h2>
          <p className="text-xs text-brand-muted">Powered by intelligent analytics • Ask anything about your sales</p>
        </div>
        <div className="ml-auto flex items-center gap-1.5">
          <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
          <span className="text-xs text-green-400">Online</span>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto space-y-4 pb-4">
        {messages.map((m, i) => <Message key={i} msg={m} />)}

        {loading && (
          <div className="flex gap-3">
            <div className="w-8 h-8 rounded-full bg-blue-500/20 flex items-center justify-center flex-shrink-0">
              <Bot size={16} className="text-blue-400" />
            </div>
            <div className="bubble-assistant flex items-center gap-2">
              <div className="flex gap-1">
                {[0,1,2].map(i => (
                  <div key={i} className="w-2 h-2 rounded-full bg-brand-muted animate-bounce"
                    style={{ animationDelay: `${i*150}ms` }} />
                ))}
              </div>
              <span className="text-xs text-brand-muted">Analysing…</span>
            </div>
          </div>
        )}

        {/* Suggestions */}
        {showSuggestions && suggestions.length > 0 && !loading && (
          <div className="ml-11">
            <p className="text-xs text-brand-muted mb-2">Suggested questions:</p>
            <div className="flex flex-wrap gap-2">
              {suggestions.map((q, i) => (
                <button key={i} onClick={() => send(q)}
                  className="text-xs bg-white/[0.04] border border-brand-border hover:border-saffron-500/40 hover:text-saffron-400 text-brand-muted rounded-full px-3 py-1.5 transition-colors">
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="pt-4 border-t border-brand-border">
        <div className="flex gap-3">
          <input
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && !e.shiftKey && send()}
            placeholder="Ask me anything about sales, dispatch, festivals…"
            className="flex-1 bg-brand-card border border-brand-border text-brand-text text-sm rounded-xl px-4 py-3 focus:outline-none focus:border-saffron-500/50 placeholder-brand-muted"
          />
          <button
            onClick={() => send()}
            disabled={!input.trim() || loading}
            className="bg-saffron-500 hover:bg-saffron-600 text-white rounded-xl px-4 py-3 transition-colors disabled:opacity-40"
          >
            <Send size={17} />
          </button>
        </div>
        <p className="text-xs text-brand-muted mt-2 text-center">
          Powered by rule-based analytics engine • Optionally enhance with OpenAI / Claude API
        </p>
      </div>
    </div>
  )
}
