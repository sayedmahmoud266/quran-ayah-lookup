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
    get_surah_verses,
    get_quran_database,
    QuranVerse,
    FuzzySearchResult,
    __version__,
)


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


class DatabaseStatsResponse(BaseModel):
    """Response model for database statistics."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "total_surahs": 114,
                "total_verses": 6348,
                "source": "Tanzil.net",
                "version": "0.0.1"
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
    limit: Optional[int] = Query(None, ge=1, description="Maximum number of results to return")
):
    """
    Search for verses containing the query text (exact substring matching).
    
    - **query**: Arabic text to search for (required)
    - **normalized**: Whether to search in normalized text without diacritics (default: true)
    - **limit**: Maximum number of results to return (optional)
    
    Returns a list of verses containing the query text.
    """
    try:
        results = search_text(query, normalized=normalized)
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
    limit: Optional[int] = Query(None, ge=1, description="Maximum number of results to return")
):
    """
    Perform fuzzy search with partial text matching across all verses.
    
    - **query**: Arabic text to search for (required)
    - **threshold**: Minimum similarity score between 0.0 and 1.0 (default: 0.7)
    - **normalized**: Whether to search in normalized text without diacritics (default: true)
    - **limit**: Maximum number of results to return (optional)
    
    Returns a list of fuzzy search results sorted by similarity score, including:
    - The matched verse
    - Word-level position of the match
    - Similarity score
    - Matched text segment
    """
    try:
        results = fuzzy_search(
            query,
            threshold=threshold,
            normalized=normalized,
            max_results=limit
        )
        return [fuzzy_result_to_response(result) for result in results]
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


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
