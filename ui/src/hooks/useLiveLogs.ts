import { useState, useEffect } from 'react';
import { TaskLog } from '../types/api';

export function useLiveLogs(taskId: string) {
  const [logs, setLogs] = useState<TaskLog[]>([]);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    if (!taskId) return;
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const ws = new WebSocket(`${protocol}//${window.location.host}/ws/tasks/${taskId}/logs`);
    ws.onopen = () => setConnected(true);
    ws.onclose = () => setConnected(false);
    ws.onmessage = (event) => {
      try {
        const log: TaskLog = JSON.parse(event.data);
        setLogs(prev => [...prev, log]);
      } catch {
        // ignore parse errors
      }
    };
    return () => ws.close();
  }, [taskId]);

  return { logs, connected };
}
