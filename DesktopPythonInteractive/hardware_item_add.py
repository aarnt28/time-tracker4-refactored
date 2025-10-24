#!/usr/bin/env python3
"""
ensure_hardware_barcode.py

Purpose:
  Ensure a hardware record with a given `barcode` exists in the tracker API.
  - If found: print the record (JSON) and exit 0 with status "exists".
  - If not found: create it with `barcode` and `description` (defaults to barcode).

API per your README:
  Base: https://tracker.turnernet.co/api/v1
  Resource: /hardware
  Auth: X-API-Key: <token>
  List: GET  /hardware?limit=<n>&offset=<n>     -> returns a JSON list
  Create: POST /hardware                        -> body: {"barcode": "...", "description": "..."}

Auth precedence:
  1) --token <value> (CLI)
  2) env TRACKER_API_TOKEN
  3) HARDCODED_API_KEY (defined below)

Examples:
  python ensure_hardware_barcode.py Dell-Optiplex-3060-SFF
  python ensure_hardware_barcode.py Dell-Optiplex-3060-SFF -d "Optiplex 3060 SFF"
  python ensure_hardware_barcode.py Dell-Optiplex-3060-SFF --token YOUR_TOKEN
  TRACKER_API_TOKEN=YOUR_TOKEN python ensure_hardware_barcode.py Dell-Optiplex-3060-SFF

Exit codes:
  0 = success (exists or created)
  1 = handled application error
  2 = network/HTTP error
"""

from __future__ import annotations
import os
import sys
import json
import argparse
import requests
from typing import Any, Dict, Optional

# ---------------------------
# Hardcoded API key fallback
# ---------------------------
# Set this if you want a baked-in token. CLI --token and env TRACKER_API_TOKEN override this.
HARDCODED_API_KEY: Optional[str] = None
# Example:
HARDCODED_API_KEY = "CaRpoauTdDYdxQwWhWeXUQy"

DEFAULT_BASE_URL = "https://tracker.turnernet.co/api/v1"
RESOURCE_PATH = "hardware"  # fixed to match README

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Ensure a hardware barcode exists in the tracker API; create if missing.")
    p.add_argument("barcode", help="Hardware barcode (e.g., 'Dell-Optiplex-3060-SFF').")
    p.add_argument("-d", "--description",
                   help="Optional description. Defaults to the barcode value if omitted.")
    p.add_argument("--base-url", default=DEFAULT_BASE_URL,
                   help=f"Base API URL (default: {DEFAULT_BASE_URL})")
    p.add_argument("--token", default=None,
                   help="API token (X-API-Key). Overrides env and hardcoded value.")
    p.add_argument("--timeout", type=float, default=15.0,
                   help="HTTP timeout in seconds (default: 15)")
    p.add_argument("--page-size", type=int, default=200,
                   help="Pagination page size for GET /hardware (default: 200)")
    p.add_argument("--no-verify-tls", action="store_true",
                   help="Disable TLS verification (use only for testing).")
    p.add_argument("-v", "--verbose", action="store_true",
                   help="Verbose logging to stderr.")
    # Optional price headers supported by README (leave unset if not needed)
    p.add_argument("--acquisition-cost", type=str, default=None,
                   help="Optional acquisition cost header value.")
    p.add_argument("--sales-price", type=str, default=None,
                   help="Optional sales price header value.")
    return p.parse_args()

def resolve_token(cli_token: Optional[str]) -> Optional[str]:
    if cli_token:
        return cli_token
    env_token = os.getenv("TRACKER_API_TOKEN")
    if env_token:
        return env_token
    return HARDCODED_API_KEY

def build_headers(token: Optional[str], accept_json: bool = True, content_json: bool = False,
                  acquisition_cost: Optional[str] = None, sales_price: Optional[str] = None) -> Dict[str, str]:
    headers: Dict[str, str] = {}
    if accept_json:
        headers["Accept"] = "application/json"
    if content_json:
        headers["Content-Type"] = "application/json"
    if token:
        headers["X-API-Key"] = token
    if acquisition_cost is not None:
        headers["x-acquisition-cost"] = acquisition_cost
    if sales_price is not None:
        headers["x-sales-price"] = sales_price
    return headers

