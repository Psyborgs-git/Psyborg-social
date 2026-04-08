import { useParams, useNavigate } from '@tanstack/react-router';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { Input } from '../../components/ui/Input';
import { Label } from '../../components/ui/Label';
import { Edit2, Trash2, CheckCircle, XCircle } from 'lucide-react';
import { useState } from 'react';
import { AccountStatusBadge } from '../../components/accounts/AccountStatusBadge';
import { accountsApi } from '../../api/accounts';
import { Account } from '../../types/api';

function formatPlatformLabel(account: Account): string {
  if (account.platform?.display_name) {
    return account.platform.display_name;
  }

  const rawPlatform = account.platform?.slug ?? account.platform_id;
  const looksLikeUuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(rawPlatform);

  if (looksLikeUuid) {
    return 'Unknown platform';
  }

  return rawPlatform
    .split('_')
    .map((segment) => segment.charAt(0).toUpperCase() + segment.slice(1))
    .join(' ');
}

export default function AccountDetailPage() {
  const { accountId } = useParams({ from: '/_layout/accounts/$accountId' });
  const navigate = useNavigate();
  const [isEditing, setIsEditing] = useState(false);
  const [displayName, setDisplayName] = useState('');

  const { data: account, isLoading } = useQuery<Account>({
    queryKey: ['account', accountId],
    queryFn: () => accountsApi.get(accountId),
  });

  const qc = useQueryClient();
  const updateMutation = useMutation({
    mutationFn: (data: { display_name: string }) => accountsApi.update(accountId, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['account', accountId] });
      qc.invalidateQueries({ queryKey: ['accounts'] });
      setIsEditing(false);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: () => accountsApi.delete(accountId),
    onSuccess: () => navigate({ to: '/accounts' }),
  });

  const pauseMutation = useMutation({
    mutationFn: () => accountsApi.pause(accountId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['account', accountId] });
      qc.invalidateQueries({ queryKey: ['accounts'] });
    },
  });

  const resumeMutation = useMutation({
    mutationFn: () => accountsApi.resume(accountId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['account', accountId] });
      qc.invalidateQueries({ queryKey: ['accounts'] });
    },
  });

  if (isLoading || !account) return <div className="p-6">Loading...</div>;

  return (
    <div className="p-4 sm:p-6 max-w-4xl space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <h1 className="text-xl sm:text-2xl md:text-3xl font-bold text-gray-900">@{account.username}</h1>
        <div className="flex gap-2 flex-shrink-0">
          {account.status === 'active' ? (
            <Button
              variant="outline"
              size="sm"
              onClick={() => pauseMutation.mutate()}
              disabled={pauseMutation.isPending}
            >
              Pause
            </Button>
          ) : (
            <Button
              size="sm"
              onClick={() => resumeMutation.mutate()}
              disabled={resumeMutation.isPending}
            >
              Resume
            </Button>
          )}
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
            <AccountStatusBadge status={account.status} />
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <p className="text-xs text-gray-500 mb-1">Platform</p>
            <p className="font-semibold text-gray-900">{formatPlatformLabel(account)}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <p className="text-xs text-gray-500 mb-1">Daily Limit</p>
            <p className="font-semibold text-gray-900">{account.daily_action_limit} actions</p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Account Details</CardTitle>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                setDisplayName(account.display_name || '');
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
                <Label htmlFor="displayName">Display Name</Label>
                <Input
                  id="displayName"
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                  className="mt-1"
                  placeholder="Optional display name"
                />
              </div>
              <div className="flex gap-2">
                <Button
                  onClick={() =>
                    updateMutation.mutate({ display_name: displayName })
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
                <p className="text-xs text-gray-500">Username</p>
                <p className="font-medium text-gray-900">@{account.username}</p>
              </div>
              <div>
                <p className="text-xs text-gray-500">Display Name</p>
                <p className="font-medium text-gray-900">{account.display_name || 'Not set'}</p>
              </div>
              <div>
                <p className="text-xs text-gray-500">Created</p>
                <p className="text-sm text-gray-600">{new Date(account.created_at).toLocaleString()}</p>
              </div>
              <div className="flex items-center gap-2">
                <p className="text-xs text-gray-500">Warmup Phase</p>
                {account.warmup_phase ? (
                  <CheckCircle className="w-4 h-4 text-yellow-600" />
                ) : (
                  <XCircle className="w-4 h-4 text-green-600" />
                )}
              </div>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
