#!/bin/bash
set -e

# DropKit Security Check Script
# Comprehensive security validation for production deployment

echo "🔒 DropKit Security Audit Starting..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

ISSUES_FOUND=0

# Function to report issues
report_issue() {
    echo -e "${RED}❌ SECURITY ISSUE: $1${NC}"
    ISSUES_FOUND=$((ISSUES_FOUND + 1))
}

report_warning() {
    echo -e "${YELLOW}⚠️  WARNING: $1${NC}"
}

report_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

# Check 1: Environment file security
echo "🔍 Checking environment configuration..."
if [ -f .env ]; then
    # Check file permissions
    PERM=$(stat -c "%a" .env 2>/dev/null || stat -f "%A" .env 2>/dev/null)
    if [ "$PERM" != "600" ]; then
        report_issue ".env file has insecure permissions ($PERM). Should be 600."
    else
        report_success "Environment file permissions are secure"
    fi
    
    # Check for default passwords
    if grep -q "CHANGE_THIS\|your-\|password123\|admin123" .env; then
        report_issue "Default or weak passwords found in .env file"
    else
        report_success "No default passwords found in .env"
    fi
    
    # Check JWT secret strength
    JWT_SECRET=$(grep "JWT_SECRET=" .env | cut -d'=' -f2)
    if [ ${#JWT_SECRET} -lt 32 ]; then
        report_issue "JWT_SECRET is too short (${#JWT_SECRET} chars). Should be at least 32 characters."
    else
        report_success "JWT_SECRET length is adequate"
    fi
else
    report_warning ".env file not found"
fi

# Check 2: Docker security
echo "🐳 Checking Docker configuration..."
if [ -f docker-compose.yml ]; then
    # Check for exposed ports
    if grep -q "0.0.0.0:" docker-compose.yml; then
        report_warning "Services exposed on all interfaces (0.0.0.0). Consider localhost binding for security."
    fi
    
    # Check for privileged containers
    if grep -q "privileged.*true" docker-compose.yml; then
        report_issue "Privileged containers found in docker-compose.yml"
    else
        report_success "No privileged containers found"
    fi
    
    # Check for security options
    if grep -q "no-new-privileges" docker-compose.yml; then
        report_success "Security options configured in Docker Compose"
    else
        report_warning "Consider adding security options to Docker Compose"
    fi
fi

# Check 3: Dependency vulnerabilities
echo "📦 Checking dependencies for vulnerabilities..."
if [ -d frontend ]; then
    cd frontend
    if command -v npm >/dev/null 2>&1; then
        echo "Scanning Node.js dependencies..."
        if npm audit --audit-level high --json > /tmp/npm-audit.json 2>/dev/null; then
            HIGH_VULNS=$(cat /tmp/npm-audit.json | grep -o '"high":[0-9]*' | cut -d':' -f2 | head -1)
            CRITICAL_VULNS=$(cat /tmp/npm-audit.json | grep -o '"critical":[0-9]*' | cut -d':' -f2 | head -1)
            
            if [ "${HIGH_VULNS:-0}" -gt 0 ] || [ "${CRITICAL_VULNS:-0}" -gt 0 ]; then
                report_issue "High/Critical vulnerabilities found in Node.js dependencies"
            else
                report_success "No high/critical vulnerabilities in Node.js dependencies"
            fi
        fi
    fi
    cd ..
fi

if [ -d backend ]; then
    cd backend
    if command -v pip >/dev/null 2>&1; then
        echo "Scanning Python dependencies..."
        if command -v pip-audit >/dev/null 2>&1; then
            if pip-audit --format=json > /tmp/pip-audit.json 2>/dev/null; then
                if [ -s /tmp/pip-audit.json ]; then
                    report_issue "Vulnerabilities found in Python dependencies"
                else
                    report_success "No vulnerabilities in Python dependencies"
                fi
            fi
        else
            report_warning "pip-audit not installed. Run: pip install pip-audit"
        fi
    fi
    cd ..
fi

# Check 4: File permissions and sensitive files
echo "📁 Checking file permissions and sensitive files..."
find . -name "*.key" -o -name "*.pem" -o -name "*.p12" -o -name "credentials.json" | while read -r file; do
    if [ -f "$file" ]; then
        PERM=$(stat -c "%a" "$file" 2>/dev/null || stat -f "%A" "$file" 2>/dev/null)
        if [ "$PERM" != "600" ]; then
            report_issue "Sensitive file $file has insecure permissions ($PERM)"
        fi
    fi
done

# Check 5: Secrets in code
echo "🔍 Scanning for hardcoded secrets..."
if command -v grep >/dev/null 2>&1; then
    # Look for potential secrets (excluding comments and this script)
    SECRETS=$(grep -r -i "password\s*=\|secret\s*=\|key\s*=\|token\s*=" --include="*.py" --include="*.js" --include="*.jsx" . | grep -v "^#\|//\|scripts/security-check.sh" | head -5)
    if [ -n "$SECRETS" ]; then
        report_warning "Potential hardcoded secrets found in code"
        echo "$SECRETS"
    else
        report_success "No obvious hardcoded secrets found"
    fi
fi

# Check 6: Network security
echo "🌐 Checking network security configuration..."
if [ -f frontend/nginx.conf ]; then
    if grep -q "server_tokens off" frontend/nginx.conf; then
        report_success "Nginx server tokens disabled"
    else
        report_warning "Consider disabling Nginx server tokens"
    fi
    
    if grep -q "X-Frame-Options" frontend/nginx.conf; then
        report_success "Security headers configured in Nginx"
    else
        report_issue "Missing security headers in Nginx configuration"
    fi
fi

# Check 7: Container image security
echo "🔒 Checking container security..."
if command -v docker >/dev/null 2>&1; then
    # Check if images exist and scan them
    if docker images | grep -q "dropkit"; then
        if command -v trivy >/dev/null 2>&1; then
            echo "Scanning container images with Trivy..."
            trivy image --severity HIGH,CRITICAL --quiet dropkit-backend:latest || report_warning "Backend image scan failed or vulnerabilities found"
            trivy image --severity HIGH,CRITICAL --quiet dropkit-frontend:latest || report_warning "Frontend image scan failed or vulnerabilities found"
        else
            report_warning "Trivy not installed. Install for container vulnerability scanning."
        fi
    else
        report_warning "Docker images not built yet. Run 'make build' first."
    fi
fi

# Summary
echo ""
echo "🔒 Security Audit Complete"
echo "=========================="
if [ $ISSUES_FOUND -eq 0 ]; then
    echo -e "${GREEN}✅ No critical security issues found!${NC}"
    echo "Your DropKit deployment appears to be secure."
else
    echo -e "${RED}❌ Found $ISSUES_FOUND security issue(s) that need attention.${NC}"
    echo "Please address the issues above before deploying to production."
    exit 1
fi

echo ""
echo "Security recommendations:"
echo "• Regularly update dependencies"
echo "• Monitor security advisories"
echo "• Use strong, unique passwords"
echo "• Enable audit logging in production"
echo "• Implement monitoring and alerting"
echo "• Regular security scans and penetration testing"
