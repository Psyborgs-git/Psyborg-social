import { useState } from 'react';
import { Label } from '../ui/Label';
import { Input } from '../ui/Input';
import { Select } from '../ui/Select';

const PRESETS = [
  { label: 'Every hour', value: '0 * * * *' },
  { label: 'Daily at 9am', value: '0 9 * * *' },
  { label: 'Twice daily', value: '0 9,18 * * *' },
  { label: 'Every 15 minutes', value: '*/15 * * * *' },
  { label: 'Weekdays at 10am', value: '0 10 * * 1-5' },
  { label: 'Custom', value: 'custom' },
];

interface CronBuilderProps {
  value: string;
  onChange: (value: string) => void;
}

export function CronBuilder({ value, onChange }: CronBuilderProps) {
  const isPreset = PRESETS.slice(0, -1).some(p => p.value === value);
  const [mode, setMode] = useState<string>(isPreset ? value : 'custom');

  const handlePresetChange = (selected: string) => {
    setMode(selected);
    if (selected !== 'custom') onChange(selected);
  };

  return (
    <div className="space-y-3">
      <div>
        <Label htmlFor="cron-preset">Schedule Preset</Label>
        <Select
          id="cron-preset"
          value={mode}
          onChange={e => handlePresetChange(e.target.value)}
          className="mt-1"
        >
          {PRESETS.map(p => (
            <option key={p.value} value={p.value}>{p.label}</option>
          ))}
        </Select>
      </div>
      {mode === 'custom' && (
        <div>
          <Label htmlFor="cron-custom">Cron Expression</Label>
          <Input
            id="cron-custom"
            placeholder="* * * * *"
            value={value}
            onChange={e => onChange(e.target.value)}
            className="mt-1 font-mono"
          />
          <p className="mt-1 text-xs text-gray-500">Format: minute hour day-of-month month day-of-week</p>
        </div>
      )}
      {mode !== 'custom' && (
        <p className="text-xs text-gray-500">Expression: <code className="font-mono bg-gray-100 px-1 rounded">{value}</code></p>
      )}
    </div>
  );
}
