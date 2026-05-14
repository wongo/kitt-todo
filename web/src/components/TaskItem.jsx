import { Check, Pencil, Trash2 } from "lucide-react";

const PRIORITY = {
  high: { label: "high", icon: "🔥", className: "border-red-500 text-red-200 bg-red-950/40" },
  medium: { label: "medium", icon: "⚡", className: "border-yellow-500 text-yellow-100 bg-yellow-950/30" },
  low: { label: "low", icon: "💤", className: "border-zinc-500 text-zinc-200 bg-zinc-900" }
};

export default function TaskItem({ task, onDone, onEdit, onDelete, completed = false }) {
  const overdue = isOverdue(task);
  const priority = PRIORITY[task.priority] || PRIORITY.medium;

  return (
    <article
      className={`grid grid-cols-[auto_1fr_auto] gap-3 rounded border p-3 transition ${
        overdue ? "border-kitt-red bg-red-950/30 shadow-[0_0_18px_rgba(255,0,0,0.14)]" : "border-kitt-line bg-[#101010]"
      }`}
    >
      <button
        className={`mt-0.5 flex h-6 w-6 items-center justify-center rounded border ${
          completed ? "border-green-500 bg-green-950 text-green-200" : "border-zinc-600 hover:border-kitt-red"
        }`}
        aria-label={completed ? "Completed" : "Mark done"}
        disabled={completed}
        onClick={() => onDone(task.id)}
      >
        {completed && <Check size={14} />}
      </button>

      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2">
          <h3 className={`break-words text-sm font-semibold ${completed ? "text-zinc-500 line-through" : "text-zinc-100"}`}>
            {task.title}
          </h3>
          <span className={`rounded border px-2 py-0.5 text-[11px] uppercase ${priority.className}`}>
            {priority.icon} {priority.label}
          </span>
          {task.repeat_type && (
            <span className="rounded border border-cyan-700 bg-cyan-950/30 px-2 py-0.5 text-[11px] uppercase text-cyan-100">
              {task.repeat_type}
            </span>
          )}
        </div>
        <div className="mt-2 flex flex-wrap gap-2 text-xs text-zinc-400">
          <span className={overdue ? "text-kitt-red" : ""}>{formatDue(task)}</span>
          {task.category && <span className="rounded bg-zinc-800 px-2 py-0.5 text-zinc-200">#{task.category}</span>}
          {task.notes && (
            <span className="rounded border border-amber-700 bg-amber-950/30 px-2 py-0.5 text-amber-200" title={task.notes}>
              📝 {task.notes.length > 20 ? task.notes.slice(0, 20) + "…" : task.notes}
            </span>
          )}
        </div>
      </div>

      <div className="flex items-start gap-1">
        {!completed && (
          <button
            className="rounded border border-kitt-line p-2 text-zinc-300 hover:border-zinc-500"
            aria-label="Edit task"
            title="Edit"
            onClick={() => onEdit(task)}
          >
            <Pencil size={15} />
          </button>
        )}
        <button
          className="rounded border border-kitt-line p-2 text-zinc-300 hover:border-kitt-red hover:text-red-200"
          aria-label="Delete task"
          title="Delete"
          onClick={() => onDelete(task.id)}
        >
          <Trash2 size={15} />
        </button>
      </div>
    </article>
  );
}

function formatDue(task) {
  if (!task.due_date) return "no due date";
  const date = new Date(`${task.due_date}T${task.due_time || "00:00"}`);
  const label = new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    hour: task.due_time ? "2-digit" : undefined,
    minute: task.due_time ? "2-digit" : undefined
  }).format(date);
  return isOverdue(task) ? `${label} · OVERDUE` : label;
}

function isOverdue(task) {
  if (!task.due_date || task.is_done) return false;
  return new Date(`${task.due_date}T${task.due_time || "23:59"}`) < new Date();
}
