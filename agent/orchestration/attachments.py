"""Carry admitted turn content through planning without converting media to text."""

from copy import deepcopy
import re

from agent.message_content import flatten_message_text

_TEXT_TYPES = {"text", "input_text", "output_text"}
_IMAGE_TYPES = {"image", "image_url", "input_image"}
_IMAGE_REF = re.compile(r'^@image:(`[^`\n]+`|"[^"\n]+"|\'[^\'\n]+\'|\S+)\s*$', re.MULTILINE)


def validate_attachments(value):
    if value is None:
        return ()
    if not isinstance(value, list) or any(
        not isinstance(part, dict) or not isinstance(part.get("type"), str) or not part["type"]
        for part in value
    ):
        raise ValueError("attachments must be an array of typed message content objects")
    return tuple(deepcopy(value))


def turn_input(state):
    """Use the live payload for admitted context and persisted refs for text-mode images."""
    original = flatten_message_text(state.original_user_message)
    goal = re.split(r"\n\n--- (?:Attached Context|Context Warnings) ---", original, maxsplit=1)[0]
    live = state.user_message
    text = flatten_message_text(live)
    parts = [deepcopy(p) for p in live if isinstance(p, dict) and p.get("type") not in _TEXT_TYPES] \
        if isinstance(live, list) else []
    # File/PDF/audio/video attachments arrive either as structured parts or as
    # already-expanded @file context. Keep the admitted expansion, including
    # binary-file paths, instead of re-resolving it in the isolated worktree.
    if text and text != goal:
        parts.insert(0, {"type": "text", "text": text})
    images = []
    if not any(p.get("type") in _IMAGE_TYPES for p in parts):
        images = [match[1].strip("`\"'") for match in _IMAGE_REF.finditer(original)]
    if not goal.strip() and (images or parts):
        goal = "Inspect the supplied attachments."
    return goal, images, parts


def has_images(request):
    return bool(request.images) or any(p.get("type") in _IMAGE_TYPES for p in request.attachments)


def child_message(message, attachments):
    """Append copied content to the child's goal after its workspace note is installed."""
    if not attachments:
        return message
    parts = deepcopy(message) if isinstance(message, list) else [{"type": "text", "text": message}]
    return [*parts, *deepcopy(list(attachments))]
