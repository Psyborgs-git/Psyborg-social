import { Link } from '@tanstack/react-router';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { campaignsApi } from '../../api/campaigns';
import { Card, CardContent } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { Badge } from '../../components/ui/Badge';
import { Plus } from 'lucide-react';

export default function CampaignsPage() {
  const { data: campaigns, isLoading } = useQuery({
    queryKey: ['campaigns'],
    queryFn: campaignsApi.list,
  });
  const qc = useQueryClient();
  const activate = useMutation({ mutationFn: campaignsApi.activate, onSuccess: () => qc.invalidateQueries({ queryKey: ['campaigns'] }) });
  const deactivate = useMutation({ mutationFn: campaignsApi.deactivate, onSuccess: () => qc.invalidateQueries({ queryKey: ['campaigns'] }) });

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Campaigns</h1>
        <Link to="/campaigns/new">
          <Button><Plus className="w-4 h-4 mr-2" />New Campaign</Button>
        </Link>
      </div>
      {isLoading && <p className="text-gray-500">Loading...</p>}
      <div className="grid gap-4">
        {campaigns?.map(campaign => (
          <Card key={campaign.id}>
            <CardContent className="flex items-center justify-between py-4">
              <div>
                <p className="font-medium text-gray-900">{campaign.name}</p>
                {campaign.description && <p className="text-sm text-gray-500">{campaign.description}</p>}
                {campaign.cron_expression && (
                  <code className="text-xs bg-gray-100 px-1 rounded">{campaign.cron_expression}</code>
                )}
              </div>
              <div className="flex items-center gap-2">
                <Badge variant={campaign.is_active ? 'success' : 'default'}>
                  {campaign.is_active ? 'Active' : 'Inactive'}
                </Badge>
                {campaign.is_active ? (
                  <Button variant="outline" size="sm" onClick={() => deactivate.mutate(campaign.id)}>Deactivate</Button>
                ) : (
                  <Button size="sm" onClick={() => activate.mutate(campaign.id)}>Activate</Button>
                )}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
