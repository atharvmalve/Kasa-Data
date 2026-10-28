import hashlib

def compute_checksums(data: bytes) -> tuple[str, str]:
    """Compute MD5 and SHA-256 checksums for binary data."""
    md5 = hashlib.md5(data).hexdigest()
    sha256 = hashlib.sha256(data).hexdigest()
    return md5, sha256

def compute_text_hash(text: str) -> str:
    """Compute SHA-256 hash for text."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

