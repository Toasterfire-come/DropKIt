#!/usr/bin/env node

const fs = require('fs');
const path = require('path');
const { promisify } = require('util');

const writeFile = promisify(fs.writeFile);

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

async function createEnvFile() {
  if (fs.existsSync('.env')) {
    log('✅ .env file already exists', 'green');
    return;
  }

  const envTemplate = `# MongoDB Configuration
MONGO_ROOT_USERNAME=admin
MONGO_ROOT_PASSWORD=your_secure_password_here

# Application URLs
REACT_APP_API_URL=https://dropkit.me/api
REACT_APP_FRONTEND_URL=https://dropkit.me

# JWT Secret (generate a secure random string)
JWT_SECRET=your_jwt_secret_here

# Other environment variables as needed
NODE_ENV=production
`;

  await writeFile('.env', envTemplate);
  log('✅ Created .env file template', 'green');
  log('⚠️  Please update the values in .env with your actual configuration', 'yellow');
}

function showCloudflareInstructions() {
  log('\n🌐 Cloudflare Tunnel Setup Instructions:', 'cyan');
  log('', 'reset');
  log('1. Go to https://dash.teams.cloudflare.com/', 'blue');
  log('2. Navigate to Access > Tunnels', 'blue');
  log('3. Create a new tunnel named "dropkit-tunnel"', 'blue');
  log('4. Download the credentials JSON file', 'blue');
  log('5. Save it as: cloudflared/credentials.json', 'blue');
  log('6. In the tunnel dashboard, add these public hostnames:', 'blue');
  log('   - dropkit.me → http://localhost:3000', 'blue');
  log('   - dropkit.me/api/* → http://localhost:8000', 'blue');
  log('   - dropkit.me/health → http://localhost:3000', 'blue');
  log('', 'reset');
  log('📝 The cloudflared/config.yml file is already configured for you!', 'green');
  log('', 'reset');
}

async function main() {
  log('🔧 Setting up DropKit configuration...', 'cyan');
  
  try {
    await createEnvFile();
    showCloudflareInstructions();
    
    log('✅ Setup guidance complete!', 'green');
    log('', 'reset');
    log('📋 Next steps:', 'yellow');
    log('1. Update .env with your actual values', 'yellow');
    log('2. Set up Cloudflare tunnel (see instructions above)', 'yellow');
    log('3. Run `npm start` to launch the application', 'yellow');
    log('', 'reset');
    
  } catch (error) {
    log('❌ Setup failed:', 'red');
    console.error(error);
    process.exit(1);
  }
}

if (require.main === module) {
  main();
}
