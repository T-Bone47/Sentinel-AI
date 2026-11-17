const fs = require('fs');

function replaceAll(file, regex, replace) {
  if (!fs.existsSync(file)) return;
  let content = fs.readFileSync(file, 'utf8');
  content = content.replace(regex, replace);
  fs.writeFileSync(file, content);
}

replaceAll('src/App.tsx', /import \{ BrowserRouter as Router, Navigate, Route, Routes \} from 'react-router-dom';/, "import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';");

replaceAll('src/types/domain.ts', /controls: number;/, "controls?: number;");

replaceAll('src/components/risk/InvestigationDrawer.tsx', /catch \(e: any\) \{/, "catch {");

replaceAll('src/index.tsx', /import React from 'react';\r?\n/, "");
replaceAll('src/pages/commandCenterView.ts', /privacy, /, "");
replaceAll('src/pages/org/CloudAssets.tsx', /const rows = filtered;/g, "");
replaceAll('src/pages/org/Identity.tsx', /const rows = filtered;/g, "");
replaceAll('src/pages/privacy/Consent.tsx', /const rows = filtered;/g, "");

// Fix dupes manually for the 4 files
replaceAll('src/pages/Copilot.tsx', /^import React from 'react';\r?\nimport React from 'react';/m, "import React from 'react';");
replaceAll('src/pages/Findings.tsx', /^import React from 'react';\r?\nimport \{ useState \} from 'react';\r?\nimport React from 'react';\r?\nimport \{ useState \} from 'react';/m, "import React, { useState } from 'react';");
replaceAll('src/pages/Policies.tsx', /^import React from 'react';\r?\nimport \{ useState, useEffect \} from 'react';\r?\nimport React from 'react';\r?\nimport \{ useState, useEffect \} from 'react';/m, "import React, { useState, useEffect } from 'react';");
replaceAll('src/pages/RiskCenter.tsx', /^import React from 'react';\r?\nimport \{ useState \} from 'react';\r?\nimport React from 'react';\r?\nimport \{ useState \} from 'react';/m, "import React, { useState } from 'react';");

