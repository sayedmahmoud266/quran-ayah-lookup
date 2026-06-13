"""
ASR Sequential Fuzzy Search
============================
Maps an ordered list of ASR output segments to their corresponding Quran
verses using a two-pass algorithm:

  Pass 1 — each segment is searched independently via four attempts:
            A) uthmani-normalised single-verse
            B) imlaai single-verse
            C) uthmani with muqatta'at normalisation
            D) sliding-window multi-ayah (for long or low-confidence segments)

  Pass 2 — a sliding-window majority-vote identifies the dominant surah at
            each position; outliers and unresolved segments are re-searched
            with positional constraints (surah_hint + start_after).

Segments that remain unresolved after both passes receive a best-guess verse
inferred by linear interpolation between the nearest resolved neighbours.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple
from collections import Counter

from .models import ASRSegmentResult, FuzzySearchResult, QuranVerse, QuranDatabase
from .text_utils import fuzzy_substring_search, normalize_arabic_text


# ---------------------------------------------------------------------------
# Muqatta'at normalisation
# ---------------------------------------------------------------------------

# Ordered longest-first so compound forms are matched before sub-forms.
_MUQATTAAT_TABLE: List[Tuple[str, str]] = [
    ("كاف ها يا عين صاد", "كهيعص"),
    ("الف لام ميم راء",   "المر"),
    ("الف لام ميم صاد",   "المص"),
    ("عين سين قاف",       "عسق"),
    ("الف لام ميم",       "الم"),
    ("الف لام راء",       "الر"),
    ("الف لام را",        "الر"),
    ("حا ميم",            "حم"),
    ("يا سين",            "يس"),
    ("طا سين ميم",        "طسم"),
    ("طا سين",            "طس"),
    ("طا ها",             "طه"),
    ("نون",               "ن"),
    ("صاد",               "ص"),
    ("قاف",               "ق"),
]


def _normalize_muqattaat(text: str) -> str:
    """Replace spelled-out Quranic opening-letter names with their compact form.

    Works on normalised (diacritic-free) text.  Processes longest entries
    first to avoid partial overlaps.
    """
    result = text
    for spelled, compact in _MUQATTAAT_TABLE:
        result = result.replace(spelled, compact)
    return result


# ---------------------------------------------------------------------------
# Internal unified match type
# ---------------------------------------------------------------------------

@dataclass
class _SegmentMatch:
    """Unified result from any search attempt (single or multi-ayah)."""
    verse: 'QuranVerse'            # first / anchor verse
    verses: List['QuranVerse']     # all matched verses in order
    similarity: float              # always 0.0–1.0
    matched_text: str
    start_word: int                # word offset within first matched verse (0-based)
    end_word: int                  # word offset within last matched verse (exclusive)
    corpus_used: str               # 'uthmani' | 'imlaai'
    is_multi_ayah: bool = False


def _from_fuzzy(r: FuzzySearchResult, corpus: str) -> _SegmentMatch:
    """Wrap a single-verse FuzzySearchResult into a _SegmentMatch."""
    return _SegmentMatch(
        verse=r.verse,
        verses=[r.verse],
        similarity=r.similarity,
        matched_text=r.matched_text,
        start_word=r.start_word,
        end_word=r.end_word,
        corpus_used=corpus,
        is_multi_ayah=False,
    )


# ---------------------------------------------------------------------------
# Thresholds
# ---------------------------------------------------------------------------

# Segments with >= this many words trigger the sliding-window (multi-ayah) attempt.
_MULTI_AYAH_WORD_THRESHOLD = 6
# Skip imlaai full-corpus scan when uthmani already scores this high.
_HIGH_CONFIDENCE = 0.85
# Try sliding window if single-verse score falls below this.
_LOW_SINGLE_CONFIDENCE = 0.65
# Multi-ayah result must beat the single-verse result by this margin to be preferred.
_MULTI_AYAH_MARGIN = 1.05
# Number of consecutive high-quality same-surah results needed to lock in a context.
_CONTEXT_MIN_COUNT = 5
# Minimum per-segment similarity required for a result to count toward context.
_CONTEXT_MIN_SIM = 0.70
# Pass-2 correction is accepted when its similarity is at least this fraction of the
# original outlier's similarity.  Lower than the old 0.8 so that partial-verse hits
# (first half / second half of the same ayah) are accepted.
_CORRECTION_ACCEPT_FACTOR = 0.65


# ---------------------------------------------------------------------------
# Internal search helpers
# ---------------------------------------------------------------------------

def _search_uthmani(
    query: str,
    db: QuranDatabase,
    threshold: float,
    surah_hint: Optional[int],
    start_after: Optional[Tuple[int, int]],
) -> Optional[FuzzySearchResult]:
    """Fuzzy search in the normalised uthmani corpus.  Returns best hit or None."""
    hits = db.fuzzy_search(
        query,
        threshold=threshold,
        normalized=True,
        max_results=1,
        surah_hint=surah_hint,
        start_after=start_after,
    )
    # Prefer corpus verses; fall back to special verses only if nothing else found.
    for hit in hits:
        if not hit.verse.is_istiadhah and not hit.verse.is_tasdiq:
            return hit
    if hits:
        return hits[0]
    return None


def _build_imlaai_candidates(
    db: QuranDatabase,
    surah_hint: Optional[int],
    start_after: Optional[Tuple[int, int]],
) -> List[QuranVerse]:
    """Return the verse subset to search in the imlaai corpus.

    When *surah_hint* is set the search is restricted to that surah ±3,
    keeping the scan fast.  Without a hint the full corpus is used.
    """
    if surah_hint is not None:
        hint = max(1, min(114, surah_hint))
        for radius in [0, 1, 3]:
            s_from = max(1, hint - radius)
            s_to = min(114, hint + radius)
            verses = db._get_surah_range_verses(s_from, s_to)
            if start_after is not None:
                verses = [v for v in verses
                          if (v.surah_number, v.ayah_number) > start_after]
            if verses:
                break
        else:
            verses = []
    elif start_after is not None:
        verses = db._get_verses_after_position(*start_after)
        if not verses:
            verses = db.get_all_verses()
    else:
        verses = db.get_all_verses()

    # Prepend special verses so they're considered for imlaai matching
    for sv in db._special_verses.values():
        if sv.text_imlaai:
            verses = [sv] + verses
    return verses


def _search_imlaai(
    query: str,
    db: QuranDatabase,
    threshold: float,
    surah_hint: Optional[int],
    start_after: Optional[Tuple[int, int]],
) -> Optional[FuzzySearchResult]:
    """Fuzzy search over verse.text_imlaai fields.  Returns best hit or None."""
    norm_query = normalize_arabic_text(query)
    candidates = _build_imlaai_candidates(db, surah_hint, start_after)

    best: Optional[FuzzySearchResult] = None
    for verse in candidates:
        imlaai_text = verse.text_imlaai
        if not imlaai_text:
            continue
        norm_imlaai = normalize_arabic_text(imlaai_text)
        match = fuzzy_substring_search(norm_query, norm_imlaai, threshold=threshold)
        if match is None:
            continue
        if best is None or match["similarity"] > best.similarity:
            best = FuzzySearchResult(
                verse=verse,
                start_word=match["start_word"],
                end_word=match["end_word"],
                similarity=match["similarity"],
                matched_text=match["matched_text"],
                query_text=norm_query,
            )
    return best


def _search_sliding(
    query: str,
    db: QuranDatabase,
    threshold: float,
    surah_hint: Optional[int],
    start_after: Optional[Tuple[int, int]],
) -> Optional[_SegmentMatch]:
    """Sliding-window multi-ayah search.  Returns best multi-verse match or None.

    The threshold is converted from the 0–1 scale used elsewhere in this
    module to the 0–100 scale used by sliding_window_multi_ayah_search.
    """
    from .text_utils import sliding_window_multi_ayah_search
    norm_query = normalize_arabic_text(query)
    sw_threshold = threshold * 100.0
    hits = sliding_window_multi_ayah_search(
        norm_query,
        threshold=sw_threshold,
        normalized=True,
        max_results=1,
        db=db,
        surah_hint=surah_hint,
        start_after=start_after,
    )
    if not hits:
        return None
    m = hits[0]
    return _SegmentMatch(
        verse=m.verses[0],
        verses=list(m.verses),
        similarity=m.similarity / 100.0,   # normalise 0–100 → 0–1
        matched_text=m.matched_text,
        start_word=m.start_word,
        end_word=m.end_word,
        corpus_used='uthmani',
        is_multi_ayah=len(m.verses) > 1,
    )


def _search_segment(
    query: str,
    db: QuranDatabase,
    threshold: float,
    surah_hint: Optional[int] = None,
    start_after: Optional[Tuple[int, int]] = None,
) -> Optional[_SegmentMatch]:
    """Four-attempt strategy to find the best match for one ASR segment.

    Attempts:
        A — uthmani corpus, single-verse, query as-is.
        B — imlaai corpus, single-verse.  Skipped when A scores ≥ _HIGH_CONFIDENCE
            and no surah_hint is given, to avoid an expensive full-corpus scan.
        C — uthmani corpus, single-verse, muqattaʽat-normalised query (only when
            normalisation actually changes the text).
        D — sliding-window multi-ayah.  Triggered when the segment has ≥
            _MULTI_AYAH_WORD_THRESHOLD words, or when the best single-verse
            score is below _LOW_SINGLE_CONFIDENCE.

    Multi-ayah (D) is preferred over the best single-verse result only when
    its similarity exceeds the single-verse score by > _MULTI_AYAH_MARGIN,
    so short segments aren’t over-split.

    Returns the best _SegmentMatch, or None if nothing exceeds the threshold.
    """
    norm_query = normalize_arabic_text(query)
    word_count = len(norm_query.split())

    # — A: uthmani single-verse
    raw_a = _search_uthmani(norm_query, db, threshold, surah_hint, start_after)
    result_a: Optional[_SegmentMatch] = _from_fuzzy(raw_a, 'uthmani') if raw_a else None

    # — B: imlaai single-verse
    run_imlaai = (
        result_a is None
        or result_a.similarity < _HIGH_CONFIDENCE
        or surah_hint is not None
    )
    result_b: Optional[_SegmentMatch] = None
    if run_imlaai:
        imlaai_hint = surah_hint
        if imlaai_hint is None and result_a is not None:
            if not result_a.verse.is_istiadhah and not result_a.verse.is_tasdiq:
                imlaai_hint = result_a.verse.surah_number
        raw_b = _search_imlaai(query, db, threshold, imlaai_hint, start_after)
        result_b = _from_fuzzy(raw_b, 'imlaai') if raw_b else None

    # — C: uthmani with muqatta'at normalisation
    muq_query = _normalize_muqattaat(norm_query)
    result_c: Optional[_SegmentMatch] = None
    if muq_query != norm_query:
        raw_c = _search_uthmani(muq_query, db, threshold, surah_hint, start_after)
        result_c = _from_fuzzy(raw_c, 'uthmani') if raw_c else None

    # Best single-verse result
    best_single: Optional[_SegmentMatch] = None
    for r in (result_a, result_b, result_c):
        if r is not None and (best_single is None or r.similarity > best_single.similarity):
            best_single = r

    # — D: sliding-window multi-ayah
    should_try_sliding = (
        word_count >= _MULTI_AYAH_WORD_THRESHOLD
        or best_single is None
        or best_single.similarity < _LOW_SINGLE_CONFIDENCE
    )
    result_d: Optional[_SegmentMatch] = None
    if should_try_sliding:
        result_d = _search_sliding(query, db, threshold, surah_hint, start_after)

    # Prefer multi-ayah only when it is meaningfully better
    if result_d is not None:
        single_sim = best_single.similarity if best_single else 0.0
        if result_d.similarity > single_sim * _MULTI_AYAH_MARGIN:
            return result_d

    return best_single


# ---------------------------------------------------------------------------
# Sequence-analysis helpers
# ---------------------------------------------------------------------------


def _is_semi_linear(ayahs: List[int]) -> bool:
    """Return True when the ayah sequence is roughly non-decreasing.

    A sequence is considered semi-linear if at most one-quarter of
    consecutive pairs regress by more than one ayah.  Equal successive
    values (same verse split across two segments) are always allowed.
    """
    if len(ayahs) < 2:
        return True
    regressions = sum(
        1 for a, b in zip(ayahs[:-1], ayahs[1:]) if b < a - 2
    )
    return regressions <= max(1, len(ayahs) // 4)


def _extract_positions(
    results: List[Optional[_SegmentMatch]],
) -> List[Optional[Tuple[int, int]]]:
    """Convert per-segment results to (surah, ayah) positions (first verse of each)."""
    out: List[Optional[Tuple[int, int]]] = []
    for m in results:
        if m is None or m.verse is None:
            out.append(None)
        elif m.verse.is_istiadhah or m.verse.is_tasdiq:
            out.append(None)  # don’t let special verses skew consensus
        else:
            out.append((m.verse.surah_number, m.verse.ayah_number))
    return out


def _sliding_consensus(
    positions: List[Optional[Tuple[int, int]]],
    window: int = 7,
) -> List[Optional[int]]:
    """Per-index majority-vote over a sliding window of surah numbers.

    Returns a list of the same length where each element is the dominant
    surah at that position, or None if the window is all unresolved.
    """
    surahs_only = [p[0] if p else None for p in positions]
    n = len(surahs_only)
    half = window // 2
    consensus: List[Optional[int]] = []
    for i in range(n):
        lo = max(0, i - half)
        hi = min(n, i + half + 1)
        window_vals = [s for s in surahs_only[lo:hi] if s is not None]
        if not window_vals:
            consensus.append(None)
        else:
            majority_surah, _ = Counter(window_vals).most_common(1)[0]
            consensus.append(majority_surah)
    return consensus


def _nearest_valid_before(
    pass_results: List[Optional[_SegmentMatch]],
    idx: int,
) -> Optional[Tuple[int, int]]:
    """Return (surah, ayah) of the *last* verse of the nearest resolved result before idx.

    For multi-ayah matches the last verse is used as anchor so that the next
    search starts after the full extent of the preceding segment.
    """
    for j in range(idx - 1, -1, -1):
        m = pass_results[j]
        if m is not None and m.verse is not None:
            if not m.verse.is_istiadhah and not m.verse.is_tasdiq:
                anchor = m.verses[-1] if m.verses else m.verse
                return (anchor.surah_number, anchor.ayah_number)
    return None


def _nearest_valid_after(
    pass_results: List[Optional[_SegmentMatch]],
    idx: int,
) -> Optional[Tuple[int, int]]:
    """Return (surah, ayah) of the first verse of the nearest resolved result after idx."""
    for j in range(idx + 1, len(pass_results)):
        m = pass_results[j]
        if m is not None and m.verse is not None:
            if not m.verse.is_istiadhah and not m.verse.is_tasdiq:
                return (m.verse.surah_number, m.verse.ayah_number)
    return None


def _infer_verse_from_neighbours(
    db: QuranDatabase,
    before: Optional[Tuple[int, int]],
    after: Optional[Tuple[int, int]],
) -> Optional[QuranVerse]:
    """Infer a best-guess verse by interpolating between two resolved neighbours.

    When both neighbours exist in the same surah the midpoint verse is
    returned.  Otherwise the verse immediately after *before* (or immediately
    before *after*) is used as a fallback.
    """
    ref_list = db.sorted_ayahs_ref_list
    if not ref_list:
        return None

    def idx_of(pos: Tuple[int, int]) -> Optional[int]:
        try:
            return ref_list.index(pos)
        except ValueError:
            return None

    if before is not None and after is not None:
        i_before = idx_of(before)
        i_after = idx_of(after)
        if i_before is not None and i_after is not None and i_after > i_before + 1:
            mid = (i_before + i_after) // 2
            s, a = ref_list[mid]
            try:
                return db.get_verse(s, a)
            except ValueError:
                pass

    if before is not None:
        i = idx_of(before)
        if i is not None and i + 1 < len(ref_list):
            s, a = ref_list[i + 1]
            try:
                return db.get_verse(s, a)
            except ValueError:
                pass

    if after is not None:
        i = idx_of(after)
        if i is not None and i > 0:
            s, a = ref_list[i - 1]
            try:
                return db.get_verse(s, a)
            except ValueError:
                pass

    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def asr_sequential_fuzzy_search(
    segments: List[str],
    threshold: float = 0.5,
    consensus_window: int = 7,
    db: Optional[QuranDatabase] = None,
) -> List[ASRSegmentResult]:
    """Map an ordered list of ASR segments to their Quran verses.

    Each segment may map to a single verse (or a partial verse) or to
    multiple consecutive ayahs when the reciter does not pause between them.
    The ``is_multi_ayah`` flag on each :class:`ASRSegmentResult` indicates
    which case applies.  ``start_word`` and ``end_word`` give word-level
    offsets *within the first and last matched verse* respectively, allowing
    callers to pinpoint exactly which part of the corpus text was matched.

    This function is designed for output from an ASR (automatic speech
    recognition) model where the input is a sequence of text segments
    extracted from a continuous recitation.  Because ASR output can contain
    transcription errors, the algorithm uses two passes:

    **Pass 1 — independent search (four attempts per segment)**

    * A — uthmani-normalised single-verse fuzzy search
    * B — imlaai corpus single-verse fuzzy search (handles spelled-out letter
      names like “حا ميم”)
    * C — uthmani single-verse with muqattaʽat normalisation
      (e.g. “حا ميم” → “حم”)
    * D — sliding-window multi-ayah search (triggered when the segment has ≥ 6
      words or single-verse confidence is low)

    The best hit across all four attempts is kept.  Multi-ayah (D) wins only
    when its score exceeds the best single-verse score by > 5 %.

    **Pass 2 — sequence correction**

    A sliding-window majority vote determines the dominant surah at each
    position.  Outliers are re-searched with ``surah_hint`` set to the
    consensus surah and ``start_after`` pointing to the end of the nearest
    preceding resolved segment.  Unresolved segments are retried at a lower
    threshold using the same context.  Segments still unresolved after Pass 2
    receive a best-guess verse inferred by linear interpolation.

    Args:
        segments: Ordered list of ASR output strings.
        threshold: Minimum fuzzy similarity score (0.0–1.0, default 0.5).
                   Lower than the usual 0.7 to tolerate ASR noise.
        consensus_window: Sliding-window size for surah majority vote
                          (default 7).
        db: Pre-loaded :class:`QuranDatabase`; uses
            :func:`get_quran_database` if *None*.

    Returns:
        A list of :class:`ASRSegmentResult` objects, one per input segment,
        in input order.  Key fields per result:

        * ``verse`` — first (or only) matched verse
        * ``verses`` — all matched verses (multi-element when ``is_multi_ayah``)
        * ``is_multi_ayah`` — True when the segment spans more than one ayah
        * ``start_word`` — word offset of match start within the first verse
        * ``end_word`` — word offset of match end within the last verse
        * ``similarity`` — best similarity score (0.0–1.0)
        * ``corpus_used`` — which corpus produced the match
        * ``corrected`` — True if Pass 2 changed the assignment

    Examples::

        >>> # Multi-ayah segment
        >>> results = asr_sequential_fuzzy_search([
        ...     'بسم الله الرحمن الرحيم الف لام ميم ذلك الكتاب لا ريب فيه',
        ... ])
        >>> print(results[0].is_multi_ayah)            # True
        >>> print([v.ayah_number for v in results[0].verses])

        >>> # Muqattaʽat handled automatically
        >>> results = asr_sequential_fuzzy_search(['حا ميم', 'والكتاب المبين'])
        >>> print(results[0].verse.surah_number)       # 44
    """
    if db is None:
        from .loader import get_quran_database
        db = get_quran_database()

    n = len(segments)
    if n == 0:
        return []

    # ── Pass 1: per-segment search with incremental context ───────────────────
    # Process segments in order.  As soon as _CONTEXT_MIN_COUNT consecutive
    # non-special results all map to the same surah with similarity ≥
    # _CONTEXT_MIN_SIM and semi-linear ayah numbers, that surah becomes the
    # active context and is passed as surah_hint for all subsequent searches.
    # This prevents short/ambiguous segments from being pulled to unrelated
    # surahs once the recitation surah is known.
    first_pass: List[Optional[_SegmentMatch]] = []
    active_context: Optional[int] = None          # currently locked surah
    context_buffer: List[Optional[_SegmentMatch]] = []  # all non-special results

    for seg in segments:
        if not seg or not seg.strip():
            first_pass.append(None)
            context_buffer.append(None)
            continue

        # Once context is established, bias every search toward that surah.
        result = _search_segment(seg.strip(), db, threshold, surah_hint=active_context)
        first_pass.append(result)

        # Exclude special verses from context tracking.
        if (result is not None and result.verse is not None
                and not result.verse.is_istiadhah
                and not result.verse.is_tasdiq):
            context_buffer.append(result)
        else:
            context_buffer.append(None)

        # Re-evaluate context after every new non-None entry.
        # Look at the last _CONTEXT_MIN_COUNT non-None entries and check
        # whether they unanimously agree on a surah with high similarity
        # and a semi-linear ayah sequence.
        recent = [m for m in context_buffer if m is not None][-_CONTEXT_MIN_COUNT:]
        if len(recent) >= _CONTEXT_MIN_COUNT:
            surahs = [m.verse.surah_number for m in recent if m.verse]
            sims   = [m.similarity         for m in recent if m.verse]
            ayahs  = [m.verse.ayah_number  for m in recent if m.verse]
            if (surahs
                    and len(set(surahs)) == 1
                    and min(sims) >= _CONTEXT_MIN_SIM
                    and _is_semi_linear(ayahs)):
                active_context = surahs[0]

    # ── Pass 2: sequence correction via sliding-window consensus ────────────
    positions = _extract_positions(first_pass)
    consensus = _sliding_consensus(positions, window=consensus_window)

    second_pass: List[Tuple[Optional[_SegmentMatch], bool]] = []

    for i, (seg, fp_match) in enumerate(zip(segments, first_pass)):
        expected_surah = consensus[i]

        # Special verses: never correct, return as-is.
        if fp_match is not None and fp_match.verse is not None:
            if fp_match.verse.is_istiadhah or fp_match.verse.is_tasdiq:
                second_pass.append((fp_match, False))
                continue

        if fp_match is not None and fp_match.verse is not None:
            fp_surah = fp_match.verse.surah_number
            if expected_surah is not None and fp_surah != expected_surah:
                # Outlier detected: re-search using ONLY surah_hint.
                #
                # CRITICAL — do NOT pass start_after here.  A single ayah can
                # legitimately be referenced by two consecutive segments (e.g.
                # the reciter pauses mid-verse): the previous segment takes the
                # first half, this one takes the second half.  Passing
                # start_after=(prev_surah, prev_ayah) would silently skip the
                # only correct verse in the context surah and cause a fallback
                # to an unrelated surah every time.
                corrected = _search_segment(
                    seg.strip(), db, threshold,
                    surah_hint=expected_surah,
                )
                # Accept if plausible — use a more lenient factor than before
                # so that partial-verse substring matches are not rejected.
                if (corrected is not None and corrected.verse is not None
                        and corrected.similarity >= fp_match.similarity * _CORRECTION_ACCEPT_FACTOR):
                    second_pass.append((corrected, True))
                    continue
            second_pass.append((fp_match, False))

        else:
            # No first-pass match — retry at a lower threshold.
            # Again: no start_after for the same reason explained above.
            retry_threshold = threshold * 0.8
            if expected_surah is not None:
                corrected = _search_segment(
                    seg.strip() if seg else "", db, retry_threshold,
                    surah_hint=expected_surah,
                )
                if corrected is not None:
                    second_pass.append((corrected, True))
                    continue
            second_pass.append((None, False))

    # ── Build final results with neighbour-interpolation for None entries ───
    resolved: List[Optional[Tuple[int, int]]] = []
    for m, _ in second_pass:
        if (m is not None and m.verse is not None
                and not m.verse.is_istiadhah and not m.verse.is_tasdiq):
            anchor = m.verses[-1] if m.verses else m.verse
            resolved.append((anchor.surah_number, anchor.ayah_number))
        else:
            resolved.append(None)

    output: List[ASRSegmentResult] = []
    for i, (seg, (m, corrected)) in enumerate(zip(segments, second_pass)):
        if m is not None and m.verse is not None:
            output.append(ASRSegmentResult(
                segment_index=i,
                segment_text=seg,
                verse=m.verse,
                verses=m.verses,
                is_multi_ayah=m.is_multi_ayah,
                similarity=m.similarity,
                matched_text=m.matched_text,
                start_word=m.start_word,
                end_word=m.end_word,
                corpus_used=m.corpus_used,
                corrected=corrected,
            ))
        else:
            # Interpolate between neighbours
            before_pos: Optional[Tuple[int, int]] = None
            after_pos: Optional[Tuple[int, int]] = None
            for j in range(i - 1, -1, -1):
                if resolved[j] is not None:
                    before_pos = resolved[j]
                    break
            for j in range(i + 1, n):
                if resolved[j] is not None:
                    after_pos = resolved[j]
                    break

            guessed_verse = _infer_verse_from_neighbours(db, before_pos, after_pos)
            output.append(ASRSegmentResult(
                segment_index=i,
                segment_text=seg,
                verse=guessed_verse,
                verses=[guessed_verse] if guessed_verse else [],
                is_multi_ayah=False,
                similarity=0.0,
                matched_text="",
                start_word=0,
                end_word=0,
                corpus_used="none",
                corrected=True,
            ))

    return output



# ---------------------------------------------------------------------------
# Muqatta'at normalisation
# ---------------------------------------------------------------------------

# Ordered longest-first so compound forms are matched before sub-forms.
