"""Shared ID normalization utilities."""


def normalize_idref_id(raw_id: str) -> str:
    """Accept a raw PPN or full URI and return a canonical IdRef URI.

    Examples:
        "121375307" → "http://www.idref.fr/121375307/id"
        "http://www.idref.fr/121375307/id" → unchanged
    """
    raw_id = raw_id.strip()
    if raw_id.startswith("http://") or raw_id.startswith("https://"):
        return raw_id
    return f"http://www.idref.fr/{raw_id}/id"
