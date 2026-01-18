import { useState, useRef, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'
import './App.css'

function App() {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const messagesEndRef = useRef(null)

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

      setMessages(prev => [...prev, { role: 'assistant', content: '' }])

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

          const dataLines = lines.filter((line) => line.startsWith('data:'))
          if (!dataLines.length) {
            continue;
          }

          const payload = dataLines
            .map((line) => line.replace(/^data:\s?/, ''))
            .join('\n')

          if (!payload) continue




          setMessages(prev => {
            const newMsgs = [...prev]
            if (newMsgs.length === 0) {
              return newMsgs;
            }
            const lastIndex = newMsgs.length - 1
            const lastMsg = { ...newMsgs[lastIndex] }
            lastMsg.content += payload
            newMsgs[lastIndex] = lastMsg
            return newMsgs
          })

          received = true
        }
      }


      buffer += decoder.decode()
      if (buffer.trim()) {
        const lines = buffer.split(/\r?\n/)
        const dataLines = lines.filter((line) => line.startsWith('data:'))
        if (dataLines.length) {
          const payload = dataLines
            .map((line) => line.replace(/^data:\s?/, ''))
            .join('\n')
          if (payload) {
            setMessages(prev => {
              const newMsgs = [...prev]
              const lastIndex = newMsgs.length - 1
              const lastMsg = { ...newMsgs[lastIndex] }
              lastMsg.content += payload
              newMsgs[lastIndex] = lastMsg
              return newMsgs
            })
            received = true
          }
        }
      }

      if (!received && buffer.trim()) {
        setMessages(prev => {
          const newMsgs = [...prev]
          const lastIndex = newMsgs.length - 1
          const lastMsg = { ...newMsgs[lastIndex] }
          lastMsg.content += buffer.trim()
          newMsgs[lastIndex] = lastMsg
          return newMsgs
        })
      }
    } catch (err) {
      console.error("Fetch error", err)
      setMessages(prev => [...prev, { role: 'system', content: `Error: ${err.message}` }])
    } finally {
      setLoading(false)
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
    <div className="chat-container">
      <header>
        {/* The Digital Seal Logo */}
        <div className="logo-seal">印</div>
        <h1>Super Power Sage</h1>
      </header>

      <div className="messages-list">
        {messages.map((msg, idx) => (
          <div key={idx} className={`message ${msg.role}`}>
            <div className="bubble">
              <ReactMarkdown>{msg.content}</ReactMarkdown>
            </div>
          </div>
        ))}
        {loading && messages.length > 0 && !messages[messages.length - 1].content && (
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
  )
}

export default App
