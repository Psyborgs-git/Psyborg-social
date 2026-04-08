import { useTasks, useCancelTask } from '../../hooks/useTasks';
import { Card, CardContent } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { TaskStatusBadge } from '../../components/tasks/TaskStatusBadge';

export default function TasksPage() {
  const { data: tasks, isLoading } = useTasks();
  const cancel = useCancelTask();

  return (
    <div className="p-4 sm:p-6 space-y-4">
      <h1 className="text-xl sm:text-2xl md:text-3xl font-bold text-gray-900">Task Queue</h1>
      <Card>
        <CardContent className="p-0 overflow-x-auto">
          {isLoading && <p className="px-4 py-3 text-gray-500">Loading...</p>}
          <table className="w-full text-xs sm:text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="px-3 sm:px-4 py-2 sm:py-3 text-left text-gray-600 whitespace-nowrap">ID</th>
                <th className="px-3 sm:px-4 py-2 sm:py-3 text-left text-gray-600 whitespace-nowrap">Type</th>
                <th className="px-3 sm:px-4 py-2 sm:py-3 text-left text-gray-600 whitespace-nowrap">Status</th>
                <th className="px-3 sm:px-4 py-2 sm:py-3 text-left text-gray-600 whitespace-nowrap">Created</th>
                <th className="px-3 sm:px-4 py-2 sm:py-3 text-left text-gray-600 whitespace-nowrap">Retries</th>
                <th className="px-3 sm:px-4 py-2 sm:py-3" />
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {tasks?.map(task => (
                <tr key={task.id} className="hover:bg-gray-50">
                  <td className="px-3 sm:px-4 py-2 sm:py-3 font-mono text-xs text-gray-500 whitespace-nowrap">{task.id.slice(0, 8)}</td>
                  <td className="px-3 sm:px-4 py-2 sm:py-3 font-mono text-xs whitespace-nowrap">{task.task_type}</td>
                  <td className="px-3 sm:px-4 py-2 sm:py-3"><TaskStatusBadge status={task.status} /></td>
                  <td className="px-3 sm:px-4 py-2 sm:py-3 text-gray-500 whitespace-nowrap text-xs sm:text-sm">{new Date(task.created_at).toLocaleString()}</td>
                  <td className="px-3 sm:px-4 py-2 sm:py-3 whitespace-nowrap">{task.retry_count}</td>
                  <td className="px-3 sm:px-4 py-2 sm:py-3 whitespace-nowrap">
                    {(task.status === 'pending' || task.status === 'queued') && (
                      <Button variant="ghost" size="sm" onClick={() => cancel.mutate(task.id)}>Cancel</Button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </CardContent>
      </Card>
    </div>
  );
}
