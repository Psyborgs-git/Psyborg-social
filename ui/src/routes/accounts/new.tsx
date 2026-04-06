import { useNavigate } from '@tanstack/react-router';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useCreateAccount } from '../../hooks/useAccounts';
import { Card, CardHeader, CardTitle, CardContent } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { Input } from '../../components/ui/Input';
import { Label } from '../../components/ui/Label';

const schema = z.object({
  username: z.string().min(1),
  platform_id: z.string().min(1),
  daily_action_limit: z.coerce.number().min(1).max(500),
});

type FormData = z.infer<typeof schema>;

export default function NewAccountPage() {
  const navigate = useNavigate();
  const create = useCreateAccount();
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: { daily_action_limit: 50 },
  });

  const onSubmit = async (data: FormData) => {
    await create.mutateAsync(data);
    navigate({ to: '/accounts' });
  };

  return (
    <div className="p-6 max-w-lg">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Add Account</h1>
      <Card>
        <CardContent className="pt-6">
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <div>
              <Label>Username</Label>
              <Input {...register('username')} className="mt-1" />
              {errors.username && <p className="text-xs text-red-500 mt-1">{errors.username.message}</p>}
            </div>
            <div>
              <Label>Platform ID</Label>
              <Input {...register('platform_id')} className="mt-1" />
            </div>
            <div>
              <Label>Daily Action Limit</Label>
              <Input type="number" {...register('daily_action_limit')} className="mt-1" />
            </div>
            <div className="flex gap-2 pt-2">
              <Button type="submit" disabled={isSubmitting}>Create</Button>
              <Button type="button" variant="outline" onClick={() => navigate({ to: '/accounts' })}>Cancel</Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
