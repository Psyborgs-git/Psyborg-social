import { useQuery } from '@tanstack/react-query';
import { analyticsApi } from '../../api/analytics';
import { Card, CardHeader, CardTitle, CardContent } from '../../components/ui/Card';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, Legend } from 'recharts';

const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6'];

export default function AnalyticsPage() {
  const { data: summary } = useQuery({
    queryKey: ['analytics-summary'],
    queryFn: analyticsApi.getSummary,
    refetchInterval: 60_000,
  });
  const { data: engagement } = useQuery({
    queryKey: ['analytics-engagement'],
    queryFn: () => analyticsApi.getEngagement({ period: '7d' }),
  });
  const { data: platforms } = useQuery({
    queryKey: ['analytics-platforms'],
    queryFn: analyticsApi.getPlatformBreakdown,
  });

  const engagementData = Array.isArray(engagement) ? engagement : [];
  const platformData = Array.isArray(platforms) ? platforms : [];

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Analytics</h1>
      <div className="grid grid-cols-3 gap-4">
        <Card><CardContent className="py-4 text-center">
          <p className="text-3xl font-bold text-gray-900">{summary?.success_rate?.toFixed(1) ?? '—'}%</p>
          <p className="text-sm text-gray-500 mt-1">Success Rate</p>
        </CardContent></Card>
        <Card><CardContent className="py-4 text-center">
          <p className="text-3xl font-bold text-gray-900">{summary?.total_tasks ?? '—'}</p>
          <p className="text-sm text-gray-500 mt-1">Total Tasks</p>
        </CardContent></Card>
        <Card><CardContent className="py-4 text-center">
          <p className="text-3xl font-bold text-gray-900">{summary?.posts_today ?? '—'}</p>
          <p className="text-sm text-gray-500 mt-1">Posts Today</p>
        </CardContent></Card>
      </div>
      <div className="grid grid-cols-2 gap-6">
        <Card>
          <CardHeader><CardTitle>Engagement (7d)</CardTitle></CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={engagementData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" tick={{ fontSize: 12 }} />
                <YAxis tick={{ fontSize: 12 }} />
                <Tooltip />
                <Bar dataKey="value" fill="#3b82f6" />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle>Platform Breakdown</CardTitle></CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={200}>
              <PieChart>
                <Pie data={platformData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={70}>
                  {platformData.map((_: unknown, index: number) => (
                    <Cell key={index} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
