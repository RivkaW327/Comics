#TODO לבדוק איפה לבצע את זיהוי התיאורים של הדמויות. בדמויות בפרקים או בסצינות עצמן (אחרי שמזהים סצינות)
# import os
# import certifi
# import ssl
# import google.generativeai as genai

from FastAPIProject.config.config_loader import config
import json
from Services.entity import Entity

from google import genai


def api_to_gemini(passage: str, characters: list[Entity]): # -> dict:
    charsWithNicks = [f"{i}. {char.name} whose nicknames is: {char.nicknames}" for i, char in enumerate(characters)]
    prompt = f"""
    Given the following passage, for each of the following characters extract the appearance. If there is no appearance description - do not mention the character. The output will be in JSON format (For example: {{"main name of character like 'Ms. goldman'": {{"feature": "feature description", "feature": "feature description"}}, "main name of additional character like 'Avi Cohen'": {{"feature": "feature description"}}}} etc.):
    The passage:
    {passage}
    The characters:
    {charsWithNicks}
    """

    client = genai.Client(api_key=config["services"]["google_gemini"]["api_key"])

    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=[prompt]
    )
    # gemini_model = genai.GenerativeModel('gemini-2.0-flash')
    # response = gemini_model.generate_content(prompt)
    text = response.candidates[0].content.parts[0].text
    parsed_json = json.loads(text.strip('```json\n'))

    return parsed_json

# print(api_to_gemini("",[]))

# import contextlib
#
# @contextlib.contextmanager
# def temporary_ssl_env():
#     old_env = {
#         "SSL_CERT_FILE": os.environ.get("SSL_CERT_FILE"),
#         "REQUESTS_CA_BUNDLE": os.environ.get("REQUESTS_CA_BUNDLE"),
#         "GRPC_DEFAULT_SSL_ROOTS_FILE_PATH": os.environ.get("GRPC_DEFAULT_SSL_ROOTS_FILE_PATH"),
#     }
#     cert_path = certifi.where()
#     os.environ["SSL_CERT_FILE"] = cert_path
#     os.environ["REQUESTS_CA_BUNDLE"] = cert_path
#     os.environ["GRPC_DEFAULT_SSL_ROOTS_FILE_PATH"] = cert_path
#     try:
#         yield
#     finally:
#         for key, val in old_env.items():
#             if val is not None:
#                 os.environ[key] = val
#             else:
#                 os.environ.pop(key, None)

# # הגדרת נתיב לתעודות SSL מותקנות
# os.environ['SSL_CERT_FILE'] = certifi.where()
# os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()
# os.environ['GRPC_DEFAULT_SSL_ROOTS_FILE_PATH'] = certifi.where()
#
# # הגדרת הקשר SSL המוגדר עם התעודות הנכונות
# ssl_context = ssl.create_default_context(cafile=certifi.where())
#
#
# def api_to_gemini(passage: str, characters: list[Character]) -> dict:
#     charsWithNicks = [f"{i}. {char.name} whose nicknames is: {char.nicknames}" for i, char in enumerate(characters)]
#     prompt = f"""
#     Given the following passage, for each of the following characters extract the appearance. If there is no appearance description - do not mention the character. The output will be in Jason format:
#     The passage:
#     {passage}
#     The characters:
#     {charsWithNicks}
#     """
#     genai.configure(api_key=config["services"]["google_gemini"]["api_key"])
#     gemini_model = genai.GenerativeModel('gemini-2.0-flash')
#     response = gemini_model.generate_content(prompt)
#     return json.loads(response.text)
