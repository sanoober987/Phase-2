"use client";

import { useState, useCallback } from "react";
import { useTasks } from "@/hooks/useTasks";
import { TaskList } from "@/components/tasks/TaskList";
import { TaskForm } from "@/components/tasks/TaskForm";
import { TaskFilter } from "@/components/tasks/TaskFilter";
import { DeleteConfirm } from "@/components/tasks/DeleteConfirm";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { AuthGuard } from "@/components/auth/AuthGuard";
import { ChatPanel } from "@/components/chat/ChatPanel";
import { useAuth } from "@/hooks/useAuth";
import type { Task, TaskFormData } from "@/types";

function DashboardContent() {
  const {
    items: tasks,
    total,
    isLoading,
    error,
    filter,
    fetchTasks,
    createTask,
    updateTask,
    deleteTask,
    toggleComplete,
    setFilter,
  } = useTasks();

  const { user } = useAuth();

  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [editingTask, setEditingTask] = useState<Task | null>(null);
  const [deletingTask, setDeletingTask] = useState<Task | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleCreate = useCallback(async (data: TaskFormData) => {
    setIsSubmitting(true);
    try {
      await createTask({
        title: data.title,
        description: data.description || undefined,
      });
      setIsCreateModalOpen(false);
    } finally {
      setIsSubmitting(false);
    }
  }, [createTask]);

  const handleEdit = useCallback(async (data: TaskFormData) => {
    if (!editingTask) return;
    setIsSubmitting(true);
    try {
      await updateTask(editingTask.id, {
        title: data.title,
        description: data.description || undefined,
      });
      setEditingTask(null);
    } finally {
      setIsSubmitting(false);
    }
  }, [editingTask, updateTask]);

  const handleDelete = useCallback(async () => {
    if (!deletingTask) return;
    setIsSubmitting(true);
    try {
      await deleteTask(deletingTask.id);
      setDeletingTask(null);
    } finally {
      setIsSubmitting(false);
    }
  }, [deletingTask, deleteTask]);

  const handleToggleComplete = useCallback(async (id: string) => {
    await toggleComplete(id);
  }, [toggleComplete]);

  return (
    <main className="flex flex-col gap-6 lg:grid lg:grid-cols-[1fr_400px] lg:gap-8 lg:items-start">
      <div className="space-y-6">
      {/* Header */}
      <header className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-zinc-900 dark:text-zinc-100">
            My Tasks
          </h1>
          <p className="text-zinc-600 dark:text-zinc-400 text-sm mt-1">
            {total} {total === 1 ? "task" : "tasks"} total
          </p>
        </div>

        <Button onClick={() => setIsCreateModalOpen(true)}>
          <svg
            xmlns="http://www.w3.org/2000/svg"
            className="h-4 w-4 mr-2"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            aria-hidden="true"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 4v16m8-8H4"
            />
          </svg>
          Create Task
        </Button>
      </header>

      {/* Filter */}
      <TaskFilter
        currentFilter={filter.isCompleted}
        onFilterChange={setFilter}
      />

      {/* Task List */}
      <TaskList
        tasks={tasks}
        isLoading={isLoading}
        error={error}
        onToggleComplete={handleToggleComplete}
        onEdit={setEditingTask}
        onDelete={setDeletingTask}
        onRetry={fetchTasks}
      />

      {/* Create Modal */}
      <Modal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        title="Create Task"
      >
        <TaskForm
          onSubmit={handleCreate}
          onCancel={() => setIsCreateModalOpen(false)}
          isSubmitting={isSubmitting}
        />
      </Modal>

      {/* Edit Modal */}
      <Modal
        isOpen={!!editingTask}
        onClose={() => setEditingTask(null)}
        title="Edit Task"
      >
        {editingTask && (
          <TaskForm
            initialData={{
              title: editingTask.title,
              description: editingTask.description || "",
            }}
            onSubmit={handleEdit}
            onCancel={() => setEditingTask(null)}
            isSubmitting={isSubmitting}
            submitLabel="Save Changes"
          />
        )}
      </Modal>

      {/* Delete Confirmation */}
      <DeleteConfirm
        isOpen={!!deletingTask}
        taskTitle={deletingTask?.title || ""}
        onConfirm={handleDelete}
        onCancel={() => setDeletingTask(null)}
        isDeleting={isSubmitting}
      />
      </div>
      {user && (
        <div className="lg:sticky lg:top-6">
          <ChatPanel userId={user.id} onTasksChanged={fetchTasks} />
        </div>
      )}
    </main>
  );
}

export default function DashboardPage() {
  return (
    <AuthGuard>
      <DashboardContent />
    </AuthGuard>
  );
}
