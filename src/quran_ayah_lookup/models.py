"""
Data models for Quran verses and related structures.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional


@dataclass
class QuranVerse:
    """
    Represents a single verse from the Quran.
    
    Attributes:
        surah_number (int): The surah number (1-114)
        ayah_number (int): The ayah number within the surah (0 for Basmala, 1+ for regular ayahs)
        text (str): The original Arabic text with all diacritics
        text_normalized (str): The normalized Arabic text without diacritics
        is_basmalah (bool): True if this is a Basmala verse (ayah_number = 0)
    """
    surah_number: int
    ayah_number: int
    text: str
    text_normalized: str
    is_basmalah: bool = False
    
    def __str__(self) -> str:
        verse_type = "Basmala" if self.is_basmalah else "Ayah"
        return f"{verse_type} {self.surah_number}:{self.ayah_number} - {self.text[:50]}..."
    
    def __repr__(self) -> str:
        return (f"QuranVerse(surah={self.surah_number}, ayah={self.ayah_number}, "
                f"text='{self.text[:30]}...', is_basmalah={self.is_basmalah})")
    
    def to_dict(self) -> dict:
        """Convert QuranVerse to dictionary for JSON serialization."""
        return {
            'surah_number': self.surah_number,
            'ayah_number': self.ayah_number,
            'text': self.text,
            'text_normalized': self.text_normalized,
            'is_basmalah': self.is_basmalah
        }


@dataclass
class FuzzySearchResult:
    """
    Represents a fuzzy search result with partial match information.
    
    Attributes:
        verse (QuranVerse): The matched verse
        start_word (int): Starting word index of the match (0-based)
        end_word (int): Ending word index of the match (exclusive)
        similarity (float): Similarity score (0.0-1.0)
        matched_text (str): The actual text segment that was matched
        query_text (str): The original query text used for matching
    """
    verse: 'QuranVerse'
    start_word: int
    end_word: int
    similarity: float
    matched_text: str
    query_text: str
    
    def __str__(self) -> str:
        verse_type = "Basmala" if self.verse.is_basmalah else "Ayah"
        return (f"{verse_type} {self.verse.surah_number}:{self.verse.ayah_number} "
                f"(similarity: {self.similarity:.3f}, words: {self.start_word}-{self.end_word}) - "
                f"{self.matched_text[:50]}...")
    
    def __repr__(self) -> str:
        return (f"FuzzySearchResult(verse={self.verse.surah_number}:{self.verse.ayah_number}, "
                f"similarity={self.similarity:.3f}, words={self.start_word}-{self.end_word})")
    
    def to_dict(self) -> dict:
        """Convert FuzzySearchResult to dictionary for JSON serialization."""
        return {
            'verse': self.verse.to_dict(),
            'start_word': self.start_word,
            'end_word': self.end_word,
            'similarity': self.similarity,
            'matched_text': self.matched_text,
            'query_text': self.query_text
        }


@dataclass
class MultiAyahMatch:
    """
    Represents a match that may span multiple ayahs using sliding window search.
    
    Attributes:
        verses (List[QuranVerse]): List of verses in the match (ordered)
        similarity (float): Similarity score (0.0-100.0)
        matched_text (str): The actual text segment that was matched
        query_text (str): The original query text used for matching
        start_surah (int): Starting surah number
        start_ayah (int): Starting ayah number
        start_word (int): Starting word index within the first ayah (0-based)
        end_surah (int): Ending surah number
        end_ayah (int): Ending ayah number
        end_word (int): Ending word index within the last ayah (exclusive)
    """
    verses: List['QuranVerse']
    similarity: float
    matched_text: str
    query_text: str
    start_surah: int
    start_ayah: int
    start_word: int
    end_surah: int
    end_ayah: int
    end_word: int
    
    def __str__(self) -> str:
        if len(self.verses) == 1:
            return (f"Surah {self.start_surah}:{self.start_ayah} "
                   f"(similarity: {self.similarity:.1f}, words: {self.start_word}-{self.end_word}) - "
                   f"{self.matched_text[:60]}...")
        else:
            return (f"Surah {self.start_surah}:{self.start_ayah} to {self.end_surah}:{self.end_ayah} "
                   f"(similarity: {self.similarity:.1f}, {len(self.verses)} ayahs) - "
                   f"{self.matched_text[:60]}...")
    
    def __repr__(self) -> str:
        return (f"MultiAyahMatch(start={self.start_surah}:{self.start_ayah}, "
                f"end={self.end_surah}:{self.end_ayah}, similarity={self.similarity:.1f})")
    
    def get_reference(self) -> str:
        """Get a human-readable reference string for this match."""
        if self.start_surah == self.end_surah and self.start_ayah == self.end_ayah:
            return f"{self.start_surah}:{self.start_ayah}"
        elif self.start_surah == self.end_surah:
            return f"{self.start_surah}:{self.start_ayah}-{self.end_ayah}"
        else:
            return f"{self.start_surah}:{self.start_ayah} - {self.end_surah}:{self.end_ayah}"
    
    def to_dict(self) -> dict:
        """Convert MultiAyahMatch to dictionary for JSON serialization."""
        return {
            'verses': [verse.to_dict() for verse in self.verses],
            'similarity': self.similarity,
            'matched_text': self.matched_text,
            'query_text': self.query_text,
            'start_surah': self.start_surah,
            'start_ayah': self.start_ayah,
            'start_word': self.start_word,
            'end_surah': self.end_surah,
            'end_ayah': self.end_ayah,
            'end_word': self.end_word,
            'reference': self.get_reference()
        }


@dataclass
class QuranChapter:
    """
    Represents a Quran chapter (surah) with O(1) verse lookup.
    
    Attributes:
        number (int): The surah number (1-114)
        ayahs (Dict[int, QuranVerse]): Dictionary mapping ayah number to verse for O(1) lookup
    """
    number: int
    ayahs: Dict[int, QuranVerse] = field(default_factory=dict)
    
    def add_verse(self, verse: QuranVerse) -> None:
        """Add a verse to this chapter."""
        if verse.surah_number != self.number:
            raise ValueError(f"Verse surah number {verse.surah_number} doesn't match chapter number {self.number}")
        self.ayahs[verse.ayah_number] = verse
    
    def get_verse(self, ayah_number: int) -> QuranVerse:
        """Get a specific verse by ayah number (O(1) operation)."""
        if ayah_number not in self.ayahs:
            raise ValueError(f"Ayah {ayah_number} not found in surah {self.number}")
        return self.ayahs[ayah_number]
    
    def get_all_verses(self) -> List[QuranVerse]:
        """Get all verses in this chapter as a list, ordered by ayah number."""
        return [self.ayahs[ayah_num] for ayah_num in sorted(self.ayahs.keys())]
    
    def get_verse_count(self, include_basmalah: bool = False) -> int:
        """
        Get the total number of verses in this chapter.
        
        Args:
            include_basmalah: Whether to include Basmala in the count (default: False)
        
        Returns:
            Total number of verses
        """
        total = len(self.ayahs)
        if not include_basmalah and self.has_basmala():
            total -= 1
        return total
    
    def has_basmala(self) -> bool:
        """Check if this chapter has a Basmala (ayah 0)."""
        return 0 in self.ayahs and self.ayahs[0].is_basmalah
    
    def __len__(self) -> int:
        return self.get_verse_count(include_basmalah=False)
    
    def __contains__(self, ayah_number: int) -> bool:
        return ayah_number in self.ayahs
    
    def __getitem__(self, ayah_number: int) -> QuranVerse:
        return self.get_verse(ayah_number)
    
    def __str__(self) -> str:
        return f"Surah {self.number} ({len(self.ayahs)} verses)"
    
    def __repr__(self) -> str:
        return f"QuranChapter(number={self.number}, verse_count={len(self.ayahs)})"
    
    def to_dict(self, include_verses: bool = True) -> dict:
        """
        Convert QuranChapter to dictionary for JSON serialization.
        
        Args:
            include_verses: Whether to include full verse data (default: True).
                           Set to False for a lighter representation.
        
        Returns:
            Dictionary representation of the chapter
        """
        result = {
            'number': self.number,
            'verse_count': len(self.ayahs),
            'has_basmala': self.has_basmala()
        }
        
        if include_verses:
            result['verses'] = [verse.to_dict() for verse in self.get_all_verses()]
        else:
            result['ayah_numbers'] = sorted(self.ayahs.keys())
        
        return result


@dataclass
class QuranDatabase:
    """
    Contains all Quran chapters and provides efficient O(1) lookup functionality.
    
    Attributes:
        surahs (Dict[int, QuranChapter]): Dictionary mapping surah number to chapter for O(1) lookup
        total_verses (int): Total number of verses (including Basmalas)
        total_verses_without_basmalah (int): Total number of verses excluding Basmalas
        total_surahs (int): Total number of surahs (114)
        sorted_surahs_ref_list (List[int]): Pre-sorted list of surah numbers for performance
        sorted_ayahs_ref_list (List[tuple]): Pre-sorted list of (surah_num, ayah_num) tuples for absolute indexing
        corpus_combined_text (str): Complete Quran text (with diacritics) as one string
        corpus_combined_text_normalized (str): Complete Quran text (normalized) as one string
        corpus_words_list (List[str]): All words from the Quran (with diacritics) in order
        corpus_words_list_normalized (List[str]): All words from the Quran (normalized) in order
    """
    surahs: Dict[int, QuranChapter] = field(default_factory=dict)
    total_verses: int = 0
    total_verses_without_basmalah: int = 0
    total_surahs: int = 114
    sorted_surahs_ref_list: List[int] = field(default_factory=list)
    sorted_ayahs_ref_list: List[tuple] = field(default_factory=list)
    corpus_combined_text: str = ""
    corpus_combined_text_normalized: str = ""
    corpus_words_list: List[str] = field(default_factory=list)
    corpus_words_list_normalized: List[str] = field(default_factory=list)
    _cache_enabled: bool = False
    
    def add_verse(self, verse: QuranVerse) -> None:
        """Add a verse to the database, creating chapter if needed."""
        if verse.surah_number not in self.surahs:
            self.surahs[verse.surah_number] = QuranChapter(number=verse.surah_number)
        
        self.surahs[verse.surah_number].add_verse(verse)
        self.total_verses += 1
        
        # Count verses without basmalah
        if not verse.is_basmalah:
            self.total_verses_without_basmalah += 1
    
    def finalize_cache(self) -> None:
        """
        Finalize the database by building cache structures for performance.
        Should be called after all verses are added.
        """
        # Build sorted surahs reference list
        self.sorted_surahs_ref_list = sorted(self.surahs.keys())
        
        # Build sorted ayahs reference list
        self.sorted_ayahs_ref_list = []
        for surah_num in self.sorted_surahs_ref_list:
            for ayah_num in sorted(self.surahs[surah_num].ayahs.keys()):
                self.sorted_ayahs_ref_list.append((surah_num, ayah_num))
        
        # Build combined corpus text
        text_parts = []
        text_normalized_parts = []
        words = []
        words_normalized = []
        
        for surah_num in self.sorted_surahs_ref_list:
            surah = self.surahs[surah_num]
            for ayah_num in sorted(surah.ayahs.keys()):
                verse = surah.ayahs[ayah_num]
                text_parts.append(verse.text)
                text_normalized_parts.append(verse.text_normalized)
                
                # Split into words
                words.extend(verse.text.split())
                words_normalized.extend(verse.text_normalized.split())
        
        self.corpus_combined_text = " ".join(text_parts)
        self.corpus_combined_text_normalized = " ".join(text_normalized_parts)
        self.corpus_words_list = words
        self.corpus_words_list_normalized = words_normalized
        
        self._cache_enabled = True
    
    def get_verse(self, surah_number: int, ayah_number: int) -> QuranVerse:
        """Get a specific verse by surah and ayah number (O(1) operation)."""
        if surah_number not in self.surahs:
            raise ValueError(f"Surah {surah_number} not found")
        return self.surahs[surah_number].get_verse(ayah_number)
    
    def get_surah(self, surah_number: int) -> QuranChapter:
        """Get a specific surah/chapter (O(1) operation)."""
        if surah_number not in self.surahs:
            raise ValueError(f"Surah {surah_number} not found")
        return self.surahs[surah_number]
    
    def get_surah_verses(self, surah_number: int) -> List[QuranVerse]:
        """Get all verses for a specific surah."""
        return self.get_surah(surah_number).get_all_verses()
    
    def get_all_verses(self) -> List[QuranVerse]:
        """Get all verses in the database as a list, ordered by surah and ayah number."""
        if self._cache_enabled and self.sorted_ayahs_ref_list:
            # Use cached sorted list for better performance
            return [self.get_verse(surah_num, ayah_num) 
                    for surah_num, ayah_num in self.sorted_ayahs_ref_list]
        else:
            # Fall back to sorting on-demand
            all_verses = []
            for surah_num in sorted(self.surahs.keys()):
                all_verses.extend(self.surahs[surah_num].get_all_verses())
            return all_verses
    
    def get_partial_verses(self, start_ayah: tuple, end_ayah: tuple) -> List[QuranVerse]:
        """
        Get a range of verses from start_ayah to end_ayah (inclusive).
        
        Args:
            start_ayah: Tuple of (surah_number, ayah_number) for the starting verse
            end_ayah: Tuple of (surah_number, ayah_number) for the ending verse
        
        Returns:
            List of QuranVerse objects in the specified range, ordered by surah and ayah number
        
        Raises:
            ValueError: If the tuples are invalid or the range is invalid
        
        Examples:
            >>> db = get_quran_database()
            >>> # Get verses from Al-Fatihah 1:1 to 1:3
            >>> verses = db.get_partial_verses((1, 1), (1, 3))
            >>> # Get verses spanning multiple surahs
            >>> verses = db.get_partial_verses((1, 7), (2, 2))
        """
        # Validate input tuples
        if not isinstance(start_ayah, tuple) or len(start_ayah) != 2:
            raise ValueError("start_ayah must be a tuple of (surah_number, ayah_number)")
        if not isinstance(end_ayah, tuple) or len(end_ayah) != 2:
            raise ValueError("end_ayah must be a tuple of (surah_number, ayah_number)")
        
        start_surah, start_ayah_num = start_ayah
        end_surah, end_ayah_num = end_ayah
        
        # Validate surah numbers
        if start_surah not in self.surahs:
            raise ValueError(f"Start surah {start_surah} not found")
        if end_surah not in self.surahs:
            raise ValueError(f"End surah {end_surah} not found")
        
        # Validate ayah numbers
        if start_ayah_num not in self.surahs[start_surah]:
            raise ValueError(f"Start ayah {start_ayah_num} not found in surah {start_surah}")
        if end_ayah_num not in self.surahs[end_surah]:
            raise ValueError(f"End ayah {end_ayah_num} not found in surah {end_surah}")
        
        # Validate range (start must come before or equal to end)
        if (start_surah > end_surah) or (start_surah == end_surah and start_ayah_num > end_ayah_num):
            raise ValueError(f"Invalid range: start ({start_surah}:{start_ayah_num}) comes after end ({end_surah}:{end_ayah_num})")
        
        # Build list of verses in the range
        result_verses = []
        
        if start_surah == end_surah:
            # Simple case: same surah
            surah = self.surahs[start_surah]
            for ayah_num in sorted(surah.ayahs.keys()):
                if start_ayah_num <= ayah_num <= end_ayah_num:
                    result_verses.append(surah.ayahs[ayah_num])
        else:
            # Complex case: spanning multiple surahs
            # First surah: from start_ayah_num to end of surah
            start_surah_obj = self.surahs[start_surah]
            for ayah_num in sorted(start_surah_obj.ayahs.keys()):
                if ayah_num >= start_ayah_num:
                    result_verses.append(start_surah_obj.ayahs[ayah_num])
            
            # Middle surahs: all verses
            for surah_num in range(start_surah + 1, end_surah):
                if surah_num in self.surahs:
                    result_verses.extend(self.surahs[surah_num].get_all_verses())
            
            # Last surah: from beginning to end_ayah_num
            end_surah_obj = self.surahs[end_surah]
            for ayah_num in sorted(end_surah_obj.ayahs.keys()):
                if ayah_num <= end_ayah_num:
                    result_verses.append(end_surah_obj.ayahs[ayah_num])
        
        return result_verses
    
    def search_text(self, query: str, normalized: bool = True) -> List[QuranVerse]:
        """
        Search for verses containing the query text.
        
        Args:
            query: Text to search for
            normalized: Whether to search in normalized text (default: True)
        
        Returns:
            List of matching verses
        """
        results = []
        for surah in self.surahs.values():
            for verse in surah.get_all_verses():
                search_text = verse.text_normalized if normalized else verse.text
                if query in search_text:
                    results.append(verse)
        return results
    
    def fuzzy_search(self, query: str, threshold: float = 0.7, normalized: bool = True, 
                    max_results: Optional[int] = None) -> List['FuzzySearchResult']:
        """
        Perform fuzzy search with partial text matching across all verses.
        
        Args:
            query: Text to search for
            threshold: Minimum similarity score (0.0-1.0)
            normalized: Whether to search in normalized text (default: True)
            max_results: Maximum number of results to return (None for no limit)
        
        Returns:
            List of FuzzySearchResult objects sorted by similarity score
        """
        from .text_utils import fuzzy_search_text
        
        all_verses = self.get_all_verses()
        return fuzzy_search_text(query, all_verses, threshold, normalized, max_results)
    
    def get_surah_count(self) -> int:
        """Get the total number of surahs in the database."""
        return len(self.surahs)
    
    def get_verse_count(self, include_basmalah: bool = False) -> int:
        """
        Get the total number of verses in the database.
        
        Args:
            include_basmalah: Whether to include Basmalas in the count (default: False)
        
        Returns:
            Total number of verses
        """
        return self.total_verses if include_basmalah else self.total_verses_without_basmalah
    
    def __len__(self) -> int:
        return self.get_verse_count(include_basmalah=False)
    
    def __contains__(self, surah_number: int) -> bool:
        return surah_number in self.surahs
    
    def __getitem__(self, surah_number: int) -> QuranChapter:
        return self.get_surah(surah_number)
    
    def __str__(self) -> str:
        return f"Quran Database ({self.total_surahs} surahs, {self.total_verses} verses)"
    
    def __repr__(self) -> str:
        return f"QuranDatabase(surahs={self.get_surah_count()}, verses={self.total_verses})"

    @property
    def verses(self) -> List[QuranVerse]:
        """Backward compatibility property to get all verses as a list."""
        return self.get_all_verses()
    
    def to_dict(self, include_verses: bool = False, include_surahs: bool = True) -> dict:
        """
        Convert QuranDatabase to dictionary for JSON serialization.
        
        Args:
            include_verses: Whether to include full verse data for all surahs (default: False).
                           Warning: This creates a very large dictionary.
            include_surahs: Whether to include surah data (default: True).
                           Set to False for a minimal representation with just statistics.
        
        Returns:
            Dictionary representation of the database
        """
        result = {
            'total_surahs': self.total_surahs,
            'total_verses': self.total_verses,
            'total_verses_without_basmalah': self.total_verses_without_basmalah,
            'cache_enabled': self._cache_enabled
        }
        
        if include_surahs:
            result['surahs'] = {
                surah_num: surah.to_dict(include_verses=include_verses)
                for surah_num, surah in sorted(self.surahs.items())
            }
        else:
            result['surah_numbers'] = self.sorted_surahs_ref_list
        
        return result