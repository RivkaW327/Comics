import json
import sys
from typing import List

from FastAPIProject.config.config_loader import config

from textranker import Interval, IntervalTree
from collections import Counter
from FastAPIProject.Services.maverick_coref.maverick import Maverick
from torch import cuda

import spacy
from FastAPIProject.Models.domain.entity import Entity
from FastAPIProject.Services.utils.pegasus_xsum import api_to_gemini
# from FastAPIProject.Services.utils.description_extraction import api_to_gemini
from FastAPIProject.Services.utils.gender import is_male


# nlp = spacy.load("en_core_web_sm")
nlp = spacy.load("en_core_web_trf")

sys.path.append(config["services"]["maverick_coref"]["path"])

coref_model = Maverick(
    hf_name_or_path=config["services"]["maverick_coref"]["weights"],
    device="cpu" if not cuda.is_available() else "cuda:0"
)


def entity_extraction(chapters: list[str]) -> list[Entity]:
    all_entities = []

    for chapter in chapters:
        c_entities = []
        ners = ner(chapter)
        # print(ners)
        corefs = coreference_resolution(chapter)

        # map the loction -> (text, label)
        ner_positions = {(start, end): (text, label) for text, label, start, end in ners}

        # build the interval tree for NER positions
        ner_tree = IntervalTree()
        for text, label, start, end in ners:
            interval = Interval(start, end)
            ner_tree.insert(interval)

        # map cluster id -> list of coreference -label
        clusters = {}

        for cluster_id, (mentions_texts, mentions_offsets) in enumerate(corefs):
            cluster_mentions = []
            labels = []

            for text, (start_char, end_char) in zip(mentions_texts, mentions_offsets):
                cluster_mentions.append(text)
                interval = Interval(start_char, end_char)
                # search in tree - return dict or None

                overlap_result = ner_tree.overlapSearch(interval)

                if overlap_result is None:
                    continue

                # extract the label from the first overlap
                overlap_interval = overlap_result['interval']
                overlap_start = overlap_interval.low
                overlap_end = overlap_interval.high

                if (overlap_start, overlap_end) in ner_positions:
                    ner_text, ner_label = ner_positions[(overlap_start, overlap_end)]
                    labels.append(ner_label)

            print(labels)
            label = Counter(labels).most_common(1)[0][0] if labels else "UNKNOWN"
            name = cluster_mentions[0]
            nicknames = list(cluster_mentions[1:])
            coref_positions = [(start, end) for (_, (start, end)) in zip(mentions_texts, mentions_offsets)]

            entity = Entity(name, label, nicknames, coref_positions)
            c_entities.append(entity)

        # description extraction
        descriptions = description_extraction(chapter, c_entities)
        print(descriptions)

        for ent, description in descriptions.items():
            c = get_ent_by_nickname(ent, c_entities)
            if c is not None:
                # if description id python dict, assign it directly
                if isinstance(description, dict):
                    c.description = description
                else:
                    # else try to parse it as JSON
                    try:
                        c.description = json.loads(description)
                    except (json.JSONDecodeError, TypeError) as e:
                        print(f"Warning: Could not parse description for {ent}: {e}")
                        c.description = {}

        all_entities.extend(c_entities)

        del ner_tree

    # add gender to entities description
    for entity in all_entities:
        if entity.label == "PERSON":
            ismale = is_male(entity)
            if isinstance(entity.description, dict):
                entity.description["gender"] = "male" if ismale else "female"
            else:
                # If description is still not a dict, initialize it properly
                entity.description = {"gender": "male" if ismale else "female"}
    return all_entities


def ner(chapter):
    """Extract named entities from a chapter using spaCy"""
    doc = nlp(chapter)
    entities = [(ent.text, ent.label_, ent.start_char, ent.end_char) for ent in doc.ents]
    return entities

def coreference_resolution(chapter: str):
    """Resolve coreferences in a chapter using Maverick"""
    result = coref_model.predict(chapter)
    print(result["clusters_char_offsets"])
    offsets = []
    for i in range(len(result["clusters_char_offsets"])):
        offsets.append([])
        for s, e in result["clusters_char_offsets"][i]:
            offsets[i].append((s, e + 1))

    chapter_chars = zip(result["clusters_token_text"], offsets)
    return chapter_chars

def description_extraction(chapter: str, characters: list[Entity]):
    """Extract character descriptions from a chapter using Google Gemini API"""
    descriptions = api_to_gemini(chapter, characters)
    return descriptions

# TODO:  להתאים שיהיה עבור כל הטקסט כך שישלח לטקסטרנק ושם יבדקו הטווחים
def count_verbs_in_paragraph(paragraph: str) -> dict:
    """Count different types of verbs in a paragraph"""
    doc = nlp(paragraph)

    verb_counts = {
        'total_verbs': 0,
        'action_verbs': 0,  # פעלי פעולה
        'auxiliary_verbs': 0,  # פעלי עזר
        'past_verbs': 0,  # פעלים בעבר
        'present_verbs': 0  # פעלים בהווה
    }

    for token in doc:
        if token.pos_ == 'VERB':
            verb_counts['total_verbs'] += 1

            # פעלי פעולה (לא פעלי עזר)
            if token.lemma_ not in ['be', 'have', 'do', 'will', 'would', 'can', 'could', 'may', 'might', 'must',
                                    'shall', 'should']:
                verb_counts['action_verbs'] += 1

            # זיהוי זמן הפעל
            if token.tag_ in ['VBD', 'VBN']:  # עבר
                verb_counts['past_verbs'] += 1
            elif token.tag_ in ['VBP', 'VBZ', 'VBG']:  # הווה
                verb_counts['present_verbs'] += 1

        elif token.pos_ == 'AUX':
            verb_counts['auxiliary_verbs'] += 1

    return verb_counts


def get_ent_by_nickname(nickname: str, entities: list[Entity]) -> Entity:
    """Get an entity by its nickname from a list of entities"""
    for entity in entities:
        for nName in entity.nicknames:
            if nName == nickname:
                return entity
    return None

def get_place_and_time(entities: Entity) -> (List[int],List[int]):
    """Find place and time in a paragraph using spaCy"""
    place = []
    time = []

    for index, ent in enumerate(entities):
        if ent.label in config["services"]["ner"]["place"]:
            place.append(index)
        elif ent.label in config["services"]["ner"]["time"]:
            time.append(index)

    return place, time

