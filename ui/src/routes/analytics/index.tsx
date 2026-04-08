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
    <div className="p-4 sm:p-6 space-y-6">
      <h1 className="text-xl sm:text-2xl md:text-3xl font-bold text-gray-900">Analytics</h1>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        <Card><CardContent className="py-4 text-center">
          <p className="text-2xl sm:text-3xl font-bold text-gray-900">{summary?.success_rate?.toFixed(1) ?? '—'}%</p>
          <p className="text-xs sm:text-sm text-gray-500 mt-1">Success Rate</p>
        </CardContent></Card>
        <Card><CardContent className="py-4 text-center">
          <p className="text-2xl sm:text-3xl font-bold text-gray-900">{summary?.total_tasks ?? '—'}</p>
          <p className="text-xs sm:text-sm text-gray-500 mt-1">Total Tasks</p>
        </CardContent></Card>
        <Card><CardContent className="py-4 text-center">
          <p className="text-2xl sm:text-3xl font-bold text-gray-900">{summary?.posts_today ?? '—'}</p>
          <p className="text-xs sm:text-sm text-gray-500 mt-1">Posts Today</p>
        </CardContent></Card>
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader><CardTitle className="text-base sm:text-lg">Engagement (7d)</CardTitle></CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={engagementData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" tick={{ fontSize: 11 }} angle={-45} textAnchor="end" height={70} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip />
                <Bar dataKey="value" fill="#3b82f6" />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle className="text-base sm:text-lg">Platform Breakdown</CardTitle></CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={200}>
              <PieChart>
                <Pie data={platformData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={60}>
                  {platformData.map((_: unknown, index: number) => (
                    <Cell key={index} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
                <Legend wrapperStyle={{ fontSize: 12 }} />
              </PieChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