def vprint(enabled: bool, *args: Any) -> None:
    if enabled:
        print(*args, file=sys.stderr)

def api_list_hardware(session: requests.Session, base_url: str, token: Optional[str],
                      page_size: int, timeout: float, verify_tls: bool, verbose: bool):
    """
    Generator over hardware items.
    """
    offset = 0
    url = f"{base_url.rstrip('/')}/{RESOURCE_PATH}"
    headers = build_headers(token, accept_json=True)
    while True:
        params = {"limit": page_size, "offset": offset}
        vprint(verbose, f"GET {url} params={params}")
        r = session.get(url, headers=headers, params=params, timeout=timeout, verify=verify_tls)
        r.raise_for_status()
        data = r.json()
        if not isinstance(data, list):
            raise ValueError(f"Expected list from GET {url}, got: {type(data).__name__}")
        if not data:
            break
        for item in data:
            yield item
        offset += page_size

def find_hardware_by_barcode(session: requests.Session, base_url: str, token: Optional[str],
                             barcode: str, page_size: int, timeout: float, verify_tls: bool, verbose: bool) -> Optional[Dict[str, Any]]:
    """
    Scan all pages until a matching barcode is found; returns the item or None.
    """
    for item in api_list_hardware(session, base_url, token, page_size, timeout, verify_tls, verbose):
        if isinstance(item, dict) and item.get("barcode") == barcode:
            return item
    return None

def api_create_hardware(session: requests.Session, base_url: str, token: Optional[str],
                        barcode: str, description: str, timeout: float, verify_tls: bool,
                        acquisition_cost: Optional[str], sales_price: Optional[str], verbose: bool) -> Dict[str, Any]:
    url = f"{base_url.rstrip('/')}/{RESOURCE_PATH}"
    payload = {"barcode": barcode, "description": description}
    headers = build_headers(token, accept_json=True, content_json=True,
                            acquisition_cost=acquisition_cost, sales_price=sales_price)
    vprint(verbose, f"POST {url} json={payload} (x-acquisition-cost={acquisition_cost}, x-sales-price={sales_price})")
    r = session.post(url, headers=headers, json=payload, timeout=timeout, verify=verify_tls)
    # Accept 200 or 201 depending on implementation
    if r.status_code not in (200, 201):
        # try to surface server error details
        try:
            detail = json.dumps(r.json(), indent=2)
        except Exception:
            detail = r.text
        raise requests.HTTPError(f"Create failed ({r.status_code}): {detail}", response=r)
    return r.json()

def main() -> int:
    args = parse_args()
    token = resolve_token(args.token)
    if not token:
        print("WARNING: No API token supplied (use --token, env TRACKER_API_TOKEN, or set HARDCODED_API_KEY).",
              file=sys.stderr)

    verify_tls = not args.no_verify_tls
    description = args.description if args.description else args.barcode

    session = requests.Session()
    try:
        # 1) Lookup
        existing = find_hardware_by_barcode(
            session=session,
            base_url=args.base_url,
            token=token,
            barcode=args.barcode,
            page_size=args.page_size,
            timeout=args.timeout,
            verify_tls=verify_tls,
            verbose=args.verbose,
        )
        if existing:
            print(json.dumps({
                "status": "exists",
                "barcode": args.barcode,
                "record": existing
            }, indent=2))
            return 0

        # 2) Create
        created = api_create_hardware(
            session=session,
            base_url=args.base_url,
            token=token,
            barcode=args.barcode,
            description=description,
            timeout=args.timeout,
            verify_tls=verify_tls,
            acquisition_cost=args.acquisition_cost,
            sales_price=args.sales_price,
            verbose=args.verbose,
        )
        print(json.dumps({
            "status": "created",
            "barcode": args.barcode,
            "record": created
        }, indent=2))
        return 0

    except requests.exceptions.RequestException as e:
        print(f"NETWORK_ERROR: {e}", file=sys.stderr)
        return 2
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())
