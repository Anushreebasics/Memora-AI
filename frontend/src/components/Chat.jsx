import React, { useState, useRef, useEffect } from 'react';
import { Send, Terminal } from 'lucide-react';
import { api } from '../api';
import CitationModal from './CitationModal';

export default function Chat() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [selectedCitation, setSelectedCitation] = useState(null);
  const [modalOpen, setModalOpen] = useState(false);
  const scrollRef = useRef(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, loading]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!input.trim() || loading) return;

    const query = input;
    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: query }]);
    setLoading(true);

    try {
      const response = await api.chat(query);
      setMessages(prev => [...prev, { 
        role: 'assistant', 
        content: response.answer,
        citations: response.citations,
        confidence: response.confidence_score
      }]);
    } catch (err) {
      setMessages(prev => [...prev, { 
        role: 'system', 
        content: 'Failed to connect to backend engine. Ensure FastAPI is running.' 
      }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', paddingBottom: '1rem', borderBottom: '1px solid var(--panel-border)' }}>
        <Terminal color="var(--accent)" />
        <h2>Knowledge Assistant Terminal</h2>
      </div>

      <div ref={scrollRef} style={{ flex: 1, overflowY: 'auto', padding: '1rem 0', display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
        {messages.length === 0 && (
          <div style={{ margin: 'auto', textAlign: 'center', color: 'var(--text-secondary)' }}>
            <p>Ready to query Knowledge Base.</p>
          </div>
        )}
        
        {messages.map((m, i) => (
          <div key={i} className="animate-slide-up" style={{ 
            alignSelf: m.role === 'user' ? 'flex-end' : 'flex-start',
            maxWidth: '80%',
            background: m.role === 'user' ? 'rgba(56, 189, 248, 0.1)' : 'rgba(255, 255, 255, 0.05)',
            border: `1px solid ${m.role === 'user' ? 'rgba(56, 189, 248, 0.3)' : 'var(--panel-border)'}`,
            padding: '1rem',
            borderRadius: '12px',
          }}>
            <p style={{ whiteSpace: 'pre-wrap' }}>{m.content}</p>
            
            {m.citations && m.citations.length > 0 && (
              <div style={{ marginTop: '1rem', paddingTop: '0.5rem', borderTop: '1px solid rgba(255,255,255,0.1)', fontSize: '0.85rem' }}>
                <span style={{ color: 'var(--accent)' }}>Citations Found:</span>
                <ul style={{ margin: 0, paddingLeft: '1.2rem', color: 'var(--text-secondary)' }}>
                  {m.citations.slice(0,3).map((c, idx) => (
                    <li 
                      key={idx}
                      onClick={() => {
                        setSelectedCitation(c);
                        setModalOpen(true);
                      }}
                      style={{
                        cursor: c.chunk_id ? 'pointer' : 'default',
                        color: c.chunk_id ? 'var(--accent)' : 'var(--text-secondary)',
                        textDecoration: c.chunk_id ? 'underline' : 'none',
                        transition: 'all 0.2s ease',
                        padding: '0.25rem 0',
                      }}
                      onMouseEnter={(e) => {
                        if (c.chunk_id) e.currentTarget.style.opacity = '0.8';
                      }}
                      onMouseLeave={(e) => {
                        if (c.chunk_id) e.currentTarget.style.opacity = '1';
                      }}
                    >
                      {c.chunk_id && '📄 '}{c.title} (Relevance: {Math.round(c.final_score * 100)}%)
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        ))}
        
        {loading && (
          <div className="animate-slide-up" style={{ alignSelf: 'flex-start', color: 'var(--accent)' }}>
            <span className="pulse-loader" style={{ display: 'inline-block' }}>Analyzing documents via Neural Reranker...</span>
          </div>
        )}
      </div>

      <form onSubmit={handleSubmit} style={{ display: 'flex', gap: '1rem', marginTop: '1rem' }}>
        <input 
          type="text" 
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask a specific query..."
          style={{
            flex: 1,
            background: 'rgba(0,0,0,0.2)',
            border: '1px solid var(--panel-border)',
            color: 'white',
            padding: '1rem',
            borderRadius: '8px',
            outline: 'none',
            fontSize: '1rem'
          }}
        />
        <button type="submit" className="btn-primary" disabled={loading} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          Execute <Send size={16} />
        </button>
      </form>

      <CitationModal 
        citation={selectedCitation} 
        isOpen={modalOpen} 
        onClose={() => {
          setModalOpen(false);
          setSelectedCitation(null);
        }} 
      />
    </div>
  );
}
