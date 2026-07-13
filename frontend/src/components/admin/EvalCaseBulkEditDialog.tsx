import { useState, useCallback } from 'react'
import HarnessDetailDialog from './HarnessDetailDialog'

interface EvalCaseBulkEditDialogProps {
  visible: boolean
  caseCount: number
  loading?: boolean
  onClose: () => void
  onSave: (payload: Record<string, unknown>) => void
}

export default function EvalCaseBulkEditDialog({ visible, caseCount, loading, onClose, onSave }: EvalCaseBulkEditDialogProps) {
  const [severity, setSeverity] = useState('')
  const [category, setCategory] = useState('')
  const [tagsAdd, setTagsAdd] = useState('')
  const [tagsRemove, setTagsRemove] = useState('')
  const [notesAppend, setNotesAppend] = useState('')

  const resetForm = useCallback(() => {
    setSeverity('')
    setCategory('')
    setTagsAdd('')
    setTagsRemove('')
    setNotesAppend('')
  }, [])

  function handleSave() {
    const updates: Record<string, unknown> = {}
    if (severity) updates.severity = severity
    if (category) updates.category = category
    if (tagsAdd.trim()) updates.tags_add = tagsAdd.split(/[,\n]/).map(t => t.trim()).filter(Boolean)
    if (tagsRemove.trim()) updates.tags_remove = tagsRemove.split(/[,\n]/).map(t => t.trim()).filter(Boolean)
    if (notesAppend.trim()) updates.notes_append = notesAppend.trim()
    if (Object.keys(updates).length === 0) return
    if (!window.confirm(`Confirm batch update of ${caseCount} Eval Case(s)?`)) return
    onSave(updates)
    resetForm()
  }

  return (
    <HarnessDetailDialog visible={visible} header="Batch Edit Eval Case" onClose={onClose}>
      <div className="bulk-edit-form">
        <div className="bulk-edit-form__field">
          <label>severity (leave empty to skip)</label>
          <select value={severity} onChange={e => setSeverity(e.target.value)}>
            <option value="">No change</option>
            <option value="low">low</option>
            <option value="medium">medium</option>
            <option value="high">high</option>
            <option value="critical">critical</option>
          </select>
        </div>
        <div className="bulk-edit-form__field">
          <label>category (leave empty to skip)</label>
          <input value={category} onChange={e => setCategory(e.target.value)} placeholder="No change" />
        </div>
        <div className="bulk-edit-form__field">
          <label>tags_add (comma or newline separated)</label>
          <textarea value={tagsAdd} onChange={e => setTagsAdd(e.target.value)} rows={2} placeholder="regression, smoke" />
        </div>
        <div className="bulk-edit-form__field">
          <label>tags_remove (comma or newline separated)</label>
          <textarea value={tagsRemove} onChange={e => setTagsRemove(e.target.value)} rows={2} placeholder="draft" />
        </div>
        <div className="bulk-edit-form__field">
          <label>notes_append</label>
          <textarea value={notesAppend} onChange={e => setNotesAppend(e.target.value)} rows={3} placeholder="Append to notes" />
        </div>
        <div className="bulk-edit-form__actions">
          <button className="btn btn--primary" onClick={handleSave} disabled={loading}>
            {loading ? 'Saving...' : 'Save'}
          </button>
          <button className="btn btn--secondary" onClick={onClose}>Cancel</button>
        </div>
      </div>

      <style>{`
        .bulk-edit-form {
          display: grid;
          gap: 1rem;
        }
        .bulk-edit-form__field {
          display: grid;
          gap: 4px;
        }
        .bulk-edit-form__field label {
          font-size: 0.84rem;
          color: var(--color-text-secondary, #8ba0c0);
        }
        .bulk-edit-form__field select,
        .bulk-edit-form__field textarea,
        .bulk-edit-form__field input {
          min-height: 38px;
          border: 1px solid rgba(129, 160, 207, 0.18);
          border-radius: 4px;
          background: rgba(10, 18, 32, 0.72);
          color: var(--color-text-primary, #e0e8f0);
          padding: 8px 10px;
          font-size: 0.84rem;
        }
        .bulk-edit-form__actions {
          display: flex;
          gap: 8px;
          justify-content: flex-end;
        }
      `}</style>
    </HarnessDetailDialog>
  )
}
