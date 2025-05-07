import fitz # PyMuPDF
import pytesseract
from PIL import Image
import io
from statistics import mean
# import time
# import multiprocessing
# from concurrent.futures import ProcessPoolExecutor, as_completed

import textranker
from textranker import TextRanker

import re
from collections import Counter

from .character import Character
from .coreference_resolution import coref_model

from .description_extraction import api_to_gemini

class Story:
    def __init__(self, path: str):
        self.text, self.chapters, self.paragraphs = self.extract_text(path)
        self.characters = self.extract_characters()
        self.keyParagraphs = []

    def extract_text(self, path: str):
        if path.endswith(".pdf"):
            text, paragraphs = self.text_from_pdf(path)
        else:
            raise Exception("Unsupported file format")  # Corrected 'throw' to 'raise'
        #TODO -  לבדוק אם צריך את הניקוי של הטקסט
        # text = self.filter_noise(text)
        chapters = self.split_into_chapters(text, 17)
        plain_text = "".join([self.remove_null_char(i[2]) + " " for i in text])
        return plain_text, chapters, paragraphs

    # def text_from_image(self, page, last_y) -> list[tuple[float, float, str]]:
    #     text = [(0.0, 0.0, "\0")]
    #     pix = page.get_pixmap()
    #     img = Image.open(io.BytesIO(pix.tobytes()))
    #     data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
    #     img.close()
    #     n_boxes = len(data['level'])
    #     avg_font_size = mean([data['height'][i] for i in range(n_boxes)])
    #     for i in range(n_boxes):
    #         x = data['left'][i]
    #         y = data['top'][i]
    #         width = data['width'][i]
    #         height = data['height'][i]
    #         text_content = data['text'][i]
    #
    #         if not text_content.strip():
    #             continue
    #
    #         # בדיקת קפיצת פסקה
    #         if last_y is not None and abs(y - last_y) >= avg_font_size * 1.2:
    #             text_content = " ###PARA### " + text_content
    #
    #         text.append((x, y, text_content))
    #         last_y = y
    #     return text, avg_font_size

