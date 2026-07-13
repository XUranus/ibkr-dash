import { useState, useEffect, useCallback } from 'react'
import Modal from '@/components/Modal'
import type { EvalCase } from '@/types/adminHarness'

interface EvalCaseEditorDialogProps {
  visible: boolean
  initialCase?: Partial<EvalCase> | null
  mode: 'create' | 'edit'
  saving?: boolean
  onClose: () => void
  onSave: (payload: Record<string, unknown>) => void
}

const SEVERITY_OPTIONS = ['low', 'medium', 'high', 'critical']
const CATEGORY_OPTIONS = ['', 'safety', 'format', 'grounding', 'tool_use', 'investment_risk', 'regression']

interface FormState {
  title: string
  agent_name: string
  description: string
  enabled: boolean
  severity: string
  category: string
  tags: string
  notes: string
  expected_output_fields: string
  expected_tools: string
  expected_data_limitations: string
  forbidden_behavior: string
  expected_behavior: string
  scoring_rubric: string
  input: string
  mock_context: string
  mock_tool_outputs: string
  metadata: string
  judge_enabled: boolean
  judge_rubric: string
  judge_model_config: string
  eval_scope: string
  node_name: string
  source_run_id: string
  source_llm_call_id: string
  source_node_trace_id: string
  prompt_key: string
  prompt_version: string
  prompt_hash: string
  model: string
}

const EMPTY_FORM: FormState = {
  title: '',
  agent_name: '',
  description: '',
  enabled: true,
  severity: 'medium',
  category: '',
  tags: '',
  notes: '',
  expected_output_fields: '',
  expected_tools: '',
  expected_data_limitations: '',
  forbidden_behavior: '',
  expected_behavior: '{}',
  scoring_rubric: '{}',
  input: '{}',
  mock_context: '{}',
  mock_tool_outputs: '{}',
  metadata: '{}',
  judge_enabled: false,
  judge_rubric: '{}',
  judge_model_config: '{}',
  eval_scope: 'agent',
  node_name: '',
  source_run_id: '',
  source_llm_call_id: '',
  source_node_trace_id: '',
  prompt_key: '',
  prompt_version: '',
  prompt_hash: '',
  model: '',
}

function safeJson(value: unknown): string {
  if (value === undefined || value === null) return '{}'
  try { return JSON.stringify(value, null, 2) } catch { return '{}' }
}

function textToArray(text: string, mode: 'line' | 'commaOrLine' = 'line'): string[] {
  const separator = mode === 'commaOrLine' ? /[\n,]/ : '\n'
  const parts = text.split(separator).map((s) => s.trim()).filter(Boolean)
  return [...new Set(parts)]
}

function parseJsonStrict(text: string, label: string, errors: string[]): Record<string, unknown> | null {
  try {
    const parsed = JSON.parse(text)
    if (typeof parsed !== 'object' || parsed === null || Array.isArray(parsed)) {
      errors.push(`${label} must be a JSON object`)
      return null
    }
    return parsed
  } catch {
    errors.push(`${label} has invalid JSON format`)
    return null
  }
}

