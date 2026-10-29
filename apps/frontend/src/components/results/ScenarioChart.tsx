'use client';

import React, { useMemo, useState } from 'react';
import { BarChart3 } from 'lucide-react';
import { ProjectionScenario } from '../../types/venture';

type Metric = 'mrr' | 'arr';

interface Props {
  scenarios: ProjectionScenario[];
  selectedIndex: number;
  onSelect: (index: number) => void;
}

const SCENARIO_COLORS = ['#f59e0b', '#6366f1', '#10b981'];
const CHART_WIDTH = 760;
const CHART_HEIGHT = 320;
const PLOT_LEFT = 56;
const PLOT_RIGHT = 18;
const PLOT_TOP = 22;
const PLOT_BOTTOM = 38;
const PLOT_WIDTH = CHART_WIDTH - PLOT_LEFT - PLOT_RIGHT;
const PLOT_HEIGHT = CHART_HEIGHT - PLOT_TOP - PLOT_BOTTOM;

function formatCompactCurrency(value: number): string {
  if (!Number.isFinite(value)) return '$0';
  if (value >= 1_000_000_000) return `$${(value / 1_000_000_000).toFixed(1)}B`;
  if (value >= 1_000_000) return `$${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1_000) return `$${(value / 1_000).toFixed(0)}K`;
  return `$${Math.round(value)}`;
}

function scenarioSeries(scenario: ProjectionScenario, metric: Metric): number[] {
  const rows = scenario.monthly_projections || [];
  if (rows.length > 0) {
    return rows.map((row) => {
      const raw = metric === 'mrr'
        ? row.mrr ?? row.revenue ?? 0
        : row.arr ?? Number(row.revenue ?? 0) * 12;
      const value = Number(raw);
      return Number.isFinite(value) ? value : 0;
    });
  }

  const fallback = metric === 'mrr'
    ? scenario.month_12_mrr ?? scenario.month_12_revenue ?? 0
    : scenario.month_12_arr ?? Number(scenario.month_12_revenue ?? 0) * 12;
  return Array.from({ length: 12 }, (_, index) => (Number(fallback) * (index + 1)) / 12);
}

export const ScenarioChart: React.FC<Props> = ({ scenarios, selectedIndex, onSelect }) => {
  const [metric, setMetric] = useState<Metric>('mrr');
  const [hoverIndex, setHoverIndex] = useState<number | null>(null);

  const safeSelectedIndex = Math.min(Math.max(selectedIndex, 0), Math.max(scenarios.length - 1, 0));
  const series = useMemo(
    () => scenarios.map((scenario) => scenarioSeries(scenario, metric)),
    [scenarios, metric],
  );
  const monthCount = Math.max(12, ...series.map((values) => values.length));
  const maxValue = Math.max(1, ...series.flat());

  const xFor = (index: number) =>
    PLOT_LEFT + (monthCount <= 1 ? 0 : (index / (monthCount - 1)) * PLOT_WIDTH);
  const yFor = (value: number) => PLOT_TOP + PLOT_HEIGHT - (value / maxValue) * PLOT_HEIGHT;
  const baseline = PLOT_TOP + PLOT_HEIGHT;

  const pathFor = (values: number[]) =>
    values
      .map((value, index) => `${index === 0 ? 'M' : 'L'} ${xFor(index).toFixed(2)} ${yFor(value).toFixed(2)}`)
      .join(' ');

  const activeValues = series[safeSelectedIndex] || [];
  const activeScenario = scenarios[safeSelectedIndex];
  const hoveredValue = hoverIndex !== null ? activeValues[hoverIndex] : undefined;
  const hoveredX = hoverIndex !== null ? xFor(hoverIndex) : 0;
  const hoveredY = hoveredValue !== undefined ? yFor(hoveredValue) : 0;
  const activeAreaPath = activeValues.length > 0
    ? `${pathFor(activeValues)} L ${xFor(activeValues.length - 1).toFixed(2)} ${baseline.toFixed(2)} L ${xFor(0).toFixed(2)} ${baseline.toFixed(2)} Z`
    : '';
  const yTicks = Array.from({ length: 5 }, (_, index) => (maxValue * (4 - index)) / 4);
  const xLabelIndexes = Array.from({ length: monthCount }, (_, index) => index).filter(
    (index) => index === 0 || index === monthCount - 1 || (index + 1) % 2 === 0,
  );

  if (scenarios.length === 0) {
    return (
      <div className="empty-state" style={{ padding: '32px 20px' }}>
        <div className="empty-state-icon">📉</div>
        <h4>No projection scenarios available</h4>
        <p>The financial engine did not return monthly projection data for this venture.</p>
      </div>
    );
  }

  return (
    <div className="scenario-chart-card">
      <div className="scenario-chart-header">
        <div>
          <div className="section-title" style={{ marginBottom: '4px' }}>
            <BarChart3 size={18} color="#818cf8" />
            <span>12-Month Scenario Trajectory</span>
          </div>
          <p className="scenario-chart-caption">
            Hover the chart to inspect a month. Toggle a scenario or switch between MRR and ARR.
          </p>
        </div>
        <div className="chart-toggle-group" role="group" aria-label="Chart metric">
          <button
            type="button"
            className={`chart-toggle-btn ${metric === 'mrr' ? 'active' : ''}`}
            onClick={() => setMetric('mrr')}
            aria-pressed={metric === 'mrr'}
          >
            MRR
          </button>
          <button
            type="button"
            className={`chart-toggle-btn ${metric === 'arr' ? 'active' : ''}`}
            onClick={() => setMetric('arr')}
            aria-pressed={metric === 'arr'}
          >
            ARR
          </button>
        </div>
      </div>

      <div className="chart-legend" role="group" aria-label="Projection scenarios">
        {scenarios.map((scenario, index) => {
          const isActive = index === safeSelectedIndex;
          const color = SCENARIO_COLORS[index % SCENARIO_COLORS.length];
          return (
            <button
              key={`${scenario.scenario_name}-${index}`}
              type="button"
              className={`chart-legend-btn ${isActive ? 'active' : ''}`}
              onClick={() => onSelect(index)}
              aria-pressed={isActive}
              style={{ borderColor: isActive ? color : undefined }}
            >
              <span className="chart-legend-dot" style={{ background: color }} />
              <span style={{ textTransform: 'capitalize' }}>{scenario.scenario_name}</span>
            </button>
          );
        })}
      </div>

      <div className="chart-svg-wrap">
        <svg
          viewBox={`0 0 ${CHART_WIDTH} ${CHART_HEIGHT}`}
          role="img"
          aria-label={`${metric.toUpperCase()} projection chart for conservative, moderate, and optimistic scenarios`}
          onMouseLeave={() => setHoverIndex(null)}
        >
          <defs>
            <linearGradient id="scenario-chart-area" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={SCENARIO_COLORS[safeSelectedIndex % SCENARIO_COLORS.length]} stopOpacity="0.28" />
              <stop offset="100%" stopColor={SCENARIO_COLORS[safeSelectedIndex % SCENARIO_COLORS.length]} stopOpacity="0.01" />
            </linearGradient>
          </defs>

          {yTicks.map((tick, index) => {
            const y = yFor(tick);
            return (
              <g key={`grid-${index}`}>
                <line
                  x1={PLOT_LEFT}
                  y1={y}
                  x2={CHART_WIDTH - PLOT_RIGHT}
                  y2={y}
                  stroke="rgba(148, 163, 184, 0.16)"
                  strokeDasharray="4 6"
                />
                <text x={PLOT_LEFT - 10} y={y + 4} textAnchor="end" className="chart-axis-label">
                  {formatCompactCurrency(tick)}
                </text>
              </g>
            );
          })}

          <line
            x1={PLOT_LEFT}
            y1={baseline}
            x2={CHART_WIDTH - PLOT_RIGHT}
            y2={baseline}
            stroke="rgba(148, 163, 184, 0.35)"
          />
          <line
            x1={PLOT_LEFT}
            y1={PLOT_TOP}
            x2={PLOT_LEFT}
            y2={baseline}
            stroke="rgba(148, 163, 184, 0.35)"
          />

          {xLabelIndexes.map((index) => (
            <text
              key={`x-${index}`}
              x={xFor(index)}
              y={CHART_HEIGHT - 14}
              textAnchor="middle"
              className="chart-axis-label"
            >
              M{index + 1}
            </text>
          ))}

          {activeAreaPath && <path d={activeAreaPath} fill="url(#scenario-chart-area)" />}

          {series.map((values, index) => {
            const isActive = index === safeSelectedIndex;
            return (
              <path
                key={`series-${index}`}
                d={pathFor(values)}
                fill="none"
                stroke={SCENARIO_COLORS[index % SCENARIO_COLORS.length]}
                strokeWidth={isActive ? 3 : 1.5}
                strokeOpacity={isActive ? 1 : 0.35}
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            );
          })}

          {series.map((values, index) => {
            if (values.length === 0) return null;
            const lastIndex = values.length - 1;
            return (
              <circle
                key={`endpoint-${index}`}
                cx={xFor(lastIndex)}
                cy={yFor(values[lastIndex])}
                r={index === safeSelectedIndex ? 4.5 : 2.5}
                fill={SCENARIO_COLORS[index % SCENARIO_COLORS.length]}
                fillOpacity={index === safeSelectedIndex ? 1 : 0.4}
              />
            );
          })}

          {Array.from({ length: monthCount }, (_, index) => {
            const columnWidth = monthCount <= 1 ? PLOT_WIDTH : PLOT_WIDTH / (monthCount - 1);
            return (
              <rect
                key={`hover-${index}`}
                x={Math.max(PLOT_LEFT, xFor(index) - columnWidth / 2)}
                y={PLOT_TOP}
                width={columnWidth}
                height={PLOT_HEIGHT}
                fill="transparent"
                onMouseEnter={() => setHoverIndex(index)}
                onFocus={() => setHoverIndex(index)}
                tabIndex={-1}
              />
            );
          })}

          {hoverIndex !== null && hoveredValue !== undefined && (
            <g pointerEvents="none">
              <line
                x1={hoveredX}
                y1={PLOT_TOP}
                x2={hoveredX}
                y2={baseline}
                stroke="rgba(226, 232, 240, 0.35)"
                strokeDasharray="3 4"
              />
              <circle
                cx={hoveredX}
                cy={hoveredY}
                r={5}
                fill={SCENARIO_COLORS[safeSelectedIndex % SCENARIO_COLORS.length]}
                stroke="#0a0d14"
                strokeWidth={2}
              />
              <g transform={`translate(${Math.min(Math.max(hoveredX - 76, PLOT_LEFT), CHART_WIDTH - PLOT_RIGHT - 152)}, ${PLOT_TOP + 8})`}>
                <rect width="152" height="54" rx="8" fill="#111726" stroke="rgba(148, 163, 184, 0.3)" />
                <text x="10" y="18" className="chart-tooltip-title">Month {hoverIndex + 1}</text>
                <text x="10" y="35" className="chart-tooltip-value">
                  {formatCompactCurrency(hoveredValue)}
                </text>
                <text x="10" y="48" className="chart-tooltip-label">
                  {activeScenario?.scenario_name || 'Scenario'} {metric.toUpperCase()}
                </text>
              </g>
            </g>
          )}
        </svg>
      </div>
    </div>
  );
};
