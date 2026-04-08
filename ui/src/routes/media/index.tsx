import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { Badge } from '../../components/ui/Badge';
import { Input } from '../../components/ui/Input';
import { Label } from '../../components/ui/Label';
import { Upload, Trash2, Download } from 'lucide-react';
import { mediaApi } from '../../api/media';

export default function MediaPage() {
  const [uploadingFile, setUploadingFile] = useState<File | null>(null);
  const { data: media, isLoading } = useQuery({
    queryKey: ['media'],
    queryFn: mediaApi.list,
  });
  const qc = useQueryClient();
  const uploadMutation = useMutation({
    mutationFn: (file: File) => mediaApi.upload(file),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['media'] });
      setUploadingFile(null);
    },
  });
  const deleteMutation = useMutation({
    mutationFn: mediaApi.delete,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['media'] }),
  });

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setUploadingFile(file);
    }
  };

  const handleUpload = async () => {
    if (uploadingFile) {
      await uploadMutation.mutateAsync(uploadingFile);
    }
  };

  const handleDownload = async (id: string, filename: string) => {
    const blob = await mediaApi.download(id, filename);
    const objectUrl = window.URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = objectUrl;
    anchor.download = filename;
    anchor.click();
    window.URL.revokeObjectURL(objectUrl);
  };

  function formatFileSize(bytes: number): string {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
  }

  function getMediaIcon(type: string): string {
    switch (type) {
      case 'image':
        return '🖼️';
      case 'video':
        return '🎬';
      case 'audio':
        return '🎵';
      case 'gif':
        return '🎞️';
      default:
        return '📄';
    }
  }

  return (
    <div className="p-4 sm:p-6 space-y-6">
      <h1 className="text-xl sm:text-2xl md:text-3xl font-bold text-gray-900">Media Library</h1>

      <Card>
        <CardHeader><CardTitle className="text-base sm:text-lg">Upload Media</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          <div>
            <Label htmlFor="file-input">Select File (Image, Video, Audio, GIF)</Label>
            <div className="mt-2 flex flex-col sm:flex-row gap-3">
              <Input
                id="file-input"
                type="file"
                onChange={handleFileSelect}
                disabled={uploadMutation.isPending}
                className="flex-1"
                accept="image/*,video/*,audio/*,.gif"
              />
              <Button
                onClick={handleUpload}
                disabled={!uploadingFile || uploadMutation.isPending}
                className="w-full sm:w-auto"
              >
                <Upload className="w-4 h-4 mr-2" />
                {uploadMutation.isPending ? 'Uploading...' : 'Upload'}
              </Button>
            </div>
            {uploadingFile && <p className="mt-2 text-xs text-gray-500">Selected: {uploadingFile.name}</p>}
          </div>
        </CardContent>
      </Card>

      <div>
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Your Media</h2>
        {isLoading && <p className="text-gray-500">Loading...</p>}

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {media?.map(item => (
            <Card key={item.id}>
              <CardContent className="p-4">
                <div className="mb-3">
                  <div className="text-3xl mb-2">{getMediaIcon(item.media_type)}</div>
                  <h3 className="font-semibold text-gray-900 text-sm truncate">{item.filename}</h3>
                  <p className="text-xs text-gray-500 mt-1">{formatFileSize(item.file_size_bytes || 0)}</p>
                </div>

                <div className="flex flex-wrap gap-2 mb-4">
                  <Badge variant="secondary" className="text-xs">{item.media_type}</Badge>
                  {item.width && item.height && (
                    <Badge variant="secondary" className="text-xs">{item.width}x{item.height}</Badge>
                  )}
                  {item.duration_seconds && (
                    <Badge variant="secondary" className="text-xs">{Math.round(item.duration_seconds)}s</Badge>
                  )}
                </div>

                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleDownload(item.id, item.filename)}
                    className="flex-1"
                  >
                    <Download className="w-3 h-3 mr-1" />
                    Download
                  </Button>
                  <Button
                    variant="destructive"
                    size="sm"
                    onClick={() => deleteMutation.mutate(item.id)}
                    disabled={deleteMutation.isPending}
                  >
                    <Trash2 className="w-3 h-3" />
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>

        {media?.length === 0 && (
          <div className="text-center py-12">
            <p className="text-gray-500">No media files yet. Upload your first file to get started!</p>
          </div>
        )}
      </div>
    </div>
  );
}
