import { Plus, RefreshCw } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import CategoryFilter from "./CategoryFilter.jsx";
import DoneList from "./DoneList.jsx";
import TaskForm from "./TaskForm.jsx";
import TaskItem from "./TaskItem.jsx";

const API_BASE = import.meta.env.PUBLIC_API_URL || "https://kitt-todo-api.onrender.com/api";
const PRIORITIES = ["high", "medium", "low"];

export default function TaskList() {
  const [tasks, setTasks] = useState([]);
  const [doneTasks, setDoneTasks] = useState([]);
  const [categories, setCategories] = useState([]);
  const [selectedCategory, setSelectedCategory] = useState(null);
  const [activeTab, setActiveTab] = useState("pending");
  const [editingTask, setEditingTask] = useState(null);
  const [formOpen, setFormOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const loadData = async () => {
    setLoading(true);
    setError("");
    try {
      const [pendingRes, doneRes, categoryRes] = await Promise.all([
        fetch(`${API_BASE}/tasks?status=pending`),
        fetch(`${API_BASE}/tasks?status=done`),
        fetch(`${API_BASE}/categories`)
      ]);
      if (!pendingRes.ok || !doneRes.ok || !categoryRes.ok) throw new Error("API request failed");
      setTasks(await pendingRes.json());
      setDoneTasks(await doneRes.json());
      setCategories(await categoryRes.json());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load tasks");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const visibleTasks = useMemo(() => {
    const filtered = selectedCategory ? tasks.filter((task) => task.category === selectedCategory) : tasks;
    return [...filtered].sort(compareTasks);
  }, [tasks, selectedCategory]);

  const recentDoneTasks = useMemo(() => {
    const cutoff = Date.now() - 7 * 24 * 60 * 60 * 1000;
    return doneTasks
      .filter((task) => task.done_at && new Date(task.done_at).getTime() >= cutoff)
      .sort((a, b) => new Date(b.done_at).getTime() - new Date(a.done_at).getTime());
  }, [doneTasks]);

  const grouped = PRIORITIES.map((priority) => ({
    priority,
    tasks: visibleTasks.filter((task) => task.priority === priority)
  }));

  const saveTask = async (payload, id) => {
    const response = await fetch(id ? `${API_BASE}/tasks/${id}` : `${API_BASE}/tasks`, {
      method: id ? "PUT" : "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    if (!response.ok) {
      setError("Could not save task");
      return;
    }
    setFormOpen(false);
    setEditingTask(null);
    await loadData();
  };

  const markDone = async (id) => {
    const response = await fetch(`${API_BASE}/tasks/${id}/done`, { method: "POST" });
    if (!response.ok) {
      setError("Could not complete task");
      return;
    }
    await loadData();
  };

  const deleteTask = async (id) => {
    const response = await fetch(`${API_BASE}/tasks/${id}`, { method: "DELETE" });
    if (!response.ok) {
      setError("Could not delete task");
      return;
    }
    await loadData();
  };

  return (
    <div className="grid gap-4 lg:grid-cols-[260px_1fr]">
      <CategoryFilter categories={categories} tasks={tasks} selectedCategory={selectedCategory} onSelect={setSelectedCategory} />

      <section className="min-w-0">
        <div className="mb-4 flex flex-col gap-3 rounded border border-kitt-line bg-kitt-panel/90 p-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex rounded border border-kitt-line p-1">
            <button
              className={`rounded px-3 py-2 text-sm ${activeTab === "pending" ? "bg-kitt-red text-white" : "text-zinc-400 hover:text-white"}`}
              onClick={() => setActiveTab("pending")}
            >
              Pending {visibleTasks.length}
            </button>
            <button
              className={`rounded px-3 py-2 text-sm ${activeTab === "done" ? "bg-kitt-red text-white" : "text-zinc-400 hover:text-white"}`}
              onClick={() => setActiveTab("done")}
            >
              Done {recentDoneTasks.length}
            </button>
          </div>

          <div className="flex gap-2">
            <button className="rounded border border-kitt-line p-2 text-zinc-300 hover:border-zinc-500" aria-label="Refresh" title="Refresh" onClick={loadData}>
              <RefreshCw size={16} />
            </button>
            <button
              className="inline-flex items-center gap-2 rounded bg-kitt-red px-4 py-2 text-sm font-semibold text-white hover:bg-red-700"
              onClick={() => {
                setEditingTask(null);
                setFormOpen(true);
              }}
            >
              <Plus size={16} />
              Task
            </button>
          </div>
        </div>

        {error && <div className="mb-4 rounded border border-kitt-red bg-red-950/40 p-3 text-sm text-red-100">{error}</div>}
        {loading && <div className="rounded border border-kitt-line bg-kitt-panel/80 p-5 text-sm text-zinc-500">Loading...</div>}

        {!loading && activeTab === "pending" && (
          <div className="grid gap-4">
            {grouped.map(({ priority, tasks: priorityTasks }) => (
              <section key={priority} className="grid gap-2">
                <h2 className="border-b border-kitt-line pb-1 text-xs uppercase text-zinc-500">
                  {priority} / {priorityTasks.length}
                </h2>
                {priorityTasks.length ? (
                  priorityTasks.map((task) => (
                    <TaskItem
                      key={task.id}
                      task={task}
                      onDone={markDone}
                      onDelete={deleteTask}
                      onEdit={(taskToEdit) => {
                        setEditingTask(taskToEdit);
                        setFormOpen(true);
                      }}
                    />
                  ))
                ) : (
                  <div className="rounded border border-kitt-line bg-kitt-panel/60 p-3 text-sm text-zinc-600">No {priority} tasks.</div>
                )}
              </section>
            ))}
          </div>
        )}

        {!loading && activeTab === "done" && <DoneList tasks={recentDoneTasks} onDelete={deleteTask} />}
      </section>

      {formOpen && <TaskForm categories={categories} task={editingTask} onCancel={() => setFormOpen(false)} onSubmit={saveTask} />}
    </div>
  );
}

function compareTasks(a, b) {
  const priorityDiff = PRIORITIES.indexOf(a.priority) - PRIORITIES.indexOf(b.priority);
  if (priorityDiff !== 0) return priorityDiff;
  const aDue = `${a.due_date || "9999-12-31"}T${a.due_time || "23:59"}`;
  const bDue = `${b.due_date || "9999-12-31"}T${b.due_time || "23:59"}`;
  return aDue.localeCompare(bDue);
}
