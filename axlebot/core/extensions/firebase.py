from core.init_firebase import initialize_firebase
from core.firebase import FirebaseClient
from dotenv import load_dotenv, find_dotenv
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(find_dotenv())
SERVICE_ACCOUNT_PATH = os.getenv("FIREBASE_ACCOUNT_KEY_PATH")


async_db, sync_db = initialize_firebase(SERVICE_ACCOUNT_PATH)
fbc = FirebaseClient(async_db)
#fbc_sync = FirebaseClientSync(sync_db)