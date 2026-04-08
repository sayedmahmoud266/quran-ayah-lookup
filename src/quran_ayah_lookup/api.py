"""
FastAPI application for Quran Ayah Lookup REST API.

This module provides a RESTful API interface for all package functionalities
including verse lookup, text search, fuzzy search, and database statistics.
"""
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, ConfigDict

# Import the package functionality
from . import (
    get_verse,
    get_surah,
    search_text,
    fuzzy_search,
    search_sliding_window,
    smart_search,
    get_surah_verses,
    get_quran_database,
    QuranVerse,
    FuzzySearchResult,
    MultiAyahMatch,
    __version__,
)

# Optional: vector search (requires [vector] extras + pre-built FAISS index)
try:
    from .vector_search import VectorSearch as _VectorSearch
    _VECTOR_AVAILABLE = True
except ImportError:
    _VECTOR_AVAILABLE = False

_vector_search_instance: Optional["_VectorSearch"] = None  # type: ignore[name-defined]


def _get_vs():
    """Return (or lazily create) the module-level VectorSearch instance."""
    global _vector_search_instance
    if _vector_search_instance is None:
        _vector_search_instance = _VectorSearch()
    return _vector_search_instance


# Pydantic models for API responses
class VerseResponse(BaseModel):
    """Response model for a single verse."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "surah_number": 1,
                "ayah_number": 1,
                "text": "بِسۡمِ ٱللَّهِ ٱلرَّحۡمَـٰنِ ٱلرَّحِیمِ",
                "text_normalized": "بسم الله الرحمن الرحيم",
                "is_basmalah": True
            }
        }
    )

    surah_number: int = Field(..., description="Surah number (1-114)")
    ayah_number: int = Field(..., description="Ayah number (0 for Basmala, 1+ for regular ayahs)")
    text: str = Field(..., description="Original Arabic text with diacritics")
    text_normalized: str = Field(..., description="Normalized Arabic text without diacritics")
    is_basmalah: bool = Field(..., description="True if this is a Basmala verse")


class SurahInfoResponse(BaseModel):
    """Response model for surah information."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "surah_number": 1,
                "verse_count": 7,
                "has_basmala": True
            }
        }
    )

    surah_number: int = Field(..., description="Surah number (1-114)")
    verse_count: int = Field(..., description="Total number of verses in the surah")
    has_basmala: bool = Field(..., description="Whether the surah has a Basmala (ayah 0)")


class FuzzySearchResultResponse(BaseModel):
    """Response model for a fuzzy search result."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "verse": {
                    "surah_number": 1,
                    "ayah_number": 1,
                    "text": "بِسۡمِ ٱللَّهِ ٱلرَّحۡمَـٰنِ ٱلرَّحِیمِ",
                    "text_normalized": "بسم الله الرحمن الرحيم",
                    "is_basmalah": True
                },
                "start_word": 0,
                "end_word": 4,
                "similarity": 0.95,
                "matched_text": "بسم الله الرحمن الرحيم",
                "query_text": "بسم الله"
            }
        }
    )

    verse: VerseResponse
    start_word: int = Field(..., description="Starting word index of the match (0-based)")
    end_word: int = Field(..., description="Ending word index of the match (exclusive)")
    similarity: float = Field(..., description="Similarity score (0.0-1.0)")
    matched_text: str = Field(..., description="The actual text segment that was matched")
    query_text: str = Field(..., description="The original query text used for matching")


class MultiAyahMatchResponse(BaseModel):
    """Response model for a multi-ayah match from sliding window search."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "verses": [
                    {
                        "surah_number": 55,
                        "ayah_number": 1,
                        "text": "ٱلرَّحۡمَـٰنُ",
                        "text_normalized": "الرحمن",
                        "is_basmalah": False
                    },
                    {
                        "surah_number": 55,
                        "ayah_number": 2,
                        "text": "عَلَّمَ ٱلۡقُرۡءَانَ",
                        "text_normalized": "علم القران",
                        "is_basmalah": False
                    }
                ],
                "similarity": 95.5,
                "matched_text": "الرحمن علم القران",
                "query_text": "الرحمن علم القران",
                "start_surah": 55,
                "start_ayah": 1,
                "start_word": 0,
                "end_surah": 55,
                "end_ayah": 2,
                "end_word": 2,
                "reference": "55:1-2"
            }
        }
    )

    verses: List[VerseResponse] = Field(..., description="List of verses in the match (ordered)")
    similarity: float = Field(..., description="Similarity score (0.0-100.0)")
    matched_text: str = Field(..., description="The actual text segment that was matched")
    query_text: str = Field(..., description="The original query text used for matching")
    start_surah: int = Field(..., description="Starting surah number")
    start_ayah: int = Field(..., description="Starting ayah number")
    start_word: int = Field(..., description="Starting word index within the first ayah (0-based)")
    end_surah: int = Field(..., description="Ending surah number")
    end_ayah: int = Field(..., description="Ending ayah number")
    end_word: int = Field(..., description="Ending word index within the last ayah (exclusive)")
    reference: str = Field(..., description="Human-readable reference string (e.g., '55:1-4')")


