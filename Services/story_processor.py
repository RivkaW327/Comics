# Services/StoryProcessor.py
import fitz  # PyMuPDF
import pytesseract
from PIL import Image
import io
from statistics import mean
from typing import List, Tuple

from FastAPIProject.Models.domain.story import Story
from FastAPIProject.Models.domain.entity import Entity
from FastAPIProject.Models.domain.paragraph import Paragraph
from FastAPIProject.Services.utils.ner import coref_model, entity_extraction
from FastAPIProject.Services.utils.pegasus_xsum import abstractive_summarization
import textranker
from textranker import TextRanker


class StoryProcessor:
    """מחלקה לעיבוד וחילוץ תוכן מסיפורים"""

    def __init__(self):
        self.text_ranker = TextRanker()

    def create_story_from_file(self, path: str) -> Story:
        """יצירת אובייקט Story מקובץ"""
        story = Story()
        story.text, story.chapters, story.paragraphs = self.extract_text(path)
        story.entities = self.extract_entities(story)
        story.keyParagraphs = self.extract_key_paragraphs(story)
        return story

    def extract_text(self, path: str) -> Tuple[str, List[Tuple[int, int]], List[Tuple[int, int]]]:
        """חילוץ טקסט ראשי - תומך כרגע רק בPDF"""
        if path.endswith(".pdf"):
            return self.text_from_pdf(path)
        else:
            raise Exception("Unsupported file format")

    # def text_from_pdf(self, pdf_path: str) -> Tuple[str, List[Tuple[int, int]], List[Tuple[int, int]]]:
    #     """חילוץ טקסט מקובץ PDF עם זיהוי פסקאות ופרקים"""
    #     doc = fitz.open(pdf_path)
    #     text_elements = [(0.0, 0.0, "\0")]
    #     last_y = None
    #     prev_block = None
    #
    #     continuous_text = ""
    #     paragraphs = []
    #     current_paragraph_start = 0
    #
    #     for page in doc:
    #         page_elements, continuous_text, paragraphs, current_paragraph_start, last_y, prev_block = \
    #             self._process_single_page(page, continuous_text, paragraphs, current_paragraph_start, last_y,
    #                                       prev_block)
    #
    #         text_elements.extend(page_elements)
    #         text_elements.append((0.0, 0.0, "\0"))
    #
    #     if len(continuous_text) > current_paragraph_start:
    #         paragraphs.append((current_paragraph_start, len(continuous_text)))
    #
    #     doc.close()
    #     plain_text = continuous_text.strip()
    #
    #     chapters = self.extract_chapters_as_indices(text_elements, plain_text, 17)
    #
    #     if not chapters and plain_text:
    #         chapters = [(0, len(plain_text))]
    #
    #     return plain_text, paragraphs, chapters
    #
    # def _process_single_page(self, page, continuous_text: str, paragraphs: list,
    #                          current_paragraph_start: int, last_y, prev_block) -> Tuple:
    #     """עיבוד עמוד יחיד - בחירה בין חילוץ רגיל לOCR"""
    #     page_text_elements = []
    #
    #     try:
    #         blocks = page.get_text("blocks")
    #         if not blocks:
    #             continuous_text, paragraphs, current_paragraph_start, last_y, page_text_elements = \
    #                 self._extract_text_with_ocr(page, continuous_text, paragraphs, current_paragraph_start, last_y)
    #         else:
    #             continuous_text, paragraphs, current_paragraph_start, prev_block, page_text_elements = \
    #                 self._extract_text_from_blocks(blocks, continuous_text, paragraphs, current_paragraph_start,
    #                                                prev_block)
    #
    #     except Exception as e:
    #         print(f"Error extracting text from page: {e}")
    #
    #     return page_text_elements, continuous_text, paragraphs, current_paragraph_start, last_y, prev_block
    #
    # def _extract_text_from_blocks(self, blocks, continuous_text: str, paragraphs: list,
    #                               current_paragraph_start: int, prev_block) -> Tuple:
    #     """חילוץ טקסט מבלוקים רגילים של PDF"""
    #     blocks = sorted(blocks, key=lambda b: (b[1], b[0]))
    #     text_elements = []
    #
    #     for block in blocks:
    #         text_content = block[4].strip()
    #         if not text_content:
    #             continue
    #
    #         if prev_block is not None and block[1] > prev_block[3] and block[0] >= prev_block[2]:
    #             if len(continuous_text) > current_paragraph_start:
    #                 paragraphs.append((current_paragraph_start, len(continuous_text)))
    #             current_paragraph_start = len(continuous_text)
    #
    #         continuous_text += text_content + " "
    #         text_elements.append((block[0], block[1], text_content))
    #         prev_block = block
    #
    #     return continuous_text, paragraphs, current_paragraph_start, prev_block, text_elements
    #
    # def _extract_text_with_ocr(self, page, continuous_text: str, paragraphs: list,
    #                            current_paragraph_start: int, last_y) -> Tuple:
    #     """חילוץ טקסט באמצעות OCR כאשר אין בלוקים זמינים"""
    #     pix = page.get_pixmap()
    #     img = Image.open(io.BytesIO(pix.tobytes()))
    #     data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
    #     img.close()
    #
    #     n_boxes = len(data['level'])
    #     if n_boxes == 0:
    #         return continuous_text, paragraphs, current_paragraph_start, last_y, []
    #
    #     heights = [data['height'][i] for i in range(n_boxes) if data['height'][i] > 0]
    #     avg_font_size = mean(heights) if heights else 12
    #     text_elements = []
    #
    #     for i in range(n_boxes):
    #         x = data['left'][i]
    #         y = data['top'][i]
    #         text_content = data['text'][i]
    #
    #         if not text_content.strip():
    #             continue
    #
    #         if last_y is not None and abs(y - last_y) >= avg_font_size * 1.1:
    #             if len(continuous_text) > current_paragraph_start:
    #                 paragraphs.append((current_paragraph_start, len(continuous_text)))
    #             current_paragraph_start = len(continuous_text)
    #
    #         continuous_text += text_content + " "
    #         text_elements.append((x, y, text_content))
    #         last_y = y
    #
    #     return continuous_text, paragraphs, current_paragraph_start, last_y, text_elements
    #
    # def extract_chapters_as_indices(self, text_elements: List[Tuple[float, float, str]],
    #                                 plain_text: str, avg_line_height: float) -> List[Tuple[int, int]]:
    #     """חילוץ פרקים כאינדקסים של התחלה וסיום בטקסט"""
    #     if len(text_elements) <= 2:
    #         return [(0, len(plain_text))] if plain_text else []
    #
    #     threshold = avg_line_height * 10
    #     start_of_page = None
    #
    #     valid_elements = [l for (_, l, t) in text_elements if t != "\0"]
    #     if not valid_elements:
    #         return [(0, len(plain_text))] if plain_text else []
    #
    #     start_of_page = min(valid_elements)
    #     end_of_page = max(valid_elements)
    #
    #     chapters = []
    #     current_chapter_start = 0
    #     current_position = 0
    #
    #     for i in range(1, len(text_elements) - 1):
    #         current_element = text_elements[i]
    #         prev_element = text_elements[i - 1]
    #         next_element = text_elements[i + 1]
    #
    #         text_content = current_element[2]
    #
    #         if text_content == "\0":
    #             continue
    #
    #         if (prev_element[2] == "\0" and
    #                 abs(start_of_page - current_element[0]) >= threshold):
    #
    #             if current_position > current_chapter_start:
    #                 chapters.append((current_chapter_start, current_position))
    #
    #             current_chapter_start = current_position
    #
    #         current_position += len(text_content) + 1
    #
    #         if (next_element[2] == "\0" and
    #                 abs(end_of_page - current_element[1]) >= threshold):
    #             chapters.append((current_chapter_start, current_position))
    #             current_chapter_start = current_position
    #
    #     if current_position > current_chapter_start:
    #         chapters.append((current_chapter_start, min(current_position, len(plain_text))))
    #
    #     if not chapters and plain_text:
    #         chapters = [(0, len(plain_text))]
    #
    #     return chapters
    #
    def extract_entities(self, story: Story) -> List[Entity]:
        """חילוץ ישויות מהפרקים"""
        chapter_texts = [story.chapter_by_range(start, end) for start, end in story.chapters]
        return entity_extraction(chapter_texts)

    def _extract_text_with_ocr(self, page, continuous_text: str, paragraphs: list,
                               current_paragraph_start: int, last_y) -> tuple[str, list, int, float, list]:
        """חילוץ טקסט באמצעות OCR כאשר אין בלוקים זמינים"""
        pix = page.get_pixmap()
        img = Image.open(io.BytesIO(pix.tobytes()))
        data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
        img.close()

        n_boxes = len(data['level'])
        if n_boxes == 0:
            return continuous_text, paragraphs, current_paragraph_start, last_y, []

        heights = [data['height'][i] for i in range(n_boxes) if data['height'][i] > 0]
        avg_font_size = mean(heights) if heights else 12
        text_elements = []

        for i in range(n_boxes):
            x = data['left'][i]
            y = data['top'][i]
            text_content = data['text'][i]

            if not text_content.strip():
                continue

            # בדיקת קפיצת פסקה
            if last_y is not None and abs(y - last_y) >= avg_font_size * 1.1:
                # סיים את הפסקה הנוכחית
                if len(continuous_text) > current_paragraph_start:
                    paragraphs.append((current_paragraph_start, len(continuous_text)))
                # התחל פסקה חדשה
                current_paragraph_start = len(continuous_text)

            # הוסף את הטקסט
            continuous_text += text_content + " "  # הוסף רווח בין מילים
            text_elements.append((x, y, text_content))
            last_y = y

        return continuous_text, paragraphs, current_paragraph_start, last_y, text_elements

    def _process_single_page(self, page, continuous_text: str, paragraphs: list,
                             current_paragraph_start: int, last_y, prev_block) -> tuple[
        list, str, list, int, float, object]:
        """עיבוד עמוד יחיד - בחירה בין חילוץ רגיל לOCR"""
        page_text_elements = []

        try:
            blocks = page.get_text("blocks")
            if not blocks:
                # נתיב OCR
                continuous_text, paragraphs, current_paragraph_start, last_y, page_text_elements = \
                    self._extract_text_with_ocr(page, continuous_text, paragraphs, current_paragraph_start, last_y)
            else:
                # נתיב בלוקים רגילים
                continuous_text, paragraphs, current_paragraph_start, prev_block, page_text_elements = \
                    self._extract_text_from_blocks(blocks, continuous_text, paragraphs, current_paragraph_start,
                                                   prev_block)

        except Exception as e:
            print(f"Error extracting text from page: {e}")

        return page_text_elements, continuous_text, paragraphs, current_paragraph_start, last_y, prev_block

    def text_from_pdf(self, pdf_path: str) -> tuple[str, list[tuple[int, int]], list[tuple[int, int]]]:
        """חילוץ טקסט מקובץ PDF עם זיהוי פסקאות ופרקים"""
        doc = fitz.open(pdf_path)
        text_elements = [(0.0, 0.0, "\0")]
        last_y = None
        prev_block = None

        # שמירת הטקסט הרציף לחישוב מדויק של המיקומים
        continuous_text = ""
        paragraphs = []
        current_paragraph_start = 0

        # עיבוד כל העמודים
        for page in doc:
            page_elements, continuous_text, paragraphs, current_paragraph_start, last_y, prev_block = \
                self._process_single_page(page, continuous_text, paragraphs, current_paragraph_start, last_y,
                                          prev_block)

            text_elements.extend(page_elements)
            # סימון סוף עמוד
            text_elements.append((0.0, 0.0, "\0"))

        # סיים את הפסקה האחרונה
        if len(continuous_text) > current_paragraph_start:
            paragraphs.append((current_paragraph_start, len(continuous_text)))

        doc.close()

        # ניקוי הטקסט הרציף
        plain_text = continuous_text.strip()

        # Debug prints
        print(f"Total text elements: {len(text_elements)}")
        print(f"Non-null text elements: {len([e for e in text_elements if e[2] != '\0'])}")

        # חילוץ פרקים כאינדקסים
        chapters = self.extract_chapters_as_indices(text_elements, plain_text, 17)

        # אם לא נמצאו פרקים, צור פרק יחיד עבור כל הטקסט
        if not chapters and plain_text:
            chapters = [(0, len(plain_text))]

        return plain_text, chapters, paragraphs

    def extract_chapters_as_indices(self, text_elements: list[tuple[float, float, str]],
                                    plain_text: str, avg_line_height: float) -> list[tuple[int, int]]:
        """חילוץ פרקים כאינדקסים של התחלה וסיום בטקסט"""
        if len(text_elements) <= 2:  # רק אלמנטים של התחלה וסוף
            return [(0, len(plain_text))] if plain_text else []

        threshold = avg_line_height * 10
        start_of_page = None

        # מציאת תחילת העמוד
        valid_elements = [l for (_, l, t) in text_elements if t != "\0"]
        if not valid_elements:
            return [(0, len(plain_text))] if plain_text else []

        start_of_page = min(valid_elements)
        end_of_page = max(valid_elements)

        chapters = []
        current_chapter_start = 0
        current_position = 0

        for i in range(1, len(text_elements) - 1):
            current_element = text_elements[i]
            prev_element = text_elements[i - 1]
            next_element = text_elements[i + 1]

            text_content = current_element[2]

            if text_content == "\0":
                continue

            # בדיקה אם זה תחילת פרק חדש
            if (prev_element[2] == "\0" and
                    abs(start_of_page - current_element[0]) >= threshold):

                # סיים את הפרק הנוכחי (אם זה לא הפרק הראשון)
                if current_position > current_chapter_start:
                    chapters.append((current_chapter_start, current_position))

                # התחל פרק חדש
                current_chapter_start = current_position

            # הוסף את אורך הטקסט הנוכחי
            current_position += len(text_content) + 1  # +1 לרווח

            # בדיקה אם זה סוף פרק
            if (next_element[2] == "\0" and
                    abs(end_of_page - current_element[1]) >= threshold):
                # סיים את הפרק הנוכחי
                chapters.append((current_chapter_start, current_position))
                current_chapter_start = current_position

        # הוסף את הפרק האחרון אם נשאר טקסט
        if current_position > current_chapter_start:
            chapters.append((current_chapter_start, min(current_position, len(plain_text))))

        # אם לא נמצאו פרקים, צור פרק יחיד
        if not chapters and plain_text:
            chapters = [(0, len(plain_text))]

        return chapters


    def extract_key_paragraphs(self, story: Story) -> List[List[Paragraph]]:
        """חילוץ פסקאות מפתח מכל פרק"""
        key_paragraphs = [[] for _ in range(len(story.chapters))]
        entities_positions = [e.get_position() for e in story.entities if e.get_position()]

        for i, (chapter_start, chapter_end) in enumerate(story.chapters):
            chapter_text = story.chapter_by_range(chapter_start, chapter_end)
            result = self.summarize_chapter(chapter_text, entities_positions, story.paragraphs)

            for index, entities in result.items():
                start, end = story.paragraphs[index][0], story.paragraphs[index][1]
                summary = abstractive_summarization(story.paragraph_by_range(start, end))
                ents = [None]  # [story.entities[e] for e in entities if e < len(story.entities)]
                para = Paragraph(index, start, end, ents, summary)
                key_paragraphs[i].append(para)

        return key_paragraphs

    def summarize_chapter(self, chapter: str, entities: List[List[Tuple[int, int]]],
                          paragraphs: List[Tuple[int, int]]) -> dict:
        """סיכום פרק והחזרת פסקאות מפתח"""
        return self.text_ranker.ExtractKeyParagraphs(
            chapter, paragraphs, entities, int(len(paragraphs) * 0.75)
        )