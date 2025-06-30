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
from textranker import TextRanker,Interval, IntervalTree

from Services.utils.ner import get_place_and_time


class StoryProcessor:
    """proccess story and extract text, entities and key paragraphs"""

    def __init__(self):
        self.text_ranker = TextRanker()

    def create_story_from_file(self, path: str) -> Story:
        """create a Story object from a file path"""
        story = Story()
        story.text, story.chapters, story.paragraphs = self.extract_text(path)
        story.entities = self.extract_entities(story)
        story.keyParagraphs = self.extract_key_paragraphs(story)
        return story

    def extract_text(self, path: str) -> Tuple[str, List[Tuple[int, int]], List[Tuple[int, int]]]:
        """extract text from a file and return the plain text, chapters and paragraphs"""
        if path.endswith(".pdf"):
            return self.text_from_pdf(path)
        else:
            raise Exception("Unsupported file format")

    def _extract_text_from_blocks(self, blocks, continuous_text: str, paragraphs: list,
                                  current_paragraph_start: int, prev_block) -> Tuple:
        """text extraction from blocks"""
        blocks = sorted(blocks, key=lambda b: (b[1], b[0]))
        text_elements = []

        for block in blocks:
            text_content = block[4].strip()
            if not text_content:
                continue

            if prev_block is not None and block[1] > prev_block[3] and block[0] >= prev_block[2]:
                if len(continuous_text) > current_paragraph_start:
                    paragraphs.append((current_paragraph_start, len(continuous_text)))
                current_paragraph_start = len(continuous_text)

            continuous_text += text_content + " "
            text_elements.append((block[0], block[1], text_content))
            prev_block = block

        return continuous_text, paragraphs, current_paragraph_start, prev_block, text_elements

    def extract_entities(self, story: Story) -> List[Entity]:
        """entities extraction"""
        chapter_texts = [story.text_by_range(start, end) for start, end in story.chapters]
        return entity_extraction(chapter_texts)

    def _extract_text_with_ocr(self, page, continuous_text: str, paragraphs: list,
                               current_paragraph_start: int, last_y) -> tuple[str, list, int, float, list]:
        """extract text using OCR when no blocks are available"""
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

            # check if this is a new paragraph based on y position
            if last_y is not None and abs(y - last_y) >= avg_font_size * 1.1:
                if len(continuous_text) > current_paragraph_start:
                    txt = continuous_text[current_paragraph_start:].split()

                    # if the paragraph is too short, skip it
                    if len(txt) < 10:
                        continuous_text = continuous_text[:current_paragraph_start]
                        continue

                    # end the current paragraph if it has content
                    paragraphs.append((current_paragraph_start, len(continuous_text)))
                # start a new paragraph
                current_paragraph_start = len(continuous_text)

            # add the text content to the continuous text
            continuous_text += text_content.strip() + " "
            text_elements.append((x, y, text_content))
            last_y = y

        return continuous_text, paragraphs, current_paragraph_start, last_y, text_elements

    def _process_single_page(self, page, continuous_text: str, paragraphs: list,
                             current_paragraph_start: int, last_y, prev_block) -> tuple[
        list, str, list, int, float, object]:
        """process a single page - choose between regular extraction and OCR"""
        page_text_elements = []

        try:
            blocks = page.get_text("blocks")
            if not blocks:
                # OCR
                continuous_text, paragraphs, current_paragraph_start, last_y, page_text_elements = \
                    self._extract_text_with_ocr(page, continuous_text, paragraphs, current_paragraph_start, last_y)
            else:
                # automatic extraction
                continuous_text, paragraphs, current_paragraph_start, prev_block, page_text_elements = \
                    self._extract_text_from_blocks(blocks, continuous_text, paragraphs, current_paragraph_start,
                                                   prev_block)

        except Exception as e:
            print(f"Error extracting text from page: {e}")

        return page_text_elements, continuous_text, paragraphs, current_paragraph_start, last_y, prev_block

    def text_from_pdf(self, pdf_path: str) -> tuple[str, list[tuple[int, int]], list[tuple[int, int]]]:
        """extract text from PDF file with paragraph and chapter detection"""
        doc = fitz.open(pdf_path)
        text_elements = [(0.0, 0.0, "\0")]
        last_y = None
        prev_block = None

        # save the continuous text for exact indexing
        continuous_text = ""
        paragraphs = []
        current_paragraph_start = 0

        # procces al the pages in the PDF
        for page in doc:
            page_elements, continuous_text, paragraphs, current_paragraph_start, last_y, prev_block = \
                self._process_single_page(page, continuous_text, paragraphs, current_paragraph_start, last_y,
                                          prev_block)

            text_elements.extend(page_elements)
            # mark the end of the page with a null character
            text_elements.append((0.0, 0.0, "\0"))

        # end of the last paragraph
        if len(continuous_text) > current_paragraph_start:
            paragraphs.append((current_paragraph_start, len(continuous_text)))

        doc.close()

        plain_text = continuous_text.strip()

        # extract chapter as indices
        chapters = self.extract_chapters_as_indices(text_elements, plain_text, 17)

        if not chapters and plain_text:
            chapters = [(0, len(plain_text))]

        return plain_text, chapters, paragraphs

    def extract_chapters_as_indices(self, text_elements: list[tuple[float, float, str]],
                                    plain_text: str, avg_line_height: float) -> list[tuple[int, int]]:
        """chapter extraction as indices"""
        if len(text_elements) <= 2:  # רק אלמנטים של התחלה וסוף
            return [(0, len(plain_text))] if plain_text else []

        threshold = avg_line_height * 10
        start_of_page = None

        # find the start and end of the page
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

            # check if this is the start of a new chapter
            if (prev_element[2] == "\0" and
                    abs(start_of_page - current_element[0]) >= threshold):

                # end the current chapter if it has content
                if current_position > current_chapter_start:
                    chapters.append((current_chapter_start, current_position))

                # start a new chapter
                current_chapter_start = current_position

            # add the text content to the current position
            current_position += len(text_content) + 1

            # check if this is the end of a chapter
            if (next_element[2] == "\0" and
                    abs(end_of_page - current_element[1]) >= threshold):
                # end the current chapter if it has content
                chapters.append((current_chapter_start, current_position))
                current_chapter_start = current_position

        # add the last chapter if it has content
        if current_position > current_chapter_start:
            chapters.append((current_chapter_start, min(current_position, len(plain_text))))

        # create a chapter for the entire text if no chapters were found
        if not chapters and plain_text:
            chapters = [(0, len(plain_text))]

        return chapters

    def extract_key_paragraphs(self, story: Story) -> List[List[Paragraph]]:
        """extract key paragraphs from the story"""
        key_paragraphs = []
        entities_positions = [e.get_position() for e in story.entities if e.get_position()]

        for i, (chapter_start, chapter_end) in enumerate(story.chapters):
            chapter_text = story.text_by_range(chapter_start, chapter_end)
            chapter_paragraphs = self.summarize_chapter(story, chapter_text, entities_positions, story.paragraphs)
            key_paragraphs.append(chapter_paragraphs)

        return key_paragraphs


    def summarize_chapter(self, story: Story, chapter: str, entities: List[List[Tuple[int, int]]],
                          paragraphs: List[Tuple[int, int]]) -> List[Paragraph]:
        """summarize the chapter and extract key paragraphs"""
        kp = self.text_ranker.ExtractKeyParagraphs(
            chapter, paragraphs, entities, int(len(paragraphs) * 0.65)
        )
        orgenized_kp = []
        for index, entities in kp.items():
            start, end = story.paragraphs[index][0], story.paragraphs[index][1]
            ents_objects = [story.entities[e] for e in entities if e < len(story.entities)]
            para = Paragraph(index, start, end, entities)
            para.place, para.time = get_place_and_time(ents_objects)
            orgenized_kp.append(para)

        orgenized_kp = self.summarize_chapter_abstractive(story, chapter, orgenized_kp)
        return orgenized_kp

    def summarize_chapter_abstractive(self,story: Story, chapter: str, paragraphs: List[Paragraph]) -> List[Paragraph]:
        """summarize the chapter using abstractive summarization"""
        paragraphs_texts = [story.text_by_range(p.start, p.end) for p in paragraphs]
        summary = abstractive_summarization(paragraphs_texts)

        for (p, s) in zip(paragraphs, summary):
            p.set_summary(s)

        return paragraphs
