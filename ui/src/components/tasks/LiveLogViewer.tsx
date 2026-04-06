import { useRef, useEffect } from 'react';
import { clsx } from 'clsx';
import { useLiveLogs } from '../../hooks/useLiveLogs';
import { TaskLog } from '../../types/api';

export function LiveLogViewer({ taskId }: { taskId: string }) {
  const { logs, connected } = useLiveLogs(taskId);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        <span className="text-sm font-medium text-gray-700">Live Logs</span>
        <span className={clsx('inline-block w-2 h-2 rounded-full', connected ? 'bg-green-500' : 'bg-gray-400')} />
        <span className="text-xs text-gray-500">{connected ? 'Connected' : 'Disconnected'}</span>
      </div>
      <div className="bg-zinc-950 rounded-lg p-4 font-mono text-sm h-64 overflow-y-auto">
        {logs.length === 0 && (
          <span className="text-zinc-500">Waiting for logs...</span>
        )}
        {logs.map((log: TaskLog, i: number) => (
          <div key={i} className={clsx('flex gap-2 leading-5', {
            'text-red-400': log.level === 'ERROR',
            'text-yellow-400': log.level === 'WARNING',
            'text-green-300': log.level === 'INFO',
          })}>
            <span className="text-zinc-500 shrink-0">{new Date(log.timestamp).toLocaleTimeString()}</span>
            <span className="text-zinc-400 shrink-0">[{log.level}]</span>
            <span>{log.message}</span>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
