import { useState, useEffect } from 'react'
import Modal from '@/components/Modal'

interface BadCaseFeedbackPayload {
  source_type: string
  source_id: string
  title: string
  agent_name: string
  description: string
  issue_type: string
  severity: string
  category: string
  tags: string[]
  notes: string
  replay_id?: string
  run_id?: string
  eval_run_id?: string
  case_id?: string
  result_case_id?: string
  evidence: Record<string, unknown>
  metadata: Record<string, unknown>
}

interface BadCaseFeedbackDialogProps {
  visible: boolean
  initial?: Partial<BadCaseFeedbackPayload>
  loading?: boolean
  onClose: () => void
  onSave: (payload: BadCaseFeedbackPayload) => void
}

export default function BadCaseFeedbackDialog({ visible, initial, loading, onClose, onSave }: BadCaseFeedbackDialogProps) {
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [issueType, setIssueType] = useState('other')
  const [severity, setSeverity] = useState('medium')
  const [category, setCategory] = useState('')
  const [tags, setTags] = useState('')
  const [notes, setNotes] = useState('')

  useEffect(() => {
    if (visible) {
      setTitle(initial?.title || '')
      setDescription(initial?.description || '')
      setIssueType(initial?.issue_type || 'other')
      setSeverity(initial?.severity || 'medium')
      setCategory(initial?.category || '')
      setTags((initial?.tags || []).join(', '))
      setNotes(initial?.notes || '')
    }
  }, [visible, initial])

  function handleSave() {
    if (!title.trim()) return
    const payload: BadCaseFeedbackPayload = {
      source_type: initial?.source_type || 'manual',
      source_id: initial?.source_id || 'manual',
      title: title.trim(),
      agent_name: initial?.agent_name || '',
      description: description.trim(),
      issue_type: issueType,
      severity,
      category: category.trim(),
      tags: tags.split(/[,\n]/).map(t => t.trim()).filter(Boolean),
      notes: notes.trim(),
      replay_id: initial?.replay_id,
      run_id: initial?.run_id,
      eval_run_id: initial?.eval_run_id,
      case_id: initial?.case_id,
      result_case_id: initial?.result_case_id,
      evidence: initial?.evidence || {},
      metadata: initial?.metadata || {},
    }
    onSave(payload)
  }

  if (!visible) return null

  return (
    <Modal open={visible} onClose={onClose}>
      <div style={{ padding: '24px', minWidth: 480 }}>
        <h3 style={{ marginTop: 0 }}>标记 Bad Case</h3>
        <div className="feedback-form">
          <div className="feedback-form__field">
            <label>标题 *</label>
            <input value={title} onChange={e => setTitle(e.target.value)} placeholder="简要描述问题" />
          </div>
          <div className="feedback-form__field">
            <label>问题描述</label>
            <textarea value={description} onChange={e => setDescription(e.target.value)} rows={3} placeholder="详细描述发现的问题" />
          </div>
          <div className="feedback-form__row">
            <div className="feedback-form__field">
              <label>问题类型</label>
              <select value={issueType} onChange={e => setIssueType(e.target.value)}>
                <option value="wrong_answer">wrong_answer</option>
                <option value="missing_risk">missing_risk</option>
                <option value="overconfident">overconfident</option>
                <option value="tool_error">tool_error</option>
                <option value="format_error">format_error</option>
                <option value="hallucination">hallucination</option>
                <option value="bad_reasoning">bad_reasoning</option>
                <option value="unsafe_investment_advice">unsafe_investment_advice</option>
                <option value="other">other</option>
              </select>
            </div>
            <div className="feedback-form__field">
              <label>严重等级</label>
              <select value={severity} onChange={e => setSeverity(e.target.value)}>
                <option value="low">low</option>
                <option value="medium">medium</option>
                <option value="high">high</option>
                <option value="critical">critical</option>
              </select>
            </div>
          </div>
          <div className="feedback-form__row">
            <div className="feedback-form__field">
              <label>分类</label>
              <select value={category} onChange={e => setCategory(e.target.value)}>
                <option value="">无</option>
                <option value="safety">safety</option>
                <option value="format">format</option>
                <option value="grounding">grounding</option>
                <option value="tool_use">tool_use</option>
                <option value="investment_risk">investment_risk</option>
                <option value="regression">regression</option>
              </select>
            </div>
            <div className="feedback-form__field">
              <label>标签（逗号分隔）</label>
              <input value={tags} onChange={e => setTags(e.target.value)} placeholder="bad_case, risk" />
            </div>
          </div>
          <div className="feedback-form__field">
            <label>备注</label>
            <textarea value={notes} onChange={e => setNotes(e.target.value)} rows={2} placeholder="其他备注信息" />
          </div>
          <div className="feedback-form__actions">
            <button className="btn btn--primary" onClick={handleSave} disabled={loading || !title.trim()}>
              {loading ? '提交中...' : '提交反馈'}
            </button>
            <button className="btn btn--secondary" onClick={onClose}>取消</button>
          </div>
        </div>
      </div>
    </Modal>
  )
}
