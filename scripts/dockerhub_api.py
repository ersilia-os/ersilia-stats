"""Shared Docker Hub access: the login flow that unlocks deep pagination.

Docker Hub caps how far an anonymous client can paginate ("pagination offset too large
for anonymous requests"), which is what made `fetch_dockerhub.py`'s full repository
listing 403 anonymously. A free login (no paid tier needed) removes the cap: POST a
Personal Access Token as the password to `/v2/users/login/`, and trade it for a
short-lived JWT used as a Bearer token on every call after that.

This is the one place among the collectors that makes a POST rather than a GET —
`collect_common.py`'s own docstring guarantees every request there is a GET, so the
login lives here instead of bending that guarantee.
"""
import json
import logging
import os
import urllib.error
import urllib.request

from collect_common import USER_AGENT

DOCKERHUB_API = "https://hub.docker.com/v2"


def get_jwt(username=None, token=None):
    """A short-lived Bearer token, or ``None`` if no credentials are set or the login
    fails. Callers treat ``None`` as "proceed unauthenticated", not a fatal error —
    every Docker Hub collector here already works anonymously, just with a shallower
    pagination limit."""
    username = username or os.environ.get("DOCKERHUB_USERNAME")
    token = token or os.environ.get("DOCKERHUB_TOKEN")
    if not username or not token:
        return None

    request = urllib.request.Request(
        "%s/users/login/" % DOCKERHUB_API,
        data=json.dumps({"username": username, "password": token}).encode("utf-8"),
        headers={"User-Agent": USER_AGENT, "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            payload = json.loads(response.read())
            return payload.get("token")
    except (urllib.error.HTTPError, urllib.error.URLError, ValueError) as error:
        logging.warning("Docker Hub login failed, continuing unauthenticated: %s", error)
        return None


def auth_headers(username=None, token=None):
    """``{}`` when unauthenticated, so callers can pass this straight to
    `collect_common.get_json`/`paginate_url` either way."""
    jwt = get_jwt(username, token)
    return {"Authorization": "Bearer %s" % jwt} if jwt else {}
