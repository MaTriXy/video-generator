import {Config} from '@remotion/cli/config';
import path from 'path';

const configDir = process.cwd();

const topic = process.env.OVG_TOPIC;
if (!topic) {
  throw new Error(
    "OVG_TOPIC is not set. Run with e.g. 'OVG_TOPIC=my-video-v2 npm run studio' " +
      "(or on Windows 'set OVG_TOPIC=my-video-v2 && npm run studio').",
  );
}

const topicDir = path.resolve(configDir, '..', 'Outputs', topic);

Config.setPublicDir(path.join(topicDir, 'public'));

const studioNodeModules = path.resolve(configDir, 'node_modules');

Config.overrideWebpackConfig((current) => ({
  ...current,
  resolve: {
    ...current.resolve,
    // Scene files live outside studio/ (in Outputs/{TOPIC}/Video/Latest/), so
    // webpack's default walk-up-for-node_modules won't find studio/node_modules.
    // Force the resolver to look there first.
    modules: [
      studioNodeModules,
      ...(current.resolve?.modules ?? ['node_modules']),
    ],
    alias: {
      ...(current.resolve?.alias ?? {}),
      '@topic': topicDir,
    },
  },
}));
