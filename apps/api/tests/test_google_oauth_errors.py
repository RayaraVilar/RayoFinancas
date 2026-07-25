from app.modules.identity.google_oauth import (
    GOOGLE_ID_TOKEN_CLOCK_SKEW_SECONDS,
    classify_id_token_error,
)


def test_google_id_token_clock_skew_is_small_and_bounded() -> None:
    assert GOOGLE_ID_TOKEN_CLOCK_SKEW_SECONDS == 60


def test_classifies_safe_id_token_failures() -> None:
    assert classify_id_token_error(ValueError("Token has wrong audience abc")) == "wrong_audience"
    assert classify_id_token_error(ValueError("Token used too early")) == "token_used_too_early"
    assert classify_id_token_error(ValueError("Token expired")) == "token_expired"
    assert classify_id_token_error(ValueError("Wrong issuer")) == "wrong_issuer"
    assert (
        classify_id_token_error(ValueError("Certificate for key id not found"))
        == "certificate_validation_failed"
    )
    assert classify_id_token_error(ValueError("Malformed token")) == "id_token_verification_failed"
