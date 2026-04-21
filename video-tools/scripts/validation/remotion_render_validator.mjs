/**
 * Remotion Runtime Validator
 *
 * Validates a TSX scene component by executing it for every frame using mocked hooks
 * and real Remotion pure functions (interpolate, spring). No Chromium/rendering needed.
 *
 * How it works:
 * 1. Uses esbuild to bundle the scene TSX with mocked remotion/react imports
 * 2. Real interpolate() and spring() are bundled (pure math, validates inputRange etc.)
 * 3. useCurrentFrame() is mocked to return a controllable frame value via globalThis
 * 4. React's createElement recursively calls function components (executes all code paths)
 * 5. Loops through every frame 0..N, catching any runtime errors
 *
 * Usage: node remotion_render_validator.mjs <scene_tsx_path> <remotion_project_dir> [duration_in_frames]
 *
 * Exit codes:
 *   0 = passed (no runtime errors)
 *   1 = runtime error found (details in stdout JSON)
 *   2 = internal error
 *
 * Output: Single JSON line to stdout:
 *   {"success": true, "framesChecked": 600}
 *   {"success": false, "error": "...", "frame": 150}
 */

import { createRequire } from 'module';
import path from 'path';
import fs from 'fs';
import crypto from 'crypto';
import os from 'os';

const sceneTsxPath = process.argv[2];
const remotionProjectDir = process.argv[3];
const durationInFrames = parseInt(process.argv[4], 10) || 600;

if (!sceneTsxPath || !remotionProjectDir) {
    process.stdout.write(JSON.stringify({
        success: false,
        error: 'Usage: node remotion_render_validator.mjs <scene_tsx_path> <remotion_project_dir> [duration_in_frames]'
    }));
    process.exit(2);
}

// Create require functions for both the project dir and monorepo root (fallback)
const projectRequire = createRequire(path.join(path.resolve(remotionProjectDir), 'node_modules', '_placeholder.js'));
const monorepoRoot = path.resolve(remotionProjectDir, '..', '..');
const monorepoRequire = createRequire(path.join(monorepoRoot, 'node_modules', '_placeholder.js'));

function resolveModule(name) {
    try { return projectRequire.resolve(name); } catch {}
    return monorepoRequire.resolve(name);
}

const esbuild = (() => { try { return projectRequire('esbuild'); } catch { return monorepoRequire('esbuild'); } })();

// Temp directory for build artifacts
const uuid = crypto.randomBytes(8).toString('hex');
const tempDir = path.join(os.tmpdir(), `remotion-validate-${uuid}`);
fs.mkdirSync(tempDir, { recursive: true });

// Absolute path to real Remotion CJS entry — resolve "remotion" (the exports map points "." require to dist/cjs/index.js)
const remotionIndexCjs = resolveModule('remotion').replace(/\\/g, '/');

// Normalized scene path for import
const sceneAbsPath = path.resolve(sceneTsxPath).replace(/\\/g, '/').replace(/\.tsx$/, '');

// Entry point wrapper: imports scene and loops through all frames
const wrapperPath = path.join(tempDir, 'wrapper.tsx');
const outputPath = path.join(tempDir, 'bundle.cjs');

const wrapperContent = `
import SceneComponent from '${sceneAbsPath}';

const duration = ${durationInFrames};

// Mock props that scenes receive — Arrow/Text work via JSX mock (undefined type → null),
// but seededRandom is called directly as a function, so it needs an explicit mock.
const mockProps = {
    seededRandom: (seed: string, n: number) => {
        // Deterministic pseudo-random based on seed+n, returns 0..1
        let h = 0;
        const s = seed + String(n);
        for (let i = 0; i < s.length; i++) {
            h = (h * 31 + s.charCodeAt(i)) | 0;
        }
        return ((h & 0x7fffffff) % 1000) / 1000;
    },
};

for (let frame = 0; frame < duration; frame++) {
    (globalThis as any).__remotion_validate_frame = frame;
    try {
        (SceneComponent as any)(mockProps);
    } catch (err: any) {
        process.stdout.write(JSON.stringify({
            success: false,
            error: err.message || String(err),
            frame,
        }));
        process.exit(1);
    }
}

process.stdout.write(JSON.stringify({ success: true, framesChecked: duration }));
process.exit(0);
`;

/**
 * esbuild plugin: Load REAL remotion package, override only React-dependent parts.
 *
 * Strategy: Load the full remotion CJS index (which gets our React mock via the
 * reactMockPlugin). This gives us ALL exports (interpolate, Easing, spring, etc.)
 * automatically. We only override:
 * - useCurrentFrame/useVideoConfig: need Remotion's internal React context
 * - Components that use internal context (Sequence, Series, etc.): stub as pass-through
 */
