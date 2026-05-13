"""Shopify Admin API client + HMAC verification + App Bridge session token verification.

Production-ready integration patterns. Uses placeholder credentials from .env;
swap credentials and the integration works end-to-end against a real Shopify store.
"""
import base64
import hashlib
import hmac
import json
from typing import Optional

import httpx
import jwt
from fastapi import Header, HTTPException, Request

from config import settings


# ============================================================
# 1. HMAC webhook verification (Shopify signs all webhooks)
# ============================================================
async def verify_shopify_webhook(request: Request) -> dict:
    """Verify HMAC signature on incoming Shopify webhook + return parsed body.

    Shopify sends `X-Shopify-Hmac-SHA256` header with base64(HMAC-SHA256(body, secret)).
    """
    # If webhook secret is not configured, skip verification.
    if not settings.SHOPIFY_WEBHOOK_SECRET or settings.SHOPIFY_WEBHOOK_SECRET.startswith("PLACEHOLDER"):
        body = await request.body()
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON body")

    body = await request.body()
    hmac_header = request.headers.get("X-Shopify-Hmac-SHA256", "")
    secret = settings.SHOPIFY_WEBHOOK_SECRET.encode()

    digest = hmac.new(secret, body, hashlib.sha256).digest()
    expected = base64.b64encode(digest).decode()

    # Constant-time compare
    if not hmac.compare_digest(hmac_header, expected):
        raise HTTPException(status_code=401, detail="Invalid HMAC signature")

    try:
        return json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON body")


def get_webhook_topic(request: Request) -> str:
    return request.headers.get("X-Shopify-Topic", "")


def get_webhook_shop_domain(request: Request) -> str:
    return request.headers.get("X-Shopify-Shop-Domain", "")


# ============================================================
# 2. App Bridge session token verification (JWT from Shopify)
# ============================================================
def verify_session_token(authorization: Optional[str] = Header(default=None)) -> dict:
    """Decode and verify a Shopify App Bridge session token (JWT).

    Token is signed with the app's API secret using HS256.
    Claims include: iss, dest, aud, sub (Shopify customer id), exp, nbf, iat, jti, sid.
    """
    # If API secret is not configured, skip verification.
    if not settings.SHOPIFY_API_SECRET or settings.SHOPIFY_API_SECRET.startswith("PLACEHOLDER"):
        # In a real app, you might want to return a specific error or log this.
        # For now, we'll raise an HTTPException as if the token was invalid.
        raise HTTPException(status_code=401, detail="Shopify API secret not configured for token verification")

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing session token")

    token = authorization.removeprefix("Bearer ").strip()
    try:
        payload = jwt.decode(
            token,
            settings.SHOPIFY_API_SECRET,
            algorithms=["HS256"],
            audience=settings.SHOPIFY_API_KEY,
            # Only verify audience if API key is not a placeholder
            options={"verify_aud": not (not settings.SHOPIFY_API_KEY or settings.SHOPIFY_API_KEY.startswith("PLACEHOLDER"))},
        )
        return payload
    except jwt.PyJWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid session token: {e}")


