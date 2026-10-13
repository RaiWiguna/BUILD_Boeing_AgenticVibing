import type { ComponentType } from 'react';
import { createBrowserRouter, Navigate, type RouteObject } from 'react-router';
import { MockControlPanel } from '@/app/devtools/MockControlPanel';
import { AppShell } from '@/components/layout/AppShell';
import { LoginPage } from '@/features/auth/LoginPage';
import { LandingPage } from '@/features/landing/LandingPage';
import { ChooseSessionPage, SessionsPage } from '@/features/sessions/SessionsPage';
import { RedirectKeepSearch, RequireAuth, SettingsIndex } from './guards';
import { NotFound, RouteError } from './RouteError';
import { LOGIN_PATH } from '@/lib/links';

/** Route-level code splitting: each area loads its own chunk on first visit. */
function page<M>(load: () => Promise<M>, name: keyof M): Pick<RouteObject, 'lazy'> {
  return { lazy: async () => ({ Component: (await load())[name] as ComponentType }) };
}
const session = () => import('@/features/workspace/SessionLayout');
const workspace = () => import('@/features/workspace/WorkspacePage');
const memory = () => import('@/features/memory/MemoryPage');
const review = () => import('@/features/review/ReviewLayout');
const transcript = () => import('@/features/review/TranscriptPage');
const findings = () => import('@/features/review/FindingsPage');
const options = () => import('@/features/review/OptionsPage');
const debrief = () => import('@/features/debrief/DebriefPage');
const metrics = () => import('@/features/debrief/MetricsPage');
const ask = () => import('@/features/queries/AskPage');
const imports = () => import('@/features/imports/ImportPage');
const settings = () => import('@/features/settings/SettingsLayout');
const account = () => import('@/features/settings/AccountPage');
const admin = () => import('@/features/settings/AdminPages');
const help = () => import('@/features/settings/HelpPage');

/** Developer scenario controls stay out of the UI unless enabled for this browser. */
function devtoolsEnabled() {
  try {
    return localStorage.getItem('flowlens.devtools') === '1';
  } catch {
    return false;
  }
}

export const routes: RouteObject[] = [
  // Public product introduction. It deliberately carries no link into the sign-in flow.
  { path: '/', element: <LandingPage />, errorElement: <RouteError /> },
  { path: LOGIN_PATH, element: <LoginPage />, errorElement: <RouteError /> },
  // Old sign-in URL keeps working (bookmarks, ?next= links).
  { path: '/login', element: <RedirectKeepSearch to={LOGIN_PATH} /> },
  {
    // Pathless layout: every app route below requires a session.
    element: (
      <RequireAuth>
        <AppShell devtools={devtoolsEnabled() ? (collapsed) => <MockControlPanel collapsed={collapsed} /> : undefined} />
      </RequireAuth>
    ),
    errorElement: <RouteError />,
    children: [
      { path: 'sessions', element: <SessionsPage /> },
      { path: 'sessions/import', ...page(imports, 'ImportPage') },
      { path: 'choose/:area', element: <ChooseSessionPage /> },
      {
        path: 's/:sid',
        ...page(session, 'SessionLayout'),
        children: [
          { index: true, element: <RedirectKeepSearch to="workspace" /> },
          { path: 'workspace', ...page(workspace, 'WorkspacePage') },
          { path: 'memory', ...page(memory, 'MemoryIndex') },
          { path: 'memory/runway', ...page(memory, 'MemoryRunwayPage') },
          { path: 'memory/:entityId', ...page(memory, 'MemoryObjectPage') },
          {
            path: 'review',
            ...page(review, 'ReviewLayout'),
            children: [
              { index: true, element: <RedirectKeepSearch to="transcript" /> },
              { path: 'transcript', ...page(transcript, 'TranscriptPage') },
              { path: 'findings', ...page(findings, 'FindingsPage') },
              { path: 'options', ...page(options, 'OptionsPage') },
            ],
          },
          { path: 'debrief', ...page(debrief, 'DebriefPage') },
          { path: 'metrics', ...page(metrics, 'MetricsPage') },
          { path: 'ask', ...page(ask, 'AskPage') },
        ],
      },
      {
        path: 'settings',
        ...page(settings, 'SettingsLayout'),
        children: [
          { index: true, element: <SettingsIndex /> },
          { path: 'account', ...page(account, 'AccountPage') },
          { path: 'users', ...page(admin, 'UsersPage') },
          { path: 'access', ...page(admin, 'AccessPage') },
          { path: 'providers', ...page(admin, 'ProvidersPage') },
          { path: 'jobs', ...page(admin, 'JobsPage') },
          { path: 'storage', ...page(admin, 'StoragePage') },
          { path: 'audit', ...page(admin, 'AuditPage') },
          { path: 'retention', ...page(admin, 'RetentionPage') },
          { path: '*', element: <Navigate to="/settings" replace /> },
        ],
      },
      { path: 'help', ...page(help, 'HelpPage') },
      { path: '*', element: <NotFound /> },
    ],
  },
];

export const router = createBrowserRouter(routes);
