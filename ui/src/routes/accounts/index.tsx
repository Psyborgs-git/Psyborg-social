import { Link } from '@tanstack/react-router';
import { useAccounts, usePauseAccount, useResumeAccount } from '../../hooks/useAccounts';
import { Card, CardHeader, CardTitle, CardContent } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { AccountStatusBadge } from '../../components/accounts/AccountStatusBadge';
import { Plus } from 'lucide-react';

export default function AccountsPage() {
  const { data: accounts, isLoading } = useAccounts();
  const pause = usePauseAccount();
  const resume = useResumeAccount();

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Accounts</h1>
        <Link to="/accounts/new">
          <Button><Plus className="w-4 h-4 mr-2" />Add Account</Button>
        </Link>
      </div>
      {isLoading && <p className="text-gray-500">Loading...</p>}
      <div className="grid gap-4">
        {accounts?.map(account => (
          <Card key={account.id}>
            <CardContent className="flex items-center justify-between py-4">
              <div className="flex items-center gap-4">
                <div>
                  <p className="font-medium text-gray-900">{account.display_name ?? account.username}</p>
                  <p className="text-sm text-gray-500">@{account.username} · {account.platform?.display_name}</p>
                </div>
                <AccountStatusBadge status={account.status} />
              </div>
              <div className="flex gap-2">
                {account.status === 'active' ? (
                  <Button variant="outline" size="sm" onClick={() => pause.mutate({ id: account.id })}>Pause</Button>
                ) : (
                  <Button variant="outline" size="sm" onClick={() => resume.mutate(account.id)}>Resume</Button>
                )}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
