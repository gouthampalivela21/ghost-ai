import firebase_admin
from firebase_admin import credentials, firestore
import os

# Prevent double initialization
if not firebase_admin._apps:
    cred = credentials.Certificate(os.getenv("SERVICE_ACCOUNT"))
    firebase_admin.initialize_app(cred)

db = firestore.client()