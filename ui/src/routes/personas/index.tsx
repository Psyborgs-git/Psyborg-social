import { Link } from '@tanstack/react-router';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Card, CardContent } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { Badge } from '../../components/ui/Badge';
import { Plus, Trash2 } from 'lucide-react';
import { personasApi } from '../../api/personas';

export default function PersonasPage() {
  const { data: personas, isLoading } = useQuery({
    queryKey: ['personas'],
    queryFn: personasApi.list,
  });
  const qc = useQueryClient();
  const deleteMutation = useMutation({
    mutationFn: personasApi.delete,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['personas'] }),
  });

  return (
    <div className="p-4 sm:p-6 space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <h1 className="text-xl sm:text-2xl md:text-3xl font-bold text-gray-900">Personas</h1>
        <Link to="/personas/$personaId" params={{ personaId: 'new' }}>
          <Button size="sm" className="w-full sm:w-auto"><Plus className="w-4 h-4 mr-2" />New Persona</Button>
        </Link>
      </div>

      {isLoading && <p className="text-gray-500">Loading...</p>}

      <div className="grid gap-3 sm:gap-4">
        {personas?.map(persona => (
          <Card key={persona.id}>
            <CardContent className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4 py-4">
              <Link to="/personas/$personaId" params={{ personaId: persona.id }} className="flex-1 min-w-0 hover:opacity-75">
                <div className="min-w-0">
                  <h3 className="font-semibold text-gray-900 truncate">{persona.name}</h3>
                  <p className="text-xs sm:text-sm text-gray-500 line-clamp-2">{persona.system_prompt}</p>
                  <div className="flex flex-wrap gap-2 mt-3">
                    <Badge variant="secondary">{persona.tone}</Badge>
                    <Badge variant="secondary">{persona.niche}</Badge>
                    <Badge variant="secondary">{persona.language}</Badge>
                  </div>
                </div>
              </Link>
              <div className="flex gap-2 flex-shrink-0">
                <Link to="/personas/$personaId" params={{ personaId: persona.id }}>
                  <Button variant="outline" size="sm">Edit</Button>
                </Link>
                <Button
                  variant="destructive"
                  size="sm"
                  onClick={() => deleteMutation.mutate(persona.id)}
                  disabled={deleteMutation.isPending}
                >
                  <Trash2 className="w-4 h-4" />
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
