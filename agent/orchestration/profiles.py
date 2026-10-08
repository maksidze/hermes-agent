"""Use Hermes' provider resolver; execution profiles never own credentials."""

import ipaddress
from urllib.parse import urlparse


def is_local_runtime(runtime):
    """Fail closed: a name such as 'lmstudio' alone does not prove local routing."""
    host = urlparse(str(runtime.get("base_url") or "")).hostname
    if host == "localhost":
        return True
    try:
        return bool(host) and ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def resolve_profile(profile):
    from hermes_cli.runtime_provider import resolve_runtime_provider
    return resolve_runtime_provider(requested=profile.provider, target_model=profile.model)


def compatible(profile, request, runtime):
    caps = profile.capabilities
    if caps.get("tools") is False:
        return False
    from agent.models_dev import get_model_capabilities
    metadata = get_model_capabilities(profile.provider, profile.model)
    if caps.get("tools", "auto") == "auto" and metadata is not None and not metadata.supports_tools:
        return False
    if request.output_schema and caps.get("structured_output") is False:
        return False
    from .attachments import has_images
    if not has_images(request):
        return True
    return vision_compatible(profile, runtime)


def vision_compatible(profile, runtime):
    caps = profile.capabilities
    vision = caps.get("vision", "auto")
    if type(vision) is bool:
        return vision
    # Use the same native-vision capability resolver as AIAgent.
    from agent.image_routing import _lookup_supports_vision
    return _lookup_supports_vision(runtime.get("provider", profile.provider), profile.model,
                                   requested_provider=profile.provider) is True
