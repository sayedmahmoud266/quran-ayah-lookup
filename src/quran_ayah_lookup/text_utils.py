"""
Text processing utilities for Arabic Quran text normalization.
"""
import re


# Arabic diacritics and special signs to be removed
ARABIC_DIACRITICS = [
    # Basic diacritics (tashkeel)
    '\u064B',  # FATHATAN (ً)
    '\u064C',  # DAMMATAN (ٌ)
    '\u064D',  # KASRATAN (ٍ)
    '\u064E',  # FATHA (َ)
    '\u064F',  # DAMMA (ُ)
    '\u0650',  # KASRA (ِ)
    '\u0651',  # SHADDA (ّ)
    '\u0652',  # SUKUN (ْ)
    
    # Maddah and other signs
    '\u0653',  # MADDAH ABOVE (ٓ)
    '\u0654',  # HAMZA ABOVE (ٔ)
    '\u0655',  # HAMZA BELOW (ٕ)
    '\u0656',  # SUBSCRIPT ALEF (ٖ)
    '\u0657',  # INVERTED DAMMA (ٗ)
    '\u0658',  # MARK NOON GHUNNA (٘)
    '\u0659',  # ZWARAKAY (ٙ)
    '\u065A',  # VOWEL SIGN SMALL V ABOVE (ٚ)
    '\u065B',  # VOWEL SIGN INVERTED SMALL V ABOVE (ٛ)
    '\u065C',  # VOWEL SIGN DOT BELOW (ٜ)
    '\u065D',  # REVERSED DAMMA (ٝ)
    '\u065E',  # FATHA WITH TWO DOTS (ٞ)
    '\u065F',  # WAVY HAMZA BELOW (ٟ)
    
    # Extended Arabic diacritics
    '\u0670',  # SUPERSCRIPT ALEF (ٰ)
    '\u06D6',  # SMALL HIGH LIGATURE SAD WITH LAM WITH ALEF MAKSURA (ۖ)
    '\u06D7',  # SMALL HIGH LIGATURE QAF WITH LAM WITH ALEF MAKSURA (ۗ)
    '\u06D8',  # SMALL HIGH MEEM INITIAL FORM (ۘ)
    '\u06D9',  # SMALL HIGH LAM ALEF (ۙ)
    '\u06DA',  # SMALL HIGH JEEM (ۚ)
    '\u06DB',  # SMALL HIGH THREE DOTS (ۛ)
    '\u06DC',  # SMALL HIGH SEEN (ۜ)
    '\u06DF',  # SMALL HIGH ROUNDED ZERO (۟)
    '\u06E0',  # SMALL HIGH UPRIGHT RECTANGULAR ZERO (۠)
    '\u06E1',  # SMALL HIGH DOTLESS HEAD OF KHAH (ۡ)
    '\u06E2',  # SMALL HIGH MEEM ISOLATED FORM (ۢ)
    '\u06E3',  # SMALL LOW SEEN (ۣ)
    '\u06E4',  # SMALL HIGH MADDA (ۤ)
    '\u06E5',  # SMALL WAW (ۥ)
    '\u06E6',  # SMALL YEH (ۦ)
    '\u06E7',  # SMALL HIGH YEH (ۧ)
    '\u06E8',  # SMALL HIGH NOON (ۨ)
    '\u06E9',  # PLACE OF SAJDAH (۩)
    '\u06EA',  # EMPTY CENTRE LOW STOP (۪)
    '\u06EB',  # EMPTY CENTRE HIGH STOP (۫)
    '\u06EC',  # ROUNDED HIGH STOP WITH FILLED CENTRE (۬)
    '\u06ED',  # SMALL LOW MEEM (ۭ)
    
    # Quranic annotation signs
    '\u06E9',  # PLACE OF SAJDAH (۩)
    '\u08F0',  # OPEN FATHATAN (ࣰ)
    '\u08F1',  # OPEN DAMMATAN (ࣱ)
    '\u08F2',  # OPEN KASRATAN (ࣲ)
    '\u08F3',  # SMALL HIGH WAW (ࣳ)
    '\u08F4',  # FATHA WITH RING (ࣴ)
    '\u08F5',  # FATHA WITH DOT ABOVE (ࣵ)
    '\u08F6',  # KASRA WITH DOT BELOW (ࣶ)
    '\u08F7',  # LEFT ARROWHEAD ABOVE (ࣷ)
    '\u08F8',  # RIGHT ARROWHEAD ABOVE (ࣸ)
    '\u08F9',  # LEFT ARROWHEAD BELOW (ࣹ)
    '\u08FA',  # RIGHT ARROWHEAD BELOW (ࣺ)
    '\u08FB',  # DOUBLE RIGHT ARROWHEAD ABOVE (ࣻ)
    '\u08FC',  # DOUBLE RIGHT ARROWHEAD ABOVE WITH DOT (ࣼ)
    '\u08FD',  # RIGHT ARROWHEAD ABOVE WITH DOT (ࣽ)
    '\u08FE',  # DAMMA WITH DOT (ࣾ)
    '\u08FF',  # MARK SIDEWAYS NOON GHUNNA (ࣿ)
]

