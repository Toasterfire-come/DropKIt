#!/usr/bin/env node

const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');

// Colors for console output
const colors = {
  reset: '\x1b[0m',
  bright: '\x1b[1m',
  red: '\x1b[31m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  magenta: '\x1b[35m',
  cyan: '\x1b[36m'
};

function log(message, color = 'reset') {
  console.log(`${colors[color]}${message}${colors.reset}`);
}

function checkRequiredFiles() {
  const requiredFiles = [
    '.env',
    'docker-compose.yml',
    'cloudflared/config.yml'
  ];

  const missing = requiredFiles.filter(file => !fs.existsSync(file));
  
  if (missing.length > 0) {
    log('❌ Missing required files:', 'red');
    missing.forEach(file => log(`   - ${file}`, 'red'));
    log('\nRun `npm run setup` to create missing configuration files.', 'yellow');
    process.exit(1);
  }
}

function runCommand(command, args = [], options = {}) {
  return new Promise((resolve, reject) => {
    const child = spawn(command, args, {
      stdio: 'inherit',
      shell: true,
      ...options
    });

    child.on('close', (code) => {
      if (code === 0) {
        resolve();
      } else {
        reject(new Error(`Command failed with exit code ${code}`));
      }
    });

    child.on('error', reject);
  });
}

async function checkDockerStatus() {
  try {
    await runCommand('docker', ['info'], { stdio: 'pipe' });
    log('✅ Docker is running', 'green');
    return true;
  } catch (error) {
    log('❌ Docker is not running. Please start Docker first.', 'red');
    return false;
  }
}

async function checkCloudflareCredentials() {
  const credentialsPath = 'cloudflared/credentials.json';
  if (!fs.existsSync(credentialsPath)) {
    log('⚠️  Cloudflare credentials not found at cloudflared/credentials.json', 'yellow');
    log('   The tunnel service may not start properly without credentials.', 'yellow');
    log('   Run `npm run setup` to get instructions for setting up Cloudflare tunnel.', 'yellow');
    return false;
  }
  log('✅ Cloudflare credentials found', 'green');
  return true;
}

async function main() {
  log('🚀 Starting DropKit...', 'cyan');
  
  // Check for required files
  checkRequiredFiles();
  
  // Check if Docker is running
  const dockerRunning = await checkDockerStatus();
  if (!dockerRunning) {
    process.exit(1);
  }

  // Check Cloudflare credentials
  await checkCloudflareCredentials();

  // Start the application
  try {
    log('📦 Building and starting services...', 'blue');
    log('   - MongoDB database', 'blue');
    log('   - Backend API server', 'blue');
    log('   - Frontend React app', 'blue');
    log('   - Cloudflare tunnel', 'blue');
    log('', 'reset');
    
    await runCommand('docker-compose', ['up', '--build']);
  } catch (error) {
    log('❌ Failed to start services', 'red');
    console.error(error.message);
    process.exit(1);
  }
}

// Handle graceful shutdown
process.on('SIGINT', async () => {
  log('\n🛑 Shutting down services...', 'yellow');
  try {
    await runCommand('docker-compose', ['down']);
    log('✅ Services stopped successfully', 'green');
  } catch (error) {
    log('❌ Error stopping services', 'red');
  }
  process.exit(0);
});

if (require.main === module) {
  main().catch(error => {
    log('❌ Startup failed:', 'red');
    console.error(error);
    process.exit(1);
  });
}
