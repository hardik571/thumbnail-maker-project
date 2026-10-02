#setting of python
import os 
from dotenv import load_dotenv
load_dotenv()#it work as reader to read the environment variables of the .env file
GEMINI_API_KEY=os.getenv("GEMINI_API_KEY")
IMAGEKIT_PRIVATE_KEY=os.getenv("IMAGEKIT_PRIVATE_KEY")
IMAGEKIT_PUBLIC_KEY=os.getenv("IMAGEKIT_PUBLIC_KEY")
IMAGEKIT_URL_ENDPOINT=os.getenv("IMAGEKIT_URL_ENDPOINT")
DATABASE_URL="sqlite:///./thumbnailbuilder.db"