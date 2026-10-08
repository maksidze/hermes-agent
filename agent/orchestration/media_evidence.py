"""Reference fidelity and candidate media for provider-independent review."""

import json
import re
from pathlib import Path

REFERENCE_CONTRACT = (
    "If creating or modifying a visual artifact from attached references, preserve their actual layout, "
    "proportions and distinctive parts, not merely generic object categories. Describe the reference "
    "before constructing the artifact. Inspect a fresh screenshot/render after the final edit and compare "
    "it with the reference; fix concrete mismatches before claiming success. A saved render alone is not "
    "a visual check. Do not clear/rebuild retained work to fix an output-path or preview failure. "
)


def result_images(content):
    if isinstance(content, list):
        return [part for part in content if isinstance(part, dict)
                and part.get("type") in {"image_url", "input_image", "image"}]
    paths = cached_image_paths(content)
    from agent.image_routing import build_native_content_parts
    parts, _skipped = build_native_content_parts("Candidate screenshot", paths[-2:])
    return [part for part in parts if part.get("type") == "image_url"]


def cached_image_paths(content):
    if not isinstance(content, str) or "MEDIA:" not in content:
        return []
    # External text may only refer to images in Hermes' cache, not arbitrary
    # local files. Native parts retain the existing provider's admission policy.
    from gateway.platforms.base import get_image_cache_dir
    root = Path(get_image_cache_dir()).resolve()
    start = content.find("{")
    if start >= 0:
        try:
            payload, _end = json.JSONDecoder().raw_decode(content, start)
        except ValueError:
            payload = None
        if isinstance(payload, dict) and isinstance(payload.get("result"), str):
            content = payload["result"]
    paths = [Path(match.strip('"\'').replace("\\\\", "\\")) for match in
             re.findall(r'MEDIA:([^\r\n<>]+?\.(?:png|jpe?g|webp|gif))(?=[\s"\']|$)', content, re.I)]
    return [str(path) for path in paths if path.resolve().is_relative_to(root) and path.is_file()]


def visual_evidence_required(request, attempt):
    return request.visual_check
