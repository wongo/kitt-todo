import { AlertTriangle } from "lucide-react";

export default function CategoryFilter({ categories, tasks, selectedCategory, onSelect }) {
  const overdueCount = (categoryName) =>
    tasks.filter((task) => {
      if (categoryName && task.category !== categoryName) return false;
      return isOverdue(task);
    }).length;

  const allOverdue = overdueCount(null);

  return (
    <aside className="flex flex-col gap-2 rounded border border-kitt-line bg-kitt-panel/90 p-3">
      <button
        className={`flex items-center justify-between rounded border px-3 py-2 text-left text-sm ${
          selectedCategory === null
            ? "border-kitt-red bg-red-950/40 text-white"
            : "border-kitt-line text-zinc-300 hover:border-zinc-500"
        }`}
        onClick={() => onSelect(null)}
      >
        <span>全部</span>
        {allOverdue > 0 && <OverduePill count={allOverdue} />}
      </button>

      {categories.map((category) => {
        const count = overdueCount(category.name);
        return (
          <button
            key={category.id}
            className={`flex items-center justify-between rounded border px-3 py-2 text-left text-sm ${
              selectedCategory === category.name
                ? "border-kitt-red bg-red-950/40 text-white"
                : "border-kitt-line text-zinc-300 hover:border-zinc-500"
            }`}
            onClick={() => onSelect(category.name)}
          >
            <span className="truncate">
              <span className="mr-2">{category.icon || "📂"}</span>
              {category.name}
            </span>
            {count > 0 && <OverduePill count={count} />}
          </button>
        );
      })}
    </aside>
  );
}

function OverduePill({ count }) {
  return (
    <span className="ml-2 inline-flex shrink-0 items-center gap-1 rounded bg-red-600 px-2 py-0.5 text-xs text-white">
      <AlertTriangle size={12} />
      {count}
    </span>
  );
}

function isOverdue(task) {
  if (!task.due_date || task.is_done) return false;
  const dueTime = task.due_time || "23:59";
  return new Date(`${task.due_date}T${dueTime}`) < new Date();
}
