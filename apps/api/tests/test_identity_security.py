from __future__ import annotations

from urllib.parse import parse_qs, urlparse

import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.modules.identity.google_oauth import GoogleIdentityProvider
from app.modules.identity.security import OAuthFlowCodec, new_oauth_flow, pkce_challenge


def test_oauth_flow_cookie_round_trip_and_tamper_rejection() -> None:
    flow = new_oauth_flow()
    codec = OAuthFlowCodec("test-secret-that-is-long-enough-for-derivation")
    encoded = codec.encode(flow)

    assert codec.decode(encoded, ttl_seconds=600) == flow
    assert codec.decode(f"{encoded[:-1]}x", ttl_seconds=600) is None


def test_google_authorization_url_uses_state_nonce_and_pkce() -> None:
    settings = Settings(
        environment="test",
        google_client_id="client-id",
        google_client_secret="client-secret",
        google_redirect_uri="http://test/api/v1/auth/google/callback",
    )
    flow = new_oauth_flow()
    query = parse_qs(urlparse(GoogleIdentityProvider(settings).authorization_url(flow)).query)

    assert query["state"] == [flow.state]
    assert query["nonce"] == [flow.nonce]
    assert query["code_challenge"] == [pkce_challenge(flow.code_verifier)]
    assert query["code_challenge_method"] == ["S256"]
    assert query["scope"] == ["openid email profile"]


def test_production_rejects_http_frontend() -> None:
    with pytest.raises(ValidationError, match="HTTPS"):
        Settings(
            environment="production",
            frontend_url="http://app.rayo.example",
            secret_key="production-secret-with-more-than-32-characters",
        )