#TODO - לבדוק אם אפשר לבצע תוך כדי גם את החלוקה לפרקים וגם לשמור את הפסקאות
    def text_from_pdf(self, pdf_path: str) -> list[tuple[float, float, str]]:
        doc = fitz.open(pdf_path)
        text = [(0.0, 0.0, "\0")]
        last_y = None
        prev_block = None
        length = 0
        paragraphs = []
        for page in doc:
            try:
                blocks = page.get_text("blocks")
                if not blocks:
                    # Extract text from image if no blocks are found
                    pix = page.get_pixmap()
                    img = Image.open(io.BytesIO(pix.tobytes()))
                    data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
                    img.close()
                    n_boxes = len(data['level'])
                    avg_font_size = mean([data['height'][i] for i in range(n_boxes)])
                    for i in range(n_boxes):
                        x = data['left'][i]
                        y = data['top'][i]
                        width = data['width'][i]
                        height = data['height'][i]
                        text_content = data['text'][i]

                        if not text_content.strip():
                            continue

                        length += len(text_content)

                        # בדיקת קפיצת פסקה
                        if last_y is not None and abs(y - last_y) >= avg_font_size * 1.1:  # אפשר לשחק עם מקדם 1.5
                            # text_content = "###PARA###" + text_content
                            paragraphs.append((length-len(text_content), length))
                        text.append((x, y, text_content))
                        last_y = y  # עדכון האחרון
                else:
                    blocks = sorted(blocks, key=lambda b: (b[1], b[0]))  # מיון לפי y ואז x
                    for block in blocks:
                        text_content = block[4]
                        if not text_content.strip():
                            continue

                        length += len(text_content)
                        if prev_block is not None and block[1] > prev_block[3] and block[0] >= prev_block[2]:
                            # text_content = "###PARA###" + text_content
                            paragraphs.append((length-len(text_content), length))


                        text.append((block[1], block[3], text_content))  # y0, y1, text
                        prev_block = block
            except Exception as e:
                print(f"Error extracting text from page: {e}")
            text.append((0.0, 0.0, "\0"))  # סימון סוף עמוד
        doc.close()
        return text, paragraphs

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

    # def get_characters_names(self):
    #     return [character.name for character in self.characters]


    def extract_characters(self):
        # ניסיתי להריץ על כל הטקסט בבת אחת אבל המודל דרש הקצאה של מטריצה מאוד גדולה (כ21 גיגה) ולכן עברתי להריץ על כל פרק בנפרד.
        #TODO צריך לבדוק איך לאחד את הדמויות של כל הפרקים.
        chars = []
        for i, chapter in enumerate(self.chapters):
                # TODO- לבדוק מה לגבי הפרמטר של המיקום בתווים- כי זה לפי פרק ולא יחסית לתחילת הסיפר.
            c = self.extract_chars_from_chapter(chapter, coref_model)
            chars.append(c)
        return chars

    def extract_chars_from_chapter(self, chapter: str, model):
        chapter_chars = []
        result = model.predict(chapter)
        for token_texts, char_offsets in zip(result["clusters_token_text"], result["clusters_char_offsets"]):
            c = Character(token_texts[0], token_texts, char_offsets)
            c.description = None
            chapter_chars.append(c)
        self.extract_descriptions(chapter,chapter_chars) # update the descriptions of the characters
        # self.summerize_chapter(chapter, [c.coref_position for c in chapter_chars])
        return chapter_chars

    def extract_descriptions(self, chapter: str, characters: list[Character]):
        # api_to_gemini(chapter, characters)
        descriptions = api_to_gemini(chapter, characters)
        print(descriptions)
        for char, description in descriptions.items():
            c = self.get_char_by_nickname(char, characters)
            c.description = description

    def get_char_by_nickname(self, nickname: str, characters: list[Character]) -> Character:
        for character in characters:
            for nName in character.nicknames:
                if nName == nickname:
                    return character
        return None

    def summerize_chapter(self, chapter: str, characters: list[list[tuple[int, int]]]):
        text_ranker = TextRanker()
        print(text_ranker.ExtractKeyParagraphs(chapter,self.paragraphs, characters, 23))
        #TODO לשנות את המספר של הפסקות לאחוזים של כמה להשאיר
        #TODO  לראות איך מעבדים את התוצאה

    # def extract_characters(self):
    #     chars = []
    #     with ProcessPoolExecutor(max_workers=4) as executor:  # את יכולה לשנות את המספר לפי הזיכרון שלך
    #         futures = [
    #             executor.submit(process_chapter, i, chapter)
    #             for i, chapter in enumerate(self.chapters)
    #         ]
    #         for future in as_completed(futures):
    #             chars.extend(future.result())
    #
    #     return chars

# def process_chapter(chapter, coref_model):
#     result = coref_model.predict(chapter)
#     chars = []
#     for token_texts, char_offsets in zip(result["clusters_token_text"], result["clusters_char_offsets"]):
#         # TODO- לבדוק מה לגבי הפרמטר של המיקום בתווים- כי זה לפי פרק ולא יחסית לתחילת הסיפר.
#         c = Character(token_texts[0], token_texts, char_offsets)
#         chars.append(c)
#     return chars


# def process_chapter(index, chapter):
#     coref_model = load_coref_model()
#
#     start = time.time()
#     print(f"[START] פרק {index} התחיל | PID: {multiprocessing.current_process().pid}")
#
#     result = coref_model.predict(chapter)
#     characters = [
#         Character(token_texts[0], token_texts, char_offsets)
#         for token_texts, char_offsets in zip(result["clusters_token_text"], result["clusters_char_offsets"])
#     ]
#
#     end = time.time()
#     print(f"[DONE ] פרק {index} הסתיים (לקח {end - start:.2f} שניות) | PID: {multiprocessing.current_process().pid}")
#     return characters