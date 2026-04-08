import { useQuery } from '@tanstack/react-query';
import { analyticsApi } from '../api/analytics';
import { useTasks } from '../hooks/useTasks';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/Card';
import { TaskStatusBadge } from '../components/tasks/TaskStatusBadge';
import { Users, Send, MessageSquare, Activity } from 'lucide-react';

function StatCard({ title, value, icon: Icon }: { title: string; value?: number; icon: React.ElementType }) {
  return (
    <Card>
      <CardContent className="flex items-center gap-3 sm:gap-4 py-4 sm:py-6">
        <div className="p-2 sm:p-3 bg-blue-50 rounded-lg">
          <Icon className="w-5 h-5 sm:w-6 sm:h-6 text-blue-600" />
        </div>
        <div className="min-w-0">
          <p className="text-xs sm:text-sm text-gray-500 truncate">{title}</p>
          <p className="text-xl sm:text-2xl font-bold text-gray-900">{value ?? '—'}</p>
        </div>
      </CardContent>
    </Card>
  );
}

export default function DashboardPage() {
  const { data: summary } = useQuery({
    queryKey: ['dashboard-summary'],
    queryFn: analyticsApi.getSummary,
    refetchInterval: 30_000,
  });
  const { data: tasks } = useTasks({ limit: 20 });

  return (
    <div className="p-4 sm:p-6 space-y-6">
      <h1 className="text-xl sm:text-2xl md:text-3xl font-bold text-gray-900">Dashboard</h1>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard title="Active Accounts" value={summary?.active_accounts} icon={Users} />
        <StatCard title="Posts Today" value={summary?.posts_today} icon={Send} />
        <StatCard title="DMs Replied" value={summary?.dms_replied} icon={MessageSquare} />
        <StatCard title="Tasks Running" value={summary?.tasks_running} icon={Activity} />
      </div>
      <Card>
        <CardHeader>
          <CardTitle className="text-lg sm:text-xl">Recent Tasks</CardTitle>
        </CardHeader>
        <CardContent className="p-0 overflow-x-auto">
          <table className="w-full text-xs sm:text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="px-3 sm:px-4 py-2 sm:py-3 text-left text-gray-600 whitespace-nowrap">Type</th>
                <th className="px-3 sm:px-4 py-2 sm:py-3 text-left text-gray-600 whitespace-nowrap">Status</th>
                <th className="px-3 sm:px-4 py-2 sm:py-3 text-left text-gray-600 whitespace-nowrap">Created</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {tasks?.map(task => (
                <tr key={task.id} className="hover:bg-gray-50">
                  <td className="px-3 sm:px-4 py-2 sm:py-3 font-mono text-xs whitespace-nowrap">{task.task_type}</td>
                  <td className="px-3 sm:px-4 py-2 sm:py-3"><TaskStatusBadge status={task.status} /></td>
                  <td className="px-3 sm:px-4 py-2 sm:py-3 text-gray-500 whitespace-nowrap text-xs sm:text-sm">{new Date(task.created_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </CardContent>
      </Card>
    </div>
  );
}
