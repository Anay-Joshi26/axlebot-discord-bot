import firebase_admin
from firebase_admin import credentials, firestore_async, firestore

def initialize_firebase(SERVICE_ACCOUNT_PATH: str):
    if not firebase_admin._apps:
        cred = credentials.Certificate(SERVICE_ACCOUNT_PATH)
        firebase_admin.initialize_app(cred)
    return firestore_async.client(), firestore.client() # async and sync clients
