const fs = require('fs');

function fixFile(file, regex, replace) {
  if (fs.existsSync(file)) {
    let content = fs.readFileSync(file, 'utf8');
    content = content.replace(regex, replace);
    fs.writeFileSync(file, content);
  }
}

// 1. ErrorBoundary
fixFile('src/components/common/ErrorBoundary.tsx', /^import /m, "import { Component, type ReactNode } from 'react';\nimport ");

// 2. Button.tsx
fixFile('src/components/ui/Button.tsx', /^import /m, "import { forwardRef } from 'react';\nimport ");
// wait, button already has some types maybe? Let's check Button.tsx
