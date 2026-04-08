import { useParams, useNavigate } from '@tanstack/react-router';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { Badge } from '../../components/ui/Badge';
import { Input } from '../../components/ui/Input';
import { Label } from '../../components/ui/Label';
import { Select } from '../../components/ui/Select';
import { Textarea } from '../../components/ui/Textarea';
import { Edit2, Trash2, Power } from 'lucide-react';
import { accountsApi } from '../../api/accounts';
import { campaignsApi } from '../../api/campaigns';
import { Account, Campaign } from '../../types/api';

function formatStatusLabel(status: string): string {
  return status
    .split('_')
    .map((segment) => segment.charAt(0).toUpperCase() + segment.slice(1))
    .join(' ');
}

export default function CampaignDetailPage() {
  const { campaignId } = useParams({ from: '/_layout/campaigns/$campaignId' });
  const navigate = useNavigate();
  const [isEditing, setIsEditing] = useState(false);
  const [formData, setFormData] = useState({ name: '', description: '' });
  const [selectedAccountId, setSelectedAccountId] = useState('');

  const { data: campaign } = useQuery({
    queryKey: ['campaign', campaignId],
    queryFn: () => campaignsApi.get(campaignId),
  });
  const { data: accounts = [] } = useQuery<Account[]>({
    queryKey: ['accounts'],
    queryFn: () => accountsApi.list(),
  });

  const qc = useQueryClient();

  const updateMutation = useMutation({
    mutationFn: (data: Partial<Campaign>) => campaignsApi.update(campaignId, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['campaign', campaignId] });
      qc.invalidateQueries({ queryKey: ['campaigns'] });
      setIsEditing(false);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: () => campaignsApi.delete(campaignId),
    onSuccess: () => navigate({ to: '/campaigns' }),
  });

  const toggleMutation = useMutation({
    mutationFn: () => campaign?.is_active ? campaignsApi.deactivate(campaignId) : campaignsApi.activate(campaignId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['campaign', campaignId] });
      qc.invalidateQueries({ queryKey: ['campaigns'] });
    },
  });

  const addAccountMutation = useMutation({
    mutationFn: (accountId: string) => campaignsApi.addAccount(campaignId, accountId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['campaign', campaignId] });
      qc.invalidateQueries({ queryKey: ['campaigns'] });
    },
  });

  const removeAccountMutation = useMutation({
    mutationFn: (accountId: string) => campaignsApi.removeAccount(campaignId, accountId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['campaign', campaignId] });
      qc.invalidateQueries({ queryKey: ['campaigns'] });
    },
  });

  const campaignAccounts = campaign?.accounts ?? [];
  const availableAccounts = accounts.filter(
    (account) => !campaignAccounts.some((campaignAccount) => campaignAccount.id === account.id)
  );

  useEffect(() => {
    if (!selectedAccountId || !availableAccounts.some((account) => account.id === selectedAccountId)) {
      setSelectedAccountId(availableAccounts[0]?.id ?? '');
    }
  }, [availableAccounts, selectedAccountId]);

  if (!campaign) return <div className="p-6">Loading...</div>;

  return (
    <div className="p-4 sm:p-6 max-w-4xl space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <h1 className="text-xl sm:text-2xl md:text-3xl font-bold text-gray-900">{campaign.name}</h1>
        <div className="flex gap-2 flex-shrink-0">
          <Button
            variant={campaign.is_active ? 'outline' : 'default'}
            size="sm"
            onClick={() => toggleMutation.mutate()}
            disabled={toggleMutation.isPending}
          >
            <Power className="w-4 h-4 mr-2" />
            {campaign.is_active ? 'Deactivate' : 'Activate'}
          </Button>
          <Button
            variant="destructive"
            size="sm"
            onClick={() => deleteMutation.mutate()}
            disabled={deleteMutation.isPending}
          >
            <Trash2 className="w-4 h-4" />
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <Card>
          <CardContent className="pt-6">
            <p className="text-xs text-gray-500 mb-1">Status</p>
            <Badge variant={campaign.is_active ? 'success' : 'default'}>
              {campaign.is_active ? 'Active' : 'Inactive'}
            </Badge>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <p className="text-xs text-gray-500 mb-1">Schedule</p>
            <p className="font-mono text-sm text-gray-900">{campaign.cron_expression}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <p className="text-xs text-gray-500 mb-1">Tasks</p>
            <p className="font-semibold text-gray-900">—</p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Details</CardTitle>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                setFormData({ name: campaign.name, description: campaign.description || '' });
                setIsEditing(!isEditing);
              }}
            >
              <Edit2 className="w-4 h-4" />
            </Button>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {isEditing ? (
            <>
              <div>
                <Label htmlFor="name">Campaign Name</Label>
                <Input
                  id="name"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  className="mt-1"
                />
              </div>
              <div>
                <Label htmlFor="description">Description</Label>
                <Textarea
                  id="description"
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  className="mt-1"
                  rows={4}
                />
              </div>
              <div className="flex gap-2">
                <Button
                  onClick={() =>
                    updateMutation.mutate({
                      name: formData.name,
                      description: formData.description,
                    })
                  }
                  size="sm"
                  disabled={updateMutation.isPending}
                >
                  Save
                </Button>
                <Button
                  variant="outline"
                  onClick={() => setIsEditing(false)}
                  size="sm"
                >
                  Cancel
                </Button>
              </div>
            </>
          ) : (
            <>
              <div>
                <p className="text-xs text-gray-500">Campaign Name</p>
                <p className="font-medium text-gray-900">{campaign.name}</p>
              </div>
              <div>
                <p className="text-xs text-gray-500">Description</p>
                <p className="text-sm text-gray-600">{campaign.description || 'No description'}</p>
              </div>
              <div>
                <p className="text-xs text-gray-500">Created</p>
                <p className="text-sm text-gray-600">{new Date(campaign.created_at).toLocaleString()}</p>
              </div>
            </>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Accounts in Campaign</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {campaignAccounts.length > 0 ? (
            <div className="space-y-3">
              {campaignAccounts.map((account) => (
                <div
                  key={account.id}
                  className="flex flex-col gap-3 rounded-lg border border-gray-200 p-3 sm:flex-row sm:items-center sm:justify-between"
                >
                  <div>
                    <p className="font-medium text-gray-900">{account.display_name || account.username}</p>
                    <p className="text-sm text-gray-500">
                      @{account.username}
                      {account.platform?.display_name ? ` · ${account.platform.display_name}` : ''}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge variant={account.status === 'active' ? 'success' : 'secondary'}>
                      {formatStatusLabel(account.status)}
                    </Badge>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => removeAccountMutation.mutate(account.id)}
                      disabled={removeAccountMutation.isPending}
                    >
                      Remove
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-gray-600">No accounts added yet. Add one below to start posting.</p>
          )}

          <div className="border-t border-gray-200 pt-4 space-y-3">
            <Label htmlFor="campaign-account-select">Add account</Label>
            {availableAccounts.length > 0 ? (
              <div className="flex flex-col gap-3 sm:flex-row">
                <Select
                  id="campaign-account-select"
                  value={selectedAccountId}
                  onChange={(event) => setSelectedAccountId(event.target.value)}
                  className="flex-1"
                >
                  {availableAccounts.map((account) => (
                    <option key={account.id} value={account.id}>
                      {(account.display_name || account.username)} ({account.username})
                    </option>
                  ))}
                </Select>
                <Button
                  onClick={() => selectedAccountId && addAccountMutation.mutate(selectedAccountId)}
                  disabled={!selectedAccountId || addAccountMutation.isPending}
                >
                  Add Account
                </Button>
              </div>
            ) : (
              <p className="text-sm text-gray-600">
                {accounts.length === 0
                  ? 'Create an account first to attach it to this campaign.'
                  : 'All available accounts are already attached to this campaign.'}
              </p>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
