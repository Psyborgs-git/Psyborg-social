import { useParams, useNavigate } from '@tanstack/react-router';
import { useQuery, useMutation } from '@tanstack/react-query';
import { useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Card, CardContent } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { Input } from '../../components/ui/Input';
import { Label } from '../../components/ui/Label';
import { Textarea } from '../../components/ui/Textarea';
import { Select } from '../../components/ui/Select';
import { personasApi } from '../../api/personas';

const personaSchema = z.object({
  name: z.string().min(1, 'Name required'),
  system_prompt: z.string().min(10, 'System prompt must be at least 10 characters'),
  tone: z.string().min(1, 'Tone required'),
  niche: z.string().min(1, 'Niche required'),
  language: z.string().default('en'),
  vocab_level: z.string().default('conversational'),
  emoji_usage: z.string().default('moderate'),
  hashtag_strategy: z.string().default('relevant'),
  reply_probability: z.coerce.number().min(0).max(1).default(0.7),
  like_probability: z.coerce.number().min(0).max(1).default(0.8),
  follow_back_probability: z.coerce.number().min(0).max(1).default(0.5),
});

type PersonaFormData = z.infer<typeof personaSchema>;

interface Persona extends PersonaFormData {
  id: string;
}

const defaultValues: PersonaFormData = {
  name: '',
  system_prompt: '',
  tone: 'casual',
  niche: '',
  language: 'en',
  vocab_level: 'conversational',
  emoji_usage: 'moderate',
  hashtag_strategy: 'relevant',
  reply_probability: 0.7,
  like_probability: 0.8,
  follow_back_probability: 0.5,
};

export default function PersonaDetailPage() {
  const { personaId } = useParams({ from: '/_layout/personas/$personaId' });
  const navigate = useNavigate();
  const { data: persona } = useQuery({
    queryKey: ['persona', personaId],
    queryFn: () => personasApi.get(personaId) as Promise<Persona>,
    enabled: personaId !== 'new',
  });

  const { register, handleSubmit, reset, formState: { errors, isSubmitting }, setError } = useForm<PersonaFormData>({
    resolver: zodResolver(personaSchema),
    defaultValues,
  });

  useEffect(() => {
    if (personaId === 'new') {
      reset(defaultValues);
      return;
    }

    if (persona) {
      reset({ ...defaultValues, ...persona });
    }
  }, [persona, personaId, reset]);

  const createMutation = useMutation({ mutationFn: personasApi.create });
  const updateMutation = useMutation({ mutationFn: (data: PersonaFormData) => personasApi.update(personaId, data) });

  const onSubmit = async (data: PersonaFormData) => {
    try {
      if (personaId === 'new') {
        await createMutation.mutateAsync(data);
      } else {
        await updateMutation.mutateAsync(data);
      }
      navigate({ to: '/personas' });
    } catch {
      setError('root', { message: 'Failed to save persona' });
    }
  };

  return (
    <div className="p-4 sm:p-6 max-w-4xl">
      <h1 className="text-xl sm:text-2xl md:text-3xl font-bold text-gray-900 mb-6">
        {personaId === 'new' ? 'Create Persona' : 'Edit Persona'}
      </h1>

      <Card>
        <CardContent className="p-6">
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <Label htmlFor="name">Name *</Label>
                <Input id="name" {...register('name')} className="mt-1" placeholder="e.g. Tech Enthusiast" />
                {errors.name && <p className="mt-1 text-xs text-red-500">{errors.name.message}</p>}
              </div>
              <div>
                <Label htmlFor="niche">Niche *</Label>
                <Input id="niche" {...register('niche')} className="mt-1" placeholder="e.g. Technology, Fashion" />
                {errors.niche && <p className="mt-1 text-xs text-red-500">{errors.niche.message}</p>}
              </div>
            </div>

            <div>
              <Label htmlFor="system_prompt">System Prompt *</Label>
              <Textarea
                id="system_prompt"
                {...register('system_prompt')}
                className="mt-1"
                rows={5}
                placeholder="Instructions for how this persona should generate content..."
              />
              {errors.system_prompt && <p className="mt-1 text-xs text-red-500">{errors.system_prompt.message}</p>}
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <Label htmlFor="tone">Tone</Label>
                <Select {...register('tone')} defaultValue="casual" className="mt-1">
                  <option value="casual">Casual</option>
                  <option value="professional">Professional</option>
                  <option value="humorous">Humorous</option>
                  <option value="inspirational">Inspirational</option>
                </Select>
              </div>
              <div>
                <Label htmlFor="language">Language</Label>
                <Input id="language" {...register('language')} className="mt-1" placeholder="en" />
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <Label htmlFor="vocab_level">Vocabulary Level</Label>
                <Select {...register('vocab_level')} defaultValue="conversational" className="mt-1">
                  <option value="simple">Simple</option>
                  <option value="conversational">Conversational</option>
                  <option value="formal">Formal</option>
                  <option value="technical">Technical</option>
                </Select>
              </div>
              <div>
                <Label htmlFor="emoji_usage">Emoji Usage</Label>
                <Select {...register('emoji_usage')} defaultValue="moderate" className="mt-1">
                  <option value="none">None</option>
                  <option value="minimal">Minimal</option>
                  <option value="moderate">Moderate</option>
                  <option value="heavy">Heavy</option>
                </Select>
              </div>
            </div>

            <div>
              <Label htmlFor="hashtag_strategy">Hashtag Strategy</Label>
              <Select {...register('hashtag_strategy')} defaultValue="relevant" className="mt-1">
                <option value="none">None</option>
                <option value="minimal">Minimal (1-2)</option>
                <option value="relevant">Relevant (3-5)</option>
                <option value="aggressive">Aggressive (6+)</option>
              </Select>
            </div>

            <div>
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Behavioral Probabilities</h3>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div>
                  <Label htmlFor="reply_probability">Reply Probability</Label>
                  <Input
                    id="reply_probability"
                    type="number"
                    step="0.1"
                    min="0"
                    max="1"
                    {...register('reply_probability')}
                    className="mt-1"
                  />
                </div>
                <div>
                  <Label htmlFor="like_probability">Like Probability</Label>
                  <Input
                    id="like_probability"
                    type="number"
                    step="0.1"
                    min="0"
                    max="1"
                    {...register('like_probability')}
                    className="mt-1"
                  />
                </div>
                <div>
                  <Label htmlFor="follow_back_probability">Follow Back Probability</Label>
                  <Input
                    id="follow_back_probability"
                    type="number"
                    step="0.1"
                    min="0"
                    max="1"
                    {...register('follow_back_probability')}
                    className="mt-1"
                  />
                </div>
              </div>
            </div>

            {errors.root && <p className="text-sm text-red-500 bg-red-50 px-4 py-2 rounded">{errors.root.message}</p>}

            <div className="flex gap-4">
              <Button
                type="submit"
                disabled={isSubmitting || createMutation.isPending || updateMutation.isPending}
                className="flex-1 sm:flex-none"
              >
                {isSubmitting || createMutation.isPending || updateMutation.isPending ? 'Saving...' : 'Save Persona'}
              </Button>
              <Button
                type="button"
                variant="outline"
                onClick={() => navigate({ to: '/personas' })}
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
