import {
  Activity,
  Boxes,
  Cloud,
  Cpu,
  FileBadge,
  FileBarChart,
  FileText,
  Fingerprint,
  Gauge,
  Handshake,
  Laptop,
  LayoutDashboard,
  ScanSearch,
  ScrollText,
  Settings,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  Network,
  Users,
  type LucideIcon } from
'lucide-react';

export interface NavItem {
  to: string;
  label: string;
  icon: LucideIcon;
  badge?: string;
  tone?: 'ai' | 'critical';
  /** Backend permission-matrix resource this screen reads. Items the signed-in
   * role cannot read are hidden; items without one are always shown. */
  resource?: string;
}

export interface NavGroup {
  label: string;
  items: NavItem[];
}

export const navigation: NavGroup[] = [
{
  label: 'Overview',
  items: [{ to: '/', label: 'Command Center', icon: LayoutDashboard, resource: 'dashboard' }]
},
{
  label: 'Intelligence',
  items: [
  { to: '/copilot', label: 'Sentinel AI', icon: Sparkles, tone: 'ai', resource: 'copilot' },
  { to: '/investigations', label: 'Investigations', icon: ScanSearch, resource: 'risks' },
  { to: '/detections', label: 'Detections', icon: ShieldAlert, resource: 'detection-rules' },
  { to: '/graph', label: 'Organization Graph', icon: Network, resource: 'organization-graph' }]

},
{
  label: 'Governance',
  items: [
  { to: '/policies', label: 'Policies', icon: FileText, resource: 'policies' },
  { to: '/controls', label: 'Controls', icon: ShieldCheck, resource: 'controls' },
  { to: '/frameworks', label: 'Frameworks', icon: ScrollText, resource: 'frameworks' }]

},
{
  label: 'Risk',
  items: [
  { to: '/risk', label: 'Risk Center', icon: ShieldAlert, badge: '4', tone: 'critical', resource: 'risks' },
  { to: '/findings', label: 'Findings', icon: Gauge, badge: '23', resource: 'findings' }]

},
{
  label: 'Organization',
  items: [
  { to: '/org/employees', label: 'Employees', icon: Users, resource: 'employees' },
  { to: '/org/identity', label: 'Identity & Access', icon: Fingerprint, resource: 'iam' },
  { to: '/org/devices', label: 'Devices', icon: Laptop, resource: 'devices' },
  { to: '/org/applications', label: 'Applications', icon: Boxes, resource: 'applications' },
  { to: '/org/cloud', label: 'Cloud Assets', icon: Cloud, resource: 'cloud-assets' },
  { to: '/org/vendors', label: 'Third-Party Vendors', icon: Handshake, resource: 'vendors' }]

},
{
  label: 'Privacy',
  items: [
  { to: '/privacy/inventory', label: 'DPDP Data Inventory', icon: Cpu, resource: 'dpdp/personal-data' },
  { to: '/privacy/consent', label: 'Consent Management', icon: FileBadge, resource: 'dpdp/consents' }]

},
{
  label: 'Assurance',
  items: [
  { to: '/evidence', label: 'Evidence Repository', icon: FileBadge, resource: 'evidence' },
  { to: '/audit-log', label: 'Audit Logs', icon: Activity, resource: 'audit-logs' },
  { to: '/reports', label: 'Reports', icon: FileBarChart, resource: 'reports' }]

},
{
  label: 'System',
  items: [{ to: '/settings', label: 'Settings', icon: Settings }]
}];


export const routeTitles: Record<string, string> = {
  '/': 'Command Center',
  '/copilot': 'Sentinel AI Copilot',
  '/investigations': 'Investigations',
  '/detections': 'Detections',
  '/graph': 'Organization Graph',
  '/policies': 'Policies',
  '/controls': 'Compliance Controls',
  '/frameworks': 'Frameworks',
  '/risk': 'Risk Center',
  '/findings': 'Findings',
  '/org/employees': 'Employees',
  '/org/identity': 'Identity & Access',
  '/org/devices': 'Devices',
  '/org/applications': 'Applications',
  '/org/cloud': 'Cloud Assets',
  '/org/vendors': 'Third-Party Vendors',
  '/privacy/inventory': 'DPDP Data Inventory',
  '/privacy/consent': 'Consent Management',
  '/evidence': 'Evidence Repository',
  '/audit-log': 'Audit Logs',
  '/reports': 'Reports',
  '/settings': 'Settings',
  '/profile': 'Profile'
};