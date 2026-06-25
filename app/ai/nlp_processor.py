"""NLP preprocessor using spaCy for entity extraction."""

import re
from datetime import datetime, timedelta
from typing import Optional


class NLPProcessor:
    """Lightweight NLP processor for extracting entities from user messages."""

    # Common date patterns
    DATE_PATTERNS = [
        r'\b(\d{4}-\d{2}-\d{2})\b',           # 2024-03-15
        r'\b(\d{2}/\d{2}/\d{4})\b',            # 15/03/2024
        r'\b(\d{2}-\d{2}-\d{4})\b',            # 15-03-2024
    ]

    # Number words
    NUMBER_WORDS = {
        'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
        'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10,
        'a': 1, 'an': 1, 'single': 1, 'couple': 2, 'pair': 2,
    }

    # Ticket type keywords
    TICKET_KEYWORDS = {
        'gate_entry': ['gate', 'entry', 'entrance', 'basic', 'general', 'regular'],
        'exhibition': ['exhibition', 'exhibit', 'gallery', 'display'],
        'show': ['show', 'planetarium', 'theater', 'theatre', 'movie', 'film', 'screening'],
        'guided_tour': ['guide', 'guided', 'tour', 'walk'],
        'combo': ['combo', 'bundle', 'package', 'all', 'everything', 'complete'],
    }

    # Category keywords
    CATEGORY_KEYWORDS = {
        'adult': ['adult', 'grown', 'regular'],
        'child': ['child', 'kid', 'children', 'kids', 'minor', 'young'],
        'student': ['student', 'college', 'university', 'school'],
        'senior': ['senior', 'elderly', 'old', 'retired', 'pension'],
        'foreign_tourist': ['foreign', 'tourist', 'international', 'overseas', 'abroad'],
    }

    # Relative date keywords
    RELATIVE_DATES = {
        'today': 0, 'tomorrow': 1, 'day after tomorrow': 2,
        'next week': 7, 'this weekend': None,  # computed dynamically
    }

    @staticmethod
    def extract_date(text: str) -> Optional[str]:
        """Extract a date from user text."""
        text_lower = text.lower().strip()

        # Check relative dates first
        today = datetime.utcnow()

        if 'today' in text_lower:
            return today.strftime('%Y-%m-%d')
        if 'tomorrow' in text_lower:
            return (today + timedelta(days=1)).strftime('%Y-%m-%d')
        if 'day after tomorrow' in text_lower:
            return (today + timedelta(days=2)).strftime('%Y-%m-%d')

        # Weekend detection
        if 'this weekend' in text_lower or 'weekend' in text_lower:
            days_until_saturday = (5 - today.weekday()) % 7
            if days_until_saturday == 0:
                days_until_saturday = 7
            saturday = today + timedelta(days=days_until_saturday)
            return saturday.strftime('%Y-%m-%d')

        if 'next week' in text_lower:
            next_monday = today + timedelta(days=(7 - today.weekday()))
            return next_monday.strftime('%Y-%m-%d')

        # Try regex patterns
        for pattern in NLPProcessor.DATE_PATTERNS:
            match = re.search(pattern, text)
            if match:
                date_str = match.group(1)
                # Try to parse and normalize
                for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y']:
                    try:
                        parsed = datetime.strptime(date_str, fmt)
                        return parsed.strftime('%Y-%m-%d')
                    except ValueError:
                        continue

        return None

    @staticmethod
    def extract_number(text: str) -> Optional[int]:
        """Extract a number of tickets from text."""
        text_lower = text.lower().strip()

        # Check word numbers first
        for word, num in NLPProcessor.NUMBER_WORDS.items():
            if word in text_lower.split():
                return num

        # Try to find digits
        numbers = re.findall(r'\b(\d+)\b', text)
        if numbers:
            num = int(numbers[0])
            if 1 <= num <= 50:  # reasonable ticket count
                return num

        return None

    @staticmethod
    def extract_ticket_type(text: str) -> Optional[str]:
        """Extract ticket type from user text."""
        text_lower = text.lower()
        for ticket_type, keywords in NLPProcessor.TICKET_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text_lower:
                    return ticket_type
        return None

    @staticmethod
    def extract_visitor_category(text: str) -> Optional[str]:
        """Extract visitor category from text."""
        text_lower = text.lower()
        for category, keywords in NLPProcessor.CATEGORY_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text_lower:
                    return category
        return None

    @staticmethod
    def extract_email(text: str) -> Optional[str]:
        """Extract email from text."""
        email_pattern = r'[\w.+-]+@[\w-]+\.[\w.-]+'
        match = re.search(email_pattern, text)
        return match.group(0) if match else None

    @staticmethod
    def extract_phone(text: str) -> Optional[str]:
        """Extract phone number from text."""
        phone_pattern = r'[\+]?[\d\s\-\(\)]{10,15}'
        match = re.search(phone_pattern, text)
        if match:
            phone = re.sub(r'[\s\-\(\)]', '', match.group(0))
            if len(phone) >= 10:
                return phone
        return None

    @staticmethod
    def detect_language(text: str) -> str:
        """Basic language detection from text."""
        # Hindi detection
        if re.search(r'[\u0900-\u097F]', text):
            return 'hi'
        # Chinese detection
        if re.search(r'[\u4e00-\u9fff]', text):
            return 'zh'
        # Japanese detection
        if re.search(r'[\u3040-\u309F\u30A0-\u30FF]', text):
            return 'ja'
        # Arabic detection
        if re.search(r'[\u0600-\u06FF]', text):
            return 'ar'
        # Default to English
        return 'en'

    @staticmethod
    def extract_name(text: str) -> Optional[str]:
        """Extract a person's name from text - basic heuristic."""
        text = text.strip()

        # If it looks like just a name (no special chars except spaces)
        if re.match(r'^[A-Za-z\s\.]{2,50}$', text):
            return text.title()

        # Check for "my name is..." patterns
        patterns = [
            r'(?:my name is|i am|i\'m|this is|name:?)\s+([A-Za-z\s\.]+)',
            r'([A-Za-z]+\s[A-Za-z]+)',  # Two word name
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                name = match.group(1).strip()
                if len(name) >= 2:
                    return name.title()

        return None

    @staticmethod
    def extract_all_entities(text: str) -> dict:
        """Extract all possible entities from a single text message."""
        return {
            "date": NLPProcessor.extract_date(text),
            "number": NLPProcessor.extract_number(text),
            "ticket_type": NLPProcessor.extract_ticket_type(text),
            "visitor_category": NLPProcessor.extract_visitor_category(text),
            "email": NLPProcessor.extract_email(text),
            "phone": NLPProcessor.extract_phone(text),
            "name": NLPProcessor.extract_name(text),
            "language": NLPProcessor.detect_language(text),
        }