const remotionMockPlugin = {
    name: 'remotion-mock',
    setup(build) {
        build.onResolve({ filter: /^remotion$/ }, (args) => ({
            path: 'remotion-mock',
            namespace: 'remotion-mock-ns',
        }));

        build.onLoad({ filter: /.*/, namespace: 'remotion-mock-ns' }, () => ({
            contents: `
                // Load the REAL remotion package (React hooks resolve to our mock)
                const realRemotion = require('${remotionIndexCjs}');

                // Override hooks that read from Remotion's internal React context
                const useCurrentFrame = () => globalThis.__remotion_validate_frame || 0;
                const useVideoConfig = () => ({
                    fps: 30,
                    width: 1920,
                    height: 1080,
                    durationInFrames: ${durationInFrames},
                    id: 'validate',
                    defaultCodec: 'h264',
                    defaultProps: {},
                });

                // Override components that depend on Remotion's internal context
                const AbsoluteFill = (props) => props ? props.children : null;
                const Sequence = (props) => props ? props.children : null;
                const Series = (props) => props ? props.children : null;
                Series.Sequence = (props) => props ? props.children : null;
                const Loop = (props) => props ? props.children : null;
                const Freeze = (props) => props ? props.children : null;
                const Audio = () => null;
                const Img = () => null;
                const Video = () => null;
                const OffthreadVideo = () => null;
                const Composition = () => null;
                const registerRoot = () => {};

                // Re-export everything from real remotion, with overrides
                module.exports = {
                    ...realRemotion,
                    useCurrentFrame,
                    useVideoConfig,
                    AbsoluteFill, Sequence, Series, Loop, Freeze,
                    Audio, Img, Video, OffthreadVideo,
                    Composition, registerRoot,
                };
            `,
            resolveDir: path.dirname(remotionIndexCjs),
            loader: 'js',
        }));
    }
};

/**
 * esbuild plugin: Mock 'react' and 'react/jsx-runtime' imports
 *
 * - createElement: recursively calls function components to execute all code paths
 * - Hooks (useState, useMemo, etc.): basic stubs
 * - jsx/jsxs: same as createElement (for automatic JSX transform)
 */
const reactMockPlugin = {
    name: 'react-mock',
    setup(build) {
        // Match 'react', 'react/jsx-runtime', 'react/jsx-dev-runtime'
        build.onResolve({ filter: /^react(\/.*)?$/ }, (args) => ({
            path: args.path,
            namespace: 'react-mock-ns',
        }));

        build.onLoad({ filter: /.*/, namespace: 'react-mock-ns' }, (args) => {
            // Common React mock with recursive component execution
            const contents = `
                function createElement(type, props) {
                    var allProps = props || {};
                    var children = [];
                    for (var i = 2; i < arguments.length; i++) {
                        children.push(arguments[i]);
                    }
                    if (children.length === 1) allProps.children = children[0];
                    else if (children.length > 1) allProps.children = children;

                    // Call function components to execute their code (hooks, interpolate, etc.)
                    if (typeof type === 'function') {
                        try { return type(allProps); } catch (e) { throw e; }
                    }
                    return null;
                }

                function jsx(type, props) {
                    if (typeof type === 'function') {
                        try { return type(props || {}); } catch (e) { throw e; }
                    }
                    return null;
                }

                var Fragment = function(props) { return props.children; };
                var useState = function(init) { return [typeof init === 'function' ? init() : init, function(){}]; };
                var useMemo = function(fn) { return fn(); };
                var useRef = function(init) { return { current: init }; };
                var useCallback = function(fn) { return fn; };
                var useEffect = function() {};
                var useLayoutEffect = function() {};
                var useContext = function() { return {}; };
                var createContext = function(def) { return { Provider: function(p) { return p.children; }, Consumer: function(p) { return p.children; }, _currentValue: def }; };
                var forwardRef = function(fn) { return fn; };
                var memo = function(fn) { return fn; };
                var useId = function() { return 'mock-id'; };
                var useReducer = function(reducer, init) { return [init, function(){}]; };
                var createRef = function() { return { current: null }; };
                var useImperativeHandle = function() {};
                var useSyncExternalStore = function(subscribe, getSnapshot) { return getSnapshot(); };
                var useDebugValue = function() {};
                var useDeferredValue = function(v) { return v; };
                var useTransition = function() { return [false, function(fn) { fn(); }]; };
                var lazy = function(fn) { return fn; };
                var Suspense = function(props) { return props.children; };
                var startTransition = function(fn) { fn(); };
                var Children = {
                    map: function(children, fn) { return Array.isArray(children) ? children.map(fn) : children ? [fn(children, 0)] : []; },
                    forEach: function(children, fn) { if (Array.isArray(children)) children.forEach(fn); else if (children) fn(children, 0); },
                    count: function(children) { return Array.isArray(children) ? children.length : children ? 1 : 0; },
                    only: function(children) { return children; },
                    toArray: function(children) { return Array.isArray(children) ? children : children ? [children] : []; },
                };
                var isValidElement = function() { return false; };
                var cloneElement = function(el) { return el; };
                var Component = function() {};
                Component.prototype = { render: function() { return null; }, setState: function() {}, forceUpdate: function() {} };
                var PureComponent = Component;

                var React = {
                    createElement: createElement,
                    Fragment: Fragment,
                    useState: useState,
                    useMemo: useMemo,
                    useRef: useRef,
                    useCallback: useCallback,
                    useEffect: useEffect,
                    useLayoutEffect: useLayoutEffect,
                    useContext: useContext,
                    createContext: createContext,
                    forwardRef: forwardRef,
                    memo: memo,
                    useId: useId,
                    useReducer: useReducer,
                    createRef: createRef,
                    useImperativeHandle: useImperativeHandle,
                    useSyncExternalStore: useSyncExternalStore,
                    useDebugValue: useDebugValue,
                    useDeferredValue: useDeferredValue,
                    useTransition: useTransition,
                    lazy: lazy,
                    Suspense: Suspense,
                    startTransition: startTransition,
                    Children: Children,
                    isValidElement: isValidElement,
                    cloneElement: cloneElement,
                    Component: Component,
                    PureComponent: PureComponent,
                    version: '19.0.0',
                };

                module.exports = React;
                module.exports.default = React;
                module.exports.jsx = jsx;
                module.exports.jsxs = jsx;
                module.exports.Fragment = Fragment;
                module.exports.createRef = createRef;
                module.exports.Children = Children;
                module.exports.isValidElement = isValidElement;
                module.exports.cloneElement = cloneElement;
                module.exports.Component = Component;
                module.exports.PureComponent = PureComponent;
            `;
            return { contents, loader: 'js' };
        });
    }
};

