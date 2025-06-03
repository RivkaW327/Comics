import sys
from FastAPIProject.config.config_loader import config

sys.path.append(config["services"]["maverick_coref"]["path"])

from textranker import Interval, IntervalTree
from collections import Counter
from FastAPIProject.Services.maverick_coref.maverick import Maverick
from torch import cuda

coref_model = Maverick(
    hf_name_or_path=config["services"]["maverick_coref"]["weights"],
    device="cpu" if not cuda.is_available() else "cuda:0"
)

import spacy
from FastAPIProject.Models.domain.entity import Entity

nlp = spacy.load("en_core_web_sm")
from FastAPIProject.Services.utils.description_extraction import api_to_gemini


def entity_extraction(chapters: list[str]) -> list[Entity]:
    all_entities = []

    for chapter in chapters:
        c_entities = []
        ners = ner(chapter)
        print(ners)
        corefs = coreference_resolution(chapter)

        # מיפוי מיקום -> (text, label)
        ner_positions = {(start, end): (text, label) for text, label, start, end in ners}

        # בנה עץ אינטרוולים מה-NER - באופן נכון
        ner_tree = IntervalTree()  # יוצר wrapper חדש
        for text, label, start, end in ners:
            interval = Interval(start, end)
            ner_tree.insert(interval)  # מוסיף לעץ ישירות

        # מיפוי מזהה קלסטר -> רשימת אזכורים ו-label
        clusters = {}

        for cluster_id, (mentions_texts, mentions_offsets) in enumerate(corefs):
            cluster_mentions = []
            labels = []

            for text, (start_char, end_char) in zip(mentions_texts, mentions_offsets):
                cluster_mentions.append(text)
                interval = Interval(start_char, end_char)

                # חיפוש בעץ - מחזיר dict או None
                overlap_result = ner_tree.overlapSearch(interval)

                if overlap_result is None:
                    continue

                # חילוץ המידע מהתוצאה
                overlap_interval = overlap_result['interval']
                overlap_start = overlap_interval.low
                overlap_end = overlap_interval.high

                if (overlap_start, overlap_end) in ner_positions:
                    ner_text, ner_label = ner_positions[(overlap_start, overlap_end)]
                    labels.append(ner_label)

            print(labels)
            label = Counter(labels).most_common(1)[0][0] if labels else "UNKNOWN"

            # שם הדמות יהיה האזכור הראשון
            name = cluster_mentions[0]
            # שאר האזכורים ייחשבו ככינויים
            nicknames = list(cluster_mentions[1:])

            # נבנה ישות לפי המיקום של כל האזכורים בטקסט
            coref_positions = [(start, end) for (_, (start, end)) in zip(mentions_texts, mentions_offsets)]

            entity = Entity(name, label, nicknames, coref_positions)
            c_entities.append(entity)

        # חילוץ תיאורים
        descriptions = description_extraction(chapter, c_entities)
        for ent, description in descriptions.items():
            c = get_ent_by_nickname(ent, c_entities)
            if c is not None:
                c.description = description

        all_entities.extend(c_entities)

        # ניקוי מפורש של העץ (אופציונלי אבל מומלץ)
        del ner_tree

    return all_entities


def ner(chapter):
    doc = nlp(chapter)
    entities = [(ent.text, ent.label_, ent.start_char, ent.end_char) for ent in doc.ents]
    return entities


def coreference_resolution(chapter: str):
    result = coref_model.predict(chapter)
    chapter_chars = zip(result["clusters_token_text"], result["clusters_char_offsets"])
    return chapter_chars


def description_extraction(chapter: str, characters: list[Entity]):
    descriptions = api_to_gemini(chapter, characters)
    return descriptions


def get_ent_by_nickname(nickname: str, entities: list[Entity]) -> Entity:
    for entity in entities:
        for nName in entity.nicknames:
            if nName == nickname:
                return entity
    return None