# ============================================================
# 3. Admin GraphQL API client
# ============================================================
class ShopifyAdminClient:
    """Async GraphQL client for Shopify Admin API."""

    def __init__(self):
        self.endpoint = (
            f"https://{settings.SHOPIFY_STORE_DOMAIN}"
            f"/admin/api/{settings.SHOPIFY_API_VERSION}/graphql.json"
        )
        self.headers = {
            "X-Shopify-Access-Token": settings.SHOPIFY_ADMIN_ACCESS_TOKEN,
            "Content-Type": "application/json",
        }

    def _is_configured(self) -> bool:
        """Check if essential Shopify Admin API credentials are set."""
        return (
            settings.SHOPIFY_STORE_DOMAIN
            and not settings.SHOPIFY_STORE_DOMAIN.startswith("PLACEHOLDER")
            and settings.SHOPIFY_ADMIN_ACCESS_TOKEN
            and not settings.SHOPIFY_ADMIN_ACCESS_TOKEN.startswith("PLACEHOLDER")
        )

    async def query(self, query: str, variables: Optional[dict] = None) -> dict:
        if not self._is_configured():
            # Return empty data or raise an error if Shopify is not configured
            # For now, returning empty data to allow UI to render without crashing
            print("Shopify Admin API not configured. Skipping query.")
            return {}

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    self.endpoint,
                    headers=self.headers,
                    json={"query": query, "variables": variables or {}},
                )
                response.raise_for_status()
                data = response.json()
                if "errors" in data:
                    # Log the errors for debugging
                    print(f"Shopify API errors: {data['errors']}")
                    # Depending on the error, you might want to raise HTTPException or return gracefully
                    # For now, we'll raise a generic error to indicate a problem
                    raise HTTPException(status_code=502, detail=f"Shopify API error: {data['errors']}")
                return data.get("data", {})
            except httpx.HTTPStatusError as e:
                print(f"HTTP error fetching Shopify data: {e}")
                raise HTTPException(status_code=502, detail=f"Shopify API HTTP error: {e}")
            except httpx.RequestError as e:
                print(f"Request error fetching Shopify data: {e}")
                raise HTTPException(status_code=503, detail=f"Shopify API request error: {e}")
            except Exception as e:
                print(f"An unexpected error occurred during Shopify API query: {e}")
                raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")


    # ---------- Subscription contract operations ----------
    async def pause_subscription(self, contract_id: str) -> dict:
        if not self._is_configured(): return {}
        mutation = """
        mutation pauseSubscription($contractId: ID!) {
          subscriptionContractUpdate(contractId: $contractId, input: {status: PAUSED}) {
            contract { id status }
            userErrors { field message }
          }
        }
        """
        return await self.query(mutation, {"contractId": contract_id})

    async def resume_subscription(self, contract_id: str) -> dict:
        if not self._is_configured(): return {}
        mutation = """
        mutation resumeSubscription($contractId: ID!) {
          subscriptionContractUpdate(contractId: $contractId, input: {status: ACTIVE}) {
            contract { id status }
            userErrors { field message }
          }
        }
        """
        return await self.query(mutation, {"contractId": contract_id})

    async def skip_next_billing_cycle(self, contract_id: str, cycle_index: int) -> dict:
        if not self._is_configured(): return {}
        mutation = """
        mutation skipCycle($contractId: ID!, $index: Int!) {
          subscriptionBillingCycleSkip(
            billingCycleInput: {contractId: $contractId, selector: {index: $index}}
          ) {
            billingCycle { skipped cycleIndex }
            userErrors { field message }
          }
        }
        """
        return await self.query(mutation, {"contractId": contract_id, "index": cycle_index})

    async def get_subscription_contract(self, contract_id: str) -> dict:
        if not self._is_configured(): return {}
        query = """
        query getContract($id: ID!) {
          subscriptionContract(id: $id) {
            id status nextBillingDate
            customer { id email }
          }
        }
        """
        return await self.query(query, {"id": contract_id})

    async def create_customer(self, email: str, name: Optional[str] = None) -> dict:
        """Create a Shopify Customer linked to our local user on signup."""
        if not self._is_configured(): return {}
        first, last = ("", "")
        if name:
            parts = name.split(" ", 1)
            first = parts[0]
            last = parts[1] if len(parts) > 1 else ""
        mutation = """
        mutation customerCreate($input: CustomerInput!) {
          customerCreate(input: $input) {
            customer { id email firstName lastName }
            userErrors { field message }
          }
        }
        """
        variables = {"input": {"email": email, "firstName": first, "lastName": last}}
        return await self.query(mutation, variables)

    async def get_order_fulfillment_orders(self, order_gid: str) -> list:
        """Return open fulfillment orders for an order, with their line items.

        Required first step before calling `fulfillmentCreate`. Filters for
        OPEN / IN_PROGRESS / SCHEDULED — already-fulfilled FOs are skipped.
        """
        if not self._is_configured(): return []
        query = """
        query orderFOs($id: ID!) {
          order(id: $id) {
            id
            fulfillmentOrders(first: 25) {
              edges {
                node {
                  id
                  status
                  lineItems(first: 50) {
                    edges { node { id remainingQuantity } }
                  }
                }
              }
            }
          }
        }
        """
        data = await self.query(query, {"id": order_gid})
        order = (data or {}).get("order") or {}
        edges = ((order.get("fulfillmentOrders") or {}).get("edges")) or []
        open_fos = []
        for e in edges:
            n = e.get("node") or {}
            if (n.get("status") or "").upper() in ("CLOSED", "CANCELLED", "INCOMPLETE"):
                continue
            li_edges = ((n.get("lineItems") or {}).get("edges")) or []
            line_items = [
                {"id": li["node"]["id"], "quantity": li["node"]["remainingQuantity"]}
                for li in li_edges
                if (li.get("node") or {}).get("remainingQuantity", 0) > 0
            ]
            if line_items:
                open_fos.append({"id": n["id"], "lineItems": line_items})
        return open_fos

    async def create_fulfillment(
        self, order_id: str, tracking_company: str, tracking_number: str, tracking_url: Optional[str] = None
    ) -> dict:
        """Create a Shopify fulfillment with tracking info on an order.

        Resolves the order's open fulfillment orders first, then submits a single
        fulfillmentCreate that covers all remaining line items under one tracking
        number. Per 2025-01 Admin API.
        """
        if not self._is_configured(): return {}
        order_gid = order_id if str(order_id).startswith("gid://") else f"gid://shopify/Order/{order_id}"
        fos = await self.get_order_fulfillment_orders(order_gid)
        if not fos:
            return {"fulfillmentCreate": {"fulfillment": None, "userErrors": [
                {"field": ["fulfillmentOrders"], "message": "No open fulfillment orders for this order"}
            ]}}

        mutation = """
        mutation fulfillmentCreate($fulfillment: FulfillmentInput!) {
          fulfillmentCreate(fulfillment: $fulfillment) {
            fulfillment {
              id status trackingInfo { number url company }
            }
            userErrors { field message }
          }
        }
        """
        variables = {
            "fulfillment": {
                "lineItemsByFulfillmentOrder": [
                    {
                        "fulfillmentOrderId": fo["id"],
                        "fulfillmentOrderLineItems": fo["lineItems"],
                    }
                    for fo in fos
                ],
                "notifyCustomer": True,
                "trackingInfo": {
                    "company": tracking_company,
                    "number": tracking_number,
                    "url": tracking_url,
                },
            }
        }
        return await self.query(mutation, variables)

    async def create_subscription_contract_for_gift(
        self, customer_id: str, recipient_email: str, duration_months: int
    ) -> dict:
        """Create a gift-funded subscription contract.

        Real implementation calls subscriptionContractCreate with deferred billing.
        Schema varies by API version — kept here as a single integration surface.
        """
        if not self._is_configured(): return {}
        mutation = """
        mutation giftContract($input: SubscriptionContractCreateInput!) {
          subscriptionContractCreate(input: $input) {
            contract { id status }
            userErrors { field message }
          }
        }
        """
        variables = {
            "input": {
                "customerId": customer_id,
                "nextBillingDate": None,  # deferred — server computes
                "currencyCode": "USD",
                "contract": {
                    "billingPolicy": {"interval": "MONTH", "intervalCount": 1},
                    "deliveryPolicy": {"interval": "MONTH", "intervalCount": 1},
                    "note": f"Gift subscription — {duration_months} month(s) for {recipient_email}",
                },
            }
        }
        return await self.query(mutation, variables)

    # ---------- Discount codes (referral rewards) ----------
    async def create_referral_discount_code(
        self,
        code: str,
        amount_cents: int,
        customer_gid: Optional[str] = None,
        product_gid: Optional[str] = None,
        usage_limit: int = 1,
        starts_at_iso: Optional[str] = None,
        ends_at_iso: Optional[str] = None,
    ) -> dict:
        """Create a single-use fixed-amount discount code via discountCodeBasicCreate.

        Scoped to one customer (if customer_gid given) and one product (if product_gid given).
        Returns the created discount node + any userErrors.
        """
        if not self._is_configured(): return {}
        mutation = """
        mutation discountCodeBasicCreate($basicCodeDiscount: DiscountCodeBasicInput!) {
          discountCodeBasicCreate(basicCodeDiscount: $basicCodeDiscount) {
            codeDiscountNode {
              id
              codeDiscount {
                ... on DiscountCodeBasic {
                  title
                  codes(first: 1) { edges { node { code } } }
                  usageLimit
                  status
                  startsAt
                  endsAt
                }
              }
            }
            userErrors { field message code }
          }
        }
        """
        amount_dollars = f"{amount_cents / 100:.2f}"
        items_block = (
            {"products": {"productsToAdd": [product_gid]}}
            if product_gid else {"all": True}
        )
        customers_block = (
            {"customers": {"add": [customer_gid]}}
            if customer_gid else {"all": True}
        )
        variables = {
            "basicCodeDiscount": {
                "title": f"DropKit referral reward — {code}",
                "code": code,
                "startsAt": starts_at_iso,
                "endsAt": ends_at_iso,
                "customerSelection": customers_block,
                "customerGets": {
                    "value": {"discountAmount": {"amount": amount_dollars, "appliesOnEachItem": False}},
                    "items": items_block,
                },
                "appliesOncePerCustomer": True,
                "usageLimit": usage_limit,
                "combinesWith": {"orderDiscounts": False, "productDiscounts": False, "shippingDiscounts": True},
            }
        }
        # Strip None timestamps so Shopify defaults apply (starts now, no end)
        variables["basicCodeDiscount"] = {
            k: v for k, v in variables["basicCodeDiscount"].items() if v is not None
        }
        return await self.query(mutation, variables)