/**
 * esbuild plugin: Smart mock for '@remotion/google-fonts/*' imports.
 *
 * Uses the REAL @remotion/google-fonts package metadata (getInfo()) to validate
 * that the weights and subsets requested in loadFont() actually exist for the font.
 * Falls back to a permissive mock if the real package can't be resolved.
 */
const remotionGoogleFontsValidatorPlugin = {
    name: 'remotion-google-fonts-validator',
    setup(build) {
        build.onResolve({ filter: /^@remotion\/google-fonts\// }, (args) => ({
            path: args.path,
            namespace: 'remotion-gf-mock-ns',
        }));

        build.onLoad({ filter: /.*/, namespace: 'remotion-gf-mock-ns' }, (args) => {
            const fontName = args.path.split('/').pop() || 'sans-serif';
            const fontNameSafe = JSON.stringify(fontName);

            // Try to load real font module to get supported weights/subsets
            let fontInfo = null;
            try {
                const packagePath = `@remotion/google-fonts/${fontName}`;
                let realModulePath;
                try { realModulePath = projectRequire.resolve(packagePath); } catch {}
                if (!realModulePath) realModulePath = monorepoRequire.resolve(packagePath);
                const realModule = (realModulePath.startsWith(path.resolve(remotionProjectDir))
                    ? projectRequire : monorepoRequire)(realModulePath);
                if (typeof realModule.getInfo === 'function') {
                    fontInfo = realModule.getInfo();
                }
            } catch (_) {
                // Real module not available — will fall back to permissive mock
            }

            let contents;
            if (fontInfo) {
                const fontsData = JSON.stringify(fontInfo.fonts || {});
                const subsetsData = JSON.stringify(fontInfo.subsets || []);
                const realFamily = JSON.stringify(fontInfo.fontFamily || fontName);

                contents = `
                    var _fonts = ${fontsData};
                    var _subsets = ${subsetsData};
                    var _family = ${realFamily};

                    function loadFont(style, options) {
                        var s = style || 'normal';
                        var styleData = _fonts[s];
                        if (!styleData) {
                            var availStyles = Object.keys(_fonts);
                            throw new Error("Font '" + ${fontNameSafe} + "' does not support style '" + s + "'. Available styles: " + availStyles.join(', '));
                        }

                        var availWeights = Object.keys(styleData);

                        if (options && options.weights) {
                            for (var i = 0; i < options.weights.length; i++) {
                                var w = String(options.weights[i]);
                                if (availWeights.indexOf(w) === -1) {
                                    throw new Error("Font '" + ${fontNameSafe} + "' does not support weight '" + w + "'. Available weights: " + availWeights.join(', '));
                                }
                            }
                        }

                        if (options && options.subsets) {
                            for (var j = 0; j < options.subsets.length; j++) {
                                var sub = options.subsets[j];
                                if (_subsets.indexOf(sub) === -1) {
                                    throw new Error("Font '" + ${fontNameSafe} + "' does not support subset '" + sub + "'. Available subsets: " + _subsets.join(', '));
                                }
                            }
                        }

                        return {
                            fontFamily: _family,
                            fonts: {},
                            unicodeRanges: {},
                            waitUntilDone: function() { return Promise.resolve(); },
                        };
                    }

                    function getInfo() {
                        return { fontFamily: _family, importName: ${fontNameSafe}, fonts: _fonts, subsets: _subsets };
                    }

                    module.exports = { loadFont: loadFont, getInfo: getInfo };
                `;
            } else {
                // Fallback: permissive mock (real package not available)
                contents = `
                    function loadFont(style, options) {
                        console.error('[google-fonts] WARNING: @remotion/google-fonts/' + ${fontNameSafe} + ' not installed — using permissive mock, no weight/subset validation');
                        return {
                            fontFamily: ${fontNameSafe},
                            fonts: {},
                            unicodeRanges: {},
                            waitUntilDone: function() { return Promise.resolve(); },
                        };
                    }
                    function getInfo() {
                        return { fontFamily: ${fontNameSafe}, fonts: {} };
                    }
                    module.exports = { loadFont: loadFont, getInfo: getInfo };
                `;
            }

            return { contents, loader: 'js' };
        });
    }
};

