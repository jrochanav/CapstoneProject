import os
from dotenv import load_dotenv
import pymongo

load_dotenv()
mongo_uri=os.getenv("MONGO_URI")

def get_db():
    client = pymongo.MongoClient("")
    db = client['grocery_app']
    return db

def insert_grocery_item(item):
    db = get_db()
    grocery_collection = db['groceries']
    grocery_collection.insert_one(item)

def get_all_grocery_items():
    db = get_db()
    grocery_collection = db['grocery_items']
    items = grocery_collection.find()
    return list(items)