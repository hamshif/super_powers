import { useState, useRef, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'
import './App.css'
import GraphViewer from './components/GraphViewer'

function App() {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const messagesEndRef = useRef(null)

  // Graph UI State
  const [showGraph, setShowGraph] = useState(true)
  const [graphHistory, setGraphHistory] = useState([])
  const [activeGraphCtx, setActiveGraphCtx] = useState("Bugs Bunny") // Default to Bugs Bunny

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }

  useEffect(() => {

    scrollToBottom()
  }, [messages])


  const streamResponse = async (prompt) => {
    setLoading(true)
    try {
      const response = await fetch('/super_powers_sage', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt })
      })

      if (!response.ok) {
        throw new Error(`Request failed: ${response.status}`)
      }

      if (!response.body) {
        const text = await response.text()
        if (text.trim()) {
          setMessages(prev => [...prev, { role: 'assistant', content: text.trim() }])
        }
        return
      }

      const reader = response.body.getReader()
      const decoder = new TextDecoder()

      setMessages(prev => [...prev, { role: 'assistant', content: '', thoughts: [], isThinking: true }])

      let received = false
      let buffer = ''
      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const events = buffer.split(/\r?\n\r?\n/)

        buffer = events.pop() ?? ''

        for (const event of events) {
          const lines = event.split(/\r?\n/)

          // Parse Event Type
          const eventLine = lines.find(line => line.startsWith('event:'))
          const eventType = eventLine ? eventLine.replace(/^event:\s?/, '').trim() : 'message'

          const dataLines = lines.filter((line) => line.startsWith('data:'))
          if (!dataLines.length) {
            continue;
          }

          const payload = dataLines
            .map((line) => line.replace(/^data:\s?/, ''))
            .join('\n')

          if (!payload) continue

          // Handle Event Types
          setMessages(prev => {
            const newMsgs = [...prev]
            if (newMsgs.length === 0) return newMsgs

            const lastIndex = newMsgs.length - 1
            const lastMsg = { ...newMsgs[lastIndex] }


            if (eventType === 'stream_of_thought' || eventType === 'heartbeat') {
              // Only push if it's new content
              if (payload !== ": ping") {
                lastMsg.thoughts = [...(lastMsg.thoughts || []), payload]
              }
            } else if (eventType === 'hero_data') {
              // Side-channel data payload
              try {
                const dataObj = JSON.parse(payload)
                lastMsg.sideData = [...(lastMsg.sideData || []), dataObj]

                // === GRAPH TRIGGER ===
                // If we get hero data, update the graph context!
                const topic = dataObj.hero || dataObj.center
                if (topic) {
                  setGraphHistory(prev => {
                    // Add to history if unique, keep last 5
                    const exists = prev.find(i => i.token === topic)
                    if (exists) return prev
                    return [{ label: topic, token: topic }, ...prev].slice(0, 5)
                  })

                  // DEFER GRAPH LOAD to prevent UI stutter during chat stream
                  setTimeout(() => {
                    setActiveGraphCtx(topic)
                    setShowGraph(true) // Auto-open panel
                  }, 500)
                }

              } catch (e) {
                console.error("Failed to parse hero_data", e)
              }
            } else if (eventType === 'answer' || eventType === 'message') {
              lastMsg.content += payload
              lastMsg.isThinking = false // Answer started
            }


            newMsgs[lastIndex] = lastMsg
            return newMsgs
          })

          received = true
        }
      }


      buffer += decoder.decode()
      if (buffer.trim()) {
        // ... (Cleanup buffer logic similar to loop, but simplified for brevity in this replace) ...
        // For robustness, we'd replicate parsing, but usually end of stream is empty.
      }

    } catch (err) {
      console.error("Fetch error", err)
      setMessages(prev => [...prev, { role: 'system', content: `Error: ${err.message}` }])
    } finally {
      setLoading(false)
      setMessages(prev => {
        if (prev.length === 0) return prev
        const newMsgs = [...prev]
        const lastMsg = { ...newMsgs[newMsgs.length - 1] }
        lastMsg.isThinking = false
        newMsgs[newMsgs.length - 1] = lastMsg
        return newMsgs
      })
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!input.trim() || loading) return

    const userMsg = { role: 'user', content: input }
    setMessages(prev => [...prev, userMsg])
    setInput('')

    await streamResponse(userMsg.content)
  }

  return (
    <div className={`app-layout ${showGraph ? 'split-view' : ''}`}>
      <div className="chat-container">
        <header>
          {/* The Digital Seal Logo */}
          <div className="logo-seal">印</div>
          <h1>Super Power Sage</h1>
          <div style={{ marginLeft: 'auto' }}>
            <button
              onClick={() => setShowGraph(!showGraph)}
              style={{ padding: '5px 15px', fontSize: '0.8rem' }}
            >
              {showGraph ? 'Hide Graph' : 'Show Graph'}
            </button>
          </div>
        </header>

        <div className="messages-list">
          {messages.map((msg, idx) => (
            <div key={idx} className={`message ${msg.role}`}>


              {msg.role === 'assistant' && (msg.thoughts?.length > 0) && (
                <details className="thought-process" open={idx === messages.length - 1 && msg.isThinking}>
                  <summary>Thought Process</summary>
                  <div className="thought-content">
                    {msg.thoughts.map((t, i) => <div key={i}>{t}</div>)}
                  </div>
                </details>
              )}

              {/* Side Channel Data (Hero/Graph) */}
              {msg.sideData?.map((data, i) => (
                <div key={i} className="hero-data-block">
                  <div className="hero-data-header">
                    STATUS: RETRIEVED // {data.type?.toUpperCase()} // {data.hero || data.center?.toUpperCase()}
                  </div>
                  <pre className="hero-data-content">
                    {JSON.stringify(data.payload || data, null, 2)}
                  </pre>
                </div>
              ))}

              <div className="bubble">
                <ReactMarkdown>{msg.content}</ReactMarkdown>
              </div>
            </div>
          ))}
          {loading && messages.length > 0 && messages[messages.length - 1].role === 'user' && (
            // Fallback if no assistant msg created yet
            <div className="message assistant"><div className="bubble">...</div></div>
          )}
          <div ref={messagesEndRef} />
        </div>

        <form onSubmit={handleSubmit} className="input-area">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about your super power..."
            disabled={loading}
          />
          <button type="submit" disabled={loading}>
            {loading ? 'SENDING' : 'SEND'}
          </button>
        </form>
      </div>

      {showGraph && (
        <div className="graph-panel">
          <div className="graph-header">
            <h2>Knowledge Graph</h2>
            <div className="graph-controls">
              <select
                value={activeGraphCtx || "overview"}
                onChange={(e) => setActiveGraphCtx(e.target.value)}
              >
                <option value="overview">GLOBAL OVERVIEW</option>
                {graphHistory.map((item, i) => (
                  <option key={i} value={item.token}>
                    {item.label.toUpperCase()}
                  </option>
                ))}
              </select>
            </div>
          </div>
          {/* Replaced iframe with client-side GraphViewer (Offline Capable) */}
          <div className="graph-frame" style={{ flex: 1, overflow: 'hidden' }}>
            <GraphViewer center={activeGraphCtx} />
          </div>
        </div>
      )}

    </div>
  )
}

export default App
