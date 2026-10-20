const { getDefaultConfig, mergeConfig } = require('@react-native/metro-config');

/**
 * Metro configuration
 * https://reactnative.dev/docs/metro
 *
 * @type {import('@react-native/metro-config').MetroConfig}
 */
const path = require('path');
const fs = require('fs');
const workspaceRoot = path.resolve(__dirname, '../..');
const dependencyRoot = fs.realpathSync(
  path.join(workspaceRoot, 'node_modules'),
);
const config = {
  // Existing dependencies may be reused by an isolated checkout. Metro must be
  // able to index their real location without resolving workspace source there.
  watchFolders: [...new Set([workspaceRoot, dependencyRoot])],
  resolver: {
    useWatchman: false,
    nodeModulesPaths: [path.join(workspaceRoot, 'node_modules')],
    extraNodeModules: {
      '@eilo/contracts': path.join(workspaceRoot, 'packages/contracts'),
      '@eilo/design-tokens': path.join(workspaceRoot, 'packages/design-tokens'),
    },
  },
};

module.exports = mergeConfig(getDefaultConfig(__dirname), config);
