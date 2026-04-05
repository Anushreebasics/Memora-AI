import React, { useEffect, useState } from 'react';
import { X, Download, Copy, CheckCircle } from 'lucide-react';
import { api } from '../api';

export default function CitationModal({ citation, isOpen, onClose }) {
  const [chunk, setChunk] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!isOpen || !citation || !citation.chunk_id) return;

    let mounted = true;

    const loadChunk = async () => {
      try {
        const data = await api.getChunk(citation.chunk_id);
        if (mounted) {
          setChunk(data);
        }
      } catch (err) {
        console.error('Failed to fetch chunk', err);
        if (mounted) {
          setError('Unable to load source text.');
        }
      } finally {
        if (mounted) {
          setLoading(false);
        }
      }
    };

    setLoading(true);
    setError('');
    loadChunk();

    return () => {
      mounted = false;
    };
  }, [isOpen, citation]);

  if (!isOpen) return null;

  const handleCopy = () => {
    if (chunk?.chunk_text) {
      navigator.clipboard.writeText(chunk.chunk_text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleExport = () => {
    if (chunk) {
      const content = `Source: ${chunk.title || 'Unknown'}\nDocument Type: ${chunk.doc_type || 'unknown'}\nTrust Level: ${chunk.trust_level || 'unknown'}\nIngested: ${chunk.created_at || 'unknown'}\n\n---\n\n${chunk.chunk_text}`;
      const blob = new Blob([content], { type: 'text/plain' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `citation_${citation.chunk_index || 0}.txt`;
      a.click();
      URL.revokeObjectURL(url);
    }
  };

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(0, 0, 0, 0.7)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 1000,
        padding: '1rem',
      }}
      onClick={onClose}
    >
      <div
        className="glass-panel"
        style={{
          maxWidth: '700px',
          width: '100%',
          maxHeight: '80vh',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '1.5rem 1.5rem 0 1.5rem' }}>
          <div>
            <h3 style={{ margin: 0, color: 'var(--accent)' }}>{citation.title}</h3>
            <p style={{ margin: '0.25rem 0 0 0', fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
              Chunk #{citation.chunk_index} • Relevance: {Math.round((citation.final_score || 0) * 100)}%
            </p>
          </div>
          <button
            onClick={onClose}
            style={{
              background: 'transparent',
              border: 'none',
              cursor: 'pointer',
              color: 'var(--text-secondary)',
              padding: '0.5rem',
              display: 'flex',
              alignItems: 'center',
            }}
          >
            <X size={24} />
          </button>
        </div>

        <div style={{ flex: 1, overflowY: 'auto', padding: '1.5rem', borderTop: '1px solid var(--panel-border)', margin: '1rem 0 0 0' }}>
          {loading && <p style={{ color: 'var(--accent)', textAlign: 'center' }}>Loading source text...</p>}

          {error && <p style={{ color: 'var(--danger)', textAlign: 'center' }}>{error}</p>}

          {chunk && !loading && (
            <div>
              <div style={{ background: 'rgba(56, 189, 248, 0.08)', border: '1px solid rgba(56, 189, 248, 0.2)', padding: '1rem', borderRadius: '8px', marginBottom: '1rem' }}>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '0.75rem', fontSize: '0.9rem' }}>
                  <div>
                    <p style={{ margin: 0, color: 'var(--text-secondary)' }}>Source</p>
                    <p style={{ margin: '0.25rem 0 0 0', color: 'var(--text-primary)', fontWeight: '500' }}>{chunk.path || chunk.title}</p>
                  </div>
                  <div>
                    <p style={{ margin: 0, color: 'var(--text-secondary)' }}>Type</p>
                    <p style={{ margin: '0.25rem 0 0 0', color: 'var(--text-primary)', fontWeight: '500' }}>{chunk.doc_type || 'document'}</p>
                  </div>
                  <div>
                    <p style={{ margin: 0, color: 'var(--text-secondary)' }}>Trust Level</p>
                    <p style={{ margin: '0.25rem 0 0 0', color: 'var(--text-primary)', fontWeight: '500' }}>
                      {chunk.trust_level === 'high' ? '✓ High' : chunk.trust_level === 'medium' ? '◐ Medium' : '○ Low'}
                    </p>
                  </div>
                  <div>
                    <p style={{ margin: 0, color: 'var(--text-secondary)' }}>Ingested</p>
                    <p style={{ margin: '0.25rem 0 0 0', color: 'var(--text-primary)', fontWeight: '500' }}>
                      {new Date(chunk.created_at).toLocaleDateString()}
                    </p>
                  </div>
                </div>
              </div>

              <div style={{ background: 'rgba(255, 255, 255, 0.02)', border: '1px solid var(--panel-border)', padding: '1rem', borderRadius: '8px', lineHeight: '1.7', color: 'var(--text-primary)' }}>
                <p style={{ margin: 0, whiteSpace: 'pre-wrap', wordWrap: 'break-word' }}>{chunk.chunk_text}</p>
              </div>
            </div>
          )}
        </div>

        <div style={{ display: 'flex', gap: '0.75rem', padding: '1.5rem', borderTop: '1px solid var(--panel-border)' }}>
          <button
            onClick={handleCopy}
            style={{
              flex: 1,
              background: copied ? 'rgba(52, 211, 153, 0.1)' : 'rgba(56, 189, 248, 0.1)',
              border: `1px solid ${copied ? 'var(--success)' : 'var(--accent)'}`,
              color: copied ? 'var(--success)' : 'var(--accent)',
              padding: '0.75rem',
              borderRadius: '8px',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '0.5rem',
              fontSize: '0.9rem',
              fontWeight: '500',
              transition: 'all 0.2s ease',
            }}
          >
            {copied ? <CheckCircle size={16} /> : <Copy size={16} />}
            {copied ? 'Copied' : 'Copy Text'}
          </button>
          <button
            onClick={handleExport}
            style={{
              flex: 1,
              background: 'rgba(251, 191, 36, 0.1)',
              border: '1px solid var(--warning)',
              color: 'var(--warning)',
              padding: '0.75rem',
              borderRadius: '8px',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '0.5rem',
              fontSize: '0.9rem',
              fontWeight: '500',
              transition: 'all 0.2s ease',
            }}
          >
            <Download size={16} />
            Export
          </button>
          <button
            onClick={onClose}
            style={{
              flex: 1,
              background: 'transparent',
              border: '1px solid var(--panel-border)',
              color: 'var(--text-secondary)',
              padding: '0.75rem',
              borderRadius: '8px',
              cursor: 'pointer',
              fontSize: '0.9rem',
              fontWeight: '500',
              transition: 'all 0.2s ease',
            }}
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
