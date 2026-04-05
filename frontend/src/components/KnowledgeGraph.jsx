import React, { useEffect, useMemo, useRef, useState } from 'react';
import { ForceGraph2D } from 'react-force-graph';
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

function toGraphData(triplets) {
  const nodeMap = new Map();
  const links = [];

  triplets.forEach((t) => {
    const source = String(t.subject || '').trim();
    const target = String(t.object_node || '').trim();
    const label = String(t.predicate || '').trim() || 'related_to';

    if (!source || !target) return;

    if (!nodeMap.has(source)) {
      nodeMap.set(source, {
        id: source,
        val: 1,
        degree: 0,
        color: colorForNode(source),
      });
    }
    if (!nodeMap.has(target)) {
      nodeMap.set(target, {
        id: target,
        val: 1,
        degree: 0,
        color: colorForNode(target),
      });
    }

    const s = nodeMap.get(source);
    const d = nodeMap.get(target);
    s.degree += 1;
    d.degree += 1;

    links.push({
      source,
      target,
      label,
      sourceTitle: t.source_title || 'Unknown source',
      sourcePath: t.source_path || '',
    });
  });

  const nodes = Array.from(nodeMap.values()).map((node) => ({
    ...node,
    val: Math.max(2, Math.min(14, 2 + Math.log2(node.degree + 1) * 3)),
  }));

  return { nodes, links };
}

export default function KnowledgeGraph() {
  const graphRef = useRef(null);
  const [triplets, setTriplets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [activeNode, setActiveNode] = useState(null);

  const graphData = useMemo(() => toGraphData(triplets), [triplets]);

  const fetchGraph = async () => {
    setLoading(true);
    setError('');
    try {
      const data = await api.getGraphTriplets(2500);
      setTriplets(data.triplets || []);
    } catch {
      setError('Unable to load graph data from backend.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchGraph();
  }, []);

  const stats = useMemo(() => ({
    nodes: graphData.nodes.length,
    edges: graphData.links.length,
  }), [graphData]);

  const handleNodeClick = (node) => {
    setActiveNode(node);
    if (graphRef.current && node) {
      const distance = 120;
      const distRatio = 1 + distance / Math.hypot(node.x || 1, node.y || 1);
      graphRef.current.centerAt((node.x || 0) * distRatio, (node.y || 0) * distRatio, 800);
      graphRef.current.zoom(2.4, 800);
    }
  };

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
        {!loading && !error && graphData.nodes.length > 0 && (
          <ForceGraph2D
            ref={graphRef}
            graphData={graphData}
            nodeRelSize={4}
            cooldownTicks={80}
            d3VelocityDecay={0.28}
            linkDirectionalParticles={1}
            linkDirectionalParticleSpeed={0.0035}
            linkColor={() => 'rgba(148, 163, 184, 0.35)'}
            nodeCanvasObject={(node, ctx, globalScale) => {
              const label = node.id;
              const fontSize = 12 / globalScale;
              ctx.beginPath();
              ctx.fillStyle = node.color;
              ctx.arc(node.x, node.y, node.val, 0, 2 * Math.PI, false);
              ctx.fill();

              if (globalScale >= 1.6 || activeNode?.id === node.id) {
                ctx.font = `${fontSize}px Inter, sans-serif`;
                ctx.textAlign = 'left';
                ctx.textBaseline = 'middle';
                ctx.fillStyle = 'rgba(226, 232, 240, 0.95)';
                ctx.fillText(label, node.x + node.val + 2, node.y);
              }
            }}
            nodePointerAreaPaint={(node, color, ctx) => {
              ctx.fillStyle = color;
              ctx.beginPath();
              ctx.arc(node.x, node.y, Math.max(8, node.val + 2), 0, 2 * Math.PI, false);
              ctx.fill();
            }}
            onNodeClick={handleNodeClick}
            onNodeHover={(node) => setActiveNode(node || null)}
            linkLabel={(link) => `${link.source.id || link.source} - ${link.label} -> ${link.target.id || link.target}`}
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

        {!loading && !error && graphData.nodes.length === 0 && (
          <div style={{ position: 'absolute', inset: 0, display: 'grid', placeItems: 'center', color: 'var(--text-secondary)', textAlign: 'center', padding: '1rem' }}>
            No graph relationships found yet. Ingest files or URLs first to extract triplets.
          </div>
        )}
      </div>

      <div style={{ minHeight: '52px', color: 'var(--text-secondary)', fontSize: '0.88rem' }}>
        {activeNode ? `Focused node: ${activeNode.id}` : 'Tip: Click a node to zoom and inspect its local neighborhood.'}
      </div>
    </div>
  );
}
