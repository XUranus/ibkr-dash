/** Copilot observation list -- displays observations/data from a run. */

interface Observation {
  key: string
  label: string
  value: string | number | null
  source?: string
}

interface Props {
  observations: Observation[]
  className?: string
}

export default function CopilotObservationList({ observations, className }: Props) {
  if (!observations.length) return null

  return (
    <div className={`copilot-observations ${className || ''}`}>
      <h4 className="copilot-observations__title">Observations</h4>
      <dl className="copilot-observations__list">
        {observations.map((obs) => (
          <div key={obs.key} className="copilot-observations__item">
            <dt>{obs.label}</dt>
            <dd>{obs.value ?? '--'}</dd>
            {obs.source && <span className="copilot-observations__source">{obs.source}</span>}
          </div>
        ))}
      </dl>
    </div>
  )
}