class SmartSearchResponse(BaseModel):
    """Response model for smart search results."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "method": "fuzzy",
                "count": 5,
                "exact_results": None,
                "fuzzy_results": [
                    {
                        "verse": {
                            "surah_number": 1,
                            "ayah_number": 1,
                            "text": "بِسۡمِ ٱللَّهِ ٱلرَّحۡمَـٰنِ ٱلرَّحِیمِ",
                            "text_normalized": "بسم الله الرحمن الرحيم",
                            "is_basmalah": True
                        },
                        "start_word": 0,
                        "end_word": 4,
                        "similarity": 0.95,
                        "matched_text": "بسم الله الرحمن الرحيم",
                        "query_text": "بسم الله"
                    }
                ],
                "sliding_window_results": None
            }
        }
    )

    method: str = Field(..., description="Search method that returned results: 'exact', 'fuzzy', 'sliding_window', or 'none'")
    count: int = Field(..., description="Total number of results found")
    exact_results: Optional[List[VerseResponse]] = Field(None, description="Results from exact text search (if method='exact')")
    fuzzy_results: Optional[List[FuzzySearchResultResponse]] = Field(None, description="Results from fuzzy search (if method='fuzzy')")
    sliding_window_results: Optional[List[MultiAyahMatchResponse]] = Field(None, description="Results from sliding window search (if method='sliding_window')")


class DatabaseStatsResponse(BaseModel):
    """Response model for database statistics."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "total_surahs": 114,
                "total_verses": 6348,
                "source": "Tanzil.net",
                "version": __version__
            }
        }
    )

    total_surahs: int = Field(..., description="Total number of surahs")
    total_verses: int = Field(..., description="Total number of verses (including Basmalas)")
    source: str = Field(..., description="Source of the Quran text")
    version: str = Field(..., description="Package version")


