import { Badge } from '../ui/Badge';
import { AccountStatus } from '../../types/api';

const statusConfig: Record<AccountStatus, { label: string; variant: 'success' | 'warning' | 'error' | 'info' | 'default' }> = {
  active: { label: 'Active', variant: 'success' },
  paused: { label: 'Paused', variant: 'warning' },
  suspended: { label: 'Suspended', variant: 'error' },
  credential_error: { label: 'Credential Error', variant: 'error' },
  warming_up: { label: 'Warming Up', variant: 'info' },
};

export function AccountStatusBadge({ status }: { status: AccountStatus }) {
  const config = statusConfig[status] ?? { label: status, variant: 'default' as const };
  return <Badge variant={config.variant}>{config.label}</Badge>;
}