/**
 * esbuild plugin: Mock '@remotion/*' sub-packages (transitions, etc.)
 */
const remotionSubpackageMockPlugin = {
    name: 'remotion-subpackage-mock',
    setup(build) {
        build.onResolve({ filter: /^@remotion\// }, () => ({
            path: 'remotion-sub-mock',
            namespace: 'remotion-sub-mock-ns',
        }));

        build.onLoad({ filter: /.*/, namespace: 'remotion-sub-mock-ns' }, () => ({
            contents: `module.exports = new Proxy({}, { get: (_, key) => typeof key === 'string' ? () => null : undefined });`,
            loader: 'js',
        }));
    }
};


async function main() {
    fs.writeFileSync(wrapperPath, wrapperContent, 'utf-8');

    try {
        // Bundle the wrapper + scene with mocked imports
        await esbuild.build({
            entryPoints: [wrapperPath],
            bundle: true,
            outfile: outputPath,
            format: 'cjs',
            platform: 'node',
            target: 'es2016',
            jsx: 'automatic',
            logLevel: 'error',
            plugins: [remotionMockPlugin, reactMockPlugin, remotionGoogleFontsValidatorPlugin, remotionSubpackageMockPlugin],
        });

        // Execute the bundle - it loops through frames and writes JSON result to stdout
        const { execSync } = await import('child_process');
        const result = execSync(`node "${outputPath}"`, {
            timeout: 30000,
            encoding: 'utf-8',
            stdio: ['pipe', 'pipe', 'pipe'],
        });

        // Forward the bundle's stdout (JSON result)
        process.stdout.write(result.trim());
        const parsed = JSON.parse(result.trim());
        process.exit(parsed.success ? 0 : 1);

    } catch (err) {
        // Check if it's an execSync error with stdout JSON from the bundle
        if (err.stdout && err.stdout.trim()) {
            try {
                const parsed = JSON.parse(err.stdout.trim());
                process.stdout.write(JSON.stringify(parsed));
                process.exit(1);
                return; // guard
            } catch (_) {
                // Not valid JSON, fall through
            }
        }

        // Extract the first "Error: ..." line from stderr/message for a cleaner message
        const stderr = err.stderr || '';
        const fullMsg = err.message || String(err);
        const errLineMatch = stderr.match(/^Error: (.+)$/m) || fullMsg.match(/\nError: (.+?)(\n|$)/);
        const errorMessage = errLineMatch ? errLineMatch[1] : fullMsg;

        process.stdout.write(JSON.stringify({
            success: false,
            error: errorMessage,
        }));
        process.exit(err.status === 2 ? 2 : 1);

    } finally {
        // Clean up temp directory
        try {
            fs.rmSync(tempDir, { recursive: true, force: true });
        } catch (_) {
            // Ignore cleanup errors
        }
    }
}

main().catch((err) => {
    process.stdout.write(JSON.stringify({
        success: false,
        error: 'Runner internal error: ' + (err.message || String(err)),
    }));
    process.exit(2);
});
