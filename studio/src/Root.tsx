import React from 'react';
import {Composition, staticFile} from 'remotion';
// @ts-ignore — '@topic' is a webpack alias set in remotion.config.ts at runtime
// based on OVG_TOPIC. TypeScript can't resolve it statically.
import {MyComposition} from '@topic/Video/Latest/composition';
// @ts-ignore — same alias
import manifest from '@topic/manifest.json';

const metadata = manifest.metadata ?? {};
const fps: number = metadata.fps ?? 30;
const width: number = metadata.viewport_width ?? 1080;
const height: number = metadata.viewport_height ?? 1920;
const totalFrames: number = metadata.totalFrames ?? metadata.total_duration_frames ?? 900;

export const RemotionRoot: React.FC = () => (
  <Composition
    id="Main"
    component={MyComposition}
    durationInFrames={totalFrames}
    fps={fps}
    width={width}
    height={height}
    defaultProps={{
      audioUrl: staticFile('audio/latest.mp3'),
    }}
  />
);