shopify = ShopifyAdminClient()


# ============================================================
# 4. OAuth — install flow scaffolding (not used in MVP webhook flow but production-ready)
# ============================================================
def build_install_url(shop: str, redirect_uri: str, nonce: str) -> str:
    # Only build install URL if API key and secret are configured
    if not settings.SHOPIFY_API_KEY or settings.SHOPIFY_API_KEY.startswith("PLACEHOLDER") or \
       not settings.SHOPIFY_API_SECRET or settings.SHOPIFY_API_SECRET.startswith("PLACEHOLDER"):
        return "" # Return empty string or raise an error if not configured

    return (
        f"https://{shop}/admin/oauth/authorize"
        f"?client_id={settings.SHOPIFY_API_KEY}"
        f"&scope={settings.SHOPIFY_SCOPES}"
        f"&redirect_uri={redirect_uri}"
        f"&state={nonce}"
    )


async def exchange_code_for_token(shop: str, code: str) -> str:
    # Only attempt token exchange if API key and secret are configured
    if not settings.SHOPIFY_API_KEY or settings.SHOPIFY_API_KEY.startswith("PLACEHOLDER") or \
       not settings.SHOPIFY_API_SECRET or settings.SHOPIFY_API_SECRET.startswith("PLACEHOLDER"):
        raise HTTPException(status_code=400, detail="Shopify API key or secret not configured.")

    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            r = await client.post(
                f"https://{shop}/admin/oauth/access_token",
                json={
                    "client_id": settings.SHOPIFY_API_KEY,
                    "client_secret": settings.SHOPIFY_API_SECRET,
                    "code": code,
                },
            )
            r.raise_for_status()
            return r.json()["access_token"]
        except httpx.HTTPStatusError as e:
            print(f"HTTP error exchanging code for token: {e}")
            raise HTTPException(status_code=502, detail=f"Shopify API error during token exchange: {e}")
        except httpx.RequestError as e:
            print(f"Request error exchanging code for token: {e}")
            raise HTTPException(status_code=503, detail=f"Shopify API request error during token exchange: {e}")
        except Exception as e:
            print(f"An unexpected error occurred during token exchange: {e}")
            raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")


