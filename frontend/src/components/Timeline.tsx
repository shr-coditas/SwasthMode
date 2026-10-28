import type {Meal} from '../api/client'
import StatusBadge from './StatusBadge'

export default function Timeline({meals, today, onCorrect}: {meals: Meal[]; today: string; onCorrect: (meal: Meal) => void}) {
  return <div className="timeline">{meals.length === 0 ?
    <div className="empty-inline">Your recorded meals will appear here. Start with what you ate today.</div> :
    meals.map(meal => <article className="meal-card" key={meal.id}>
      <div className="meal-mark" aria-hidden="true">◒</div>
      <div className="meal-content">
        <div className="meal-title"><h3>{meal.meal_type}</h3><time>{meal.local_day}</time></div>
        <p className="foods">{meal.foods.map(food => [food.quantity, food.name].filter(Boolean).join(' ')).join(', ')}</p>
        <StatusBadge status={meal.insight_status} />
        {meal.insight && <p className="insight">{meal.insight}</p>}
        {meal.insight_status === 'failed' && <p className="muted">Your meal is saved. The insight could not be generated.</p>}
        <div className="meal-foot"><span>Revision {meal.revision}</span>
          {meal.local_day === today ? <button className="text-button" onClick={() => onCorrect(meal)}>Describe a correction ↗</button> :
            <span>Corrections are available for today's meals</span>}
        </div>
      </div>
    </article>)}</div>
}
