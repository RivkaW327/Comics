# from itertools import count

import fitz # PyMuPDF
import pytesseract
from PIL import Image
import io

import re
# from collections import Counter
from statistics import mean

def text_from_image(image_path: str) -> list[tuple[float, float, str]]:
    img = Image.open(image_path)
    data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
    img.close()

    text_blocks = []
    n_boxes = len(data['level'])
    for i in range(n_boxes):
        x = data['left'][i]
        y = data['top'][i]
        width = data['width'][i]
        height = data['height'][i]
        text = data['text'][i]
        if text.strip():  # Only add non-empty text
            text_blocks.append((x, y, x+width, y+height, text))
    # text_blocks = sorted(text_blocks, key=lambda b: (b[1], b[0]))
    # return text_blocks
    text = []
    for text_block in text_blocks:
        text.append((text_block[1], text_block[3], text_block[4]))
    return text
#לא כל כך מדוייק (מילים עם אותיות שחורגות למעלה ולמטה מקבלות גודל מאוד גדול)
def text_from_image_with_font_size(image_path: str) -> list[tuple[str, int]]:
    img = Image.open(image_path)
    ocr_data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
    text_with_font_sizes = []
    for i in range(len(ocr_data["text"])):
        word = ocr_data["text"][i].strip()
        if word:
            word_height = ocr_data["height"][i]
            text_with_font_sizes.append((word, word_height))
    img.close()
    return text_with_font_sizes

# return a list of tuples, each tuple contains the x0, y0, and text of a block of text
def text_from_pdf(pdf_path: str) -> list[tuple[float, float, str]]:
    doc = fitz.open(pdf_path)
    text = [(0.0, 0.0, "\0")]
    last_y = None
    prev_block = None
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

                    # בדיקת קפיצת פסקה
                    if last_y is not None and abs(y - last_y) >= avg_font_size * 1.1:  # אפשר לשחק עם מקדם 1.5
                        text_content = "###PARA###" + text_content

                    text.append((x, y, text_content))
                    last_y = y  # עדכון האחרון
            else:
                blocks = sorted(blocks, key=lambda b: (b[1], b[0]))  # מיון לפי y ואז x
                for block in blocks:
                    string_text = block[4]
                    if not string_text.strip():
                        continue

                    if prev_block is not None and block[1] > prev_block[3] and block[0] >= prev_block[2]:
                        string_text = "###PARA###" + string_text

                    text.append((block[1], block[3], string_text))  # y0, y1, text
                    prev_block = block
        except Exception as e:
            print(f"Error extracting text from page: {e}")
        text.append((0.0, 0.0, "\0"))  # סימון סוף עמוד
    doc.close()
    return text


def text_with_font_size_from_pdf(pdf_path: str) -> list[tuple[str, int]]:
    text_with_font_sizes = []
    doc = fitz.open(pdf_path)
    for page in doc:  # iterate the document pages
        blocks = page.get_text("dict")["blocks"]
        if blocks:
            for block in blocks:  # iterate the text blocks
                if 'lines' in block:
                    for line in block['lines']:
                        for span in line['spans']:
                            text_with_font_sizes.append((span['text'], span['size']))
        text_with_font_sizes.append(('\0', -1))
    doc.close()
    return text_with_font_sizes

# להוסיף מחיקה של בלוקים שחוזרים על עצמם יותר מ90% של העמודים------------------
def filter_noise(text: list[tuple[float, float, str]]) -> list[tuple[float, float, str]]:
    cleaned_text = []
    # new line with less than 14 characters
    pattern = r'^.{1,15}$'

    for index in range(1, len(text)-1):
        ct = text[index][2]
        # delete single characters
        ct = re.sub(r'(?:(?<=\s)(\w)(?=\s|\n)|(?<=\n)(\w)(?=\s|\n)|(^\w(?=\s|\n))|(\w$))', '', ct)
        # ct = ct.strip()
        if text[index][2] != "\0" and (text[index-1][2] == "\0" or text[index+1][2] == "\0"):
            ct = re.sub(pattern, '', ct, flags=re.M)

        ct = re.sub(r'\s\s+', ' ', ct)
        ct = re.sub(r'\n\n+', '\n', ct)
        if ct != "":
            cleaned_text.append((text[index][0], text[index][1], ct))
    # return remove_frequent_strings(cleaned_text, 0.7)
    return cleaned_text

