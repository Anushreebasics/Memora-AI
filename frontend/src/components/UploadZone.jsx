import React, { useState, useRef } from 'react';
import { UploadCloud, File, CheckCircle, AlertTriangle } from 'lucide-react';
import { api } from '../api';

export default function UploadZone() {
  const [dragActive, setDragActive] = useState(false);
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [urlValue, setUrlValue] = useState('');
  const [urlIngesting, setUrlIngesting] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState(null);
  const inputRef = useRef(null);

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setSelectedFiles(prev => [...prev, ...Array.from(e.dataTransfer.files)]);
      setResult(null);
    }
  };

  const handleChange = (e) => {
    e.preventDefault();
    if (e.target.files && e.target.files[0]) {
      setSelectedFiles(prev => [...prev, ...Array.from(e.target.files)]);
      setResult(null);
    }
  };

  const onUpload = async () => {
    if (selectedFiles.length === 0) return;
    setUploading(true);
    setResult(null);
    try {
      const res = await api.uploadFiles(selectedFiles);
      setResult({ type: 'success', message: `Successfully ingested ${selectedFiles.length} files into the Knowledge Graph.` });
      setSelectedFiles([]);
    } catch (err) {
      setResult({ type: 'error', message: 'Failed to upload files. Check backend connection.' });
    } finally {
      setUploading(false);
    }
  };

  const onIngestUrl = async () => {
    if (!urlValue.trim()) return;
    setUrlIngesting(true);
    setResult(null);

    try {
      const res = await api.ingestUrl(urlValue.trim());
      if (res.status === 'ingested') {
        setResult({ type: 'success', message: `Ingested webpage with ${res.chunks_added} chunks.` });
      } else if (res.status === 'unchanged') {
        setResult({ type: 'success', message: 'This URL is already up to date in your knowledge base.' });
      } else {
        setResult({ type: 'error', message: `Unable to ingest URL (${res.status}).` });
      }
      setUrlValue('');
    } catch (err) {
      setResult({ type: 'error', message: 'Failed to ingest URL. Check backend connection and URL accessibility.' });
    } finally {
      setUrlIngesting(false);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem', width: '100%', maxWidth: '600px' }}>
      
      <div 
        className="glass-panel"
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
        onClick={() => inputRef.current.click()}
        style={{
          padding: '3rem 2rem',
          textAlign: 'center',
          border: `2px dashed ${dragActive ? 'var(--accent)' : 'var(--panel-border)'}`,
          background: dragActive ? 'rgba(56, 189, 248, 0.05)' : 'var(--panel-bg)',
          cursor: 'pointer',
          borderRadius: '16px',
          transition: 'all 0.2s ease',
        }}
      >
        <input 
          ref={inputRef} 
          type="file" 
          multiple 
          onChange={handleChange} 
          style={{ display: 'none' }} 
        />
        
        <UploadCloud size={48} color={dragActive ? 'var(--accent)' : 'var(--text-secondary)'} style={{ margin: '0 auto 1rem' }} />
        <h3 style={{ marginBottom: '0.5rem' }}>Drag & Drop your knowledge files here</h3>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>Supports PDF, TXT, MD, DOCX, and CSV formats</p>
      </div>

      <div className="glass-panel" style={{ padding: '1.25rem' }}>
        <h4 style={{ marginBottom: '0.75rem' }}>Paste URL for Live Web Scraping</h4>
        <p style={{ color: 'var(--text-secondary)', marginBottom: '0.75rem', fontSize: '0.9rem' }}>
          Add public docs pages like Wikipedia, API docs, or public Notion links.
        </p>
        <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
          <input
            type="url"
            value={urlValue}
            onChange={(e) => setUrlValue(e.target.value)}
            placeholder="https://example.com/docs/page"
            style={{
              flex: '1 1 360px',
              minWidth: '220px',
              padding: '0.7rem 0.85rem',
              borderRadius: '10px',
              border: '1px solid var(--panel-border)',
              background: 'var(--panel-bg)',
              color: 'var(--text-primary)',
            }}
          />
          <button
            onClick={onIngestUrl}
            disabled={urlIngesting || !urlValue.trim()}
            className="btn-primary"
            style={{ whiteSpace: 'nowrap' }}
          >
            {urlIngesting ? 'Scraping...' : 'Ingest URL'}
          </button>
        </div>
      </div>

      {selectedFiles.length > 0 && (
        <div className="glass-panel animate-slide-up" style={{ padding: '1.5rem' }}>
          <h4 style={{ marginBottom: '1rem', display: 'flex', justifyContent: 'space-between' }}>
            Ready to Process:
            <span style={{ color: 'var(--accent)' }}>{selectedFiles.length} Files</span>
          </h4>
          <ul style={{ listStyle: 'none', padding: 0, margin: '0 0 1.5rem 0', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            {selectedFiles.map((f, i) => (
              <li key={i} style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', fontSize: '0.9rem', color: 'var(--text-secondary)' }}>
                <File size={16} /> {f.name}
              </li>
            ))}
          </ul>
          <button 
            onClick={onUpload} 
            disabled={uploading} 
            className="btn-primary" 
            style={{ width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem' }}
          >
            {uploading ? (
              <span className="pulse-loader">Extracting Knowledge Graph Entities...</span>
            ) : (
              'Ingest into Database'
            )}
          </button>
        </div>
      )}

      {result && (
        <div className="animate-slide-up" style={{ 
          padding: '1rem', 
          borderRadius: '8px', 
          display: 'flex', 
          alignItems: 'center', 
          gap: '0.75rem',
          background: result.type === 'success' ? 'rgba(52, 211, 153, 0.1)' : 'rgba(248, 113, 113, 0.1)',
          border: `1px solid ${result.type === 'success' ? 'var(--success)' : 'var(--danger)'}`,
          color: result.type === 'success' ? 'var(--success)' : 'var(--danger)'
        }}>
          {result.type === 'success' ? <CheckCircle size={20} /> : <AlertTriangle size={20} />}
          {result.message}
        </div>
      )}

    </div>
  );
}
