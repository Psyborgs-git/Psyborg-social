import { Badge } from '../ui/Badge';
import { TaskStatus } from '../../types/api';

const statusConfig: Record<TaskStatus, { label: string; variant: 'success' | 'warning' | 'error' | 'info' | 'default' }> = {
  pending: { label: 'Pending', variant: 'default' },
  queued: { label: 'Queued', variant: 'info' },
  running: { label: 'Running', variant: 'info' },
  success: { label: 'Success', variant: 'success' },
  failed: { label: 'Failed', variant: 'error' },
  retrying: { label: 'Retrying', variant: 'warning' },
  skipped: { label: 'Skipped', variant: 'default' },
};

export function TaskStatusBadge({ status }: { status: TaskStatus }) {
  const config = statusConfig[status] ?? { label: status, variant: 'default' as const };
  return <Badge variant={config.variant}>{config.label}</Badge>;
}
