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
    <div className="p-4 sm:p-6 space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <h1 className="text-xl sm:text-2xl md:text-3xl font-bold text-gray-900">Campaigns</h1>
        <Link to="/campaigns/new">
          <Button size="sm" className="w-full sm:w-auto"><Plus className="w-4 h-4 mr-2" />New Campaign</Button>
        </Link>
      </div>
      {isLoading && <p className="text-gray-500">Loading...</p>}
      <div className="grid gap-3 sm:gap-4">
        {campaigns?.map(campaign => (
          <Card key={campaign.id}>
            <CardContent className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 sm:gap-4 py-4">
              <div className="min-w-0">
                <p className="font-medium text-gray-900 truncate">{campaign.name}</p>
                {campaign.description && <p className="text-xs sm:text-sm text-gray-500 line-clamp-2">{campaign.description}</p>}
                {campaign.cron_expression && (
                  <code className="text-xs bg-gray-100 px-2 py-1 rounded inline-block mt-2 overflow-x-auto">{campaign.cron_expression}</code>
                )}
              </div>
              <div className="flex items-center gap-2 flex-shrink-0">
                <Link to="/campaigns/$campaignId" params={{ campaignId: campaign.id }}>
                  <Button variant="ghost" size="sm">Details</Button>
                </Link>
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
      {!isLoading && campaigns?.length === 0 && (
        <Card>
          <CardContent className="py-8 text-center text-gray-500">
            No campaigns yet. Create one to schedule automated content.
          </CardContent>
        </Card>
      )}
    </div>
  );
}
