const fs = require('fs');

const missingHooks = {
  'src/components/common/ErrorBoundary.tsx': ['Component', 'type ReactNode'],
  'src/components/ui/Button.tsx': ['forwardRef'],
  'src/components/ui/Controls.tsx': ['forwardRef'],
  'src/components/ui/Input.tsx': ['forwardRef', 'useId'],
  'src/components/ui/Tabs.tsx': ['useId'],
  'src/contexts/ThemeContext.tsx': ['createContext', 'useContext'],
  'src/pages/Findings.tsx': ['useState'],
  'src/pages/Frameworks.tsx': ['useState'],
  'src/pages/Graph.tsx': ['useState', 'useMemo'],
  'src/pages/Investigations.tsx': ['useState'],
  'src/pages/Policies.tsx': ['useState', 'useEffect'],
  'src/pages/Profile.tsx': ['useState'],
  'src/pages/Reports.tsx': ['useState'],
  'src/pages/RiskCenter.tsx': ['useState'],
  'src/pages/Settings.tsx': ['useState'],
};

for (const [file, hooks] of Object.entries(missingHooks)) {
  if (!fs.existsSync(file)) continue;
  let content = fs.readFileSync(file, 'utf8');
  let importStr = `import { ${hooks.join(', ')} } from 'react';\n`;
  fs.writeFileSync(file, importStr + content);
}

const missingReact = [
  'src/pages/Copilot.tsx',
  'src/pages/Evidence.tsx',
  'src/pages/Findings.tsx',
  'src/pages/org/Applications.tsx',
  'src/pages/org/CloudAssets.tsx',
  'src/pages/org/Devices.tsx',
  'src/pages/org/Employees.tsx',
  'src/pages/org/Identity.tsx',
  'src/pages/org/Vendors.tsx',
  'src/pages/Policies.tsx',
  'src/pages/privacy/Consent.tsx',
  'src/pages/privacy/DataInventory.tsx',
  'src/pages/RiskCenter.tsx'
];

for (const file of missingReact) {
  if (!fs.existsSync(file)) continue;
  let content = fs.readFileSync(file, 'utf8');
  let importStr = `import React from 'react';\n`;
  fs.writeFileSync(file, importStr + content);
}

function replaceFile(path, regex, replacement) {
  if (!fs.existsSync(path)) return;
  let content = fs.readFileSync(path, 'utf8');
  content = content.replace(regex, replacement);
  fs.writeFileSync(path, content);
}

replaceFile('src/index.tsx', /import React from 'react';\r?\n/, '');
replaceFile('src/pages/commandCenterView.ts', /privacy,/, '');
replaceFile('src/pages/org/CloudAssets.tsx', /const providerTone = { AWS: 'warning', Azure: 'info', GCP: 'primary' } as const;/, "const providerTone: Record<string, 'warning' | 'info' | 'primary'> = { AWS: 'warning', Azure: 'info', GCP: 'primary' };");
replaceFile('src/pages/org/CloudAssets.tsx', /const rows = filtered;/g, '');
replaceFile('src/pages/org/Identity.tsx', /const rows = filtered;/g, '');
replaceFile('src/pages/privacy/Consent.tsx', /const rows = filtered;/g, '');
replaceFile('src/pages/privacy/DataInventory.tsx', /const categoryTone = {/g, "const categoryTone: Record<string, 'danger' | 'warning' | 'neutral'> = {");
replaceFile('src/pages/RiskCenter.tsx', /StackedBarsChart, TrendAreaChart/g, 'StackedBarsChart');
replaceFile('src/components/risk/InvestigationDrawer.tsx', /import { AsyncSection } from '\.\.\/common\/AsyncSection';\r?\n/, '');
replaceFile('src/components/risk/InvestigationDrawer.tsx', /catch \(e\) {/g, 'catch (e: any) {');
replaceFile('src/pages/Profile.tsx', /catch \(e\) {/g, 'catch (e: any) {');
replaceFile('src/pages/Graph.tsx', /const toneMap = {/g, "const toneMap: Record<string, 'danger' | 'warning' | 'info' | 'neutral' | 'success'> = {");
