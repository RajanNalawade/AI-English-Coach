import type { Change } from '../api'

export default function ChangeList({ changes }: { changes: Change[] }) {
  if (changes.length === 0) return <p className="ok">No mistakes found. Well done!</p>
  return (
    <ul className="changes">
      {changes.map((c, i) => (
        <li key={i}>
          <span className="from">{c.original}</span> → <span className="to">{c.correction}</span>
          <span className="badge">{c.category.replace('_', ' ')}</span>
          <div className="why">{c.explanation}</div>
        </li>
      ))}
    </ul>
  )
}
