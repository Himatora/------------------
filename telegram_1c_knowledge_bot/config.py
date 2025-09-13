import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
KNOWLEDGE_PATH = "knowledge_base/"
TEXTS_PATH = os.path.join(KNOWLEDGE_PATH, "texts")
IMAGES_PATH = os.path.join(KNOWLEDGE_PATH, "images")
FILES_PATH = os.path.join(KNOWLEDGE_PATH, "files")
MATERIALS_FILE = os.path.join(KNOWLEDGE_PATH, "materials.json")