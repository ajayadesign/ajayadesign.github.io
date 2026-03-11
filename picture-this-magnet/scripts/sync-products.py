#!/usr/bin/env python3
"""
Shopify Product Sync — PictureThisMagnet
=========================================
Fetches all products from the Shopify REST Storefront and saves to _data/products.json.

Run locally:  python3 scripts/sync-products.py
Run in CI:    triggered by .github/workflows/sync-products.yml
"""

import json
import os
import sys
from datetime import datetime, timezone
from urllib.request import Request, urlopen

# ─── Config ──────────────────────────────────────────────
SHOPIFY_DOMAIN = os.environ.get('SHOPIFY_DOMAIN', 'picturethismagnet.myshopify.com')
PRODUCTS_URL = f'https://{SHOPIFY_DOMAIN}/products.json'

# Paths (relative to repo root)
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(REPO_ROOT, '_data')
DATA_FILE = os.path.join(DATA_DIR, 'products.json')


def fetch_products():
    """Fetch all products from Shopify REST Storefront."""
    req = Request(PRODUCTS_URL)
    req.add_header('Accept', 'application/json')

    print(f'Fetching products from {SHOPIFY_DOMAIN}...')
    resp = urlopen(req, timeout=30)
    data = json.loads(resp.read().decode())

    products = data.get('products', [])
    print(f'  Found {len(products)} products')
    return products


def save_json(products):
    """Save products to _data/products.json with metadata."""
    os.makedirs(DATA_DIR, exist_ok=True)
    payload = {
        'lastUpdated': datetime.now(timezone.utc).isoformat(),
        'shopifyDomain': SHOPIFY_DOMAIN,
        'productCount': len(products),
        'products': products,
    }
    with open(DATA_FILE, 'w') as f:
        json.dump(payload, f, indent=2)
    print(f'  Saved {DATA_FILE}')


def main():
    products = fetch_products()
    if not products:
        print('Warning: No products returned', file=sys.stderr)
    save_json(products)
    print('Done!')


if __name__ == '__main__':
    main()
