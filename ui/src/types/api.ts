export interface Account {
  id: string;
  username: string;
  display_name?: string;
  platform_id: string;
  platform?: Platform;
  status: AccountStatus;
  daily_action_limit: number;
  warmup_phase: boolean;
  created_at: string;
  updated_at: string;
}

export type AccountStatus = 'active' | 'paused' | 'suspended' | 'credential_error' | 'warming_up';

export interface Platform {
  id: string;
  slug: string;
  display_name: string;
}

export interface Task {
  id: string;
  account_id: string;
  task_type: TaskType;
  status: TaskStatus;
  scheduled_at?: string;
  started_at?: string;
  completed_at?: string;
  config: Record<string, unknown>;
  retry_count: number;
  created_at: string;
}

export type TaskType = 'post' | 'comment' | 'reply_dm' | 'like' | 'follow' | 'unfollow' | 'story' | 'reel' | 'research' | 'engage_feed' | 'warmup';
export type TaskStatus = 'pending' | 'queued' | 'running' | 'success' | 'failed' | 'retrying' | 'skipped';

export interface TaskLog {
  id: string;
  task_id: string;
  timestamp: string;
  level: 'INFO' | 'WARNING' | 'ERROR';
  message: string;
  metadata: Record<string, unknown>;
}

export interface Campaign {
  id: string;
  name: string;
  description?: string;
  is_active: boolean;
  cron_expression?: string;
  created_at: string;
  updated_at: string;
}

export interface PostRecord {
  id: string;
  task_id: string;
  account_id: string;
  platform_post_id: string;
  platform_url?: string;
  content_text?: string;
  published_at: string;
  likes_count: number;
  comments_count: number;
  shares_count: number;
  views_count: number;
}

export interface AnalyticsSummary {
  active_accounts: number;
  posts_today: number;
  dms_replied: number;
  tasks_running: number;
  total_tasks: number;
  success_rate: number;
}

export interface User {
  id: string;
  username: string;
  is_admin: boolean;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: User;
}
