import { lazy, Suspense } from 'react';
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { ThemeProvider } from './contexts/ThemeContext';
import { AppShell } from './components/layout/AppShell';
import { SkeletonCard } from './components/ui/Skeleton';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { navigation } from './data/navigation';
import { Login } from './pages/Login';

const load = <T extends Record<string, React.ComponentType>,>(
factory: () => Promise<T>,
name: keyof T) =>
lazy(() => factory().then((module) => ({ default: module[name] })));

const CommandCenter = load(() => import('./pages/CommandCenter'), 'CommandCenter');
const Copilot = load(() => import('./pages/Copilot'), 'Copilot');
const Investigations = load(() => import('./pages/Investigations'), 'Investigations');
const Detections = load(() => import('./pages/Detections'), 'Detections');
const Graph = load(() => import('./pages/Graph'), 'Graph');
const Policies = load(() => import('./pages/Policies'), 'Policies');
const Controls = load(() => import('./pages/Controls'), 'Controls');
const Frameworks = load(() => import('./pages/Frameworks'), 'Frameworks');
const RiskCenter = load(() => import('./pages/RiskCenter'), 'RiskCenter');
const Findings = load(() => import('./pages/Findings'), 'Findings');
const Employees = load(() => import('./pages/org/Employees'), 'Employees');
const Identity = load(() => import('./pages/org/Identity'), 'Identity');
const Devices = load(() => import('./pages/org/Devices'), 'Devices');
const Applications = load(() => import('./pages/org/Applications'), 'Applications');
const CloudAssets = load(() => import('./pages/org/CloudAssets'), 'CloudAssets');
const Vendors = load(() => import('./pages/org/Vendors'), 'Vendors');
const DataInventory = load(() => import('./pages/privacy/DataInventory'), 'DataInventory');
const Consent = load(() => import('./pages/privacy/Consent'), 'Consent');
const Evidence = load(() => import('./pages/Evidence'), 'Evidence');
const AuditLog = load(() => import('./pages/AuditLog'), 'AuditLog');
const Reports = load(() => import('./pages/Reports'), 'Reports');
const Settings = load(() => import('./pages/Settings'), 'Settings');
const Profile = load(() => import('./pages/Profile'), 'Profile');
const NotFound = load(() => import('./pages/NotFound'), 'NotFound');

function RouteFallback() {
  return (
    <div className="space-y-6" role="status" aria-label="Loading workspace">
      <div className="h-8 w-64 animate-pulse rounded-lg bg-muted" />
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) =>
        <SkeletonCard key={i} />
        )}
      </div>
      <div className="h-80 animate-pulse rounded-xl bg-muted" />
    </div>);

}

/** Every route is lazy-loaded behind a single consistent skeleton. */
function page(element: React.ReactNode) {
  return <Suspense fallback={<RouteFallback />}>{element}</Suspense>;
}

export function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <SignedInApp />
      </AuthProvider>
    </ThemeProvider>);

}

/**
 * Nothing behind this point renders without a server-confirmed session.
 * There is deliberately no automatic or pre-filled sign-in: the app never
 * holds credentials of its own.
 */
function SignedInApp() {
  const { state, can } = useAuth();

  if (state.status === 'loading') {
    return (
      <div className="min-h-screen bg-background p-6">
        <RouteFallback />
      </div>);

  }
  if (state.status === 'anonymous') return <Login notice={state.notice} />;

  // Roles without the dashboard (e.g. employee) land on the first screen they can read.
  const home = navigation.
  flatMap((group) => group.items).
  find((item) => item.resource && can(item.resource))?.to ?? '/profile';

  return (
      <BrowserRouter>
        <Routes>
          <Route element={<AppShell />}>
            <Route
              index
              element={can('dashboard') ? page(<CommandCenter />) : <Navigate to={home} replace />} />

            {/* Intelligence */}
            <Route path="/copilot" element={page(<Copilot />)} />
            <Route path="/investigations" element={page(<Investigations />)} />
            <Route path="/detections" element={page(<Detections />)} />
            <Route path="/graph" element={page(<Graph />)} />

            {/* Governance */}
            <Route path="/policies" element={page(<Policies />)} />
            <Route path="/controls" element={page(<Controls />)} />
            <Route path="/frameworks" element={page(<Frameworks />)} />

            {/* Risk */}
            <Route path="/risk" element={page(<RiskCenter />)} />
            <Route path="/findings" element={page(<Findings />)} />

            {/* Organization */}
            <Route path="/org/employees" element={page(<Employees />)} />
            <Route path="/org/identity" element={page(<Identity />)} />
            <Route path="/org/devices" element={page(<Devices />)} />
            <Route path="/org/applications" element={page(<Applications />)} />
            <Route path="/org/cloud" element={page(<CloudAssets />)} />
            <Route path="/org/vendors" element={page(<Vendors />)} />

            {/* Privacy */}
            <Route path="/privacy/inventory" element={page(<DataInventory />)} />
            <Route path="/privacy/consent" element={page(<Consent />)} />

            {/* Assurance */}
            <Route path="/evidence" element={page(<Evidence />)} />
            <Route path="/audit-log" element={page(<AuditLog />)} />
            <Route path="/reports" element={page(<Reports />)} />

            {/* System */}
            <Route path="/settings" element={page(<Settings />)} />
            <Route path="/profile" element={page(<Profile />)} />

            <Route path="/404" element={page(<NotFound />)} />
            <Route path="*" element={<Navigate to="/404" replace />} />
          </Route>
        </Routes>
      </BrowserRouter>);

}