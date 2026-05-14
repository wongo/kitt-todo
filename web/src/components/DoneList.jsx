import TaskItem from "./TaskItem.jsx";

export default function DoneList({ tasks, onDelete }) {
  if (!tasks.length) {
    return <div className="rounded border border-kitt-line bg-kitt-panel/80 p-5 text-sm text-zinc-500">No completed tasks in the last 7 days.</div>;
  }

  return (
    <section className="grid gap-3">
      {tasks.map((task) => (
        <TaskItem key={task.id} task={task} completed onDelete={onDelete} onDone={() => {}} onEdit={() => {}} />
      ))}
    </section>
  );
}
