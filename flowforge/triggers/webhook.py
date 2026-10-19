"""Webhook trigger validation and handler logic."""

import hmac
import hashlib
from typing import Any, Dict, Optional
from flowforge.core.models import TriggerDefinition, TriggerType


def verify_webhook_token(
    expected_token: Optional[str],
    provided_token: Optional[str],
) -> bool:
    """Validate webhook authentication token with constant-time comparison."""
    if not expected_token:
        return True  # No token required
    if not provided_token:
        return False
    return hmac.compare_digest(expected_token, provided_token)


def verify_hmac_signature(
    secret: str,
    payload_bytes: bytes,
    signature_header: str,
    algorithm: str = "sha256",
) -> bool:
    """Verify HMAC signature (e.g. GitHub X-Hub-Signature-256)."""
    if not secret or not signature_header:
        return False

    prefix = f"{algorithm}="
    if signature_header.startswith(prefix):
        received_sig = signature_header[len(prefix):]
    else:
        received_sig = signature_header

    mac = hmac.new(secret.encode("utf-8"), payload_bytes, getattr(hashlib, algorithm))
    expected_sig = mac.hexdigest()

    return hmac.compare_digest(expected_sig, received_sig)


def get_webhook_trigger_config(trigger: TriggerDefinition) -> Dict[str, Any]:
    """Extract configuration options for a webhook trigger."""
    if trigger.type != TriggerType.WEBHOOK:
        return {}
    return trigger.config
