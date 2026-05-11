from __future__ import annotations

import json
from datetime import datetime

from .models import Article, CandidateCluster, DuplicateClusterResult
from .normalizer import tokenize_normalized
from .repository import ArticleRepository


class DuplicateChecker:
    def find_duplicate_cluster(
        self,
        article: Article,
        repository: ArticleRepository,
    ) -> DuplicateClusterResult:
        candidates = repository.find_candidate_clusters(article)
        best = DuplicateClusterResult(is_duplicate=False)

        for cluster in candidates:
            result = self._score_cluster(article, cluster)
            if result.similarity_score > best.similarity_score:
                best = result

        return best if best.is_duplicate else DuplicateClusterResult(is_duplicate=False)

    def _score_cluster(
        self,
        article: Article,
        cluster: CandidateCluster,
    ) -> DuplicateClusterResult:
        if article.content_hash and article.content_hash == cluster.content_hash:
            return DuplicateClusterResult(
                is_duplicate=True,
                matched_cluster_id=cluster.id,
                representative_article_id=cluster.representative_article_id,
                similarity_score=1.0,
                duplicate_reason="CONTENT_HASH",
            )

        title_similarity = calculate_title_similarity(
            article.normalized_title,
            cluster.normalized_title,
        )
        description_similarity = calculate_description_similarity(
            article.normalized_description,
            cluster.normalized_description,
        )
        keyword_overlap = calculate_keyword_overlap(article, cluster)
        hours_apart = _hours_apart(article.published_at, cluster.last_published_at)

        is_duplicate = False
        reason = None
        score = max(title_similarity, (title_similarity + description_similarity) / 2)

        if title_similarity >= 0.85:
            is_duplicate = True
            reason = "TITLE_SIMILARITY"
        elif title_similarity >= 0.75 and description_similarity >= 0.65:
            is_duplicate = True
            reason = "TITLE_AND_DESCRIPTION_SIMILARITY"
        elif (
            title_similarity >= 0.65
            and keyword_overlap >= 0.5
            and (hours_apart is None or hours_apart <= 24)
        ):
            is_duplicate = True
            reason = "TITLE_KEYWORD_TIME_SIMILARITY"
            score = max(score, (title_similarity + keyword_overlap) / 2)

        return DuplicateClusterResult(
            is_duplicate=is_duplicate,
            matched_cluster_id=cluster.id if is_duplicate else None,
            representative_article_id=cluster.representative_article_id if is_duplicate else None,
            similarity_score=round(score, 4),
            duplicate_reason=reason,
        )


def calculate_title_similarity(left: str | None, right: str | None) -> float:
    return _jaccard_similarity(tokenize_normalized(left), tokenize_normalized(right))


def calculate_description_similarity(left: str | None, right: str | None) -> float:
    return _jaccard_similarity(tokenize_normalized(left), tokenize_normalized(right))


def calculate_keyword_overlap(article: Article, cluster: CandidateCluster) -> float:
    left = _keyword_set(article.main_keywords)
    left.update(_keyword_set(article.parties))
    left.update(_keyword_set(article.regions))
    left.update(_keyword_set(article.people))

    right = _keyword_set(cluster.main_keywords)
    right.update(_keyword_set(cluster.parties))
    right.update(_keyword_set(cluster.regions))
    right.update(_keyword_set(cluster.people))

    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def _jaccard_similarity(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def _keyword_set(value: str | None) -> set[str]:
    if not value:
        return set()
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return {token.strip().casefold() for token in value.split(",") if token.strip()}
    if isinstance(parsed, list):
        return {str(item).strip().casefold() for item in parsed if str(item).strip()}
    return set()


def _hours_apart(left: datetime | None, right: datetime | None) -> float | None:
    if not left or not right:
        return None
    return abs((left - right).total_seconds()) / 3600
