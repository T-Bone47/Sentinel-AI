const fs = require('fs');
const { execSync } = require('child_process');

try {
  console.log("Running tsc...");
  execSync('npx tsc --noEmit');
  console.log("Success!");
} catch (err) {
  const output = err.stdout ? err.stdout.toString() : err.output.toString();
  const lines = output.split('\n');
  const missingImports = {};

  for (const line of lines) {
    const match = line.match(/(src\/.*\.tsx?)\(\d+,\d+\): error TS2304: Cannot find name '(useState|useEffect|useMemo|useRef|useCallback)'/);
    if (match) {
      const file = match[1];
      const hook = match[2];
      if (!missingImports[file]) missingImports[file] = new Set();
      missingImports[file].add(hook);
    }
    const matchReact = line.match(/(src\/.*\.tsx?)\(\d+,\d+\): error TS2686: 'React' refers to a UMD global/);
    if (matchReact) {
      const file = matchReact[1];
      if (!missingImports[file]) missingImports[file] = new Set();
      missingImports[file].add('React');
    }
  }

  console.log("Missing imports found in: ", Object.keys(missingImports));
  
  for (const [file, hooks] of Object.entries(missingImports)) {
    let content = fs.readFileSync(file, 'utf8');
    const hookList = Array.from(hooks).filter(h => h !== 'React').join(', ');
    const hasReact = hooks.has('React');
    let importStr = 'import ';
    if (hasReact) importStr += 'React';
    if (hasReact && hookList) importStr += ', { ' + hookList + ' }';
    else if (hookList) importStr += '{ ' + hookList + ' }';
    importStr += " from 'react';\n";
    
    fs.writeFileSync(file, importStr + content);
    console.log(`Updated ${file}`);
  }
}
