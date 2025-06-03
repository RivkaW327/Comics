import json
from FastAPIProject.config.config_loader import config
from FastAPIProject.Models.domain.entity import Entity
from google import genai


def api_to_gemini(passage: str, characters: list[Entity]) -> dict[str, dict[str, str]]:
    charsWithNicks = [
        f"{i}. {char.name} whose nicknames is: {char.nicknames}"
        for i, char in enumerate(characters)
    ]

    prompt = f"""
    Given the following passage, for each of the following characters extract the appearance. 
    If there is no appearance description - do not mention the character. 
    The output must be in JSON format (example: {{
        "Ms. Goldman": {{"hair": "curly", "height": "tall"}},
        "Avi Cohen": {{"eyes": "blue"}}
    }}):

    The passage:
    {passage}

    The characters:
    {charsWithNicks}
    """

    try:
        client = genai.Client(api_key=config["services"]["google_gemini"]["api_key"])

        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[prompt]
        )

        text = response.candidates[0].content.parts[0].text.strip()
        if not text:
            print("Gemini returned empty response")
            return {}

        # ניקוי תגיות קוד אם קיימות
        if text.startswith("```json"):
            text = text.strip("```json").strip("```").strip()

        parsed_json = json.loads(text)

        if not isinstance(parsed_json, dict):
            print(f"Gemini returned non-dict JSON: {parsed_json}")
            return {}

        # בדיקה שהערכים הם גם dict
        for k, v in parsed_json.items():
            if not isinstance(v, dict):
                print(f"Invalid value for key '{k}': Expected dict, got {type(v)}")
                return {}

        return parsed_json

    except json.JSONDecodeError as e:
        print(f"JSON Decode Error: {e}")
        print(f"Response text: {text}")
        return {}

    except Exception as e:
        print(f"Gemini ServerError: {e}")
        return {}
