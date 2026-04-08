import { Link } from '@tanstack/react-router';
import { useAccounts, usePauseAccount, useResumeAccount } from '../../hooks/useAccounts';
import { Card, CardContent } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { AccountStatusBadge } from '../../components/accounts/AccountStatusBadge';
import { Plus } from 'lucide-react';

function formatPlatformLabel(platformId: string): string {
  return platformId
    .split('_')
    .map((segment) => segment.charAt(0).toUpperCase() + segment.slice(1))
    .join(' ');
}

export default function AccountsPage() {
  const { data: accounts, isLoading } = useAccounts();
  const pause = usePauseAccount();
  const resume = useResumeAccount();

  return (
    <div className="p-4 sm:p-6 space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <h1 className="text-xl sm:text-2xl md:text-3xl font-bold text-gray-900">Accounts</h1>
        <Link to="/accounts/new">
          <Button size="sm" className="w-full sm:w-auto"><Plus className="w-4 h-4 mr-2" />Add Account</Button>
        </Link>
      </div>
      {isLoading && <p className="text-gray-500">Loading...</p>}
      <div className="grid gap-3 sm:gap-4">
        {accounts?.map(account => (
          <Card key={account.id}>
            <CardContent className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 sm:gap-4 py-4">
              <div className="flex items-center gap-3 min-w-0">
                <div className="min-w-0">
                  <p className="font-medium text-gray-900 truncate">{account.display_name ?? account.username}</p>
                  <p className="text-xs sm:text-sm text-gray-500 truncate">
                    @{account.username} · {account.platform?.display_name ?? formatPlatformLabel(account.platform_id)}
                  </p>
                </div>
                <div className="flex-shrink-0">
                  <AccountStatusBadge status={account.status} />
                </div>
              </div>
              <div className="flex gap-2">
                <Link to="/accounts/$accountId" params={{ accountId: account.id }}>
                  <Button variant="ghost" size="sm" className="flex-1 sm:flex-none">Details</Button>
                </Link>
                {account.status === 'active' ? (
                  <Button variant="outline" size="sm" onClick={() => pause.mutate({ id: account.id })} className="flex-1 sm:flex-none">Pause</Button>
                ) : (
                  <Button variant="outline" size="sm" onClick={() => resume.mutate(account.id)} className="flex-1 sm:flex-none">Resume</Button>
                )}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
      {!isLoading && accounts?.length === 0 && (
        <Card>
          <CardContent className="py-8 text-center text-gray-500">
            No accounts yet. Add your first account to start automating.
          </CardContent>
        </Card>
      )}
    </div>
  );
}