class ErrorResponse(BaseModel):
    """Response model for errors."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "detail": "Verse not found"
            }
        }
    )

    detail: str = Field(..., description="Error message")


# Create FastAPI app
app = FastAPI(
    title="Quran Ayah Lookup API",
    description="""
    A high-performance REST API for Quranic ayah lookup with O(1) verse access and Arabic text normalization.
    
    **Features:**
    - 🚀 O(1) Performance: Lightning-fast verse lookup
    - 📖 Ayah Lookup: Direct access to any verse
    - 🔍 Arabic Text Search: Search for ayahs using Arabic text
    - 🎯 Fuzzy Search: Advanced partial text matching with similarity scoring
    - 📚 Tanzil.net Corpus: Uses trusted Quran text from Tanzil.net
    - 🕌 Arabic Only: Focused on Arabic Quranic text (no translations supported)
    
    **Source:** This API uses the Quran text corpus from [Tanzil.net](https://tanzil.net/), 
    a trusted source for accurate Quranic text.
    """,
    version=__version__,
    contact={
        "name": "Sayed Mahmoud",
        "email": "foss-support@sayedmahmoud266.website",
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    },
)


# Helper function to convert QuranVerse to VerseResponse
def verse_to_response(verse: QuranVerse) -> VerseResponse:
    """Convert a QuranVerse object to a VerseResponse."""
    return VerseResponse(
        surah_number=verse.surah_number,
        ayah_number=verse.ayah_number,
        text=verse.text,
        text_normalized=verse.text_normalized,
        is_basmalah=verse.is_basmalah
    )


# Helper function to convert FuzzySearchResult to FuzzySearchResultResponse
def fuzzy_result_to_response(result: FuzzySearchResult) -> FuzzySearchResultResponse:
    """Convert a FuzzySearchResult object to a FuzzySearchResultResponse."""
    return FuzzySearchResultResponse(
        verse=verse_to_response(result.verse),
        start_word=result.start_word,
        end_word=result.end_word,
        similarity=result.similarity,
        matched_text=result.matched_text,
        query_text=result.query_text
    )


# Helper function to convert MultiAyahMatch to MultiAyahMatchResponse
def multi_ayah_match_to_response(match: MultiAyahMatch) -> MultiAyahMatchResponse:
    """Convert a MultiAyahMatch object to a MultiAyahMatchResponse."""
    return MultiAyahMatchResponse(
        verses=[verse_to_response(verse) for verse in match.verses],
        similarity=match.similarity,
        matched_text=match.matched_text,
        query_text=match.query_text,
        start_surah=match.start_surah,
        start_ayah=match.start_ayah,
        start_word=match.start_word,
        end_surah=match.end_surah,
        end_ayah=match.end_ayah,
        end_word=match.end_word,
        reference=match.get_reference()
    )


@app.get(
    "/",
    summary="API Root",
    description="Welcome endpoint with basic API information",
    tags=["Info"]
)
async def root():
    """Root endpoint returning API information."""
    return {
        "message": "Quran Ayah Lookup API",
        "version": __version__,
        "docs": "/docs",
        "source": "Tanzil.net",
        "endpoints": {
            "verses": "/verses/{surah_number}/{ayah_number}",
            "surah_info": "/surahs/{surah_number}",
            "surah_verses": "/surahs/{surah_number}/verses",
            "search": "/search",
            "fuzzy_search": "/fuzzy-search",
            "sliding_window": "/sliding-window",
            "smart_search": "/smart-search",
            "vector_search": "/vector-search",
            "stats": "/stats"
        }
    }


@app.get(
    "/verses/{surah_number}/{ayah_number}",
    response_model=VerseResponse,
    summary="Get a specific verse",
    description="Get a specific verse by surah and ayah number with O(1) performance",
    tags=["Verses"],
    responses={
        200: {"description": "Verse retrieved successfully"},
        404: {"model": ErrorResponse, "description": "Verse not found"},
    }
)
async def get_verse_endpoint(
    surah_number: int,
    ayah_number: int
):
    """
    Get a specific verse by surah and ayah number.
    
    - **surah_number**: Surah number between 1 and 114
    - **ayah_number**: Ayah number (0 for Basmala, 1 or higher for regular ayahs)
    
    Returns the verse with both original (with diacritics) and normalized (without diacritics) Arabic text.
    """
    try:
        verse = get_verse(surah_number, ayah_number)
        return verse_to_response(verse)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get(
    "/surahs/{surah_number}",
    response_model=SurahInfoResponse,
    summary="Get surah information",
    description="Get information about a specific surah/chapter",
    tags=["Surahs"],
    responses={
        200: {"description": "Surah information retrieved successfully"},
        404: {"model": ErrorResponse, "description": "Surah not found"},
    }
)
async def get_surah_info_endpoint(
    surah_number: int
):
    """
    Get information about a specific surah/chapter.
    
    - **surah_number**: Surah number between 1 and 114
    
    Returns surah information including verse count and whether it has a Basmala.
    """
    try:
        surah = get_surah(surah_number)
        return SurahInfoResponse(
            surah_number=surah_number,
            verse_count=surah.get_verse_count(),
            has_basmala=surah.has_basmala()
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get(
    "/surahs/{surah_number}/verses",
    response_model=List[VerseResponse],
    summary="Get all verses in a surah",
    description="Get all verses for a specific surah",
    tags=["Surahs"],
    responses={
        200: {"description": "Verses retrieved successfully"},
        404: {"model": ErrorResponse, "description": "Surah not found"},
    }
)
async def get_surah_verses_endpoint(
    surah_number: int
):
    """
    Get all verses for a specific surah.
    
    - **surah_number**: Surah number between 1 and 114
    
    Returns a list of all verses in the surah, including the Basmala if present.
    """
    try:
        verses = get_surah_verses(surah_number)
        return [verse_to_response(verse) for verse in verses]
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get(
    "/search",
    response_model=List[VerseResponse],
    summary="Search for verses containing text",
    description="Search for verses containing the query text (exact substring matching)",
    tags=["Search"],
    responses={
        200: {"description": "Search completed successfully"},
        400: {"model": ErrorResponse, "description": "Invalid query"},
    }
)
async def search_text_endpoint(
    query: str = Query(..., min_length=1, description="Arabic text to search for"),
    normalized: bool = Query(True, description="Search in normalized text (without diacritics)"),
    limit: Optional[int] = Query(None, ge=1, description="Maximum number of results to return"),
    surah_hint: Optional[int] = Query(None, ge=1, le=114, description="Search in this surah first, expanding ±1, ±3, then full Quran"),
    start_after_surah: Optional[int] = Query(None, ge=1, le=114, description="Start search after this surah (must be paired with start_after_ayah)"),
    start_after_ayah: Optional[int] = Query(None, ge=0, description="Start search after this ayah (must be paired with start_after_surah)"),
):
    """
    Search for verses containing the query text (exact substring matching).
    
    - **query**: Arabic text to search for (required)
    - **normalized**: Whether to search in normalized text without diacritics (default: true)
    - **limit**: Maximum number of results to return (optional)
    - **surah_hint**: Search in this surah first, expanding ±1, ±3, then full Quran (optional)
    - **start_after_surah** / **start_after_ayah**: Start search after this position (optional, must be paired)

    Returns a list of verses containing the query text.
    """
    if (start_after_surah is None) != (start_after_ayah is None):
        raise HTTPException(
            status_code=400,
            detail="start_after_surah and start_after_ayah must both be provided or both omitted.",
        )
    start_after = (start_after_surah, start_after_ayah) if start_after_surah is not None else None
    try:
        results = search_text(query, normalized=normalized, surah_hint=surah_hint, start_after=start_after)
        if limit:
            results = results[:limit]
        return [verse_to_response(verse) for verse in results]
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get(
    "/fuzzy-search",
    response_model=List[FuzzySearchResultResponse],
    summary="Fuzzy search for verses",
    description="Perform fuzzy search with partial text matching and similarity scoring",
    tags=["Search"],
    responses={
        200: {"description": "Fuzzy search completed successfully"},
        400: {"model": ErrorResponse, "description": "Invalid parameters"},
    }
)
async def fuzzy_search_endpoint(
    query: str = Query(..., min_length=1, description="Arabic text to search for"),
    threshold: float = Query(0.7, ge=0.0, le=1.0, description="Minimum similarity score (0.0-1.0)"),
    normalized: bool = Query(True, description="Search in normalized text (without diacritics)"),
    limit: Optional[int] = Query(None, ge=1, description="Maximum number of results to return"),
    surah_hint: Optional[int] = Query(None, ge=1, le=114, description="Search in this surah first, expanding ±1, ±3, then full Quran"),
    start_after_surah: Optional[int] = Query(None, ge=1, le=114, description="Start search after this surah (must be paired with start_after_ayah)"),
    start_after_ayah: Optional[int] = Query(None, ge=0, description="Start search after this ayah (must be paired with start_after_surah)"),
):
    """
    Perform fuzzy search with partial text matching across all verses.
    
    - **query**: Arabic text to search for (required)
    - **threshold**: Minimum similarity score between 0.0 and 1.0 (default: 0.7)
    - **normalized**: Whether to search in normalized text without diacritics (default: true)
    - **limit**: Maximum number of results to return (optional)
    - **surah_hint**: Search in this surah first, expanding ±1, ±3, then full Quran (optional)
    - **start_after_surah** / **start_after_ayah**: Start search after this position (optional, must be paired)

    Returns a list of fuzzy search results sorted by similarity score, including:
    - The matched verse
    - Word-level position of the match
    - Similarity score
    - Matched text segment
    """
    if (start_after_surah is None) != (start_after_ayah is None):
        raise HTTPException(
            status_code=400,
            detail="start_after_surah and start_after_ayah must both be provided or both omitted.",
        )
    start_after = (start_after_surah, start_after_ayah) if start_after_surah is not None else None
    try:
        results = fuzzy_search(
            query,
            threshold=threshold,
            normalized=normalized,
            max_results=limit,
            surah_hint=surah_hint,
            start_after=start_after,
        )
        return [fuzzy_result_to_response(result) for result in results]
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get(
    "/sliding-window",
    response_model=List[MultiAyahMatchResponse],
    summary="Sliding window search across multiple ayahs",
    description="Search for text that may span multiple ayahs using vectorized fuzzy matching",
    tags=["Search"],
    responses={
        200: {"description": "Sliding window search completed successfully"},
        400: {"model": ErrorResponse, "description": "Invalid parameters"},
    }
)
async def sliding_window_search_endpoint(
    query: str = Query(..., min_length=1, description="Arabic text to search for (can span multiple ayahs)"),
    threshold: float = Query(80.0, ge=0.0, le=100.0, description="Minimum similarity score (0.0-100.0)"),
    normalized: bool = Query(True, description="Search in normalized text (without diacritics)"),
    limit: Optional[int] = Query(None, ge=1, description="Maximum number of results to return"),
    surah_hint: Optional[int] = Query(None, ge=1, le=114, description="Search in this surah first, expanding ±1, ±3, then full Quran"),
    start_after_surah: Optional[int] = Query(None, ge=1, le=114, description="Start search after this surah (must be paired with start_after_ayah)"),
    start_after_ayah: Optional[int] = Query(None, ge=0, description="Start search after this ayah (must be paired with start_after_surah)"),
):
    """
    Search for text that may span multiple ayahs using a sliding window approach.
    
    This endpoint is particularly useful for finding longer passages or quotes that cross
    ayah or even surah boundaries. It uses vectorized fuzzy matching for efficient searching.
    
    - **query**: Arabic text to search for (required, can span multiple ayahs)
    - **threshold**: Minimum similarity score between 0.0 and 100.0 (default: 80.0)
    - **normalized**: Whether to search in normalized text without diacritics (default: true)
    - **limit**: Maximum number of results to return (optional)
    - **surah_hint**: Search in this surah first, expanding ±1, ±3, then full Quran (optional)
    - **start_after_surah** / **start_after_ayah**: Start search after this position (optional, must be paired)

    Returns a list of multi-ayah matches sorted by similarity score, including:
    - All verses involved in the match
    - Exact word positions within the first and last ayah
    - Similarity score (0.0-100.0)
    - Matched text segment
    - Human-readable reference (e.g., "55:1-4" or "93:6 - 94:1")

    **Examples:**
    - Query: "الرحمن علم القران خلق الانسان علمه البيان" → Returns Surah Ar-Rahman (55:1-4)
    - Query: "بسم الله الرحمن الرحيم الم ذلك الكتاب" → Returns Surah Al-Baqarah (2:1-2)
    """
    if (start_after_surah is None) != (start_after_ayah is None):
        raise HTTPException(
            status_code=400,
            detail="start_after_surah and start_after_ayah must both be provided or both omitted.",
        )
    start_after = (start_after_surah, start_after_ayah) if start_after_surah is not None else None
    try:
        results = search_sliding_window(
            query,
            threshold=threshold,
            normalized=normalized,
            max_results=limit,
            surah_hint=surah_hint,
            start_after=start_after,
        )
        return [multi_ayah_match_to_response(match) for match in results]
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get(
    "/smart-search",
    response_model=SmartSearchResponse,
    summary="Intelligent multi-method search",
    description="Automatically tries multiple search methods to find the best results",
    tags=["Search"],
    responses={
        200: {"description": "Smart search completed successfully"},
        400: {"model": ErrorResponse, "description": "Invalid parameters"},
    }
)
async def smart_search_endpoint(
    query: str = Query(..., min_length=1, description="Arabic text to search for"),
    fuzzy_threshold: float = Query(0.7, ge=0.0, le=1.0, description="Minimum similarity score for fuzzy search (0.0-1.0)"),
    sliding_threshold: float = Query(80.0, ge=0.0, le=100.0, description="Minimum similarity score for sliding window (0.0-100.0)"),
    normalized: bool = Query(True, description="Search in normalized text (without diacritics)"),
    limit: Optional[int] = Query(None, ge=1, description="Maximum number of results to return"),
    surah_hint: Optional[int] = Query(None, ge=1, le=114, description="Search in this surah first, expanding ±1, ±3, then full Quran"),
    start_after_surah: Optional[int] = Query(None, ge=1, le=114, description="Start search after this surah (must be paired with start_after_ayah)"),
    start_after_ayah: Optional[int] = Query(None, ge=0, description="Start search after this ayah (must be paired with start_after_surah)"),
):
    """
    Intelligent search that automatically tries multiple search methods.
    
    This endpoint cascades through different search methods in order of precision:
    1. **Exact text search** (fastest, most precise) - Returns `QuranVerse` objects
    2. **Fuzzy search** (moderate speed, handles variations) - Returns `FuzzySearchResult` objects
    3. **Sliding window search** (slower, handles multi-ayah matches) - Returns `MultiAyahMatch` objects
    
    The first method that returns results will be used, making this the most convenient
    endpoint for general search queries.
    
    - **query**: Arabic text to search for (required)
    - **fuzzy_threshold**: Minimum similarity score for fuzzy search (0.0-1.0, default: 0.7)
    - **sliding_threshold**: Minimum similarity score for sliding window (0.0-100.0, default: 80.0)
    - **normalized**: Whether to search in normalized text without diacritics (default: true)
    - **limit**: Maximum number of results to return (optional)
    - **surah_hint**: Search in this surah first, expanding ±1, ±3, then full Quran (optional)
    - **start_after_surah** / **start_after_ayah**: Start search after this position (optional, must be paired)

    Returns a response indicating which method was used and the results:
    - `method`: The search method that succeeded ('exact', 'fuzzy', 'sliding_window', or 'none')
    - `count`: Number of results found
    - Results in the appropriate field based on the method used

    **Examples:**
    - Query: "الرحمن الرحيم" → Likely uses exact search (appears many times)
    - Query: "الرحمن علم القران" → May use fuzzy or sliding window search
    - Query: "الرحمن علم القران خلق الانسان" → Likely uses sliding window search
    """
    if (start_after_surah is None) != (start_after_ayah is None):
        raise HTTPException(
            status_code=400,
            detail="start_after_surah and start_after_ayah must both be provided or both omitted.",
        )
    start_after = (start_after_surah, start_after_ayah) if start_after_surah is not None else None
    try:
        result = smart_search(
            query,
            threshold=fuzzy_threshold,
            sliding_threshold=sliding_threshold,
            normalized=normalized,
            max_results=limit,
            surah_hint=surah_hint,
            start_after=start_after,
        )

        response = SmartSearchResponse(
            method=result['method'],
            count=result['count'],
            exact_results=None,
            fuzzy_results=None,
            sliding_window_results=None
        )

        if result['method'] == 'exact':
            response.exact_results = [verse_to_response(verse) for verse in result['results']]
        elif result['method'] == 'fuzzy':
            response.fuzzy_results = [fuzzy_result_to_response(r) for r in result['results']]
        elif result['method'] == 'sliding_window':
            response.sliding_window_results = [multi_ayah_match_to_response(m) for m in result['results']]

        return response
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get(
    "/vector-search",
    response_model=MultiAyahMatchResponse,
    summary="Semantic vector search",
    description=(
        "Search for ayahs using meaning-aware semantic similarity via "
        "sentence-transformers and FAISS. Supports partial ayah matching, "
        "surah-scoped expanding-window search, and positional gravity."
    ),
    tags=["Search"],
    responses={
        200: {"description": "Vector search completed successfully"},
        400: {"model": ErrorResponse, "description": "Invalid parameters"},
        503: {"model": ErrorResponse, "description": "Vector search extras not installed or index not built"},
    },
)
async def vector_search_endpoint(
    query: str = Query(..., min_length=1, description="Arabic text to search for"),
    normalize: bool = Query(
        False,
        description="Normalise diacritics in the query before encoding (default: false)",
    ),
    threshold: float = Query(
        0.7, ge=0.0, le=1.0, description="Minimum cosine similarity (0.0-1.0)"
    ),
    surah_hint: Optional[int] = Query(
        None, ge=1, le=114,
        description="Search within this surah first, expanding outward if needed",
    ),
    start_after_surah: Optional[int] = Query(
        None, ge=1, le=114,
        description="Gravity anchor: surah number (must be paired with start_after_ayah)",
    ),
    start_after_ayah: Optional[int] = Query(
        None, ge=0,
        description="Gravity anchor: ayah number (must be paired with start_after_surah)",
    ),
    asymmetric: bool = Query(
        True,
        description=(
            "Search mode: true (default) = asymmetric e5-base + BM25 + RRF; "
            "false = symmetric MiniLM, FAISS only."
        ),
    ),
    semantic_only: bool = Query(
        False,
        description=(
            "Skip BM25 and use pure FAISS cosine ranking (asymmetric mode only). "
            "Default false."
        ),
    ),
):
    """
    Semantic vector search over the Quran corpus.

    Finds the most semantically similar ayah(s) to the query.  For **partial
    ayah** matches (where the query covers only part of an ayah), the response
    includes ``start_word`` and ``end_word`` to indicate the matched word range
    within the verse.

    Requires the ``[vector]`` optional extras and a pre-built FAISS index::

        pip install "quran-ayah-lookup[vector]"
        python scripts/build_vector_index.py

    **Parameters:**

    - **query**: Arabic text to search for.
    - **normalize**: Strip diacritics from the query before encoding (default: ``false``).
    - **threshold**: Minimum cosine similarity 0.0–1.0 (default: ``0.7``).
    - **surah_hint**: If set, the search starts within this surah and expands ±1, ±2, …
      until a confident result is found.
    - **start_after_surah** / **start_after_ayah**: Together they define a gravity anchor.
      Results appearing after this position receive a 15 % ranking boost.

    **Examples:**

    - ``/vector-search?query=الله لا إله إلا هو الحي القيوم&surah_hint=2``
      → returns 2:255 with ``start_word=0``, ``end_word=10`` (partial ayah).
    - ``/vector-search?query=الرحمن علم القران خلق الانسان&surah_hint=55``
      → returns a multi-ayah match across Surah 55.
    """
    if not _VECTOR_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail=(
                "Vector search is not available. "
                'Install the optional extras with: pip install "quran-ayah-lookup[vector]" '
                "and build the index with: python scripts/build_vector_index.py"
            ),
        )

    # Validate that start_after_surah and start_after_ayah are paired
    if (start_after_surah is None) != (start_after_ayah is None):
        raise HTTPException(
            status_code=400,
            detail="start_after_surah and start_after_ayah must both be provided or both omitted.",
        )
    start_after = (
        (start_after_surah, start_after_ayah)
        if start_after_surah is not None
        else None
    )

    try:
        vs = _get_vs()
        match = vs.vector_search(
            query,
            normalize=normalize,
            threshold=threshold,
            surah_hint=surah_hint,
            start_after=start_after,
            asymmetric=asymmetric,
            semantic_only=semantic_only,
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    return multi_ayah_match_to_response(match)


@app.get(
    "/stats",
    response_model=DatabaseStatsResponse,
    summary="Get database statistics",
    description="Get statistics about the Quran database",
    tags=["Info"]
)
async def get_stats_endpoint():
    """
    Get statistics about the Quran database.
    
    Returns information including:
    - Total number of surahs
    - Total number of verses
    - Source of the Quran text
    - Package version
    """
    db = get_quran_database()
    return DatabaseStatsResponse(
        total_surahs=len(db.surahs),
        total_verses=db.total_verses,
        source="Tanzil.net",
        version=__version__
    )


# Health check endpoint
@app.get(
    "/health",
    summary="Health check",
    description="Check if the API is running",
    tags=["Info"]
)
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": __version__}


# Custom exception handler
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Custom exception handler for HTTPException."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )


# Main function for running the API server
def run_server(host: str = "127.0.0.1", port: int = 8000, reload: bool = False):
    """
    Run the API server using uvicorn.
    
    Args:
        host: Host to bind to (default: 127.0.0.1)
        port: Port to bind to (default: 8000)
        reload: Enable auto-reload (default: False)
    """
    import uvicorn
    uvicorn.run(
        "quran_ayah_lookup.api:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info"
    )


if __name__ == "__main__":
    run_server()
