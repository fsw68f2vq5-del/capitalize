"""
Geographic Name Capitalization Checker
Uses GeoNames database to check proper capitalization of geographic names
"""

import sqlite3
import re
from typing import Optional, Tuple, List, Dict

class GeoCapitalizer:
    def __init__(self, db_path: str = "geonames.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        
        # Feature classes in GeoNames
        self.feature_classes = {
            'A': 'Administrative',     # countries, states, regions
            'H': 'Hydrographic',       # streams, lakes, rivers
            'L': 'Area',               # parks, areas
            'P': 'Populated place',    # cities, villages
            'R': 'Road/Railroad',      # roads, railroads
            'S': 'Spot',               # buildings, farms
            'T': 'Hypsographic',       # mountains, hills, rocks
            'U': 'Undersea',           # undersea features
            'V': 'Vegetation'          # forests, heaths
        }
        
        # Generic terms that follow special rules
        self.generic_terms = {
            'river', 'lake', 'ocean', 'sea', 'bay', 'gulf',
            'mountain', 'mount', 'hill', 'valley', 'peak',
            'street', 'road', 'avenue', 'boulevard', 'drive',
            'city', 'town', 'village',
            'island', 'peninsula',
            'desert', 'forest', 'park'
        }
        
        # Compass directions
        self.directions = {
            'north', 'south', 'east', 'west',
            'northern', 'southern', 'eastern', 'western',
            'northeast', 'northwest', 'southeast', 'southwest',
            'northeastern', 'northwestern', 'southeastern', 'southwestern',
            'central', 'upper', 'lower', 'middle'
        }
        
    def close(self):
        """Close database connection"""
        self.conn.close()
    
    def lookup_name(self, name: str) -> Optional[Dict]:
        """
        Look up a geographic name in the database
        Returns dict with name info or None if not found
        """
        cursor = self.conn.cursor()
        
        # Try exact match first
        cursor.execute("""
            SELECT geonameid, name, asciiname, feature_class, feature_code, 
                   country_code, population
            FROM geonames 
            WHERE name = ? OR asciiname = ?
            ORDER BY population DESC
            LIMIT 1
        """, (name, name))
        
        result = cursor.fetchone()
        
        if result:
            return {
                'geonameid': result[0],
                'name': result[1],
                'asciiname': result[2],
                'feature_class': result[3],
                'feature_code': result[4],
                'country_code': result[5],
                'population': result[6]
            }
        
        # Try case-insensitive search
        cursor.execute("""
            SELECT geonameid, name, asciiname, feature_class, feature_code,
                   country_code, population
            FROM geonames 
            WHERE LOWER(name) = LOWER(?) OR LOWER(asciiname) = LOWER(?)
            ORDER BY population DESC
            LIMIT 1
        """, (name, name))
        
        result = cursor.fetchone()
        
        if result:
            return {
                'geonameid': result[0],
                'name': result[1],
                'asciiname': result[2],
                'feature_class': result[3],
                'feature_code': result[4],
                'country_code': result[5],
                'population': result[6]
            }
        
        return None
    
    def is_proper_name(self, name: str) -> bool:
        """Check if a name exists in the database as a geographic feature"""
        return self.lookup_name(name) is not None
    
    def get_correct_capitalization(self, name: str) -> Optional[str]:
        """
        Get the correct capitalization for a geographic name
        Returns the properly capitalized name or None if not found
        """
        info = self.lookup_name(name)
        if info:
            return info['name']
        return None
    
    def check_capitalization(self, text: str) -> Tuple[bool, str]:
        """
        Check if a geographic name is properly capitalized
        Returns (is_correct, correct_form)
        """
        correct_form = self.get_correct_capitalization(text)
        if correct_form is None:
            return (None, None)  # Not a known geographic name
        
        is_correct = (text == correct_form)
        return (is_correct, correct_form)
    
    def apply_capitalization_rules(self, phrase: str) -> str:
        """
        Apply geographic capitalization rules to a phrase
        Handles compound names like "Mississippi River" or "Mount Everest"
        """
        words = phrase.split()
        result = []
        
        for i, word in enumerate(words):
            word_lower = word.lower()
            
            # Check if it's a direction/descriptor
            if word_lower in self.directions:
                # Capitalize if it's part of a well-defined region
                if i < len(words) - 1:
                    next_word = words[i + 1]
                    # Check if the full phrase is a known place
                    test_phrase = ' '.join(words[i:])
                    if self.is_proper_name(test_phrase):
                        correct = self.get_correct_capitalization(test_phrase)
                        if correct:
                            return correct
                    # Otherwise keep lowercase for directions
                    result.append(word_lower)
                else:
                    result.append(word_lower)
            
            # Check if it's a generic term
            elif word_lower in self.generic_terms:
                # Check if it's part of a proper name
                if i > 0:
                    # Generic term after a proper name (e.g., "Mississippi River")
                    result.append(word.capitalize())
                else:
                    result.append(word_lower)
            
            # Otherwise, look it up
            else:
                correct = self.get_correct_capitalization(word)
                if correct:
                    result.append(correct)
                else:
                    # Default: capitalize first letter
                    result.append(word.capitalize())
        
        return ' '.join(result)
    
    def check_text(self, text: str) -> List[Tuple[str, str, str]]:
        """
        Check an entire text for geographic names and their capitalization
        Returns list of (found_text, correct_form, location_in_text)
        """
        issues = []
        
        # Pattern to find potential geographic names (capitalized words)
        # This is a simple approach - can be refined
        words = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', text)
        
        for word in words:
            is_correct, correct_form = self.check_capitalization(word)
            if is_correct is not None and not is_correct:
                issues.append((word, correct_form, text.find(word)))
        
        return issues
    
    def get_feature_info(self, name: str) -> Optional[str]:
        """
        Get descriptive information about a geographic feature
        """
        info = self.lookup_name(name)
        if not info:
            return None
        
        feature_class = self.feature_classes.get(info['feature_class'], 'Unknown')
        
        description = f"{info['name']} ({feature_class})"
        if info['country_code']:
            description += f" in {info['country_code']}"
        if info['population'] > 0:
            description += f", population: {info['population']:,}"
        
        return description


def demo():
    """Demonstrate the capitalization checker"""
    checker = GeoCapitalizer()
    
    print("Geographic Name Capitalization Checker Demo\n")
    
    # Test individual names
    test_names = [
        "new york",
        "New York",
        "mississippi river",
        "Mississippi River",
        "mount everest",
        "Mount Everest",
        "atlantic ocean",
        "Atlantic Ocean",
        "paris",
        "Paris"
    ]
    
    print("Individual Name Checks:")
    print("-" * 60)
    for name in test_names:
        is_correct, correct_form = checker.check_capitalization(name)
        if is_correct is not None:
            status = "✓" if is_correct else "✗"
            print(f"{status} '{name}' -> '{correct_form}'")
            info = checker.get_feature_info(name)
            if info:
                print(f"   {info}")
        else:
            print(f"? '{name}' -> Not found in database")
        print()
    
    # Test text checking
    print("\nText Analysis:")
    print("-" * 60)
    sample_text = """
    I visited new york and saw the mississippi river. 
    Then I went to mount everest and crossed the atlantic ocean.
    """
    
    print(f"Sample text: {sample_text.strip()}")
    print("\nIssues found:")
    issues = checker.check_text(sample_text)
    for found, correct, position in issues:
        print(f"  Position {position}: '{found}' should be '{correct}'")
    
    checker.close()


if __name__ == "__main__":
    demo()
