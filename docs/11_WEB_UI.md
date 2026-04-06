# Web UI Dashboard

The SocialMind dashboard is a React + TypeScript single-page application served at port 3000. It provides full visibility and control over all automation — accounts, campaigns, tasks, analytics, and real-time logs.

---

## Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| Framework | React 18 | UI component framework |
| Build tool | Vite 5 | Dev server + production builds |
| Language | TypeScript 5 | Type-safe frontend code |
| Styling | Tailwind CSS 3 | Utility-first styling |
| Components | shadcn/ui | Accessible, composable components |
| Routing | TanStack Router | Type-safe file-based routing |
| Server state | TanStack Query | API fetching, caching, invalidation |
| Client state | Zustand | Auth state, UI state, toasts |
| Charts | Recharts | Analytics visualizations |
| Real-time | native WebSocket | Live task log streaming |
| Forms | React Hook Form + Zod | Validated forms |
| Icons | Lucide React | Icon set |
| HTTP client | Axios | API calls |

---

## Application Structure

```
ui/
├── src/
│   ├── app/                      # Root app setup, providers, router
│   │   ├── App.tsx
│   │   └── providers.tsx         # QueryClient, auth, etc.
│   ├── routes/                   # TanStack Router file-based routes
│   │   ├── _layout.tsx           # Root layout with sidebar
│   │   ├── index.tsx             # Dashboard home
│   │   ├── accounts/
│   │   │   ├── index.tsx         # Account list
│   │   │   ├── $accountId.tsx    # Account detail
│   │   │   └── new.tsx           # Add account form
│   │   ├── campaigns/
│   │   │   ├── index.tsx
│   │   │   ├── $campaignId.tsx
│   │   │   └── new.tsx
│   │   ├── tasks/
│   │   │   ├── index.tsx         # Task queue view
│   │   │   └── $taskId.tsx       # Task detail + logs
│   │   ├── analytics/
│   │   │   └── index.tsx         # Engagement analytics
│   │   ├── proxies/
│   │   │   └── index.tsx         # Proxy pool management
│   │   ├── personas/
│   │   │   ├── index.tsx
│   │   │   └── $personaId.tsx
│   │   └── settings/
│   │       └── index.tsx
│   ├── components/               # Shared UI components
│   │   ├── accounts/
│   │   │   ├── AccountCard.tsx
│   │   │   ├── AccountStatusBadge.tsx
│   │   │   └── AddAccountDialog.tsx
│   │   ├── campaigns/
│   │   │   ├── CampaignForm.tsx
│   │   │   └── CronBuilder.tsx   # Visual cron expression builder
│   │   ├── tasks/
│   │   │   ├── TaskTable.tsx
│   │   │   ├── TaskStatusBadge.tsx
│   │   │   └── LiveLogViewer.tsx # Real-time log stream
│   │   ├── analytics/
│   │   │   ├── EngagementChart.tsx
│   │   │   ├── PostHeatmap.tsx
│   │   │   └── PlatformBreakdown.tsx
│   │   └── ui/                   # shadcn/ui base components
│   ├── hooks/
│   │   ├── useAccounts.ts
│   │   ├── useTasks.ts
│   │   ├── useLiveLogs.ts        # WebSocket hook
│   │   └── useAuth.ts
│   ├── api/
│   │   ├── client.ts             # Axios instance with auth
│   │   ├── accounts.ts           # Account API functions
│   │   ├── campaigns.ts
│   │   ├── tasks.ts
│   │   └── analytics.ts
│   ├── stores/
│   │   └── auth.ts               # Zustand auth store
│   └── types/
│       └── api.ts                # TypeScript types matching backend schemas
```

---

## Key Pages

### Dashboard Home (`/`)