export default function EvalCaseEditorDialog({ visible, initialCase, mode, saving, onClose, onSave }: EvalCaseEditorDialogProps) {
  const [form, setForm] = useState<FormState>(EMPTY_FORM)
  const [errors, setErrors] = useState<string[]>([])
  const [collapsedSections, setCollapsedSections] = useState({
    input: true,
    mock: true,
    metadata: true,
    judge: true,
  })

  useEffect(() => {
    if (!visible) return
    setErrors([])
    const c = initialCase
    if (!c) return
    setForm({
      title: c.title ?? '',
      agent_name: c.agent_name ?? '',
      description: c.description ?? '',
      enabled: c.enabled ?? true,
      severity: c.severity ?? 'medium',
      category: c.category ?? '',
      tags: (c.tags ?? []).join(', '),
      notes: c.notes ?? '',
      expected_output_fields: (c.expected_output_fields ?? []).join('\n'),
      expected_tools: (c.expected_tools ?? []).join('\n'),
      expected_data_limitations: (c.expected_data_limitations ?? []).join('\n'),
      forbidden_behavior: (c.forbidden_behavior ?? []).join('\n'),
      expected_behavior: safeJson(c.expected_behavior),
      scoring_rubric: safeJson(c.scoring_rubric),
      input: safeJson(c.input),
      mock_context: safeJson(c.mock_context),
      mock_tool_outputs: safeJson(c.mock_tool_outputs),
      metadata: safeJson(c.metadata),
      judge_enabled: c.judge_enabled ?? false,
      judge_rubric: safeJson(c.judge_rubric),
      judge_model_config: safeJson(c.judge_model_config),
      eval_scope: c.eval_scope ?? 'agent',
      node_name: c.node_name ?? '',
      source_run_id: c.source_run_id ?? '',
      source_llm_call_id: c.source_llm_call_id ?? '',
      source_node_trace_id: c.source_node_trace_id ?? '',
      prompt_key: c.prompt_key ?? '',
      prompt_version: c.prompt_version ?? '',
      prompt_hash: c.prompt_hash ?? '',
      model: c.model ?? '',
    })
  }, [visible, initialCase])

  const update = useCallback((field: keyof FormState, value: unknown) => {
    setForm(prev => ({ ...prev, [field]: value }))
  }, [])

  const toggleSection = useCallback((section: keyof typeof collapsedSections) => {
    setCollapsedSections(prev => ({ ...prev, [section]: !prev[section] }))
  }, [])

  function buildPayload(): Record<string, unknown> | null {
    const newErrors: string[] = []
    if (!form.title.trim()) newErrors.push('Title is required')
    if (!form.agent_name.trim()) newErrors.push('Agent name is required')

    const evalScope = form.eval_scope.trim() || 'agent'
    if (evalScope !== 'agent' && evalScope !== 'node') {
      newErrors.push('eval_scope must be "agent" or "node"')
    }
    if (evalScope === 'node' && !form.node_name.trim()) {
      newErrors.push('node_name is required when eval_scope is "node"')
    }

    const expectedBehavior = parseJsonStrict(form.expected_behavior, 'expected_behavior', newErrors)
    const scoringRubric = parseJsonStrict(form.scoring_rubric, 'scoring_rubric', newErrors)
    const inputObj = parseJsonStrict(form.input, 'input', newErrors)
    const mockContext = parseJsonStrict(form.mock_context, 'mock_context', newErrors)
    const mockToolOutputs = parseJsonStrict(form.mock_tool_outputs, 'mock_tool_outputs', newErrors)
    const metadata = parseJsonStrict(form.metadata, 'metadata', newErrors)
    const judgeRubric = form.judge_enabled ? parseJsonStrict(form.judge_rubric, 'judge_rubric', newErrors) : null
    const judgeModelConfig = form.judge_enabled ? parseJsonStrict(form.judge_model_config, 'judge_model_config', newErrors) : null

    if (newErrors.length) {
      setErrors(newErrors)
      return null
    }

    const payload: Record<string, unknown> = {
      title: form.title.trim(),
      agent_name: form.agent_name.trim(),
      description: form.description.trim(),
      enabled: form.enabled,
      severity: form.severity,
      category: form.category,
      tags: textToArray(form.tags, 'commaOrLine'),
      notes: form.notes.trim(),
      expected_output_fields: textToArray(form.expected_output_fields),
      expected_tools: textToArray(form.expected_tools),
      expected_data_limitations: textToArray(form.expected_data_limitations),
      forbidden_behavior: textToArray(form.forbidden_behavior),
      expected_behavior: expectedBehavior,
      scoring_rubric: scoringRubric,
      input: inputObj,
      mock_context: mockContext,
      mock_tool_outputs: mockToolOutputs,
      metadata: metadata,
      judge_enabled: form.judge_enabled,
      judge_rubric: judgeRubric || {},
      judge_model_config: judgeModelConfig || {},
      eval_scope: evalScope,
      node_name: form.node_name.trim() || null,
      source_run_id: form.source_run_id.trim() || null,
      source_llm_call_id: form.source_llm_call_id.trim() || null,
      source_node_trace_id: form.source_node_trace_id.trim() || null,
      prompt_key: form.prompt_key.trim() || null,
      prompt_version: form.prompt_version.trim() || null,
      prompt_hash: form.prompt_hash.trim() || null,
      model: form.model.trim() || null,
    }

    if (mode === 'create' && initialCase) {
      const draft = initialCase as Record<string, unknown>
      if (draft.case_id) payload.case_id = draft.case_id
      if (draft.source) payload.source = draft.source
      if (draft.source_replay_id) payload.source_replay_id = draft.source_replay_id
      if (draft.created_at) payload.created_at = draft.created_at
      if (draft.updated_at) payload.updated_at = draft.updated_at
      if (draft.version) payload.version = draft.version
      if (draft.metadata && metadata) {
        payload.metadata = { ...(draft.metadata as Record<string, unknown>), ...metadata }
      }
    }

    return payload
  }

  function handleSave() {
    const payload = buildPayload()
    if (!payload) return
    onSave(payload)
  }

  if (!visible) return null

  return (
    <Modal open={true} onClose={onClose} title={mode === 'create' ? 'Create Eval Case' : 'Edit Eval Case'} width="min(900px, 92vw)">
      <div style={{ display: 'flex', flexDirection: 'column', maxHeight: 'calc(90vh - 64px)' }}>
        <div className="eval-case-editor__body">
          {errors.length > 0 && (
            <div className="eval-case-editor__errors">
              {errors.map((err, i) => <span key={i}>{err}</span>)}
            </div>
          )}

          <fieldset className="eval-case-editor__section">
            <legend>Basic Info</legend>
            <div className="eval-case-editor__grid">
              <label className="eval-case-editor__field">
                <span>Title *</span>
                <input value={form.title} onChange={e => update('title', e.target.value)} />
              </label>
              <label className="eval-case-editor__field">
                <span>Agent *</span>
                <input value={form.agent_name} onChange={e => update('agent_name', e.target.value)} disabled={mode === 'edit'} />
              </label>
              <label className="eval-case-editor__field eval-case-editor__field--full">
                <span>Description</span>
                <input value={form.description} onChange={e => update('description', e.target.value)} />
              </label>
              <label className="eval-case-editor__field">
                <span>Enabled</span>
                <select value={String(form.enabled)} onChange={e => update('enabled', e.target.value === 'true')}>
                  <option value="true">Enabled</option>
                  <option value="false">Disabled</option>
                </select>
              </label>
              <label className="eval-case-editor__field">
                <span>Severity</span>
                <select value={form.severity} onChange={e => update('severity', e.target.value)}>
                  {SEVERITY_OPTIONS.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </label>
              <label className="eval-case-editor__field">
                <span>Category</span>
                <select value={form.category} onChange={e => update('category', e.target.value)}>
                  {CATEGORY_OPTIONS.map(c => <option key={c} value={c}>{c || '(none)'}</option>)}
                </select>
              </label>
              <label className="eval-case-editor__field eval-case-editor__field--full">
                <span>Tags (comma separated)</span>
                <input value={form.tags} onChange={e => update('tags', e.target.value)} placeholder="replay, trade_review" />
              </label>
              <label className="eval-case-editor__field eval-case-editor__field--full">
                <span>Notes</span>
                <input value={form.notes} onChange={e => update('notes', e.target.value)} />
              </label>
            </div>
          </fieldset>

          <fieldset className="eval-case-editor__section">
            <legend>Eval Rules</legend>
            <div className="eval-case-editor__grid">
              <label className="eval-case-editor__field">
                <span>Eval Scope</span>
                <select value={form.eval_scope} onChange={e => update('eval_scope', e.target.value)}>
                  <option value="agent">agent</option>
                  <option value="node">node</option>
                </select>
              </label>
              <label className="eval-case-editor__field">
                <span>Node Name{form.eval_scope === 'node' ? ' *' : ''}</span>
                <input
                  value={form.node_name}
                  onChange={e => update('node_name', e.target.value)}
                  placeholder={form.eval_scope === 'node' ? 'Required, e.g. event_catalyst' : '(only required for node scope)'}
                />
              </label>
              <label className="eval-case-editor__field">
                <span>Prompt Key</span>
                <input value={form.prompt_key} onChange={e => update('prompt_key', e.target.value)} />
              </label>
              <label className="eval-case-editor__field">
                <span>Prompt Version</span>
                <input value={form.prompt_version} onChange={e => update('prompt_version', e.target.value)} />
              </label>
              <label className="eval-case-editor__field">
                <span>Prompt Hash</span>
                <input value={form.prompt_hash} onChange={e => update('prompt_hash', e.target.value)} />
              </label>
              <label className="eval-case-editor__field">
                <span>Model</span>
                <input value={form.model} onChange={e => update('model', e.target.value)} />
              </label>
              <label className="eval-case-editor__field">
                <span>Source Run ID</span>
                <input value={form.source_run_id} onChange={e => update('source_run_id', e.target.value)} />
              </label>
              <label className="eval-case-editor__field">
                <span>Source LLM Call ID</span>
                <input value={form.source_llm_call_id} onChange={e => update('source_llm_call_id', e.target.value)} />
              </label>
              <label className="eval-case-editor__field eval-case-editor__field--full">
                <span>Source Node Trace ID</span>
                <input value={form.source_node_trace_id} onChange={e => update('source_node_trace_id', e.target.value)} />
              </label>
              <label className="eval-case-editor__field eval-case-editor__field--full">
                <span>expected_output_fields (one per line)</span>
                <textarea value={form.expected_output_fields} onChange={e => update('expected_output_fields', e.target.value)} rows={3} />
              </label>
              <label className="eval-case-editor__field eval-case-editor__field--full">
                <span>expected_tools (one per line)</span>
                <textarea value={form.expected_tools} onChange={e => update('expected_tools', e.target.value)} rows={3} />
              </label>
              <label className="eval-case-editor__field eval-case-editor__field--full">
                <span>expected_data_limitations (one per line)</span>
                <textarea value={form.expected_data_limitations} onChange={e => update('expected_data_limitations', e.target.value)} rows={2} />
              </label>
              <label className="eval-case-editor__field eval-case-editor__field--full">
                <span>forbidden_behavior (one per line)</span>
                <textarea value={form.forbidden_behavior} onChange={e => update('forbidden_behavior', e.target.value)} rows={3} />
              </label>
              <label className="eval-case-editor__field eval-case-editor__field--full">
                <span>expected_behavior (JSON)</span>
                <textarea value={form.expected_behavior} onChange={e => update('expected_behavior', e.target.value)} rows={4} className="eval-case-editor__json" />
              </label>
              <label className="eval-case-editor__field eval-case-editor__field--full">
                <span>scoring_rubric (JSON)</span>
                <textarea value={form.scoring_rubric} onChange={e => update('scoring_rubric', e.target.value)} rows={3} className="eval-case-editor__json" />
              </label>
            </div>
          </fieldset>

          <fieldset className="eval-case-editor__section">
            <legend role="button" tabIndex={0} onClick={() => toggleSection('input')}>
              Input {collapsedSections.input ? '▶' : '▼'}
            </legend>
            {!collapsedSections.input && (
              <label className="eval-case-editor__field eval-case-editor__field--full">
                <textarea value={form.input} onChange={e => update('input', e.target.value)} rows={6} className="eval-case-editor__json" />
              </label>
            )}
          </fieldset>

          <fieldset className="eval-case-editor__section">
            <legend role="button" tabIndex={0} onClick={() => toggleSection('mock')}>
              Mock Data {collapsedSections.mock ? '▶' : '▼'}
            </legend>
            {!collapsedSections.mock && (
              <>
                <label className="eval-case-editor__field eval-case-editor__field--full">
                  <span>mock_context (JSON)</span>
                  <textarea value={form.mock_context} onChange={e => update('mock_context', e.target.value)} rows={4} className="eval-case-editor__json" />
                </label>
                <label className="eval-case-editor__field eval-case-editor__field--full">
                  <span>mock_tool_outputs (JSON)</span>
                  <textarea value={form.mock_tool_outputs} onChange={e => update('mock_tool_outputs', e.target.value)} rows={4} className="eval-case-editor__json" />
                </label>
              </>
            )}
          </fieldset>

          <fieldset className="eval-case-editor__section">
            <legend role="button" tabIndex={0} onClick={() => toggleSection('metadata')}>
              Metadata {collapsedSections.metadata ? '▶' : '▼'}
            </legend>
            {!collapsedSections.metadata && (
              <label className="eval-case-editor__field eval-case-editor__field--full">
                <textarea value={form.metadata} onChange={e => update('metadata', e.target.value)} rows={4} className="eval-case-editor__json" />
              </label>
            )}
          </fieldset>

          <fieldset className="eval-case-editor__section">
            <legend role="button" tabIndex={0} onClick={() => toggleSection('judge')}>
              LLM Judge Config {collapsedSections.judge ? '▶' : '▼'}
            </legend>
            {!collapsedSections.judge && (
              <>
                <p className="eval-case-editor__hint">
                  LLM Judge will invoke a model to judge output quality, which may incur extra token costs. Recommended only for critical cases.
                </p>
                <div className="eval-case-editor__grid">
                  <label className="eval-case-editor__field">
                    <span>Enable LLM Judge</span>
                    <select value={String(form.judge_enabled)} onChange={e => update('judge_enabled', e.target.value === 'true')}>
                      <option value="false">Disabled</option>
                      <option value="true">Enabled</option>
                    </select>
                  </label>
                </div>
                {form.judge_enabled && (
                  <>
                    <label className="eval-case-editor__field eval-case-editor__field--full">
                      <span>judge_rubric (JSON, leave empty for default)</span>
                      <textarea value={form.judge_rubric} onChange={e => update('judge_rubric', e.target.value)} rows={4} className="eval-case-editor__json" />
                    </label>
                    <label className="eval-case-editor__field eval-case-editor__field--full">
                      <span>judge_model_config (JSON, optional)</span>
                      <textarea value={form.judge_model_config} onChange={e => update('judge_model_config', e.target.value)} rows={3} className="eval-case-editor__json" />
                    </label>
                  </>
                )}
              </>
            )}
          </fieldset>
        </div>

        <div className="eval-case-editor__footer">
          <button className="btn btn--secondary" onClick={onClose}>Cancel</button>
          <button className="btn btn--primary" onClick={handleSave} disabled={saving}>
            {saving ? 'Saving...' : 'Save'}
          </button>
        </div>
      </div>

      <style>{`
        .eval-case-editor__body {
          flex: 1;
          overflow-y: auto;
          padding: 18px 20px;
          display: grid;
          gap: 14px;
          background: #07111f;
        }
        .eval-case-editor__errors {
          margin: 0;
          padding: 10px 14px;
          border-radius: 4px;
          background: rgba(255, 107, 122, 0.12);
          color: var(--color-negative, #ff6b7a);
          display: grid;
          gap: 2px;
        }
        .eval-case-editor__section {
          border: 1px solid rgba(129, 160, 207, 0.14);
          border-radius: 4px;
          padding: 14px;
          display: grid;
          gap: 10px;
        }
        .eval-case-editor__section legend {
          color: var(--color-text-primary, #e0e8f0);
          font-weight: 700;
          font-size: 0.92rem;
          cursor: pointer;
          padding: 0 6px;
        }
        .eval-case-editor__grid {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 10px;
        }
        .eval-case-editor__field {
          display: grid;
          gap: 4px;
          font-size: 0.85rem;
          color: var(--color-text-secondary, #8ba0c0);
        }
        .eval-case-editor__field--full {
          grid-column: 1 / -1;
        }
        .eval-case-editor__field input,
        .eval-case-editor__field select,
        .eval-case-editor__field textarea {
          min-height: 36px;
          border: 1px solid rgba(129, 160, 207, 0.18);
          border-radius: 4px;
          background: rgba(10, 18, 32, 0.72);
          color: var(--color-text-primary, #e0e8f0);
          padding: 6px 10px;
          font-family: inherit;
          font-size: 0.85rem;
          resize: vertical;
        }
        .eval-case-editor__field textarea {
          min-height: 60px;
        }
        .eval-case-editor__json {
          font-family: 'Menlo', 'Consolas', monospace;
          font-size: 0.8rem;
        }
        .eval-case-editor__hint {
          margin: 0;
          font-size: 0.8rem;
          color: var(--color-text-secondary, #8ba0c0);
          opacity: 0.8;
          padding: 6px 0;
        }
        .eval-case-editor__footer {
          display: flex;
          justify-content: flex-end;
          gap: 10px;
          padding: 12px 20px;
          border-top: 1px solid rgba(129, 160, 207, 0.2);
          background: #081827;
        }
      `}</style>
    </Modal>
  )
}
