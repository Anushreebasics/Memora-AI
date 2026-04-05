import React, { useEffect, useState } from 'react';
import { Zap, AlertTriangle, TrendingUp, Target } from 'lucide-react';
import { api } from '../api';

export default function Insights() {
  const [insights, setInsights] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchInsights = async () => {
      setLoading(true);
      try {
        const data = await api.getInsights();
        setInsights(data);
      } catch (err) {
        console.error('Failed to fetch insights', err);
      } finally {
        setLoading(false);
      }
    };
    fetchInsights();
  }, []);

  if (loading) {
    return (
      <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-secondary)' }}>
        <div className="pulse-loader">Generating deep insights...</div>
      </div>
    );
  }

  if (!insights || insights.status === 'no_data') {
    return (
      <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-secondary)' }}>
        <p>No activity to analyze yet. Ingest some documents to generate insights.</p>
      </div>
    );
  }

  return (
    <div style={{ padding: '2rem', display: 'flex', flexDirection: 'column', gap: '1.5rem', overflowY: 'auto', height: '100%' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.5rem' }}>
        <Zap size={24} color="var(--accent)" />
        <h2 style={{ margin: 0 }}>Weekly Intelligence Report</h2>
      </div>

      <div className="glass-panel" style={{ padding: '1.25rem' }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '1rem', marginBottom: '1rem' }}>
          <div style={{ background: 'rgba(56, 189, 248, 0.1)', borderRadius: '8px', padding: '0.75rem', borderLeft: '3px solid var(--accent)' }}>
            <p style={{ margin: '0 0 0.25rem 0', fontSize: '0.9rem', color: 'var(--text-secondary)' }}>Sources Ingested</p>
            <p style={{ margin: 0, fontSize: '1.4rem', fontWeight: 'bold', color: 'var(--accent)' }}>{insights.sources_count}</p>
          </div>
          <div style={{ background: 'rgba(52, 211, 153, 0.1)', borderRadius: '8px', padding: '0.75rem', borderLeft: '3px solid var(--success)' }}>
            <p style={{ margin: '0 0 0.25rem 0', fontSize: '0.9rem', color: 'var(--text-secondary)' }}>Knowledge Chunks</p>
            <p style={{ margin: 0, fontSize: '1.4rem', fontWeight: 'bold', color: 'var(--success)' }}>{insights.chunks_count}</p>
          </div>
          <div style={{ background: 'rgba(251, 191, 36, 0.1)', borderRadius: '8px', padding: '0.75rem', borderLeft: '3px solid var(--warning)' }}>
            <p style={{ margin: '0 0 0.25rem 0', fontSize: '0.9rem', color: 'var(--text-secondary)' }}>Questions Asked</p>
            <p style={{ margin: 0, fontSize: '1.4rem', fontWeight: 'bold', color: 'var(--warning)' }}>{insights.questions_count}</p>
          </div>
          <div style={{ background: 'rgba(248, 113, 113, 0.1)', borderRadius: '8px', padding: '0.75rem', borderLeft: '3px solid var(--danger)' }}>
            <p style={{ margin: '0 0 0.25rem 0', fontSize: '0.9rem', color: 'var(--text-secondary)' }}>Time Window</p>
            <p style={{ margin: 0, fontSize: '1.4rem', fontWeight: 'bold', color: 'var(--danger)' }}>{insights.period_days}d</p>
          </div>
        </div>

        <p style={{ margin: '1rem 0 0 0', color: 'var(--text-secondary)', fontSize: '0.9rem', lineHeight: '1.5' }}>
          {insights.summary}
        </p>
      </div>

      {insights.contradictions && insights.contradictions.length > 0 && (
        <div className="glass-panel" style={{ padding: '1.25rem', borderLeft: '3px solid var(--danger)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1rem' }}>
            <AlertTriangle size={20} color="var(--danger)" />
            <h3 style={{ margin: 0 }}>🚨 Contradictions Detected</h3>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            {insights.contradictions.slice(0, 4).map((c, i) => (
              <div key={i} style={{ background: 'rgba(248, 113, 113, 0.05)', padding: '0.75rem', borderRadius: '8px', borderLeft: '2px solid var(--danger)' }}>
                <p style={{ margin: '0 0 0.5rem 0', fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                  <strong style={{ color: 'var(--text-primary)' }}>{c.source_1}</strong> vs <strong style={{ color: 'var(--text-primary)' }}>{c.source_2}</strong>
                </p>
                <p style={{ margin: '0.25rem 0', fontSize: '0.9rem', color: 'var(--text-primary)', fontStyle: 'italic' }}>
                  "{c.snippet_1.substring(0, 70)}..."
                </p>
                <p style={{ margin: '0.25rem 0', fontSize: '0.9rem', color: 'var(--text-primary)', fontStyle: 'italic' }}>
                  "{c.snippet_2.substring(0, 70)}..."
                </p>
                <p style={{ margin: '0.5rem 0 0 0', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                  Conflict confidence: {Math.round((c.conflict_score || 0.5) * 100)}%
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {insights.topics && insights.topics.length > 0 && (
        <div className="glass-panel" style={{ padding: '1.25rem', borderLeft: '3px solid var(--accent)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1rem' }}>
            <TrendingUp size={20} color="var(--accent)" />
            <h3 style={{ margin: 0 }}>Dominant Topics</h3>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem' }}>
            {insights.topics.slice(0, 4).map((t, i) => (
              <div key={i} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0.5rem 0', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                <div style={{ flex: 1 }}>
                  <p style={{ margin: 0, fontSize: '0.95rem', fontWeight: '500', color: 'var(--text-primary)' }}>
                    {t.label}
                  </p>
                  <p style={{ margin: '0.25rem 0 0 0', fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                    {t.chunk_count} chunks · {t.top_source}
                  </p>
                </div>
                <div style={{ background: 'rgba(56, 189, 248, 0.2)', padding: '0.4rem 0.8rem', borderRadius: '6px', fontSize: '0.8rem', color: 'var(--accent)' }}>
                  {Math.round(t.confidence * 100)}%
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {insights.skill_gaps && insights.skill_gaps.length > 0 && (
        <div className="glass-panel" style={{ padding: '1.25rem', borderLeft: '3px solid var(--warning)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1rem' }}>
            <Target size={20} color="var(--warning)" />
            <h3 style={{ margin: 0 }}>Areas for Improvement</h3>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem' }}>
            {insights.skill_gaps.slice(0, 3).map((g, i) => (
              <div key={i} style={{ background: 'rgba(251, 191, 36, 0.05)', padding: '0.75rem', borderRadius: '8px', borderLeft: '2px solid var(--warning)' }}>
                <p style={{ margin: 0, fontSize: '0.9rem', color: 'var(--text-primary)' }}>
                  <strong>{g.insight || g.question}</strong>
                </p>
                {g.recommendation && (
                  <p style={{ margin: '0.5rem 0 0 0', fontSize: '0.85rem', color: 'var(--text-secondary)', fontStyle: 'italic' }}>
                    💡 {g.recommendation}
                  </p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {insights.top_sources && insights.top_sources.length > 0 && (
        <div className="glass-panel" style={{ padding: '1.25rem' }}>
          <h3 style={{ margin: '0 0 1rem 0' }}>📚 Key Sources</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            {insights.top_sources.map((s, i) => (
              <div key={i} style={{ display: 'flex', justifyContent: 'space-between', padding: '0.5rem 0', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                <span style={{ color: 'var(--text-primary)', fontSize: '0.95rem' }}>{s.title}</span>
                <span style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>{s.doc_type}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
