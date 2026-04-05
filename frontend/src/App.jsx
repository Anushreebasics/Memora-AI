import React, { useState } from 'react';
import Sidebar from './components/Sidebar';
import Chat from './components/Chat';
import UploadZone from './components/UploadZone';
import Settings from './components/Settings';
import KnowledgeGraph from './components/KnowledgeGraph';
import Insights from './components/Insights';

export default function App() {
  const [activeTab, setActiveTab] = useState('chat');

  return (
    <div className="app-container">
      <Sidebar activeTab={activeTab} setActiveTab={setActiveTab} />
      
      <main className="main-content glass-panel" style={{ margin: '1rem', flex: 1 }}>
        {activeTab === 'chat' && <Chat />}
        {activeTab === 'sources' && (
          <div style={{ padding: '2rem', height: '100%', display: 'flex', flexDirection: 'column', gap: '1.25rem', overflowY: 'auto' }}>
            <h2 style={{ marginBottom: '0.25rem' }}>Data Sources and Entity Network</h2>
            <KnowledgeGraph />
            <div style={{ display: 'flex', justifyContent: 'center', paddingBottom: '1rem' }}>
              <UploadZone />
            </div>
          </div>
        )}
        {activeTab === 'settings' && <Settings />}
        {activeTab === 'insights' && <Insights />}
      </main>
    </div>
  );
}
