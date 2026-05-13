#!/usr/bin/env python3
"""
Shopify connection test script
Tests the connection to Shopify Admin API
"""

import asyncio
import os
import sys
import re
from pathlib import Path

# Add parent directory to path to import from backend
sys.path.append(str(Path(__file__).parent.parent))

try:
    from shopify_client import ShopifyAdminClient
except ImportError:
    print("❌ Could not import ShopifyAdminClient. Make sure you're running from the backend directory.")
    sys.exit(1)

try:
    from dotenv import load_dotenv
except ImportError:
    print("❌ python-dotenv not installed. Run: pip install python-dotenv")
    sys.exit(1)

def validate_shop_domain(domain):
    """Validate Shopify shop domain format"""
    if not domain:
        return False
    
    # Must be a valid .myshopify.com domain
    pattern = r'^[a-zA-Z0-9][a-zA-Z0-9\-]*[a-zA-Z0-9]\.myshopify\.com$'
    return bool(re.match(pattern, domain))

def validate_access_token(token):
    """Validate Shopify access token format"""
    if not token:
        return False
    
    # Shopify access tokens are typically 32 characters of hex
    pattern = r'^[a-f0-9]{32}$'
    return bool(re.match(pattern, token))

async def test_shopify_connection():
    """Test Shopify API connection with security validation"""
    load_dotenv()
    
    shop_domain = os.getenv("SHOPIFY_SHOP_DOMAIN", "").strip()
    access_token = os.getenv("SHOPIFY_ACCESS_TOKEN", "").strip()
    
    # Validate environment variables
    if not shop_domain or not access_token:
        print("❌ Missing Shopify configuration:")
        print(f"   SHOPIFY_SHOP_DOMAIN: {'✓' if shop_domain else '✗'}")
        print(f"   SHOPIFY_ACCESS_TOKEN: {'✓' if access_token else '✗'}")
        print("\nPlease set these environment variables in your .env file:")
        print("   SHOPIFY_SHOP_DOMAIN=your-shop.myshopify.com")
        print("   SHOPIFY_ACCESS_TOKEN=your-access-token")
        return False
    
    # Security validation
    if not validate_shop_domain(shop_domain):
        print("❌ Invalid SHOPIFY_SHOP_DOMAIN format. Must be: shop-name.myshopify.com")
        return False
    
    if not validate_access_token(access_token):
        print("❌ Invalid SHOPIFY_ACCESS_TOKEN format. Must be 32 character hex string.")
        return False
    
    # Sanitize domain for logging (remove sensitive parts)
    safe_domain = shop_domain.split('.')[0] + ".myshopify.com"
    print(f"🔗 Testing connection to {safe_domain}...")
    
    try:
        client = ShopifyAdminClient()
        
        # Test basic shop info query using the public query method
        query = """
        query {
            shop {
                name
                domain
                plan {
                    displayName
                }
            }
        }
        """
        
        result = await client.query(query)
        
        if result and "shop" in result:
            shop = result["shop"]
            print("✅ Shopify connection successful!")
            print(f"   Shop Name: {shop['name']}")
            print(f"   Domain: {shop['domain']}")
            print(f"   Plan: {shop['plan']['displayName']}")
            return True
        else:
            print("❌ Unexpected response from Shopify API")
            print("   Check your SHOPIFY_SHOP_DOMAIN and SHOPIFY_ACCESS_TOKEN")
            return False
            
    except Exception as e:
        print(f"❌ Shopify connection failed: {str(e)}")
        print("   Verify your credentials and network connectivity")
        return False

if __name__ == "__main__":
    try:
        success = asyncio.run(test_shopify_connection())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n❌ Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
        sys.exit(1)
