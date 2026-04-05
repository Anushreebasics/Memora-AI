import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Network, RefreshCw } from 'lucide-react';
import { api } from '../api';

const palette = ['#38bdf8', '#34d399', '#fbbf24', '#f87171', '#a78bfa', '#fb7185', '#22d3ee'];

function colorForNode(id) {
  let hash = 0;
  for (let i = 0; i < id.length; i += 1) {
    hash = ((hash << 5) - hash) + id.charCodeAt(i);
    hash |= 0;
  }
  return palette[Math.abs(hash) % palette.length];
}

export default function KnowledgeGraph() {
  const canvasRef = useRef(null);
  const [triplets, setTriplets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [stats, setStats] = useState({ nodes: 0, edges: 0 });

  const fetchGraph = async () => {
    setLoading(true);
    setError('');
    try {
      const data = await api.getGraphTriplets(1000);
      const tripletsList = data.triplets || [];
      setTriplets(tripletsList);
      
      // Calculate stats
      const nodeSet = new Set();
      tripletsList.forEach(t => {
        if (t.subject) nodeSet.add(t.subject);
        if (t.object_node) nodeSet.add(t.object_node);
      });
      setStats({ nodes: nodeSet.size, edges: tripletsList.length });
    } catch (err) {
      console.error('Failed to fetch graph:', err);
      setError('Unable to load graph data from backend.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchGraph();
  }, []);

  useEffect(() => {
    if (triplets.length === 0 || !canvasRef.current) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Simple grid visualization
    const nodeMap = new Map();
    const nodes = [];
    
    triplets.forEach(t => {
      if (!nodeMap.has(t.subject)) {
        nodeMap.set(t.subject, {
          id: t.subject,
          x: Math.random() * (canvas.width - 100) + 50,
          y: Math.random() * (canvas.height - 100) + 50,
          color: colorForNode(t.subject),
        });
        nodes.push(nodeMap.get(t.subject));
      }
      if (!nodeMap.has(t.object_node)) {
        nodeMap.set(t.object_node, {
          id: t.object_node,
          x: Math.random() * (canvas.width - 100) + 50,
          y: Math.random() * (canvas.height - 100) + 50,
          color: colorForNode(t.object_node),
        });
        nodes.push(nodeMap.get(t.object_node));
      }
    });

    // Draw
    ctx.fillStyle = 'rgba(11, 15, 25, 0.8)';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // Draw edges
    ctx.strokeStyle = 'rgba(148, 163, 184, 0.3)';
    ctx.lineWidth = 1;
    triplets.forEach(t => {
      const s = nodeMap.get(t.subject);
      const o = nodeMap.get(t.object_node);
      if (s && o) {
        ctx.beginPath();
        ctx.moveTo(s.x, s.y);
        ctx.lineTo(o.x, o.y);
        ctx.stroke();
      }
    });

    // Draw nodes
    nodes.forEach(node => {
      ctx.fillStyle = node.color;
      ctx.beginPath();
      ctx.arc(node.x, node.y, 6, 0, Math.PI * 2);
      ctx.fill();
      
      // Draw label
      ctx.fillStyle = '#e2e8f0';
      ctx.font = '10px Inter, sans-serif';
      ctx.textAlign = 'left';
      ctx.fillText(node.id.substring(0, 15), node.x + 10, node.y);
    });
  }, [triplets]);

  return (
    <div className="glass-panel" style={{ padding: '1rem', height: '460px', display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '1rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
          <Network size={20} color="var(--accent)" />
          <h3 style={{ margin: 0 }}>Interactive Knowledge Graph</h3>
        </div>
        <button onClick={fetchGraph} className="btn-outline" style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
          <RefreshCw size={14} /> Refresh
        </button>
      </div>

      <div style={{ display: 'flex', gap: '0.75rem', color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
        <span>Nodes: <strong style={{ color: 'var(--text-primary)' }}>{stats.nodes}</strong></span>
        <span>Relationships: <strong style={{ color: 'var(--text-primary)' }}>{stats.edges}</strong></span>
      </div>

      <div style={{ flex: 1, borderRadius: '12px', border: '1px solid var(--panel-border)', overflow: 'hidden', position: 'relative', background: 'radial-gradient(circle at 35% 20%, rgba(56,189,248,0.09), rgba(10,15,25,0.96) 65%)' }}>
        {!loading && !error && triplets.length > 0 && (
          <canvas
            ref={canvasRef}
            width={600}
            height={400}
            style={{ width: '100%', height: '100%', display: 'block' }}
          />
        )}

        {loading && (
          <div style={{ position: 'absolute', inset: 0, display: 'grid', placeItems: 'center', color: 'var(--accent)' }}>
            Building graph topology...
          </div>
        )}

        {!loading && error && (
          <div style={{ position: 'absolute', inset: 0, display: 'grid', placeItems: 'center', color: 'var(--danger)' }}>
            {error}
          </div>
        )}

        {!loading && !error && triplets.length === 0 && (
          <div style={{ position: 'absolute', inset: 0, display: 'grid', placeItems: 'center', color: 'var(--text-secondary)', textAlign: 'center', padding: '1rem' }}>
            No graph relationships found yet. Ingest files or URLs first to extract triplets.
          </div>
        )}
      </div>

      <div style={{ minHeight: '52px', color: 'var(--text-secondary)', fontSize: '0.88rem' }}>
        Tip: Graph shows entity relationships extracted from your documents.
      </div>
    </div>
  );
}
