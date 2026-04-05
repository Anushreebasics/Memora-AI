import React from 'react';
import { MessageSquare, Database, Settings, Zap } from 'lucide-react';

export default function Sidebar({ activeTab, setActiveTab }) {
  return (
    <div className="glass-panel" style={{ width: '260px', margin: '0 1rem 0 0', display: 'flex', flexDirection: 'column', padding: '1rem' }}>
      <h2 style={{ marginBottom: '2rem', paddingLeft: '0.5rem', color: 'var(--accent)' }}>Memora AI</h2>
      
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
        <button 
          onClick={() => setActiveTab('chat')}
          style={{ 
            display: 'flex', alignItems: 'center', gap: '0.75rem', padding: '0.75rem',
            borderRadius: '8px',
            color: activeTab === 'chat' ? '#fff' : 'var(--text-secondary)',
            background: activeTab === 'chat' ? 'rgba(255, 255, 255, 0.1)' : 'transparent',
            textAlign: 'left'
          }}>
          <MessageSquare size={18} /> Chat Assistant
        </button>

        <button 
          onClick={() => setActiveTab('sources')}
          style={{ 
            display: 'flex', alignItems: 'center', gap: '0.75rem', padding: '0.75rem',
            borderRadius: '8px',
            color: activeTab === 'sources' ? '#fff' : 'var(--text-secondary)',
            background: activeTab === 'sources' ? 'rgba(255, 255, 255, 0.1)' : 'transparent',
            textAlign: 'left'
          }}>
          <Database size={18} /> Data Sources
        </button>

        <button 
          onClick={() => setActiveTab('insights')}
          style={{ 
            display: 'flex', alignItems: 'center', gap: '0.75rem', padding: '0.75rem',
            borderRadius: '8px',
            color: activeTab === 'insights' ? '#fff' : 'var(--text-secondary)',
            background: activeTab === 'insights' ? 'rgba(255, 255, 255, 0.1)' : 'transparent',
            textAlign: 'left'
          }}>
          <Zap size={18} /> Weekly Insights
        </button>

        <button 
          onClick={() => setActiveTab('settings')}
          style={{ 
            display: 'flex', alignItems: 'center', gap: '0.75rem', padding: '0.75rem',
            borderRadius: '8px',
            color: activeTab === 'settings' ? '#fff' : 'var(--text-secondary)',
            background: activeTab === 'settings' ? 'rgba(255, 255, 255, 0.1)' : 'transparent',
            textAlign: 'left',
            marginTop: 'auto'
          }}>
          <Settings size={18} /> Global Memory
        </button>
      </div>
    </div>
  );
}