```tsx
// src/routes/index.tsx
export default function Dashboard() {
  const { data: summary } = useQuery({
    queryKey: ["dashboard-summary"],
    queryFn: api.analytics.getSummary,
    refetchInterval: 30_000,
  });

  return (
    <div className="grid grid-cols-4 gap-4 p-6">
      {/* KPI Cards */}
      <StatCard title="Active Accounts" value={summary?.activeAccounts} icon={Users} />
      <StatCard title="Posts Today" value={summary?.postsToday} icon={Send} />
      <StatCard title="DMs Replied" value={summary?.dmsReplied} icon={MessageSquare} />
      <StatCard title="Tasks Running" value={summary?.tasksRunning} icon={Activity} />

      {/* Recent task activity */}
      <div className="col-span-4">
        <TaskActivityFeed limit={20} />
      </div>

      {/* Engagement chart */}
      <div className="col-span-2">
        <EngagementChart period="7d" />
      </div>

      {/* Platform breakdown */}
      <div className="col-span-2">
        <PlatformBreakdown />
      </div>
    </div>
  );
}
```

### Account Detail (`/accounts/:accountId`)

```tsx
// src/routes/accounts/$accountId.tsx
export default function AccountDetail() {
  const { accountId } = useParams();
  const { data: account } = useAccount(accountId);
  const { data: tasks } = useTasks({ accountId, limit: 20 });
  const { data: posts } = usePostRecords({ accountId, limit: 10 });

  return (
    <div className="space-y-6 p-6">
      {/* Account header with status */}
      <AccountHeader account={account} />

      {/* Action buttons */}
      <div className="flex gap-2">
        <Button onClick={() => createTask({ accountId, type: "post" })}>
          Post Now
        </Button>
        <Button variant="outline" onClick={() => createTask({ accountId, type: "engage_feed" })}>
          Engage Feed
        </Button>
        <Button variant="outline" onClick={() => createTask({ accountId, type: "reply_dm" })}>
          Reply DMs
        </Button>
        <Button variant="destructive" onClick={() => pauseAccount(accountId)}>
          Pause
        </Button>
      </div>

      {/* Rate limit usage bars */}
      <RateLimitUsage accountId={accountId} />

      {/* Recent posts */}
      <PostGrid posts={posts} />

      {/* Recent tasks */}
      <TaskTable tasks={tasks} />
    </div>
  );
}
```

### Live Task Logs

```tsx
// src/components/tasks/LiveLogViewer.tsx
export function LiveLogViewer({ taskId }: { taskId: string }) {
  const [logs, setLogs] = useState<TaskLog[]>([]);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const ws = new WebSocket(`ws://localhost:8000/ws/tasks/${taskId}/logs`);
    ws.onmessage = (event) => {
      const log: TaskLog = JSON.parse(event.data);
      setLogs(prev => [...prev, log]);
      bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    };
    return () => ws.close();
  }, [taskId]);

  return (
    <div className="bg-zinc-950 rounded-lg p-4 font-mono text-sm h-64 overflow-y-auto">
      {logs.map((log, i) => (
        <div key={i} className={cn("flex gap-2", {
          "text-red-400": log.level === "ERROR",
          "text-yellow-400": log.level === "WARNING",
          "text-zinc-300": log.level === "INFO",
        })}>
          <span className="text-zinc-500">{formatTime(log.timestamp)}</span>
          <span className="font-bold">[{log.level}]</span>
          <span>{log.message}</span>
        </div>
      ))}
      <div ref={bottomRef} />
    </div>
  );
}
```

### Campaign Builder

```tsx
// src/components/campaigns/CampaignForm.tsx
const campaignSchema = z.object({
  name: z.string().min(1),
  accountIds: z.array(z.string()).min(1, "Select at least one account"),
  taskType: z.enum(["post", "engage_feed", "respond_dms", "research"]),
  cronExpression: z.string().min(1),
  config: z.object({
    prompt: z.string().optional(),
    postType: z.enum(["feed", "story", "reel"]).optional(),
    includeImage: z.boolean().default(true),
    durationMinutes: z.number().min(1).max(60).optional(),
  }),
});

