// craco.config.js
const path = require("path");

const isDevServer = process.env.NODE_ENV !== "production";
const enableHealthCheck = process.env.ENABLE_HEALTH_CHECK === "true";

// Conditionally load health check modules
let WebpackHealthPlugin, setupHealthEndpoints, healthPluginInstance;

if (enableHealthCheck) {
  try {
    WebpackHealthPlugin = require("./plugins/health-check/webpack-health-plugin");
    setupHealthEndpoints = require("./plugins/health-check/health-endpoints");
    healthPluginInstance = new WebpackHealthPlugin();
  } catch (err) {
    console.warn("[Health Check] Plugins not found, health check disabled");
  }
}

const webpackConfig = {
  eslint: {
    configure: {
      extends: ["plugin:react-hooks/recommended"],
      rules: {
        "react-hooks/rules-of-hooks": "error",
        "react-hooks/exhaustive-deps": "warn",
      },
    },
  },
  webpack: {
    alias: {
      '@': path.resolve(__dirname, 'src'),
    },
    configure: (config) => {
      // Optimize watch options
      config.watchOptions = {
        ...config.watchOptions,
        ignored: [
          '**/node_modules/**',
          '**/.git/**',
          '**/build/**',
          '**/dist/**',
          '**/coverage/**',
          '**/public/**',
        ],
      };

      // Add health check plugin if available
      if (healthPluginInstance) {
        config.plugins.push(healthPluginInstance);
      }
      
      return config;
    },
  },
  devServer: (devServerConfig) => {
    // Proxy /api/* requests to the backend during local development.
    // This ensures same-origin requests whether accessing via localhost:3000
    // or through the Cloudflare tunnel. Avoids Chrome Private Network Access
    // (CORS-RFC1918) blocks and eliminates all CORS issues for API calls.
    devServerConfig.proxy = {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    };

    if (enableHealthCheck && setupHealthEndpoints && healthPluginInstance) {
      const originalSetupMiddlewares = devServerConfig.setupMiddlewares;
      
      devServerConfig.setupMiddlewares = (middlewares, devServer) => {
        if (originalSetupMiddlewares) {
          middlewares = originalSetupMiddlewares(middlewares, devServer);
        }
        setupHealthEndpoints(devServer, healthPluginInstance);
        return middlewares;
      };
    }
    return devServerConfig;
  },
};

// Add visual edits in development
if (isDevServer) {
  try {
    const { withVisualEdits } = require("@emergentbase/visual-edits/craco");
    module.exports = withVisualEdits(webpackConfig);
  } catch (err) {
    if (err.code === 'MODULE_NOT_FOUND') {
      console.warn("[Visual Edits] Package not installed — visual editing disabled");
    } else {
      throw err;
    }
    module.exports = webpackConfig;
  }
} else {
  module.exports = webpackConfig;
}
