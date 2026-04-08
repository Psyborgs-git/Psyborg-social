import { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { useForm } from 'react-hook-form';
import { useAuth } from '../hooks/useAuth';
import { userApi } from '../api/user';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { Label } from '../components/ui/Label';
import { Badge } from '../components/ui/Badge';
import { User as UserIcon, Lock, Bell, Shield } from 'lucide-react';

type PasswordFormData = {
  oldPassword: string;
  newPassword: string;
};

export default function SettingsPage() {
  const { user } = useAuth();
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const { data: settings } = useQuery({
    queryKey: ['user-settings'],
    queryFn: userApi.getSettings,
  });

  const {
    register,
    handleSubmit,
    reset,
    clearErrors,
    setError,
    formState: { isSubmitting, errors },
  } = useForm<PasswordFormData>();

  const passwordMutation = useMutation({
    mutationFn: (data: PasswordFormData) => userApi.changePassword(data.oldPassword, data.newPassword),
    onSuccess: () => {
      setSuccessMessage('Password updated successfully.');
      reset();
      clearErrors('root');
    },
    onError: (error) => {
      setSuccessMessage(null);
      setError('root', {
        message: error instanceof Error ? error.message : 'Failed to change password',
      });
    },
  });

  return (
    <div className="p-4 sm:p-6 max-w-4xl space-y-6">
      <h1 className="text-xl sm:text-2xl md:text-3xl font-bold text-gray-900">Settings</h1>

      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <UserIcon className="w-5 h-5" />
            <CardTitle>Account Information</CardTitle>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <p className="text-xs text-gray-500">Username</p>
            <p className="font-medium text-gray-900">{settings?.username ?? user?.username ?? '—'}</p>
          </div>
          <div>
            <p className="text-xs text-gray-500">Email</p>
            <p className="font-medium text-gray-900">{settings?.email || 'Not set'}</p>
          </div>
          <div>
            <p className="text-xs text-gray-500">Account Status</p>
            <Badge className="mt-1">Active</Badge>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Lock className="w-5 h-5" />
            <CardTitle>Change Password</CardTitle>
          </div>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit((data) => passwordMutation.mutate(data))} className="space-y-4">
            <div>
              <Label htmlFor="oldPassword">Current Password</Label>
              <Input
                id="oldPassword"
                type="password"
                {...register('oldPassword', { required: 'Current password is required' })}
                className="mt-1"
              />
              {errors.oldPassword && <p className="text-xs text-red-500 mt-1">{errors.oldPassword.message}</p>}
            </div>
            <div>
              <Label htmlFor="newPassword">New Password</Label>
              <Input
                id="newPassword"
                type="password"
                {...register('newPassword', {
                  required: 'New password is required',
                  minLength: { value: 8, message: 'New password must be at least 8 characters' },
                })}
                className="mt-1"
              />
              {errors.newPassword && <p className="text-xs text-red-500 mt-1">{errors.newPassword.message}</p>}
            </div>
            {errors.root && <p className="text-sm text-red-500 bg-red-50 px-4 py-2 rounded-md">{errors.root.message}</p>}
            {successMessage && <p className="text-sm text-green-700 bg-green-50 px-4 py-2 rounded-md">{successMessage}</p>}
            <Button type="submit" disabled={isSubmitting || passwordMutation.isPending}>
              {isSubmitting || passwordMutation.isPending ? 'Updating...' : 'Change Password'}
            </Button>
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Bell className="w-5 h-5" />
            <CardTitle>Notifications</CardTitle>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <label className="flex items-center gap-3 p-3 border border-gray-200 rounded-lg bg-gray-50">
            <input type="checkbox" checked={settings?.notifications_enabled ?? true} readOnly className="rounded" />
            <div>
              <p className="text-sm font-medium text-gray-900">Dashboard Notifications</p>
              <p className="text-xs text-gray-500">Status notifications are enabled for your current account.</p>
            </div>
          </label>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Shield className="w-5 h-5" />
            <CardTitle>Security</CardTitle>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="bg-blue-50 border border-blue-200 rounded p-4">
            <p className="text-xs text-blue-700">
              🔒 <strong>Your data is secure.</strong> Credentials are encrypted at rest and MCP requests require a bearer token when enabled.
            </p>
          </div>
          <div>
            <p className="text-sm font-medium text-gray-900 mb-2">Active Session</p>
            <div className="flex items-center justify-between p-2 bg-gray-50 rounded">
              <span className="text-gray-600">Current Browser</span>
              <Badge variant="success">Active</Badge>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
