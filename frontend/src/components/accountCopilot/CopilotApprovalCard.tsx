/** Copilot approval card -- displays pending skill approval requests. */

interface ApprovalRequest {
  id: string
  skill_name: string
  description?: string
  arguments?: Record<string, unknown>
}

interface Props {
  approval: ApprovalRequest | null
  onApprove: (id: string) => void
  onDeny: (id: string) => void
}

export default function CopilotApprovalCard({ approval, onApprove, onDeny }: Props) {
  if (!approval) return null

  return (
    <div className="copilot-approval">
      <div className="copilot-approval__header">
        <span className="copilot-approval__icon">approval</span>
        <h4>Approval Required</h4>
      </div>
      <p className="copilot-approval__skill">{approval.skill_name}</p>
      {approval.description && (
        <p className="copilot-approval__desc">{approval.description}</p>
      )}
      <div className="copilot-approval__actions">
        <button className="copilot-approval__btn copilot-approval__btn--approve" onClick={() => onApprove(approval.id)}>
          Approve
        </button>
        <button className="copilot-approval__btn copilot-approval__btn--deny" onClick={() => onDeny(approval.id)}>
          Deny
        </button>
      </div>
    </div>
  )
}
