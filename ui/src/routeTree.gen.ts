import { createRootRoute, createRoute } from '@tanstack/react-router';
import Layout from './routes/_layout';
import LoginPage from './routes/login';
import DashboardPage from './routes/index';
import AccountsPage from './routes/accounts/index';
import NewAccountPage from './routes/accounts/new';
import AccountDetailPage from './routes/accounts/$accountId';
import CampaignsPage from './routes/campaigns/index';
import NewCampaignPage from './routes/campaigns/new';
import CampaignDetailPage from './routes/campaigns/$campaignId';
import PersonasPage from './routes/personas/index';
import PersonaDetailPage from './routes/personas/$personaId';
import MediaPage from './routes/media/index';
import SettingsPage from './routes/settings';
import TasksPage from './routes/tasks/index';
import AnalyticsPage from './routes/analytics/index';

const rootRoute = createRootRoute();

const loginRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/login',
  component: LoginPage,
});

const layoutRoute = createRoute({
  getParentRoute: () => rootRoute,
  id: '_layout',
  component: Layout,
});

const dashboardRoute = createRoute({
  getParentRoute: () => layoutRoute,
  path: '/',
  component: DashboardPage,
});

const accountsRoute = createRoute({
  getParentRoute: () => layoutRoute,
  path: '/accounts',
  component: AccountsPage,
});

const newAccountRoute = createRoute({
  getParentRoute: () => layoutRoute,
  path: '/accounts/new',
  component: NewAccountPage,
});

const accountDetailRoute = createRoute({
  getParentRoute: () => layoutRoute,
  path: '/accounts/$accountId',
  component: AccountDetailPage,
});

const campaignsRoute = createRoute({
  getParentRoute: () => layoutRoute,
  path: '/campaigns',
  component: CampaignsPage,
});

const newCampaignRoute = createRoute({
  getParentRoute: () => layoutRoute,
  path: '/campaigns/new',
  component: NewCampaignPage,
});

const campaignDetailRoute = createRoute({
  getParentRoute: () => layoutRoute,
  path: '/campaigns/$campaignId',
  component: CampaignDetailPage,
});

const personasRoute = createRoute({
  getParentRoute: () => layoutRoute,
  path: '/personas',
  component: PersonasPage,
});

const personaDetailRoute = createRoute({
  getParentRoute: () => layoutRoute,
  path: '/personas/$personaId',
  component: PersonaDetailPage,
});

const mediaRoute = createRoute({
  getParentRoute: () => layoutRoute,
  path: '/media',
  component: MediaPage,
});

const settingsRoute = createRoute({
  getParentRoute: () => layoutRoute,
  path: '/settings',
  component: SettingsPage,
});

const tasksRoute = createRoute({
  getParentRoute: () => layoutRoute,
  path: '/tasks',
  component: TasksPage,
});

const analyticsRoute = createRoute({
  getParentRoute: () => layoutRoute,
  path: '/analytics',
  component: AnalyticsPage,
});

export const routeTree = rootRoute.addChildren([
  loginRoute,
  layoutRoute.addChildren([
    dashboardRoute,
    accountsRoute,
    newAccountRoute,
    accountDetailRoute,
    campaignsRoute,
    newCampaignRoute,
    campaignDetailRoute,
    personasRoute,
    personaDetailRoute,
    mediaRoute,
    settingsRoute,
    tasksRoute,
    analyticsRoute,
  ]),
]);
