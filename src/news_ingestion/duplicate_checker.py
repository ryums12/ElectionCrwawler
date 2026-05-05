from __future__ import annotations

from .models import Article


class DuplicateChecker:
    """Placeholder for future article-level duplicate detection.

    This is intentionally conservative today: exact URL idempotency lives in the
    repository, while future semantic/title/content duplicate detection can set
    duplicate_of here before save.
    """

    def mark_duplicate(self, article: Article) -> Article:
        return article
