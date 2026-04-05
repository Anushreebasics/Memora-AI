import React, { useState, useEffect } from 'react';
import { Save, BrainCircuit, CheckCircle } from 'lucide-react';
import { api } from '../api';

export default function Settings() {
  const [memory, setMemory] = useState('');
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    const fetchMemory = async () => {
      try {
        const data = await api.getMemory();
        if (data && data.preferences) {
          setMemory(data.preferences);
        }
      } catch (err) {
        console.error("Failed to fetch memory", err);
      }
    };
    fetchMemory();
  }, []);

  const handleSave = async () => {
    setSaving(true);
    try {
      await api.setMemory(memory);
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (err) {
      console.error("Failed to save memory", err);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div style={{ padding: '2rem', maxWidth: '800px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '2rem' }}>
      
      <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', borderBottom: '1px solid var(--panel-border)', paddingBottom: '1rem' }}>
        <BrainCircuit size={32} color="var(--accent)" />
        <div>
          <h2 style={{ margin: 0 }}>Global Memory Requirements</h2>
          <p style={{ margin: 0, color: 'var(--text-secondary)', fontSize: '0.9rem', marginTop: '0.25rem' }}>
            Instruct the RAG Agent on strict rules and context it should remember across all conversations.
          </p>
        </div>
      </div>

      <div className="glass-panel" style={{ padding: '1.5rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        <label style={{ fontWeight: '600', color: 'var(--text-primary)' }}>System Prompt Injection</label>
        <textarea 
          value={memory}
          onChange={(e) => setMemory(e.target.value)}
          placeholder="e.g. Always answer in French. Assume I am a Senior Data Scientist. Prefer short, concise bullet points."
          rows={10}
          style={{
            width: '100%',
            background: 'rgba(0,0,0,0.3)',
            border: '1px solid var(--panel-border)',
            color: 'var(--text-primary)',
            padding: '1rem',
            borderRadius: '8px',
            fontFamily: 'inherit',
            fontSize: '0.95rem',
            lineHeight: '1.5',
            resize: 'vertical',
            outline: 'none'
          }}
        />
        
        <div style={{ display: 'flex', justifyContent: 'flex-end', alignItems: 'center', gap: '1rem', marginTop: '0.5rem' }}>
          {saved && (
            <span className="animate-slide-up" style={{ color: 'var(--success)', display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.9rem' }}>
              <CheckCircle size={16} /> Memory Persisted!
            </span>
          )}
          <button 
            onClick={handleSave} 
            disabled={saving} 
            className="btn-primary" 
            style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}
          >
            {saving ? 'Saving...' : 'Save Global Memory'} <Save size={16} />
          </button>
        </div>
      </div>
      
    </div>
  );
}
