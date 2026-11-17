const fs = require('fs');
const path = require('path');

function walkDir(dir, callback) {
  fs.readdirSync(dir).forEach(f => {
    let dirPath = path.join(dir, f);
    let isDirectory = fs.statSync(dirPath).isDirectory();
    isDirectory ? walkDir(dirPath, callback) : callback(path.join(dir, f));
  });
}

walkDir('src', function(filePath) {
  if (filePath.endsWith('.tsx') || filePath.endsWith('.ts')) {
    let content = fs.readFileSync(filePath, 'utf8');
    let lines = content.split('\n');
    let seenReact = false;
    let seenState = false;
    let seenUseMemo = false;
    let newLines = [];
    
    for (let i = 0; i < lines.length; i++) {
      let line = lines[i];
      if (i < 15) {
        if (line.match(/^import React from 'react';/)) {
          if (seenReact) continue;
          seenReact = true;
        }
        if (line.match(/^import { useState } from 'react';/)) {
          if (seenState) continue;
          seenState = true;
        }
        if (line.match(/^import { useState, useMemo } from 'react';/)) {
          if (seenState && seenUseMemo) continue;
          seenState = true;
          seenUseMemo = true;
        }
        if (line.match(/^import { useState, useEffect } from 'react';/)) {
          if (seenState) continue; // Note: we're blindly deduplicating here
        }
      }
      newLines.push(line);
    }
    
    let newContent = newLines.join('\n');
    if (newContent !== content) {
      fs.writeFileSync(filePath, newContent);
    }
  }
});
