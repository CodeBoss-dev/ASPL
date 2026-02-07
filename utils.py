import hashlib
import json

def compute_content_hash(article) -> str:
    """
    Computes a deterministic hash of the critical article content.
    Currently uses Title + Main Text.
    """
    # Create a consistent string representation
    # Using separators to avoid ambiguity
    content_str = f"{article.title}|{article.main_text}"
    
    # Compute SHA256
    return hashlib.sha256(content_str.encode('utf-8')).hexdigest()
