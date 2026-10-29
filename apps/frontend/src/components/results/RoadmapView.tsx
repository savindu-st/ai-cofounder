'use client';

import React, { useState } from 'react';
import { StartupRoadmap } from '../../types/venture';
import { downloadAndSaveVentureExport, ExportFormat } from '../../services/api';
import {
  Award,
  ShieldAlert,
  FileText,
  Download,
  Loader2,
  AlertCircle,
  Rocket,
} from 'lucide-react';

interface Props {
  data?: StartupRoadmap | null;
}

export const RoadmapView: React.FC<Props> = ({ data }) => {
  const [downloading, setDownloading] = useState<ExportFormat | null>(null);
  const [downloadError, setDownloadError] = useState<string | null>(null);

  if (!data) {
    return (
      <div className="empty-state">
        <div className="empty-state-icon">🏁</div>
        <h4>No data received from agent</h4>
        <p>The Final Executive Roadmap has not yet been compiled by the orchestrator.</p>
      </div>
    );
  }

  const handleDownload = async (format: ExportFormat) => {
    setDownloading(format);
    setDownloadError(null);
    try {
      await downloadAndSaveVentureExport(data.venture_id, format);
    } catch (err: any) {
      setDownloadError(err.message || `Failed to download ${format.toUpperCase()} report.`);
    } finally {
      setDownloading(null);
    }
  };

  return (
    <div>
      {/* Executive Summary Card */}
      <div
        style={{
          background: 'linear-gradient(135deg, rgba(99, 102, 241, 0.14) 0%, rgba(168, 85, 247, 0.08) 100%)',
          border: '1px solid var(--border-highlight)',
          borderRadius: 'var(--radius-lg)',
          padding: '24px',
          marginBottom: '24px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '12px', flexWrap: 'wrap', marginBottom: '12px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <Award size={22} color="#818cf8" />
            <h3 style={{ fontSize: '1.25rem', fontWeight: 800, color: 'var(--text-primary)' }}>
              Executive Advisory Roadmap
            </h3>
          </div>
          {typeof data.overall_confidence_score === 'number' && (
            <span className="status-badge completed">
              Overall Viability: {Math.round(data.overall_confidence_score * 100)}%
            </span>
          )}
        </div>

        <p style={{ color: 'var(--text-primary)', fontSize: '0.98rem', lineHeight: 1.65 }}>
          {data.executive_summary}
        </p>
      </div>

      {/* Export Actions */}
      <div className="roadmap-export-bar">
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontWeight: 700, fontSize: '0.95rem' }}>
            <Download size={17} color="#818cf8" />
            <span>Export Founder-Ready Documents</span>
          </div>
          <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '3px' }}>
            Download the complete roadmap for pitch decks, grant applications, or investor follow-ups.
          </p>
        </div>
        <div className="roadmap-export-actions">
          <button
            type="button"
            className="export-btn primary"
            onClick={() => handleDownload('pdf')}
            disabled={downloading !== null}
          >
            {downloading === 'pdf' ? <Loader2 size={15} className="spin" /> : <FileText size={15} />}
            <span>{downloading === 'pdf' ? 'Preparing PDF...' : 'Download PDF Report'}</span>
          </button>
          <button
            type="button"
            className="export-btn"
            onClick={() => handleDownload('docx')}
            disabled={downloading !== null}
          >
            {downloading === 'docx' ? <Loader2 size={15} className="spin" /> : <FileText size={15} />}
            <span>{downloading === 'docx' ? 'Preparing Word...' : 'Download Word Roadmap'}</span>
          </button>
        </div>
      </div>

      {downloadError && (
        <div className="export-error" role="alert">
          <AlertCircle size={16} />
          <span>{downloadError}</span>
        </div>
      )}

      {/* Synthesis Snapshot Across All Agents */}
      <div className="content-section">
        <div className="section-title">
          <FileText size={18} color="#6366f1" />
          <span>Strategic Synthesis Snapshot</span>
        </div>

        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
            gap: '16px',
            marginTop: '12px',
          }}
        >
          {data.idea_analysis && (
            <div className="feature-card" style={{ padding: '18px' }}>
              <div style={{ fontSize: '0.8rem', color: '#818cf8', fontWeight: 700, textTransform: 'uppercase', marginBottom: '6px' }}>
                1. Core Value Proposition
              </div>
              <p style={{ fontSize: '0.88rem', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                {data.idea_analysis.refined_value_proposition}
              </p>
            </div>
          )}

          {data.market_research && (
            <div className="feature-card" style={{ padding: '18px' }}>
              <div style={{ fontSize: '0.8rem', color: '#34d399', fontWeight: 700, textTransform: 'uppercase', marginBottom: '6px' }}>
                2. Market Landscape
              </div>
              <p style={{ fontSize: '0.88rem', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                {data.market_research.competitor_landscape?.length || 0} competitors analyzed. Top trends:{' '}
                {data.market_research.market_trends?.slice(0, 2).join(', ') || 'Emerging market sector.'}
              </p>
            </div>
          )}

          {data.revenue_estimation && (
            <div className="feature-card" style={{ padding: '18px' }}>
              <div style={{ fontSize: '0.8rem', color: '#f59e0b', fontWeight: 700, textTransform: 'uppercase', marginBottom: '6px' }}>
                3. Financial Trajectory
              </div>
              <p style={{ fontSize: '0.88rem', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                Pricing: {data.revenue_estimation.pricing_strategy}. Moderate Yr 1 MRR:{' '}
                ${Math.round(data.revenue_estimation.scenarios?.[1]?.month_12_revenue || data.revenue_estimation.scenarios?.[0]?.month_12_revenue || 0).toLocaleString()}
              </p>
            </div>
          )}

          {data.marketing_plan && (
            <div className="feature-card" style={{ padding: '18px' }}>
              <div style={{ fontSize: '0.8rem', color: '#ec4899', fontWeight: 700, textTransform: 'uppercase', marginBottom: '6px' }}>
                4. Primary GTM Channels
              </div>
              <p style={{ fontSize: '0.88rem', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                {data.marketing_plan.priority_channels?.join(', ') || 'Direct founder outreach & organic search.'}
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Four Gated Execution Phases */}
      {data.execution_phases && data.execution_phases.length > 0 && (
        <div className="content-section" style={{ marginTop: '28px' }}>
          <div className="section-title">
            <Rocket size={18} color="#38bdf8" />
            <span>Gated Execution Roadmap</span>
          </div>
          <div className="phase-grid">
            {data.execution_phases.map((phase) => (
              <article key={`${phase.phase_number}-${phase.name}`} className="phase-card">
                <div className="phase-card-number">
                  Phase {phase.phase_number} · {phase.duration_weeks} weeks
                </div>
                <h5>{phase.name}</h5>
                <p className="phase-card-focus">{phase.focus}</p>

                {phase.key_milestones.length > 0 && (
                  <>
                    <h6>Key Milestones</h6>
                    <ul>
                      {phase.key_milestones.map((milestone, index) => (
                        <li key={index}>{milestone}</li>
                      ))}
                    </ul>
                  </>
                )}

                {phase.success_metrics.length > 0 && (
                  <>
                    <h6>Success Metrics</h6>
                    <ul>
                      {phase.success_metrics.map((metric, index) => (
                        <li key={index}>{metric}</li>
                      ))}
                    </ul>
                  </>
                )}
              </article>
            ))}
          </div>
        </div>
      )}

      {/* Top Cross-Functional Risks */}
      {data.top_risks && data.top_risks.length > 0 && (
        <div className="content-section" style={{ marginTop: '28px' }}>
          <div className="section-title">
            <ShieldAlert size={18} color="#f59e0b" />
            <span>Top Cross-Functional Risks & Mitigations</span>
          </div>
          <div className="risk-grid">
            {data.top_risks.map((risk, index) => (
              <article key={`${risk.category}-${index}`} className="risk-card">
                <div className="risk-card-header">
                  <span className="risk-category">{risk.category}</span>
                  <span className="risk-severity">
                    <span>Likelihood: {risk.likelihood}</span>
                    <span>·</span>
                    <span>Impact: {risk.impact}</span>
                  </span>
                </div>
                <h5>{risk.risk}</h5>
                <p className="risk-mitigation">
                  <strong>Mitigation: </strong>
                  {risk.mitigation}
                </p>
              </article>
            ))}
          </div>
        </div>
      )}

      {/* Advisory Disclaimer */}
      <div
        style={{
          marginTop: '32px',
          borderTop: '1px solid var(--border-subtle)',
          paddingTop: '16px',
          fontSize: '0.8rem',
          color: 'var(--text-muted)',
          lineHeight: 1.5,
        }}
      >
        <span style={{ fontWeight: 600 }}>Notice: </span>
        {data.disclaimer ||
          'This document is an AI-generated decision-support roadmap and does not constitute formal legal, tax, or investment advice.'}
      </div>
    </div>
  );
};
