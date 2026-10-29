'use client';

import React, { useEffect, useRef, useState } from 'react';
import { RevenueEstimationOutput } from '../../types/venture';
import { ScenarioChart } from './ScenarioChart';
import { TrendingUp, DollarSign, Calendar, Users, CheckCircle, AlertTriangle, Gauge } from 'lucide-react';

interface Props {
  data?: RevenueEstimationOutput | null;
}

export const RevenueProjectionsView: React.FC<Props> = ({ data }) => {
  const [selectedScenarioIdx, setSelectedScenarioIdx] = useState(0);
  const initializedScenarioRef = useRef(false);

  useEffect(() => {
    const scenarioList = data?.scenarios ?? [];
    if (!initializedScenarioRef.current && scenarioList.length > 0) {
      const moderateIndex = scenarioList.findIndex(
        (scenario) => scenario.scenario_name.toLowerCase() === 'moderate',
      );
      setSelectedScenarioIdx(moderateIndex >= 0 ? moderateIndex : 0);
      initializedScenarioRef.current = true;
      return;
    }
    if (scenarioList.length > 0 && selectedScenarioIdx >= scenarioList.length) {
      setSelectedScenarioIdx(0);
    }
  }, [data, selectedScenarioIdx]);

  if (!data) {
    return (
      <div className="empty-state">
        <div className="empty-state-icon">📈</div>
        <h4>No data received from agent</h4>
        <p>Revenue & deterministic financial modeling output is pending or has not yet been generated.</p>
      </div>
    );
  }

  const { parameters, scenarios, pricing_strategy, assumptions_summary, unit_economics, invariant_violations } = data;
  const activeScenario = scenarios && scenarios[selectedScenarioIdx] ? scenarios[selectedScenarioIdx] : null;
  const runwayMonths = activeScenario?.ending_runway_months;
  const runwayLabel = runwayMonths === undefined || runwayMonths === null
    ? '—'
    : runwayMonths >= 999
      ? 'Cash-flow positive'
      : `${runwayMonths.toFixed(1)} mo`;

  return (
    <div>
      {/* Pricing Strategy */}
      <div
        style={{
          background: 'var(--bg-surface)',
          border: '1px solid var(--border-subtle)',
          borderRadius: 'var(--radius-md)',
          padding: '16px',
          marginBottom: '20px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
          <DollarSign size={18} color="#10b981" />
          <h4 style={{ fontSize: '1rem', fontWeight: 700 }}>Pricing & Monetization Strategy</h4>
        </div>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.92rem', lineHeight: 1.5 }}>
          {pricing_strategy || 'Subscription / transactional pricing'}
        </p>
      </div>

      {/* Financial Parameters */}
      {parameters && (
        <div className="scores-grid">
          <div className="score-box">
            <div className="score-label">Unit / Monthly Price</div>
            <div className="score-value" style={{ color: '#10b981' }}>
              ${parameters.monthly_price ?? 0}
            </div>
          </div>
          <div className="score-box">
            <div className="score-label">Starting Customers</div>
            <div className="score-value" style={{ color: '#818cf8' }}>
              {parameters.starting_customers ?? 0}
            </div>
          </div>
          <div className="score-box">
            <div className="score-label">Monthly Growth</div>
            <div className="score-value" style={{ color: '#38bdf8' }}>
              {Math.round((parameters.monthly_growth_rate ?? 0) * 100)}%
            </div>
          </div>
          <div className="score-box">
            <div className="score-label">Monthly Churn</div>
            <div className="score-value" style={{ color: '#f87171' }}>
              {Math.round((parameters.monthly_churn_rate ?? 0) * 100)}%
            </div>
          </div>
          <div className="score-box">
            <div className="score-label">Fixed Monthly Costs</div>
            <div className="score-value" style={{ color: '#f59e0b' }}>
              ${parameters.fixed_monthly_costs ?? 0}
            </div>
          </div>
        </div>
      )}

      {/* Unit Economics & Scenario Health */}
      <div className="content-section" style={{ marginTop: '24px' }}>
        <div className="section-title">
          <Gauge size={18} color="#a855f7" />
          <span>Unit Economics & Scenario Health</span>
        </div>
        <div className="unit-econ-grid">
          <div className="unit-econ-card">
            <div className="unit-econ-label">Customer Acquisition Cost</div>
            <div className="unit-econ-value" style={{ color: '#f59e0b' }}>
              {unit_economics ? `$${Math.round(unit_economics.cac).toLocaleString()}` : '—'}
            </div>
            <div className="unit-econ-note">Blended cost to acquire one paying customer</div>
          </div>
          <div className="unit-econ-card">
            <div className="unit-econ-label">Customer Lifetime Value</div>
            <div className="unit-econ-value" style={{ color: '#38bdf8' }}>
              {unit_economics ? `$${Math.round(unit_economics.ltv).toLocaleString()}` : '—'}
            </div>
            <div className="unit-econ-note">Expected gross value over the customer lifecycle</div>
          </div>
          <div className="unit-econ-card">
            <div className="unit-econ-label">LTV : CAC</div>
            <div className="unit-econ-value" style={{ color: unit_economics && unit_economics.ltv_cac_ratio >= 3 ? '#10b981' : '#f87171' }}>
              {unit_economics ? `${unit_economics.ltv_cac_ratio.toFixed(1)}x` : '—'}
            </div>
            <div className="unit-econ-note">Healthy target is at least 3.0x</div>
          </div>
          <div className="unit-econ-card">
            <div className="unit-econ-label">CAC Payback</div>
            <div className="unit-econ-value" style={{ color: '#a855f7' }}>
              {unit_economics ? `${unit_economics.cac_payback_months.toFixed(1)} mo` : '—'}
            </div>
            <div className="unit-econ-note">Months to recover acquisition cost</div>
          </div>
          <div className="unit-econ-card">
            <div className="unit-econ-label">Active Scenario Runway</div>
            <div className="unit-econ-value" style={{ color: '#34d399' }}>
              {runwayLabel}
            </div>
            <div className="unit-econ-note">Based on the selected projection scenario</div>
          </div>
          <div className="unit-econ-card">
            <div className="unit-econ-label">Break-Even</div>
            <div className="unit-econ-value" style={{ color: activeScenario?.break_even_month ? '#10b981' : '#f59e0b' }}>
              {activeScenario?.break_even_month ? `Month ${activeScenario.break_even_month}` : 'Not reached'}
            </div>
            <div className="unit-econ-note">First month with non-positive net burn</div>
          </div>
        </div>
      </div>

      {/* Scenarios Header & Selector */}
      {scenarios && scenarios.length > 0 && (
        <div className="content-section" style={{ marginTop: '24px' }}>
          <div className="section-title">
            <TrendingUp size={18} color="#6366f1" />
            <span>Deterministic Projection Scenarios</span>
          </div>

          <div className="scenarios-grid">
            {scenarios.map((sc, idx) => {
              const isSelected = idx === selectedScenarioIdx;
              return (
                <div
                  key={idx}
                  className={`scenario-card ${isSelected ? 'moderate' : ''}`}
                  onClick={() => setSelectedScenarioIdx(idx)}
                  style={{
                    cursor: 'pointer',
                    borderColor: isSelected ? 'var(--accent-primary)' : undefined,
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                    <h5 style={{ textTransform: 'capitalize', fontSize: '1rem', color: isSelected ? '#818cf8' : 'var(--text-primary)' }}>
                      {sc.scenario_name}
                    </h5>
                    {isSelected && <CheckCircle size={16} color="#6366f1" />}
                  </div>
                  <div style={{ fontSize: '1.3rem', fontWeight: 800, color: '#10b981', marginBottom: '4px' }}>
                    ${Math.round(sc.month_12_revenue).toLocaleString()}
                    <span style={{ fontSize: '0.75rem', fontWeight: 500, color: 'var(--text-muted)' }}> /mo (Yr 1)</span>
                  </div>
                  <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', display: 'flex', gap: '12px' }}>
                    <span><Users size={13} style={{ display: 'inline', marginRight: '4px' }} />{sc.month_12_customers} Users</span>
                    <span><Calendar size={13} style={{ display: 'inline', marginRight: '4px' }} />Break-even: {sc.break_even_month ? `Mo ${sc.break_even_month}` : 'N/A'}</span>
                  </div>
                </div>
              );
            })}
          </div>

          <ScenarioChart
            scenarios={scenarios}
            selectedIndex={selectedScenarioIdx}
            onSelect={setSelectedScenarioIdx}
          />

          {/* Monthly Table for Active Scenario */}
          {activeScenario && activeScenario.monthly_projections && activeScenario.monthly_projections.length > 0 && (
            <div style={{ marginTop: '20px', overflowX: 'auto' }}>
              <h5 style={{ fontSize: '0.9rem', marginBottom: '10px', color: 'var(--text-secondary)' }}>
                Monthly Trajectory ({activeScenario.scenario_name.toUpperCase()} SCENARIO)
              </h5>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
                <thead>
                  <tr style={{ background: 'var(--bg-surface-elevated)', borderBottom: '1px solid var(--border-subtle)', textAlign: 'left' }}>
                    <th style={{ padding: '8px 12px' }}>Month</th>
                    <th style={{ padding: '8px 12px' }}>Active Customers</th>
                    <th style={{ padding: '8px 12px' }}>Revenue</th>
                    <th style={{ padding: '8px 12px' }}>Net Profit / Burn</th>
                  </tr>
                </thead>
                <tbody>
                  {activeScenario.monthly_projections.map((row: any, idx: number) => {
                    const netProfit = typeof row.net_burn === 'number'
                      ? -row.net_burn
                      : row.net_profit ?? row.profit;
                    return (
                      <tr key={idx} style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                        <td style={{ padding: '8px 12px' }}>Month {row.month || idx + 1}</td>
                        <td style={{ padding: '8px 12px' }}>{row.customers || row.users || '—'}</td>
                        <td style={{ padding: '8px 12px', color: '#34d399' }}>
                          {row.revenue ? `$${Math.round(row.revenue).toLocaleString()}` : '—'}
                        </td>
                        <td
                          style={{
                            padding: '8px 12px',
                            color: (netProfit ?? 0) >= 0 ? '#10b981' : '#f87171',
                          }}
                        >
                          {netProfit !== undefined ? `$${Math.round(netProfit).toLocaleString()}` : '—'}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {invariant_violations && invariant_violations.length > 0 && (
        <div className="invariant-warning" style={{ marginTop: '24px' }}>
          <h5>
            <AlertTriangle size={16} />
            <span>Financial Model Warnings</span>
          </h5>
          <ul>
            {invariant_violations.map((violation, idx) => (
              <li key={idx} style={{ marginBottom: '4px' }}>{violation}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Assumptions Summary */}
      {assumptions_summary && assumptions_summary.length > 0 && (
        <div className="content-section" style={{ marginTop: '24px' }}>
          <div className="section-title">
            <span>Model Invariants & Assumptions</span>
          </div>
          <ul style={{ paddingLeft: '20px', fontSize: '0.88rem', color: 'var(--text-secondary)' }}>
            {assumptions_summary.map((assump, idx) => (
              <li key={idx} style={{ marginBottom: '4px' }}>
                {assump}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};
