# Model/Story.py
from typing import List, Tuple, Optional
from FastAPIProject.Models.domain.entity import Entity
from FastAPIProject.Models.domain.paragraph import Paragraph


class Story:
    """מחלקת נתונים בסיסית לסיפור - ללא לוגיקה עסקית"""

    def __init__(self):
        self.text: str = ""
        self.chapters: List[Tuple[int, int]] = []
        self.paragraphs: List[Tuple[int, int]] = []
        self.entities: List[Entity] = []
        self.keyParagraphs: List[List[Paragraph]] = []

    def paragraph_by_range(self, start: int, end: int) -> str:
        """החזרת טקסט פסקה לפי טווח אינדקסים"""
        if start < 0 or end > len(self.text) or start >= end:
            print(f"Invalid range: [{start}, {end}]")
            return ""
        return self.text[start:end].strip()

    def chapter_by_range(self, start: int, end: int) -> str:
        """החזרת טקסט פרק לפי טווח אינדקסים"""
        if start < 0 or end > len(self.text) or start >= end:
            print(f"Invalid range: [{start}, {end}]")
            return ""
        return self.text[start:end].strip()

    def remove_null_char(self, text: str) -> str:
        """הסרת תווי null מהטקסט"""
        return text.replace("\0", "")

    def get_chapter_count(self) -> int:
        """החזרת מספר הפרקים"""
        return len(self.chapters)

    def get_paragraph_count(self) -> int:
        """החזרת מספר הפסקאות"""
        return len(self.paragraphs)

    def get_entity_count(self) -> int:
        """החזרת מספר הישויות"""
        return len(self.entities)

    def is_empty(self) -> bool:
        """בדיקה אם הסיפור ריק"""
        return not self.text or not self.text.strip()