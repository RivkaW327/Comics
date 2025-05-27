import fitz # PyMuPDF
import pytesseract
from PIL import Image
import io
from statistics import mean
from Services.utils.ner import coref_model
import textranker
from textranker import TextRanker

from Services.entity import Entity
from Services.utils.ner import entity_extraction

class Story:
    def __init__(self, path: str):
        self.text, self.chapters, self.paragraphs = self.extract_text(path)
        self.entities = self.entities_extraction()
        self.keyParagraphs = [[] for _ in range(len(self.chapters))]  # Initialize key paragraphs for each chapter
        self.extract_key_paragraphs()
        self.print_all_paragraphs()

    # def extract_text(self, path: str):
    #     if path.endswith(".pdf"):
    #         text, paragraphs = self.text_from_pdf(path)
    #     else:
    #         raise Exception("Unsupported file format")  # Corrected 'throw' to 'raise'
    #     #TODO -  לבדוק אם צריך את הניקוי של הטקסט
    #     # text = self.filter_noise(text)
    #     chapters = self.split_into_chapters(text, 17)
    #     plain_text = "".join([self.remove_null_char(i[2]) + " " for i in text])
    #     return plain_text, chapters, paragraphs
    #

#TODO - לבדוק אם אפשר לבצע תוך כדי גם את החלוקה לפרקים וגם לשמור את הפסקאות
    # def text_from_pdf(self, pdf_path: str) -> list[tuple[float, float, str]]:
    #     doc = fitz.open(pdf_path)
    #     text = [(0.0, 0.0, "\0")]
    #     last_y = None
    #     prev_block = None
    #     length = 0
    #     paragraphs = []
    #
    #     for page in doc:
    #         try:
    #             blocks = page.get_text("blocks")
    #             if not blocks:
    #                 # Extract text from image if no blocks are found
    #                 pix = page.get_pixmap()
    #                 img = Image.open(io.BytesIO(pix.tobytes()))
    #                 data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
    #                 img.close()
    #                 n_boxes = len(data['level'])
    #                 avg_font_size = mean([data['height'][i] for i in range(n_boxes)])
    #
    #                 for i in range(n_boxes):
    #                     x = data['left'][i]
    #                     y = data['top'][i]
    #                     text_content = data['text'][i]
    #
    #                     if not text_content.strip():
    #                         continue
    #
    #                     # בדיקת קפיצת פסקה לפני עדכון length
    #                     paragraph_start = length
    #                     if last_y is not None and abs(y - last_y) >= avg_font_size * 1.1:
    #                         # סיום הפסקה הקודמת אם יש כזו
    #                         if paragraphs and len(paragraphs) > 0:
    #                             # עדכון סוף הפסקה הקודמת
    #                             prev_start, _ = paragraphs[-1]
    #                             paragraphs[-1] = (prev_start, length)
    #
    #                         # התחלת פסקה חדשה
    #                         paragraph_start = length
    #
    #                     # עדכון length רק אחרי הבדיקה
    #                     length += len(text_content)
    #
    #                     # אם זו התחלת פסקה חדשה, הוסף אותה לרשימה
    #                     if (last_y is not None and abs(y - last_y) >= avg_font_size * 1.1) or len(paragraphs) == 0:
    #                         paragraphs.append((paragraph_start, length))
    #                     else:
    #                         # עדכון סוף הפסקה הנוכחית
    #                         if paragraphs:
    #                             start_pos, _ = paragraphs[-1]
    #                             paragraphs[-1] = (start_pos, length)
    #
    #                     text.append((x, y, text_content))
    #                     last_y = y
    #             else:
    #                 blocks = sorted(blocks, key=lambda b: (b[1], b[0]))
    #
    #                 for block in blocks:
    #                     text_content = block[4]
    #                     if not text_content.strip():
    #                         continue
    #
    #                     # בדיקת קפיצת פסקה לפני עדכון length
    #                     paragraph_start = length
    #                     is_new_paragraph = False
    #
    #                     if prev_block is not None and block[1] > prev_block[3] and block[0] >= prev_block[2]:
    #                         is_new_paragraph = True
    #                         # סיום הפסקה הקודמת
    #                         if paragraphs:
    #                             prev_start, _ = paragraphs[-1]
    #                             paragraphs[-1] = (prev_start, length)
    #
    #                     # עדכון length רק אחרי הבדיקה
    #                     length += len(text_content)
    #
    #                     # הוספת פסקה חדשה או עדכון הקיימת
    #                     if is_new_paragraph or len(paragraphs) == 0:
    #                         paragraphs.append((paragraph_start, length))
    #                     else:
    #                         # עדכון סוף הפסקה הנוכחית
    #                         if paragraphs:
    #                             start_pos, _ = paragraphs[-1]
    #                             paragraphs[-1] = (start_pos, length)
    #
    #                     text.append((block[1], block[3], text_content))
    #                     prev_block = block
    #
    #         except Exception as e:
    #             print(f"Error extracting text from page: {e}")
    #         text.append((0.0, 0.0, "\0"))
    #
    #     doc.close()
    #
    #     # וידוא שהפסקה האחרונה מסתיימת בסוף הטקסט
    #     if paragraphs:
    #         start_pos, _ = paragraphs[-1]
    #         paragraphs[-1] = (start_pos, length)
    #
    #     return text, paragraphs

    def text_from_pdf(self, pdf_path: str) -> tuple[list[tuple[float, float, str]], list[tuple[int, int]]]:
        doc = fitz.open(pdf_path)
        text = [(0.0, 0.0, "\0")]
        last_y = None
        prev_block = None

        # שמירת הטקסט הרציף לחישוב מדויק של המיקומים
        continuous_text = ""
        paragraphs = []
        current_paragraph_start = 0

        for page in doc:
            try:
                blocks = page.get_text("blocks")
                if not blocks:
                    # OCR path
                    pix = page.get_pixmap()
                    img = Image.open(io.BytesIO(pix.tobytes()))
                    data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
                    img.close()
                    n_boxes = len(data['level'])
                    avg_font_size = mean([data['height'][i] for i in range(n_boxes)])

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
                        text.append((x, y, text_content))
                        last_y = y

                else:
                    # Regular blocks path
                    blocks = sorted(blocks, key=lambda b: (b[1], b[0]))

                    for block in blocks:
                        text_content = block[4].strip()
                        if not text_content:
                            continue

                        # בדיקת קפיצת פסקה
                        if prev_block is not None and block[1] > prev_block[3] and block[0] >= prev_block[2]:
                            # סיים את הפסקה הנוכחית
                            if len(continuous_text) > current_paragraph_start:
                                paragraphs.append((current_paragraph_start, len(continuous_text)))
                            # התחל פסקה חדשה
                            current_paragraph_start = len(continuous_text)

                        # הוסף את הטקסט
                        continuous_text += text_content + " "  # הוסף רווח בין בלוקים
                        text.append((block[1], block[3], text_content))
                        prev_block = block

            except Exception as e:
                print(f"Error extracting text from page: {e}")

            # סימון סוף עמוד
            text.append((0.0, 0.0, "\0"))

        # סיים את הפסקה האחרונה
        if len(continuous_text) > current_paragraph_start:
            paragraphs.append((current_paragraph_start, len(continuous_text)))

        doc.close()

        # ניקוי הטקסט הרציף
        plain_text = continuous_text.strip()

        return text, paragraphs, plain_text

    # עדכן גם את extract_text:
    def extract_text(self, path: str):
        if path.endswith(".pdf"):
            text, paragraphs, plain_text = self.text_from_pdf(path)
        else:
            raise Exception("Unsupported file format")

        chapters = self.split_into_chapters(text, 17)

        # בדיקת תקינות (אופציונלי)
        # self.validate_paragraphs(plain_text, paragraphs)

        return plain_text, chapters, paragraphs

    def print_all_paragraphs(self):
        """הדפסת כל הפסקאות"""
        print(f"סה\"כ {len(self.paragraphs)} פסקאות:")
        print("=" * 60)

        for i, (start, end) in enumerate(self.paragraphs):
            self.print_paragraph_by_range(start, end, i)

    def print_paragraph_by_range(self, start: int, end: int, paragraph_index: int = None):
        """הדפסת פסקה בודדת על פי טווח"""
        if start < 0 or end > len(self.text) or start >= end:
            print(f"טווח לא תקין: [{start}, {end}]")
            return

        paragraph_text = self.text[start:end].strip()
        if paragraph_index is not None:
            print(f"פסקה {paragraph_index}: [{start}-{end}]")
        else:
            print(f"טווח [{start}-{end}]:")
        print(f"'{paragraph_text}'")
        print("-" * 50)

    # def filter_noise(self, text: list[tuple[float, float, str]]) -> list[tuple[float, float, str]]:
    #     cleaned_text = []
    #     # new line with less than 14 characters
    #     pattern = r'^.{1,15}$'
    #
    #     for index in range(1, len(text) - 1):
    #         ct = text[index][2]
    #         # delete single characters
    #             #TODO Iחוץ מ
    #         # ct = re.sub(r'(?:(?<=\s)(\w)(?=\s|\n)|(?<=\n)(\w)(?=\s|\n)|(^\w(?=\s|\n))|(\w$))', '', ct)
    #         # ct = ct.strip()
    #         if text[index][2] != "\0" and (text[index - 1][2] == "\0" or text[index + 1][2] == "\0"):
    #             ct = re.sub(pattern, '', ct, flags=re.M)
    #
    #         ct = re.sub(r'\s\s+', ' ', ct)
    #         ct = re.sub(r'\n\n+', '\n', ct)
    #         if ct != "":
    #             cleaned_text.append((text[index][0], text[index][1], ct))
    #     # return remove_frequent_strings(cleaned_text, 0.7)
    #     return cleaned_text

    def remove_null_char(self, text: str) -> str:
        return text.replace("\0", "")

    def split_into_chapters(self, text: list[tuple[float, float, str]], avg_line_height:float) -> list[str]:
        threshold = avg_line_height * 10
        start_of_page = None
        for (_, l, t) in text:
            if t != "\0" and (start_of_page == None or l < start_of_page):
                start_of_page = l

        end_of_page = max([l for (_, l, _) in text])
        chapters = []
        chapters.append(text[0][2])
        i = 0
        for tpl in range(1, len(text) - 1):
            if text[tpl - 1][2] == "\0" and abs(start_of_page - text[tpl][0]) >= threshold:
                chapters.append(text[tpl][2] + " ")
                i += 1
            else:
                chapters[i] += text[tpl][2] + " "
            if text[tpl + 1][2] == "\0" and abs(end_of_page - text[tpl][1]) >= threshold:
                chapters.append("")
                i += 1

        chapters = [self.remove_null_char(c) for c in chapters]  # Corrected the loop to list comprehension
        return chapters

    def entities_extraction(self) -> list[Entity]:
        return entity_extraction(self.chapters)


    def extract_key_paragraphs(self):
        entities_positions = [e.get_position() for e in self.entities if e.get_position()]
        for i, chapter in enumerate(self.chapters):
            self.keyParagraphs[i].append(self.summerize_chapter(chapter, entities_positions))

    def summerize_chapter(self, chapter: str, entities: list[list[tuple[int, int]]]):
        text_ranker = TextRanker()
        return text_ranker.ExtractKeyParagraphs(chapter, self.paragraphs, entities, int(len(self.paragraphs)*0.75))
        # print(text_ranker.ExtractKeyParagraphs(chapter, self.paragraphs, entities, int(len(self.paragraphs)*0.75)))
        #TODO  לראות איך מעבדים את התוצאה