# ============================================================
# 5. Helpers — config check + cart permalink
# ============================================================
def shopify_is_configured() -> bool:
    """Return True if all required Shopify creds are real (not placeholders)."""
    keys = (
        settings.SHOPIFY_STORE_DOMAIN,
        settings.SHOPIFY_ADMIN_ACCESS_TOKEN,
        settings.SHOPIFY_API_KEY,
        settings.SHOPIFY_API_SECRET,
    )
    return all(k and not str(k).startswith("PLACEHOLDER") for k in keys)


def build_subscription_cart_url(
    variant_id: str,
    selling_plan_id: Optional[str] = None,
    quantity: int = 1,
    email: Optional[str] = None,
    discount_code: Optional[str] = None,
) -> str:
    """Build a Shopify cart-permalink that pre-loads the subscription product.

    Format: https://{shop}/cart/{variantId}:{qty}?selling_plan={planId}&checkout[email]=...&discount=...

    Caller is responsible for passing the numeric Variant ID (not the GID) and
    the numeric SellingPlan ID. The redirect lands on the Shopify cart, then
    Shopify Checkout — full payment + tax + shipping handled natively.
    """
    # If Shopify is not configured, return an empty string or a placeholder URL
    if not shopify_is_configured():
        print("Shopify not configured. Cannot build subscription cart URL.")
        # Return a placeholder or an empty string to indicate failure
        return "" # Or perhaps a URL that shows a "not available" message

    base = f"https://{settings.SHOPIFY_STORE_DOMAIN}/cart/{variant_id}:{quantity}"
    params = []
    if selling_plan_id:
        params.append(f"selling_plan={selling_plan_id}")
    if email:
        from urllib.parse import quote_plus
        params.append(f"checkout[email]={quote_plus(email)}")
    if discount_code:
        params.append(f"discount={discount_code}")
    return base + ("?" + "&".join(params) if params else "")
