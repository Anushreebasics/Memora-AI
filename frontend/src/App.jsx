import React, { useState, Suspense, lazy } from 'react';
import Sidebar from './components/Sidebar';
import Chat from './components/Chat';
import UploadZone from './components/UploadZone';
import Settings from './components/Settings';
import Insights from './components/Insights';

const KnowledgeGraph = lazy(() => import('./components/KnowledgeGraph'));

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('App error:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{ padding: '2rem', color: 'red', fontFamily: 'monospace' }}>
          <h1>React Error</h1>
          <pre>{this.state.error?.toString()}</pre>
          <p>Check browser console for details.</p>
        </div>
      );
    }

    return this.props.children;
  }
}

export default function App() {
  const [activeTab, setActiveTab] = useState('chat');

  console.log('App component rendering, activeTab:', activeTab);

  return (
    <ErrorBoundary>
      <div className="app-container" style={{ backgroundColor: 'var(--bg-color)' }}>
        <Sidebar activeTab={activeTab} setActiveTab={setActiveTab} />
        
        <main className="main-content glass-panel" style={{ margin: '1rem', flex: 1 }}>
          {activeTab === 'chat' && <Chat />}
          {activeTab === 'sources' && (
            <div style={{ padding: '2rem', height: '100%', display: 'flex', flexDirection: 'column', gap: '1.25rem', overflowY: 'auto' }}>
              <h2 style={{ marginBottom: '0.25rem' }}>Data Sources and Entity Network</h2>
              <Suspense fallback={<div style={{ color: 'var(--text-secondary)' }}>Loading knowledge graph...</div>}>
                <KnowledgeGraph />
              </Suspense>
              <div style={{ display: 'flex', justifyContent: 'center', paddingBottom: '1rem' }}>
                <UploadZone />
              </div>
            </div>
          )}
          {activeTab === 'settings' && <Settings />}
          {activeTab === 'insights' && <Insights />}
        </main>
      </div>
    </ErrorBoundary>
  );
}
