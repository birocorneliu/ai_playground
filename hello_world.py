import json
import pypdf
from pprint import pprint

from google import genai
from google.genai import types

from config import GEMINI_API_KEY, CATEGORIES
import os


def get_json_output(text):
    if text.startswith("```"):
        text = text.replace("```json\n", "").replace("```", "")

    return json.loads(text)


def extract_text_from_pdf(pdf_path):
    if not os.path.isfile(pdf_path):
        raise ValueError("The provided path does not exist or is not a file.")
    if not pdf_path.lower().endswith('.pdf'):
        raise ValueError("The provided file is not a PDF.")

    text = ""
    with open(pdf_path, "rb") as fd:
        reader = pypdf.PdfReader(fd)
        for page in reader.pages:
            text += page.extract_text()
    clean_text = ' '.join(text.split())

    return clean_text




SYSTEM_INSTRUCTION = """
    You are an expert that can classify text into categories and tags/keywords and can extract the title and description of the text. 
    Expected output
        {
        "title": ["text_title1", "title2", ...],
        "description": "text_description",
        "tags": ["tag1", "tag2", "tag3", ...],
        "authors": ["author1", "author2", "author3", ...],
        "license": "license",
        "categories": [
            {"id": "id1", "title": "category_title1"},
            {"id": "id2", "title": "category_title2"},
            ...
            ]
        }
    - "title" should be a list of strings representing the title(essence) of the text. Provide ~3 title suggestions if possible.
    - "description" should be a string representing a brief summary of the text.
    - "authors" should be an array of strings representing the authors of the text if you can find any, if not return an empty array. Authors are usually set at the beginning of the text.
    - "tags" should be an array of strings representing relevant keywords or labels for the text. Add a maximum of 7 tags.
    - "license" should be a string representing the license of the text if you can find any, if not return an empty string.
    - "categories" should be an array of JSON objects. Each object must have "id" (string) and "title" (string) fields representing category IDs and titles.
    - Ensure the returned JSON is always valid and adheres strictly to the specified structure.
    - If no tags or categories are found, return empty arrays for those fields.
    - Do not include any additional text or explanations outside the JSON object.
    - Categories are listed below: 
""" + json.dumps(CATEGORIES)

client = genai.Client(api_key=GEMINI_API_KEY)
chat = client.chats.create(model="gemini-2.0-flash", config=types.GenerateContentConfig(system_instruction=SYSTEM_INSTRUCTION))

while True:
    pdf_path = "/Users/corneliu/Downloads/" + input("Enter the PDF file name from downloads folder (eg: om4c00469_si_001.pdf): ")
    text = extract_text_from_pdf(pdf_path)
    response = chat.send_message(text)
    pprint(get_json_output(response.text))