# לבדוק אם עובד טוב ואם צריך לשנות את הפונקציה או אם יש עניין להשתמש בה
def remove_frequent_strings(strings :list[tuple[float, float, str]], threshold=0.85)-> list[tuple[float, float, str]]:
    # flag = {key: False for key in set(t[2] for t in strings)}
    count = {key: 0 for key in set(t[2] for t in strings)}
    for string in strings:
        if string[2] != "\0": #not flag[string[2]] and
            count[string[2]] += 1
        #     flag[string[2]] = True
        # elif string[2] == "\0":
        #     flag[string[2]] = False

    total = len([string[2] for string in strings if string[2] == "\0"])
    # print(sorted(list(set([i/total for i in count.values()]))))
    filtered_strings = []
    for i in range(len(strings)):
        if count[strings[i][2]]/total < threshold:
            filtered_strings.append(strings[i])
        else:
            print(f"Removed: {strings[i][2]}")
    return filtered_strings

# def avg_font_size(text_with_font_sizes: list[tuple[str, int]]) -> float:
#     font_sizes = [size for _, size in text_with_font_sizes if size is not None]
#     return sum(font_sizes) / len(font_sizes)

def split_into_chapters(text: list[tuple[float, float, str]], avg_line_height) -> list[str]:
    threshold = avg_line_height * 10
    start_of_page = None
    for (_, l, t) in text:
        if t != "\0" and (start_of_page==None or l < start_of_page):
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

    # chapters = re.split(r'\n{3,}', text)    # Combine chapter titles with their content
    # chapters = [part.strip() for part in chapters if part.strip()]
    chapters = [remove_null_char(c) for c in chapters]  # Corrected the loop to list comprehension
    return chapters


def remove_null_char(text: str) -> str:
    return text.replace("\0", "")

# לא בטוח שעובד
def split_into_chapters_by_numbers(text_with_font_sizes: list[tuple[str, int]]) -> list:
    text = ' '.join([word for word, _ in text_with_font_sizes])
    # Use regular expression to split the text into chapters
    chapters =  re.split(r'(?im)^(Chapter\s+\d+|Chapter\s+[IVXLCDM]+|\d+|[IVXLCDM]+)$', text)
    # Combine chapter titles with their content
    chapters = [part.strip() for part in chapters if part.strip()]
    result = []
    for i in range(1, len(chapters), 2):
        result.append(chapters[i] + chapters[i + 1])
    return result
    # avgFontSize = avg_font_size(text_with_font_sizes)
    # result = [[]]
    # chapter = 0
    # for item in text_with_font_sizes:
    #     size = item[1]
    #     if size > avgFontSize and :
    #         chapter += 1
    #         result.append([])  # Start a new chapter list
    #     result[chapter].append(item)
    # return result





#בדיקות
# path = "C:/Users/user/Documents/year2/project/data/CC_Pollyanna_Reader_W1.pdf"
path = "C:/Users/user/Documents/year2/project/data/anne_of_the_green_gables_montogomery.pdf"
# path = "C:/Users/user/Documents/year2/project/data/Burnett_Secret_Garden.pdf"
# image = "C:/Users/user/Pictures/Screenshots/צילום מסך 2025-03-06 233449.png"
# path ="C:/Users/user/Downloads/SKM_C458eu25032522550.pdf"
# path = "C:/Users/user/Documents/year2/project/data/such_as_i_have.pdf"
# path = "C:\\Users\\user\\Documents\\year2\\project\\data\\the_gift_of_the_magi.pdf"

role_story = text_from_pdf(path)
# filter_noise(text_from_pdf(file2))
# print(role_story)
text  = "".join([i[2]+" " for i in role_story])
# print(text)
# clean_story = filter_noise(role_story)
# print(clean_story)
# clean_text  = "".join([i[2]+" " for i in role_story])
# print(text)
chapters = split_into_chapters(role_story,18)
print(len(chapters))
# for i,c in enumerate(chapters):
#     print("\n\n", i, "\n", c)  # Print the first chapter

# text_with_font_sizes = text_with_font_size_from_pdf(file)
# print(text_with_font_sizes)
# txt = text_from_image(image)
# print(txt)
# txt_with_font = text_from_image_with_font_size(image)
# print(txt_with_font)
# chapters = split_into_chapters(role_story)
# print(chapters)  # Print the first chapter
# story_image = text_from_image(filescan)
# print(story_image)