"""
TsxBuildEnvController manages the TsxBuildEnv folder and environment setup.
Standalone version for video build service.
"""

import os
import json
import subprocess
import shutil
import logging
from pathlib import Path
from typing import Dict, Any

logger = logging.getLogger('tsx_build_env_controller')


class TsxBuildEnvController:
    """Controller for managing the TsxBuildEnv build environment."""

    def __init__(self, project_root: Path = None):
        """Initialize the TsxBuildEnvController."""
        if project_root is None:
            # Default to course-workflow root
            self.project_root = Path(__file__).parent.parent.parent
        else:
            self.project_root = project_root
        self.build_env_path = self.project_root / "TsxBuildEnv"
        self.src_path = self.build_env_path / "src"
        self.dist_path = self.build_env_path / "dist"
        self.components_path = self.build_env_path / "components"
        self.lib_path = self.build_env_path / "lib"

    def ensure_build_env_exists(self) -> bool:
        """Ensure the TsxBuildEnv folder exists with all necessary files."""
        try:
            if not self.build_env_path.exists():
                return self.create_build_env()

            if not self._validate_env_structure():
                return self.create_build_env()

            if not (self.build_env_path / "node_modules").exists():
                return self.install_dependencies()

            return True

        except Exception as e:
            logger.error(f"Error ensuring build environment: {e}")
            return False

    def create_build_env(self) -> bool:
        """Create the TsxBuildEnv folder with all necessary files."""
        try:
            self.build_env_path.mkdir(parents=True, exist_ok=True)
            self.src_path.mkdir(exist_ok=True)
            self.dist_path.mkdir(exist_ok=True)

            # Copy components from project root
            source_components = self.project_root / "components"
            self.components_path.mkdir(exist_ok=True)
            if source_components.exists():
                if self.components_path.exists():
                    shutil.rmtree(self.components_path)
                shutil.copytree(source_components, self.components_path)

            self.lib_path.mkdir(exist_ok=True)
            source_lib = self.project_root / "lib"
            if source_lib.exists():
                if self.lib_path.exists():
                    shutil.rmtree(self.lib_path)
                shutil.copytree(source_lib, self.lib_path)

            if not self.write_config_files():
                return False

            return self.install_dependencies()

        except Exception as e:
            logger.error(f"Error creating build environment: {e}")
            return False

    def write_config_files(self) -> bool:
        """Write all necessary configuration files to TsxBuildEnv."""
        try:
            package_json = self._get_package_json()
            with open(self.build_env_path / "package.json", "w") as f:
                json.dump(package_json, f, indent=2)

            tsconfig = self._get_tsconfig()
            with open(self.build_env_path / "tsconfig.json", "w") as f:
                json.dump(tsconfig, f, indent=2)

            vite_config = self._get_vite_config()
            with open(self.build_env_path / "vite.config.ts", "w") as f:
                f.write(vite_config)

            tailwind_config = self._get_tailwind_config()
            with open(self.build_env_path / "tailwind.config.js", "w") as f:
                f.write(tailwind_config)

            postcss_config = self._get_postcss_config()
            with open(self.build_env_path / "postcss.config.js", "w") as f:
                f.write(postcss_config)

            index_css = self._get_index_css()
            with open(self.build_env_path / "index.css", "w") as f:
                f.write(index_css)

            return True

        except Exception as e:
            logger.error(f"Error writing config files: {e}")
            return False

    def install_dependencies(self) -> bool:
        """Install npm dependencies in the TsxBuildEnv."""
        try:
            import platform
            use_shell = platform.system() == "Windows"

            result = subprocess.run(
                ["npm", "install"],
                cwd=str(self.build_env_path),
                capture_output=True,
                text=True,
                timeout=300,
                shell=use_shell
            )

            if result.returncode != 0:
                logger.error(f"npm install failed: {result.stderr}")
                return False

            return True

        except subprocess.TimeoutExpired:
            logger.error("npm install timed out")
            return False
        except FileNotFoundError:
            logger.error("npm not found. Please ensure Node.js and npm are installed")
            return False
        except Exception as e:
            logger.error(f"Error installing dependencies: {e}")
            return False

    def get_build_env_path(self) -> Path:
        """Get the path to the TsxBuildEnv folder."""
        return self.build_env_path

    def get_src_path(self) -> Path:
        """Get the path to the src folder in TsxBuildEnv."""
        return self.src_path

    def get_dist_path(self) -> Path:
        """Get the path to the dist folder in TsxBuildEnv."""
        return self.dist_path

    def _validate_env_structure(self) -> bool:
        """Validate that all necessary files and folders exist."""
        required_files = [
            "package.json",
            "tsconfig.json",
            "vite.config.ts",
            "tailwind.config.js",
            "postcss.config.js",
            "index.css"
        ]

        required_dirs = ["src", "dist"]

        for file_name in required_files:
            if not (self.build_env_path / file_name).exists():
                return False

        for dir_name in required_dirs:
            if not (self.build_env_path / dir_name).exists():
                return False

        return True

    def _get_package_json(self) -> Dict[str, Any]:
        """Get the package.json configuration."""
        return {
            "name": "remote-components",
            "version": "1.0.0",
            "type": "module",
            "scripts": {
                "dev": "vite",
                "build:MyComponentA": "cross-env COMPONENT=MyComponentA vite build",
                "build:video": "cross-env COMPONENT=video vite build",
                "build": "vite build",
                "serve": "serve dist -p 3001",
                "preview": "vite preview"
            },
            "devDependencies": {
                "@types/react": "^18.2.43",
                "@types/react-dom": "^18.2.17",
                "@vitejs/plugin-react": "^4.2.1",
                "autoprefixer": "^10.4.21",
                "cross-env": "^7.0.3",
                "framer-motion": "^12.23.6",
                "postcss": "^8.5.6",
                "postcss-prefixwrap": "^1.51.0",
                "serve": "^10.0.2",
                "tailwindcss": "^3.4.15",
                "typescript": "^5.2.2",
                "vite": "^7.0.5",
                "vite-plugin-css-injected-by-js": "^3.5.2"
            },
            "peerDependencies": {
                "framer-motion": "^12.23.5",
                "react": "^19.1.0",
                "react-dom": "^19.1.0"
            }
        }

    def _get_tsconfig(self) -> Dict[str, Any]:
        """Get the tsconfig.json configuration."""
        return {
            "compilerOptions": {
                "target": "ES2020",
                "useDefineForClassFields": True,
                "lib": ["ES2020", "DOM", "DOM.Iterable"],
                "module": "ESNext",
                "skipLibCheck": True,
                "moduleResolution": "bundler",
                "allowImportingTsExtensions": True,
                "resolveJsonModule": True,
                "isolatedModules": True,
                "noEmit": True,
                "jsx": "react-jsx",
                "strict": True,
                "noUnusedLocals": True,
                "noUnusedParameters": True,
                "noFallthroughCasesInSwitch": True
            },
            "include": ["src"]
        }

    def _get_vite_config(self) -> str:
        """Get the vite.config.ts configuration."""
        return '''import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { resolve } from "path";
import { readdirSync, statSync } from "fs";
import cssInjectedByJsPlugin from 'vite-plugin-css-injected-by-js';
import path from 'path';

const getComponentName = () => {
  const componentArg = process.argv.find((arg) =>
    arg.startsWith("--component=")
  );
  if (componentArg) {
    return componentArg.split("=")[1];
  }
  return process.env.COMPONENT || null;
};

const getAllComponents = () => {
  const srcDir = resolve(__dirname, "src");
  const components = [];

  const entries = readdirSync(srcDir);

  for (const entry of entries) {
    const entryPath = resolve(srcDir, entry);
    const stat = statSync(entryPath);

    if (stat.isDirectory()) {
      const componentFile = resolve(entryPath, `${entry}.tsx`);
      try {
        statSync(componentFile);
        components.push(entry);
      } catch {
      }
    } else if (entry.endsWith(".tsx")) {
      components.push(entry.replace(".tsx", ""));
    }
  }

  return components;
};

const buildComponent = getComponentName();
const allComponents = getAllComponents();

if (!buildComponent) {
  console.error(
    "No component specified. Use: cross-env COMPONENT=<name> npm run build"
  );
  console.error(`Available components: ${allComponents.join(", ")}`);
  process.exit(1);
}

if (!allComponents.includes(buildComponent)) {
  console.error(
    `Component ${buildComponent} not found. Available components: ${allComponents.join(
      ", "
    )}`
  );
  process.exit(1);
}

const getInputConfig = () => {
  const input: Record<string, string> = {};
  const srcDir = resolve(__dirname, "src");

  allComponents.forEach((component) => {
    const folderPath = resolve(srcDir, component, `${component}.tsx`);
    const directPath = resolve(srcDir, `${component}.tsx`);

    try {
      statSync(folderPath);
      input[component] = folderPath;
    } catch {
      input[component] = directPath;
    }
  });
  return input;
};

const wrapWithScopeClass = () => ({
  name: 'wrap-with-scope-class',
  transform(code, id) {
    if (id.includes('/src/') && id.endsWith('.tsx')) {
      const functionExportRegex = /export default function\\s+(\\w+)/;
      const identifierExportRegex = /export default\\s+(\\w+);?$/m;

      if (functionExportRegex.test(code)) {
        let functionName = '';
        code = code.replace(functionExportRegex, (match, name) => {
          functionName = name;
          return 'function ' + name;
        });
        const wrapper = `\\n\\nconst Wrapped${functionName} = (props) => React.createElement('div', { className: 'remote-component' }, React.createElement(${functionName}, props));\\nexport default Wrapped${functionName};\\n`;
        code = code + wrapper;
      } else if (identifierExportRegex.test(code)) {
        code = code.replace(identifierExportRegex, (match, componentName) => {
          return `const Wrapped${componentName} = (props) => React.createElement('div', { className: 'remote-component' }, React.createElement(${componentName.trim()}, props));\\nexport default Wrapped${componentName};`;
        });
      }
    }
    return code;
  },
});

export default defineConfig({
  plugins: [
    react(),
    wrapWithScopeClass(),
    cssInjectedByJsPlugin()
  ],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './'),
    },
  },
  css: {
    postcss: './postcss.config.js',
  },
  server: {
    port: 3001,
    cors: {
      origin: ["http://localhost:3000", "http://localhost:3001"],
      credentials: true,
    },
  },
  preview: {
    port: 3001,
    cors: {
      origin: ["http://localhost:3000", "http://localhost:3001"],
      credentials: true,
    },
  },
  build: {
    emptyOutDir: false,
    lib: {
      entry: (() => {
        const srcDir = resolve(__dirname, "src");
        const folderPath = resolve(
          srcDir,
          buildComponent,
          `${buildComponent}.tsx`
        );
        const directPath = resolve(srcDir, `${buildComponent}.tsx`);

        try {
          statSync(folderPath);
          return folderPath;
        } catch {
          return directPath;
        }
      })(),
      formats: ["umd"],
      fileName: () => `${buildComponent}/${buildComponent}.js`,
      name: buildComponent,
    },
    rollupOptions: {
      external: ["react", "react-dom", "framer-motion"],
      output: {
        globals: {
          react: "React",
          "react-dom": "ReactDOM",
          "framer-motion": "FramerMotion",
        },
      },
    },
    cssCodeSplit: false,
  },
});
'''

    def _get_tailwind_config(self) -> str:
        """Get the tailwind.config.js configuration."""
        return '''/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./src/**/*.{js,ts,jsx,tsx}",
    "./src/*.{js,ts,jsx,tsx}",
  ],
  corePlugins: {
    preflight: false,
  },
  theme: {
    extend: {},
  },
  plugins: [],
}'''

    def _get_postcss_config(self) -> str:
        """Get the postcss.config.js configuration."""
        return '''export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
    'postcss-prefixwrap': '.remote-component',
  },
}'''

    def _get_index_css(self) -> str:
        """Get the index.css file content."""
        return '''@tailwind base;
@tailwind components;
@tailwind utilities;'''
