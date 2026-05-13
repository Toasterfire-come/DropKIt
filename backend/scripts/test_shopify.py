#!/usr/bin/env python3
"""
Shopify connection test script
Tests the connection to Shopify Admin API
"""

import asyncio
import os
import sys
from pathlib import Path

# Add parent directory to path to import from backend
sys.path.append(str(Path(__file__).parent.parent))

from shopify_client import ShopifyAdminClient
from dotenv import load_dotenv

async def test_shopify_connection():
    """Test Shopify API connection"""
    load_dotenv()
    
    shop_domain = os.getenv("SHOPIFY_SHOP_DOMAIN")
    access_token = os.getenv("SHOPIFY_ACCESS_TOKEN")
    
    if not shop_domain or not access_token:
        print("❌ Missing Shopify configuration:")
        print(f"   SHOPIFY_SHOP_DOMAIN: {'✓' if shop_domain else '✗'}")
        print(f"   SHOPIFY_ACCESS_TOKEN: {'✓' if access_token else '✗'}")
        return False
    
    print(f"🔗 Testing connection to {shop_domain}...")
    
    try:
        client = ShopifyAdminClient(shop_domain, access_token)
        
        # Test basic shop info query
        query = """
        query {
            shop {
                name
                email
                domain
                plan {
                    displayName
                }
            }
        }
        """
        
        result = await client._execute_query(query)
        
        if result and "shop" in result:
            shop = result["shop"]
            print("✅ Shopify connection successful!")
            print(f"   Shop Name: {shop['name']}")
            print(f"   Email: {shop['email']}")
            print(f"   Domain: {shop['domain']}")
            print(f"   Plan: {shop['plan']['displayName']}")
            return True
        else:
            print("❌ Unexpected response from Shopify API")
            return False
            
    except Exception as e:
        print(f"❌ Shopify connection failed: {str(e)}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_shopify_connection())
    sys.exit(0 if success else 1)
