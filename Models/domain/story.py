from typing import List, Tuple, Optional
from FastAPIProject.Models.domain.entity import Entity
from FastAPIProject.Models.domain.paragraph import Paragraph


class Story:
    def __init__(self):
        self.text: str = ""
        self.chapters: List[Tuple[int, int]] = []
        self.paragraphs: List[Tuple[int, int]] = []
        self.entities: List[Entity] = []
        self.keyParagraphs: List[List[Paragraph]] = []

    def text_by_range(self, start: int, end: int) -> str:
        """:return text by index range"""
        if start < 0 or end > len(self.text) or start >= end:
            print(f"Invalid range: [{start}, {end}]")
            return ""
        return self.text[start:end].strip()

    def remove_null_char(self, text: str) -> str:
        """remove null characters from text"""
        return text.replace("\0", "")

    def get_chapter_count(self) -> int:
        """:return number of chapters"""
        return len(self.chapters)

    def get_paragraph_count(self) -> int:
        """:return number of paragraphs"""
        return len(self.paragraphs)

    def get_entity_count(self) -> int:
        """:return number of entities"""
        return len(self.entities)

    def is_empty(self) -> bool:
        """check if the story is empty"""
        return not self.text or not self.text.strip()