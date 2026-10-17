"""Confidential-pilot boundaries shared by the API, CLI and matching pipeline."""
import os


def confidential_mode() -> bool:
    # Hosted services cannot turn this protection off with KAIZEN_CONFIDENTIAL=0.
    return os.environ.get('KAIZEN_HOSTED') == '1' or os.environ.get('KAIZEN_CONFIDENTIAL') == '1'


def session_lifetime() -> int:
    return 8 * 60 * 60 if confidential_mode() else 0


def private_headers() -> dict[str, str]:
    return {
        'Cache-Control': 'no-store',
        'Pragma': 'no-cache',
        'X-Content-Type-Options': 'nosniff',
        'Referrer-Policy': 'no-referrer',
        'X-Frame-Options': 'DENY',
        'Content-Security-Policy': "frame-ancestors 'none'; object-src 'none'; base-uri 'self'",
    }
