"""
Integration Module: Combines GeoNames Database with Capitalization App
This merges geographic name checking with your existing capitalization rules
"""

from geo_capitalizer import GeoCapitalizer
import re
from typing import List, Tuple, Dict

class IntegratedCapitalizer:
    """
    Combines GeoNames geographic database with your existing capitalization rules
    """
    
    def __init__(self, geonames_db_path: str = "geonames.db"):
        """
        Initialize with both systems
        
        Args:
            geonames_db_path: Path to GeoNames SQLite database
        """
        self.geo_checker = GeoCapitalizer(geonames_db_path)
        
        # Your existing capitalization rules from the app
        self.rules = {
            'days': ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'],
            'months': ['january', 'february', 'march', 'april', 'may', 'june', 
                      'july', 'august', 'september', 'october', 'november', 'december'],
            'holidays': ['christmas', 'easter', 'thanksgiving', 'halloween', 
                        'valentine', 'independence day', 'new year'],
            'languages': ['english', 'spanish', 'french', 'german', 'italian', 
                         'chinese', 'japanese', 'russian', 'arabic'],
            'military_ranks': ['captain', 'colonel', 'general', 'lieutenant', 
                              'sergeant', 'major', 'admiral', 'commander'],
            'titles': ['president', 'senator', 'governor', 'mayor', 'doctor', 
                      'professor', 'judge', 'reverend'],
            'religions': ['christianity', 'islam', 'judaism', 'buddhism', 'hinduism'],
            'deities': ['god', 'allah', 'buddha', 'jesus', 'christ']
        }
        
        # Terms that should NOT be capitalized
        self.lowercase_terms = {
            'seasons': ['spring', 'summer', 'fall', 'autumn', 'winter'],
            'directions': ['north', 'south', 'east', 'west', 'northern', 'southern', 
                          'eastern', 'western'] # When used directionally, not as region names
        }
    
    def check_word(self, word: str, context: str = "") -> Tuple[bool, str, str]:
        """
        Check a single word using all available rules
        
        Args:
            word: The word to check
            context: Surrounding text for context (e.g., "north america" vs "went north")
        
        Returns:
            (needs_correction, correct_form, reason)
        """
        word_lower = word.lower()
        
        # Priority 1: Check if it's a geographic name
        geo_result = self.geo_checker.check_capitalization(word)
        if geo_result[0] is not None:  # Found in geographic database
            is_correct, correct_form = geo_result
            if not is_correct:
                return (True, correct_form, "Geographic name")
            return (False, word, "Correct")
        
        # Priority 2: Days of the week
        if word_lower in self.rules['days']:
            correct = word_lower.capitalize()
            if word != correct:
                return (True, correct, "Day of week")
        
        # Priority 3: Months
        if word_lower in self.rules['months']:
            correct = word_lower.capitalize()
            if word != correct:
                return (True, correct, "Month")
        
        # Priority 4: Holidays
        for holiday in self.rules['holidays']:
            if word_lower == holiday or holiday in context.lower():
                correct = word_lower.title()
                if word != correct:
                    return (True, correct, "Holiday")
        
        # Priority 5: Languages
        if word_lower in self.rules['languages']:
            correct = word_lower.capitalize()
            if word != correct:
                return (True, correct, "Language")
        
        # Priority 6: Check for titles before names
        # This requires context to determine if followed by a proper name
        if word_lower in self.rules['military_ranks'] or word_lower in self.rules['titles']:
            # Check if followed by a capitalized word (likely a name)
            context_words = context.split()
            try:
                word_index = context_words.index(word)
                if word_index + 1 < len(context_words):
                    next_word = context_words[word_index + 1]
                    if next_word[0].isupper():  # Followed by capitalized word (name)
                        correct = word_lower.capitalize()
                        if word != correct:
                            category = "Military rank" if word_lower in self.rules['military_ranks'] else "Title"
                            return (True, correct, f"{category} before name")
            except ValueError:
                pass
        
        # Priority 7: Religions
        if word_lower in self.rules['religions']:
            correct = word_lower.capitalize()
            if word != correct:
                return (True, correct, "Religion")
        
        # Priority 8: Deities (special handling - often capitalized)
        if word_lower in self.rules['deities']:
            # "God" when referring to monotheistic deity should be capitalized
            if word_lower in ['god', 'allah', 'jesus', 'christ', 'buddha']:
                correct = word_lower.capitalize()
                if word != correct:
                    return (True, correct, "Deity")
        
        # Check lowercase exceptions
        # Seasons should be lowercase
        if word_lower in self.lowercase_terms['seasons']:
            if word != word_lower:
                return (True, word_lower, "Season (lowercase)")
        
        # Directions - only lowercase if used directionally, not as region name
        if word_lower in self.lowercase_terms['directions']:
            # This is tricky - would need more context
            # For now, if it's lowercase in original, leave it
            pass
        
        return (False, word, "Correct")
    
    def check_phrase(self, phrase: str) -> List[Dict]:
        """
        Check an entire phrase for capitalization issues
        
        Returns list of corrections needed
        """
        corrections = []
        words = phrase.split()
        
        # First, try to find multi-word geographic names
        for i in range(len(words)):
            # Try 3-word combinations
            if i + 2 < len(words):
                three_word = ' '.join(words[i:i+3])
                geo_result = self.geo_checker.check_capitalization(three_word)
                if geo_result[0] is not None:
                    is_correct, correct_form = geo_result
                    if not is_correct:
                        corrections.append({
                            'position': i,
                            'original': three_word,
                            'correct': correct_form,
                            'reason': 'Geographic name (3 words)'
                        })
                        continue
            
            # Try 2-word combinations
            if i + 1 < len(words):
                two_word = ' '.join(words[i:i+2])
                geo_result = self.geo_checker.check_capitalization(two_word)
                if geo_result[0] is not None:
                    is_correct, correct_form = geo_result
                    if not is_correct:
                        corrections.append({
                            'position': i,
                            'original': two_word,
                            'correct': correct_form,
                            'reason': 'Geographic name (2 words)'
                        })
                        continue
            
            # Check individual word
            word = words[i]
            needs_correction, correct_form, reason = self.check_word(word, phrase)
            if needs_correction:
                corrections.append({
                    'position': i,
                    'original': word,
                    'correct': correct_form,
                    'reason': reason
                })
        
        return corrections
    
    def correct_text(self, text: str) -> Tuple[str, List[Dict]]:
        """
        Correct all capitalization in a text
        
        Returns:
            (corrected_text, list_of_changes)
        """
        changes = []
        sentences = re.split(r'([.!?]\s+)', text)
        corrected_sentences = []
        
        for sentence in sentences:
            if not sentence.strip():
                corrected_sentences.append(sentence)
                continue
            
            corrections = self.check_phrase(sentence)
            corrected = sentence
            
            # Apply corrections (in reverse order to maintain positions)
            for correction in sorted(corrections, key=lambda x: x['position'], reverse=True):
                words = corrected.split()
                words[correction['position']] = correction['correct']
                corrected = ' '.join(words)
                changes.append(correction)
            
            corrected_sentences.append(corrected)
        
        final_text = ''.join(corrected_sentences)
        return final_text, changes
    
    def analyze_text(self, text: str) -> Dict:
        """
        Analyze text and return detailed report
        
        Returns dictionary with:
        - original_text
        - corrected_text
        - changes (list)
        - stats (counts by category)
        """
        corrected_text, changes = self.correct_text(text)
        
        # Count changes by category
        stats = {}
        for change in changes:
            reason = change['reason']
            stats[reason] = stats.get(reason, 0) + 1
        
        return {
            'original_text': text,
            'corrected_text': corrected_text,
            'changes': changes,
            'stats': stats,
            'total_corrections': len(changes)
        }
    
    def close(self):
        """Close database connections"""
        self.geo_checker.close()


def main():
    """Example usage"""
    
    print("Integrated Capitalization Checker\n")
    print("=" * 60 + "\n")
    
    checker = IntegratedCapitalizer()
    
    # Test cases combining geographic names and other rules
    test_texts = [
        "I visited new york on monday.",
        "The army officers arrived: captain Smith, colonel Johnson, and general Jones.",
        "In january, we went to the mississippi river.",
        "He speaks english and spanish fluently.",
        "The meeting is next wednesday in los angeles.",
        "We celebrate christmas and easter every year.",
        "Mount everest is in the himalayas, which are in asia.",
        "The atlantic ocean borders north america and europe."
    ]
    
    for text in test_texts:
        print(f"Original:  {text}")
        result = checker.analyze_text(text)
        print(f"Corrected: {result['corrected_text']}")
        
        if result['changes']:
            print(f"Changes ({result['total_corrections']}):")
            for change in result['changes']:
                print(f"  - '{change['original']}' → '{change['correct']}' ({change['reason']})")
        else:
            print("  No changes needed")
        
        print()
    
    checker.close()


if __name__ == "__main__":
    main()
