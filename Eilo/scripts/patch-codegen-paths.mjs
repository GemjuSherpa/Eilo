import {readFileSync, writeFileSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
const root = new URL('../', import.meta.url);
const packageFile = new URL('node_modules/react-native/package.json', root);
if (JSON.parse(readFileSync(packageFile, 'utf8')).version !== '0.87.1') {
  throw new Error('Review Codegen path patch for the new React Native version');
}
const file = new URL('node_modules/react-native/scripts/codegen/generate-artifacts-executor/generateReactCodegenPodspec.js', root);
let source = readFileSync(file, 'utf8');
if (!source.includes('/* Eilo: argument-safe Codegen paths */')) {
  const first = 'execSync(`find ${resolvedAppPath} -type d -name "*.xcodeproj"`)';
  if (!source.includes(first)) {throw new Error('Unexpected Codegen source; review required');}
  source = source.replace("const {execSync} = require('child_process');", "const {execFileSync} = require('child_process'); /* Eilo: argument-safe Codegen paths */");
  source = source.replace(first, "execFileSync('find', [resolvedAppPath, '-type', 'd', '-name', '*.xcodeproj'])");
  const begin = source.indexOf('  const jsFiles =');
  const end = source.indexOf('\n    .trim()', begin);
  if (begin < 0 || end < 0) {throw new Error('Unexpected Codegen input discovery; review required');}
  source = source.slice(0, begin) + `  const list = String(execFileSync('find', [path.join(resolvedAppPath, jsSrcsDir),
    '-type', 'f', '-not', '-path', '*/__mocks__/*', '-and', '(',
    '-name', 'Native*.js', '-or', '-name', '*NativeComponent.js', '-or',
    '-name', 'Native*.ts', '-or', '-name', '*NativeComponent.ts', ')']))` + source.slice(end);
  writeFileSync(fileURLToPath(file), source);
}