export function CampaignForm() {
  const form = useForm({ resolver: zodResolver(campaignSchema) });
  const createCampaign = useCreateCampaign();

  return (
    <Form {...form}>
      <FormField name="name" label="Campaign Name" />
      <FormField name="taskType" label="Task Type">
        <Select options={TASK_TYPES} />
      </FormField>
      <FormField name="accountIds" label="Accounts">
        <AccountMultiSelect />
      </FormField>
      <FormField name="cronExpression" label="Schedule">
        <CronBuilder />  {/* Visual cron builder with presets */}
      </FormField>
      <FormField name="config.prompt" label="Content Prompt" />
      <Button type="submit" onClick={form.handleSubmit(createCampaign.mutate)}>
        Create Campaign
      </Button>
    </Form>
  );
}
```

---

## API Contract

The UI communicates exclusively with the FastAPI backend. All endpoints are prefixed with `/api/v1/`.

### Accounts

```
GET    /api/v1/accounts              → List accounts (filterable)
POST   /api/v1/accounts              → Create account
GET    /api/v1/accounts/:id          → Get account detail
PATCH  /api/v1/accounts/:id          → Update account
DELETE /api/v1/accounts/:id          → Delete account
POST   /api/v1/accounts/:id/pause    → Pause account
POST   /api/v1/accounts/:id/resume   → Resume account
GET    /api/v1/accounts/:id/posts    → Recent posts
GET    /api/v1/accounts/:id/rate-limits → Rate limit usage
```

### Tasks

```
GET    /api/v1/tasks                 → List tasks (paginated, filterable)
POST   /api/v1/tasks                 → Create and dispatch task
GET    /api/v1/tasks/:id             → Task detail
DELETE /api/v1/tasks/:id             → Cancel task
GET    /api/v1/tasks/:id/logs        → Task logs
WS     /ws/tasks/:id/logs            → Live log stream
```

### Campaigns

```
GET    /api/v1/campaigns             → List campaigns
POST   /api/v1/campaigns             → Create campaign
PATCH  /api/v1/campaigns/:id         → Update campaign
DELETE /api/v1/campaigns/:id         → Delete campaign
POST   /api/v1/campaigns/:id/pause   → Pause campaign
POST   /api/v1/campaigns/:id/resume  → Resume campaign
```

### Analytics

```
GET    /api/v1/analytics/summary     → Dashboard KPIs
GET    /api/v1/analytics/engagement  → Engagement over time (query: period, accountId)
GET    /api/v1/analytics/posts       → Post performance
GET    /api/v1/analytics/platforms   → Per-platform breakdown
```

---

## Authentication

The dashboard uses JWT-based authentication. On first setup, a single admin user is created.

```typescript
// src/stores/auth.ts
interface AuthStore {
  token: string | null;
  user: User | null;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
}

export const useAuth = create<AuthStore>((set) => ({
  token: localStorage.getItem("sm_token"),
  user: null,

  login: async (username, password) => {
    const resp = await axios.post("/api/v1/auth/token", { username, password });
    localStorage.setItem("sm_token", resp.data.access_token);
    set({ token: resp.data.access_token, user: resp.data.user });
  },

  logout: () => {
    localStorage.removeItem("sm_token");
    set({ token: null, user: null });
  },
}));
```

---

## Docker Build

The UI is built into a static bundle and served by Nginx:

```dockerfile
# docker/ui.Dockerfile
FROM node:20-alpine AS builder
WORKDIR /app
COPY ui/package*.json ./
RUN npm ci
COPY ui/ .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY docker/nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 3000
```

```nginx
# docker/nginx.conf
server {
    listen 3000;

    # Serve React SPA
    location / {
        root /usr/share/nginx/html;
        index index.html;
        try_files $uri $uri/ /index.html;  # SPA fallback
    }

    # Proxy API requests to FastAPI
    location /api/ {
        proxy_pass http://api:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # Proxy WebSocket
    location /ws/ {
        proxy_pass http://api:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```
