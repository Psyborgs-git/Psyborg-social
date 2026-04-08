import { useNavigate } from '@tanstack/react-router';
import { useMutation } from '@tanstack/react-query';
import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Card, CardContent } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { Input } from '../../components/ui/Input';
import { Label } from '../../components/ui/Label';
import { Textarea } from '../../components/ui/Textarea';
import { Select } from '../../components/ui/Select';
import { campaignsApi } from '../../api/campaigns';

const campaignSchema = z.object({
  name: z.string().min(1, 'Campaign name required'),
  description: z.string().optional(),
  cron_expression: z.string().default('0 * * * *'),
});

type CampaignFormData = z.infer<typeof campaignSchema>;

const CRON_PRESETS = [
  { label: 'Every hour', value: '0 * * * *' },
  { label: 'Every 30 minutes', value: '*/30 * * * *' },
  { label: 'Every 6 hours', value: '0 */6 * * *' },
  { label: 'Daily at 9 AM', value: '0 9 * * *' },
  { label: 'Daily at 12 PM', value: '0 12 * * *' },
  { label: 'Daily at 6 PM', value: '0 18 * * *' },
  { label: 'Weekdays at 9 AM', value: '0 9 * * 1-5' },
  { label: 'Weekends at 10 AM', value: '0 10 * * 0,6' },
  { label: '3 times a week', value: '0 12 * * 0,3,5' },
  { label: 'Custom...', value: 'custom' },
];

export default function CreateCampaignPage() {
  const navigate = useNavigate();
  const [schedulePreset, setSchedulePreset] = useState('0 12 * * *');

  const { register, handleSubmit, setValue, formState: { errors, isSubmitting }, setError } = useForm<CampaignFormData>({
    resolver: zodResolver(campaignSchema),
    defaultValues: { cron_expression: '0 12 * * *' },
  });

  const mutation = useMutation({
    mutationFn: campaignsApi.create,
    onSuccess: (data) => {
      navigate({ to: `/campaigns/${data.id}` });
    },
    onError: (error) => {
      setError('root', {
        message: error instanceof Error ? error.message : 'Failed to create campaign',
      });
    },
  });

  const handleScheduleChange = (value: string) => {
    setSchedulePreset(value);
    setValue('cron_expression', value === 'custom' ? '' : value, {
      shouldDirty: true,
      shouldValidate: true,
    });
  };

  const onSubmit = async (data: CampaignFormData) => {
    await mutation.mutateAsync(data);
  };

  return (
    <div className="p-4 sm:p-6 max-w-3xl space-y-6">
      <h1 className="text-xl sm:text-2xl md:text-3xl font-bold text-gray-900">Create Campaign</h1>

      <Card>
        <CardContent className="p-6">
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
            <div>
              <Label htmlFor="name">Campaign Name *</Label>
              <Input
                id="name"
                {...register('name')}
                className="mt-1"
                placeholder="e.g. Daily Tech Updates"
              />
              {errors.name && <p className="mt-1 text-xs text-red-500">{errors.name.message}</p>}
            </div>

            <div>
              <Label htmlFor="description">Description</Label>
              <Textarea
                id="description"
                {...register('description')}
                className="mt-1"
                rows={4}
                placeholder="Campaign description and objectives..."
              />
            </div>

            <div>
              <Label htmlFor="schedule">Schedule</Label>
              <Select
                id="schedule"
                className="mt-1"
                value={schedulePreset}
                onChange={(event) => handleScheduleChange(event.target.value)}
              >
                {CRON_PRESETS.map(preset => (
                  <option key={preset.value} value={preset.value}>
                    {preset.label}
                  </option>
                ))}
              </Select>
              {schedulePreset === 'custom' && (
                <Input
                  {...register('cron_expression')}
                  className="mt-2"
                  placeholder="Custom cron expression (e.g. 0 9 * * *)"
                />
              )}
              {errors.cron_expression && <p className="mt-1 text-xs text-red-500">{errors.cron_expression.message}</p>}
              <p className="text-xs text-gray-500 mt-2">
                Using cron format: min hour day month weekday
              </p>
            </div>

            <div className="bg-blue-50 border border-blue-200 rounded p-4">
              <h4 className="font-semibold text-sm text-blue-900 mb-2">📋 Next Steps</h4>
              <ul className="text-xs text-blue-700 space-y-1">
                <li>• Create the campaign first</li>
                <li>• Add accounts to include in this campaign</li>
                <li>• Set up personas and content templates</li>
                <li>• Activate the campaign to start scheduling</li>
              </ul>
            </div>

            {errors.root && <p className="text-sm text-red-500 bg-red-50 px-4 py-2 rounded">{errors.root.message}</p>}

            <div className="flex gap-4">
              <Button
                type="submit"
                disabled={isSubmitting || mutation.isPending}
                className="flex-1 sm:flex-none"
              >
                {isSubmitting || mutation.isPending ? 'Creating...' : 'Create Campaign'}
              </Button>
              <Button
                type="button"
                variant="outline"
                onClick={() => navigate({ to: '/campaigns' })}
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