# Quarter hizb and other special marks
QURAN_SPECIAL_MARKS = [
    '\u06DE',  # START OF RUB EL HIZB (۞)
    '\u060C',  # ARABIC COMMA (،)
    '\u061B',  # ARABIC SEMICOLON (؛)
    '\u061F',  # ARABIC QUESTION MARK (؟)
    '\u0640',  # ARABIC TATWEEL (ـ)
]

# Combine all characters to remove
ALL_DIACRITICS_AND_MARKS = ARABIC_DIACRITICS + QURAN_SPECIAL_MARKS


def normalize_arabic_text(text: str) -> str:
    """
    Normalize Arabic text by removing all diacritics, tashkeel, madd, 
    tajweed signs, sajdah signs, and quarter_hizb signs, and normalize
    Alif wasla to regular Alif.
    
    Args:
        text (str): Original Arabic text with diacritics
        
    Returns:
        str: Normalized Arabic text without diacritics
    """
    if not text:
        return text
    
    # Remove all diacritics and special marks
    normalized = text
    for mark in ALL_DIACRITICS_AND_MARKS:
        normalized = normalized.replace(mark, '')
    
    # Remove any remaining diacritics using Unicode categories
    # This catches any diacritics we might have missed
    normalized = re.sub(r'[\u064B-\u065F\u0670\u06D6-\u06ED\u08F0-\u08FF]', '', normalized)
    
    # Normalize Alif wasla (ٱ) to regular Alif (ا)
    normalized = normalized.replace('\u0671', '\u0627')  # ٱ → ا
    
    # Clean up extra whitespace
    normalized = ' '.join(normalized.split())
    
    return normalized


_BASMALA_CACHE = None

def extract_basmala() -> str:
    """
    Return the standard Basmala text as it appears in Al-Fatihah.
    
    Returns:
        str: The exact Basmala from the Quran text file
    """
    global _BASMALA_CACHE
    
    if _BASMALA_CACHE is None:
        # Load the exact Basmala from Al-Fatihah 1:1 in our data file
        # This ensures the diacritics match exactly with the file content
        import os
        from pathlib import Path
        
        # Get path to the data file
        current_dir = Path(__file__).parent
        data_file = current_dir / "resources" / "quran-uthmani_all.txt"
        
        try:
            with open(data_file, 'r', encoding='utf-8') as f:
                first_line = f.readline().strip()
                parts = first_line.split('|')
                if len(parts) == 3 and parts[0] == '1' and parts[1] == '1':
                    _BASMALA_CACHE = parts[2]  # Al-Fatihah 1:1 text
                else:
                    # Fallback if file format is unexpected
                    _BASMALA_CACHE = "بِسْمِ ٱللَّهِ ٱلرَّحْمَـٰنِ ٱلرَّحِيمِ"
        except FileNotFoundError:
            # Fallback if file not found
            _BASMALA_CACHE = "بِسْمِ ٱللَّهِ ٱلرَّحْمَـٰنِ ٱلرَّحِيمِ"
    
    return _BASMALA_CACHE


def is_basmala_present(text: str) -> bool:
    """
    Check if text starts with Basmala using normalized text comparison.
    This is more reliable than exact Unicode matching.
    
    Args:
        text (str): Arabic text to check
        
    Returns:
        bool: True if text starts with Basmala
    """
    # Normalize both the input text and the expected Basmala
    normalized_text = normalize_arabic_text(text.strip())
    normalized_basmala = get_normalized_basmala()
    
    return normalized_text.startswith(normalized_basmala)


def remove_basmala_from_text(text: str) -> str:
    """
    Remove Basmala from the beginning of text if present using normalized matching.
    
    Args:
        text (str): Arabic text that may start with Basmala
        
    Returns:
        str: Text with Basmala removed, or original text if no Basmala
    """
    text = text.strip()
    if not is_basmala_present(text):
        return text
    
    # Use the original Basmala from the file as reference
    original_basmala = extract_basmala()
    
    # Simple approach: if the text starts with the exact Basmala, remove it
    if text.startswith(original_basmala):
        return text[len(original_basmala):].strip()
    
    # Fallback: if normalized matching found Basmala but exact match fails,
    # try to find where the Basmala ends by looking for common patterns
    # The normalized Basmala should be: "بسم ٱلله ٱلرحمن ٱلرحيم"
    words = text.split()
    if len(words) >= 4:
        # Try to identify the 4 main words of Basmala and remove them
        normalized_words = [normalize_arabic_text(word) for word in words[:4]]
        expected = get_normalized_basmala().split()
        
        if len(normalized_words) >= len(expected):
            # Check if first N words match Basmala pattern
            match_count = 0
            for i, exp_word in enumerate(expected):
                if i < len(normalized_words) and normalized_words[i] == exp_word:
                    match_count += 1
                else:
                    break
            
            if match_count == len(expected):
                # Remove the matched words
                remaining_words = words[match_count:]
                return ' '.join(remaining_words)
    
    # If all else fails, return original text
    return text


def get_normalized_basmala() -> str:
    """
    Get the normalized version of Basmala (without diacritics).
    
    Returns:
        str: Normalized Basmala text
    """
    return normalize_arabic_text(extract_basmala())