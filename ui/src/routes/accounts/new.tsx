import { useNavigate } from '@tanstack/react-router';
import { useMutation } from '@tanstack/react-query';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Card, CardContent } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { Input } from '../../components/ui/Input';
import { Label } from '../../components/ui/Label';
import { Select } from '../../components/ui/Select';
import { accountsApi } from '../../api/accounts';

const accountSchema = z.object({
  platform: z.string().min(1, 'Platform required'),
  username: z.string().min(1, 'Username required'),
  password: z.string().min(6, 'Password must be at least 6 characters'),
  proxy_url: z.string().optional(),
});

type AccountFormData = z.infer<typeof accountSchema>;

const PLATFORMS = [
  { id: 'instagram', name: 'Instagram' },
  { id: 'twitter', name: 'Twitter/X' },
  { id: 'tiktok', name: 'TikTok' },
  { id: 'reddit', name: 'Reddit' },
  { id: 'threads', name: 'Threads' },
  { id: 'linkedin', name: 'LinkedIn' },
  { id: 'youtube', name: 'YouTube' },
  { id: 'facebook', name: 'Facebook' },
];

export default function CreateAccountPage() {
  const navigate = useNavigate();
  const { register, handleSubmit, formState: { errors, isSubmitting }, setError } = useForm<AccountFormData>({
    resolver: zodResolver(accountSchema),
  });

  const mutation = useMutation({
    mutationFn: accountsApi.create,
    onSuccess: (data) => {
      navigate({ to: `/accounts/${data.id}` });
    },
    onError: (error) => {
      setError('root', {
        message: error instanceof Error ? error.message : 'Failed to create account',
      });
    },
  });

  const onSubmit = async (data: AccountFormData) => {
    await mutation.mutateAsync(data);
  };

  return (
    <div className="p-4 sm:p-6 max-w-2xl">
      <h1 className="text-xl sm:text-2xl md:text-3xl font-bold text-gray-900 mb-6">Add New Account</h1>

      <Card>
        <CardContent className="p-6">
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
            <div>
              <Label htmlFor="platform">Platform *</Label>
              <Select {...register('platform')} defaultValue="" className="mt-1">
                <option value="">Select a platform...</option>
                {PLATFORMS.map(p => (
                  <option key={p.id} value={p.id}>{p.name}</option>
                ))}
              </Select>
              {errors.platform && <p className="mt-1 text-xs text-red-500">{errors.platform.message}</p>}
            </div>

            <div>
              <Label htmlFor="username">Username *</Label>
              <Input
                id="username"
                {...register('username')}
                className="mt-1"
                placeholder="@username or email"
              />
              {errors.username && <p className="mt-1 text-xs text-red-500">{errors.username.message}</p>}
            </div>

            <div>
              <Label htmlFor="password">Password *</Label>
              <Input
                id="password"
                type="password"
                {...register('password')}
                className="mt-1"
                placeholder="Account password"
              />
              {errors.password && <p className="mt-1 text-xs text-red-500">{errors.password.message}</p>}
            </div>

            <div>
              <Label htmlFor="proxy_url">Proxy URL (Optional)</Label>
              <Input
                id="proxy_url"
                {...register('proxy_url')}
                className="mt-1"
                placeholder="http://proxy.example.com:8080"
              />
              {errors.proxy_url && <p className="mt-1 text-xs text-red-500">{errors.proxy_url.message}</p>}
            </div>

            {errors.root && <p className="text-sm text-red-500 bg-red-50 px-4 py-2 rounded">{errors.root.message}</p>}

            <div className="bg-blue-50 border border-blue-200 rounded p-4">
              <p className="text-xs text-blue-700">
                🔐 <strong>Security:</strong> Your credentials are encrypted and stored securely. We only access your account to perform authorized actions.
              </p>
            </div>

            <div className="flex gap-4">
              <Button
                type="submit"
                disabled={isSubmitting || mutation.isPending}
                className="flex-1 sm:flex-none"
              >
                {isSubmitting || mutation.isPending ? 'Adding...' : 'Add Account'}
              </Button>
              <Button
                type="button"
                variant="outline"
                onClick={() => navigate({ to: '/accounts' })}
                className="flex-1 sm:flex-none"
              >
                Cancel
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
