import { Save, X } from "lucide-react";
import { useEffect, useState } from "react";

const EMPTY_FORM = {
  title: "",
  priority: "medium",
  due_date: "",
  due_time: "",
  category: "",
  repeat_type: ""
};

export default function TaskForm({ categories, task, onCancel, onSubmit }) {
  const [form, setForm] = useState(EMPTY_FORM);
  const isEditing = Boolean(task);

  useEffect(() => {
    setForm(
      task
        ? {
            title: task.title || "",
            priority: task.priority || "medium",
            due_date: task.due_date || "",
            due_time: task.due_time || "",
            category: task.category || "",
            repeat_type: task.repeat_type || ""
          }
        : EMPTY_FORM
    );
  }, [task]);

  const update = (field, value) => setForm((current) => ({ ...current, [field]: value }));

  const submit = (event) => {
    event.preventDefault();
    const payload = {
      title: form.title.trim(),
      priority: form.priority,
      due_date: form.due_date || null,
      due_time: form.due_time || null,
      category: form.category || null,
      repeat_type: form.repeat_type || null
    };
    onSubmit(payload, task?.id);
  };

  return (
    <div className="fixed inset-0 z-20 flex items-center justify-center bg-black/70 p-4">
      <form className="w-full max-w-2xl rounded border border-kitt-red bg-[#101010] p-4 shadow-[0_0_30px_rgba(255,0,0,0.2)]" onSubmit={submit}>
        <div className="mb-4 flex items-center justify-between gap-3 border-b border-kitt-line pb-3">
          <h2 className="text-sm uppercase text-zinc-200">{isEditing ? "Edit Task" : "New Task"}</h2>
          <button className="rounded border border-kitt-line p-2 text-zinc-300 hover:border-zinc-500" type="button" onClick={onCancel} aria-label="Close">
            <X size={16} />
          </button>
        </div>

        <div className="grid gap-3 md:grid-cols-2">
          <label className="md:col-span-2">
            <span className="mb-1 block text-xs uppercase text-zinc-500">Title</span>
            <input
              className="w-full rounded border border-kitt-line bg-black px-3 py-2 text-sm text-white outline-none focus:border-kitt-red"
              required
              value={form.title}
              onChange={(event) => update("title", event.target.value)}
            />
          </label>

          <label>
            <span className="mb-1 block text-xs uppercase text-zinc-500">Priority</span>
            <select
              className="w-full rounded border border-kitt-line bg-black px-3 py-2 text-sm text-white outline-none focus:border-kitt-red"
              value={form.priority}
              onChange={(event) => update("priority", event.target.value)}
            >
              <option value="high">🔥 high</option>
              <option value="medium">⚡ medium</option>
              <option value="low">💤 low</option>
            </select>
          </label>

          <label>
            <span className="mb-1 block text-xs uppercase text-zinc-500">Category</span>
            <select
              className="w-full rounded border border-kitt-line bg-black px-3 py-2 text-sm text-white outline-none focus:border-kitt-red"
              value={form.category}
              onChange={(event) => update("category", event.target.value)}
            >
              <option value="">none</option>
              {categories.map((category) => (
                <option key={category.id} value={category.name}>
                  {(category.icon || "📂") + " " + category.name}
                </option>
              ))}
            </select>
          </label>

          <label>
            <span className="mb-1 block text-xs uppercase text-zinc-500">Due Date</span>
            <input
              className="w-full rounded border border-kitt-line bg-black px-3 py-2 text-sm text-white outline-none focus:border-kitt-red"
              type="date"
              value={form.due_date}
              onChange={(event) => update("due_date", event.target.value)}
            />
          </label>

          <label>
            <span className="mb-1 block text-xs uppercase text-zinc-500">Due Time</span>
            <input
              className="w-full rounded border border-kitt-line bg-black px-3 py-2 text-sm text-white outline-none focus:border-kitt-red"
              type="time"
              value={form.due_time}
              onChange={(event) => update("due_time", event.target.value)}
            />
          </label>

          <label className="md:col-span-2">
            <span className="mb-1 block text-xs uppercase text-zinc-500">Repeat</span>
            <div className="grid grid-cols-3 gap-2">
              {[
                ["", "none"],
                ["daily", "daily"],
                ["weekly", "weekly"]
              ].map(([value, label]) => (
                <button
                  key={label}
                  type="button"
                  className={`rounded border px-3 py-2 text-sm ${
                    form.repeat_type === value ? "border-kitt-red bg-red-950/50 text-white" : "border-kitt-line text-zinc-300"
                  }`}
                  onClick={() => update("repeat_type", value)}
                >
                  {label}
                </button>
              ))}
            </div>
          </label>
        </div>

        <div className="mt-5 flex justify-end gap-2">
          <button className="rounded border border-kitt-line px-4 py-2 text-sm text-zinc-300 hover:border-zinc-500" type="button" onClick={onCancel}>
            Cancel
          </button>
          <button className="inline-flex items-center gap-2 rounded bg-kitt-red px-4 py-2 text-sm font-semibold text-white hover:bg-red-700" type="submit">
            <Save size={16} />
            Save
          </button>
        </div>
      </form>
    </div>
  );
}
