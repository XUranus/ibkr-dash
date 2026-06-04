import { useState, useCallback } from 'react'
import type { AgentMetadata, EvidenceSummary, RunTraceSummary } from '@/types/agentEvidence'

interface AgentEvidencePanelProps {
  metadata?: Record<string, unknown>
  evidenceSummary?: Record<string, unknown>
  runTraceSummary?: Record<string, unknown>
}

function formatBytes(bytes: number | null | undefined): string {
  if (bytes === null || bytes === undefined) return '--'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function formatMs(ms: number | null | undefined): string {
  if (ms === null || ms === undefined) return '--'
  return `${ms}ms`
}

function sectionStatusClass(status: string): string {
  if (status === 'available') return 'tag-positive'
  if (status === 'partial') return 'tag-accent'
  return 'tag-negative'
}

export default function AgentEvidencePanel({ metadata, evidenceSummary, runTraceSummary }: AgentEvidencePanelProps) {
  const [visible, setVisible] = useState(false)

  const meta = metadata as AgentMetadata | undefined
  const evidence = evidenceSummary as EvidenceSummary | undefined
  const trace = runTraceSummary as RunTraceSummary | undefined

  const handleToggle = useCallback(() => {
    setVisible((prev) => !prev)
  }, [])

  if (!meta && !evidence && !trace) return null

  return (
    <section className="surface-panel" style={{ marginTop: 'var(--space-3)' }}>
      <div className="surface-panel__content">
        <button
          type="button"
          onClick={handleToggle}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            width: '100%',
            background: 'none',
            border: 'none',
            padding: 0,
            cursor: 'pointer',
            color: 'var(--color-text-secondary)',
            fontSize: '0.85rem',
          }}
        >
          <span style={{ fontWeight: 500 }}>Agent Run Info</span>
          <span style={{ marginLeft: 'auto', fontSize: '0.8rem' }}>{visible ? 'Collapse' : 'Expand'}</span>
          <span>{visible ? '▲' : '▼'}</span>
        </button>

        {visible && (
          <div style={{ marginTop: 'var(--space-3)', display: 'grid', gap: 'var(--space-3)' }}>
            {/* Metadata */}
            {meta && (
              <div>
                <h4 style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--color-text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em', margin: '0 0 8px' }}>
                  Agent Version Info
                </h4>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: 6 }}>
                  <MetaItem label="Harness" value={meta.harness_version} />
                  <MetaItem label="Agent" value={meta.agent_version} />
                  <MetaItem label="Prompt" value={meta.prompt_version} />
                  <MetaItem label="Schema" value={meta.schema_version} />
                  <MetaItem label="Toolset" value={meta.toolset_version} />
                  <MetaItem label="Mode" value={meta.agent_mode} />
                  {meta.model_provider_snapshot?.provider_name && (
                    <MetaItem label="LLM" value={`${meta.model_provider_snapshot.provider_name} / ${meta.model_provider_snapshot.model ?? ''}`} />
                  )}
                  {meta.generated_at && <MetaItem label="Generated At" value={meta.generated_at} mono />}
                </div>
              </div>
            )}

            {/* Evidence */}
            {evidence && (
              <div>
                <h4 style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--color-text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em', margin: '0 0 8px' }}>
                  Evidence Sources
                </h4>
                <div style={{ display: 'grid', gap: 4 }}>
                  {(evidence.evidence_sections ?? []).map((section) => (
                    <div key={section.section} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '6px 8px', borderRadius: 'var(--radius-sm)', background: 'rgba(129, 160, 207, 0.04)', fontSize: '0.82rem' }}>
                      <span className={sectionStatusClass(section.status)} style={{ padding: '2px 8px', borderRadius: 'var(--radius-sm)', fontSize: '0.72rem', fontWeight: 600 }}>{section.status}</span>
                      <span style={{ fontWeight: 500, minWidth: 140 }}>{section.section}</span>
                      <span style={{ color: 'var(--color-text-secondary)', minWidth: 80 }}>{section.source}</span>
                      <span style={{ color: 'var(--color-text-secondary)', minWidth: 50 }}>{section.item_count} items</span>
                      <span style={{ color: 'var(--color-text-secondary)', flex: 1 }}>{section.summary}</span>
                    </div>
                  ))}
                </div>

                {evidence.missing_data?.length > 0 && (
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, alignItems: 'center', marginTop: 8 }}>
                    <span style={{ fontSize: '0.8rem', color: 'var(--color-text-secondary)' }}>Missing data:</span>
                    {evidence.missing_data.map((item) => (
                      <span key={item} style={{ fontSize: '0.78rem', padding: '2px 8px', background: 'rgba(239, 83, 80, 0.1)', color: 'var(--color-negative)', borderRadius: 'var(--radius-sm)' }}>{item}</span>
                    ))}
                  </div>
                )}

                {evidence.data_limitations?.length > 0 && (
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, alignItems: 'center', marginTop: 8 }}>
                    <span style={{ fontSize: '0.8rem', color: 'var(--color-text-secondary)' }}>Data limitations:</span>
                    {evidence.data_limitations.map((item) => (
                      <span key={item} style={{ fontSize: '0.78rem', padding: '2px 8px', background: 'rgba(239, 83, 80, 0.1)', color: 'var(--color-negative)', borderRadius: 'var(--radius-sm)' }}>{item}</span>
                    ))}
                  </div>
                )}

                {evidence.budget_summary && (
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: '0.8rem', color: 'var(--color-text-secondary)', marginTop: 8 }}>
                    <span style={{ fontWeight: 500 }}>Context budget:</span>
                    <span>{formatBytes(evidence.budget_summary.total_original_size)} {'→'} {formatBytes(evidence.budget_summary.total_final_size)}</span>
                    {evidence.budget_summary.truncated_sections?.length > 0 && (
                      <span style={{ color: 'var(--color-accent)' }}>Truncated: {evidence.budget_summary.truncated_sections.join(', ')}</span>
                    )}
                  </div>
                )}
              </div>
            )}

            {/* Run Trace */}
            {trace && (
              <div>
                <h4 style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--color-text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em', margin: '0 0 8px' }}>
                  Tool Call Summary
                </h4>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                  <TraceStat value={trace.llm_rounds} label="LLM Rounds" />
                  <TraceStat value={trace.tool_call_count} label="Tool Calls" />
                  <TraceStat value={trace.tool_success_count} label="Success" positive />
                  {trace.tool_error_count > 0 && <TraceStat value={trace.tool_error_count} label="Failed" error />}
                  {trace.llm_started && trace.llm_finished && <TraceStat value={formatMs((trace.llm_finished as number) - (trace.llm_started as number))} label="Duration" />}
                  {trace.truncated_observations > 0 && <TraceStat value={trace.truncated_observations} label="Truncated" warn />}
                </div>

                {trace.tools?.length > 0 && (
                  <div style={{ display: 'grid', gap: 4, marginTop: 12 }}>
                    {trace.tools.map((tool) => (
                      <div key={tool.tool} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '6px 8px', borderRadius: 'var(--radius-sm)', background: tool.ok ? 'rgba(129, 160, 207, 0.04)' : 'rgba(239, 83, 80, 0.06)', fontSize: '0.82rem' }}>
                        <span style={{ padding: '2px 8px', borderRadius: 'var(--radius-sm)', fontSize: '0.72rem', fontWeight: 600, background: tool.ok ? 'rgba(52, 210, 163, 0.15)' : 'rgba(255, 107, 122, 0.15)', color: tool.ok ? 'var(--color-positive)' : 'var(--color-negative)' }}>{tool.ok ? 'OK' : 'ERR'}</span>
                        <span style={{ fontWeight: 500, minWidth: 200 }}>{tool.tool}</span>
                        <span style={{ color: 'var(--color-text-secondary)', flex: 1 }}>{tool.summary}</span>
                        {tool.original_size != null && (
                          <span style={{ fontSize: '0.75rem', color: 'var(--color-text-secondary)', fontFamily: 'monospace' }}>{formatBytes(tool.original_size)} {'→'} {formatBytes(tool.final_size)}</span>
                        )}
                        {tool.truncated && <span style={{ padding: '2px 8px', borderRadius: 'var(--radius-sm)', fontSize: '0.72rem', background: 'rgba(86, 213, 255, 0.15)', color: 'var(--color-accent)' }}>Truncated</span>}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </section>
  )
}

function MetaItem({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 2, padding: '8px 10px', background: 'rgba(129, 160, 207, 0.06)', borderRadius: 'var(--radius-sm)' }}>
      <span style={{ fontSize: '0.72rem', color: 'var(--color-text-secondary)', textTransform: 'uppercase' }}>{label}</span>
      <span style={{ fontSize: '0.82rem', color: 'var(--color-text-primary)', fontWeight: 500, fontFamily: mono ? 'monospace' : undefined }}>{value}</span>
    </div>
  )
}

function TraceStat({ value, label, positive, error, warn }: { value: number | string; label: string; positive?: boolean; error?: boolean; warn?: boolean }) {
  let valueColor = 'var(--color-text-primary)'
  if (positive) valueColor = 'var(--color-positive)'
  if (error) valueColor = 'var(--color-negative)'
  if (warn) valueColor = 'var(--color-accent)'

  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', padding: '8px 16px', background: 'rgba(129, 160, 207, 0.06)', borderRadius: 'var(--radius-sm)', minWidth: 80 }}>
      <span style={{ fontSize: '1.2rem', fontWeight: 700, color: valueColor }}>{value}</span>
      <span style={{ fontSize: '0.72rem', color: 'var(--color-text-secondary)', textTransform: 'uppercase' }}>{label}</span>
    </div>
  )
}
