
import json
import pypdf
from pprint import pprint
import requests

from google import genai
from google.genai import types

from config import GEMINI_API_KEY, CATEGORIES, TOKEN, API_BASE_URL
from file_uploader import FigshareUploader
import os


def get_json_output(text):
    if text.startswith("```"):
        text = text.replace("```json\n", "").replace("```", "")

    ai_data = json.loads(text)
    pprint(ai_data)
    article_data = {
        "title": ai_data["title"][0],
        "description": ai_data["description"],
        "is_metadata_record": False,
        "tags": ai_data["tags"],
        "categories": [int(cat["id"]) for cat in ai_data["categories"]], 
        "authors": [{"name": author} for author in ai_data["authors"]],
        "defined_type": "dataset",
    }

    return article_data


def extract_text_from_pdf(pdf_path):
    if not os.path.isfile(pdf_path):
        raise ValueError("The provided path does not exist or is not a file.")
    if not pdf_path.lower().endswith(".pdf"):
        raise ValueError("The provided file is not a PDF.")

    text = ""
    with open(pdf_path, "rb") as fd:
        reader = pypdf.PdfReader(fd)
        for page in reader.pages:
            text += page.extract_text()
    clean_text = " ".join(text.split())

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
    - "description" should be a string representing a brief summary of the text. If possible, add a longer description.
    - "authors" should be an array of strings representing the authors of the text if you can find any, if not return an empty array. Authors are usually set at the beginning of the text.
    - "tags" should be an array of strings representing relevant keywords or labels for the text. Add a maximum of 7 tags.
    - "license" should be a string representing the license of the text if you can find any, if not return an empty string.
    - "categories" should be an array of JSON objects. Each object must have "id" (string) and "title" (string) fields representing category IDs and titles.
    - Ensure the returned JSON is always valid and adheres strictly to the specified structure.
    - If no tags or categories are found, return empty arrays for those fields.
    - Do not include any additional text or explanations outside the JSON object.
    - Categories are listed below: 
""" + json.dumps(CATEGORIES)


def create_article(article_data):
    endpoint = f"{API_BASE_URL}/account/articles?access_token={TOKEN}"
    try:
        response = requests.post(endpoint, data=json.dumps(article_data))
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as error:
        print(f"Caught an HTTPError: {error}")
        print(f"Body:\n{response.content.decode()}")
        return None
    except requests.exceptions.RequestException as error:
        print(f"Caught a RequestException: {error}")
        return None
    

if __name__ == "__main__":
    client = genai.Client(api_key=GEMINI_API_KEY)
    chat = client.chats.create(model="gemini-2.0-flash", config=types.GenerateContentConfig(system_instruction=SYSTEM_INSTRUCTION))

    pdf_path = "/Users/corneliu/Downloads/" + input("Enter the PDF file name from downloads folder (eg: em5c00054_si_002.pdf): ")
    text = extract_text_from_pdf(pdf_path)
    response = chat.send_message(text)
    article_data = get_json_output(response.text)

    creation_response = create_article(article_data)
    print("\nArticle created successfully!")
    article_id = creation_response["location"].split("/")[-1]
    print(f"\nhttps://figsh.com/account/articles/{article_id}")
    print(f"\nhttps://api.figsh.com/v2/account/articles/{article_id}?access_token={TOKEN}")

    uploader = FigshareUploader(TOKEN)
    uploader.upload_file(article_id, pdf_path)
    