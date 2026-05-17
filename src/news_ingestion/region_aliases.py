from __future__ import annotations

import re
from collections.abc import Iterable


CITY_ALIASES = {
    "서울": ("서울특별시", "서울시", "서울"),
    "부산": ("부산광역시", "부산시", "부산"),
    "대구": ("대구광역시", "대구시", "대구"),
    "인천": ("인천광역시", "인천시", "인천"),
    "광주": ("광주광역시", "광주시", "광주"),
    "대전": ("대전광역시", "대전시", "대전"),
    "울산": ("울산광역시", "울산시", "울산"),
    "세종": ("세종특별자치시", "세종시", "세종"),
}

PROVINCE_ALIASES = {
    "경기": ("경기도", "경기"),
    "강원": ("강원특별자치도", "강원도", "강원"),
    "충북": ("충청북도", "충북도", "충북"),
    "충남": ("충청남도", "충남도", "충남"),
    "전북": ("전북특별자치도", "전라북도", "전북도", "전북"),
    "전남": ("전라남도", "전남도", "전남"),
    "경북": ("경상북도", "경북도", "경북"),
    "경남": ("경상남도", "경남도", "경남"),
    "제주": ("제주특별자치도", "제주도", "제주"),
}

GROUP_ALIASES = {
    "수도권": ("수도권", "서울", "경기", "인천"),
    "호남": ("호남", "광주", "전북", "전남"),
    "영남": ("영남", "부산", "대구", "울산", "경북", "경남"),
    "충청권": ("충청권", "대전", "세종", "충북", "충남"),
    "충청": ("충청권", "대전", "세종", "충북", "충남"),
    "부울경": ("부울경", "부산", "울산", "경남"),
    "PK": ("PK", "부산", "울산", "경남"),
    "TK": ("TK", "대구", "경북"),
}

UNIVERSITY_FALSE_POSITIVE_RE = re.compile(
    r"(경북대(?:학교)?|경남대(?:학교)?|전북대(?:학교)?|전남대(?:학교)?|충북대(?:학교)?|충남대(?:학교)?)"
)
AMBIGUOUS_DISTRICT_NAMES = {"중구", "서구", "동구", "남구", "북구"}

_ALIAS_TO_NORMALIZED: dict[str, str] = {}
for normalized, aliases in CITY_ALIASES.items():
    _ALIAS_TO_NORMALIZED.update({alias: normalized for alias in aliases})
for normalized, aliases in PROVINCE_ALIASES.items():
    _ALIAS_TO_NORMALIZED.update({alias: normalized for alias in aliases})

_TEXT_RULES = sorted(
    [
        *((alias, (normalized,)) for alias, normalized in _ALIAS_TO_NORMALIZED.items()),
        *((alias, expanded) for alias, expanded in GROUP_ALIASES.items()),
    ],
    key=lambda rule: len(rule[0]),
    reverse=True,
)


def normalize_regions_from_text(text: str | None) -> list[str]:
    if not text:
        return []

    clean_text = UNIVERSITY_FALSE_POSITIVE_RE.sub(" ", text)
    matches: list[tuple[int, int, tuple[str, ...]]] = []
    for alias, normalized_values in _TEXT_RULES:
        start = 0
        while True:
            index = clean_text.find(alias, start)
            if index == -1:
                break
            matches.append((index, -len(alias), normalized_values))
            start = index + len(alias)

    regions: list[str] = []
    for _index, _negative_length, normalized_values in sorted(matches):
        regions.extend(normalized_values)
    return _dedupe(regions)


def normalize_region_values(values: Iterable[str] | None) -> list[str]:
    if values is None:
        return []

    regions: list[str] = []
    for raw_value in values:
        value = str(raw_value).strip()
        if not value:
            continue
        if value in AMBIGUOUS_DISTRICT_NAMES or UNIVERSITY_FALSE_POSITIVE_RE.fullmatch(value):
            continue
        if value in GROUP_ALIASES:
            regions.extend(GROUP_ALIASES[value])
        elif value in _ALIAS_TO_NORMALIZED:
            regions.append(_ALIAS_TO_NORMALIZED[value])
        else:
            regions.append(value)
    return _dedupe(regions)


def merge_regions(*region_lists: Iterable[str] | None) -> list[str]:
    merged: list[str] = []
    for region_list in region_lists:
        merged.extend(normalize_region_values(region_list))
    return _dedupe(merged)


def _dedupe(values: Iterable[str]) -> list[str]:
    seen = set()
    deduped: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        deduped.append(value)
    return deduped
