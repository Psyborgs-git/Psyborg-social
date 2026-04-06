import { useNavigate } from '@tanstack/react-router';
import { useForm, Controller } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { campaignsApi } from '../../api/campaigns';
import { Card, CardContent } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { Input } from '../../components/ui/Input';
import { Label } from '../../components/ui/Label';
import { CronBuilder } from '../../components/campaigns/CronBuilder';

const schema = z.object({
  name: z.string().min(1),
  description: z.string().optional(),
  cron_expression: z.string().optional(),
});

type FormData = z.infer<typeof schema>;

export default function NewCampaignPage() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const create = useMutation({
    mutationFn: campaignsApi.create,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['campaigns'] }); navigate({ to: '/campaigns' }); },
  });
  const { register, handleSubmit, control } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: { cron_expression: '0 9 * * *' },
  });

  return (
    <div className="p-6 max-w-lg">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">New Campaign</h1>
      <Card>
        <CardContent className="pt-6">
          <form onSubmit={handleSubmit(data => create.mutate(data))} className="space-y-4">
            <div>
              <Label>Name</Label>
              <Input {...register('name')} className="mt-1" />
            </div>
            <div>
              <Label>Description</Label>
              <Input {...register('description')} className="mt-1" />
            </div>
            <div>
              <Controller
                name="cron_expression"
                control={control}
                render={({ field }) => (
                  <CronBuilder value={field.value ?? ''} onChange={field.onChange} />
                )}
              />
            </div>
            <div className="flex gap-2 pt-2">
              <Button type="submit" disabled={create.isPending}>Create</Button>
              <Button type="button" variant="outline" onClick={() => navigate({ to: '/campaigns' })}>Cancel</Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
