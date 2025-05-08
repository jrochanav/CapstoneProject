from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()  # load .env file

MONGO_URI = os.getenv("MONGO_SERVER")
client = MongoClient(MONGO_URI)

# Get database and collections
db = client["grocery_app"]
users = db["users"]
grocery_list = db["grocery_list"]

def get_user(user_id):
    return users.find_one({"user_id": user_id})

def save_user(user_data):
    users.update_one(
        {"user_id": user_data["user_id"]},
        {"$setOnInsert": {"user_id": user_data["user_id"]},
         "$set": {
             "preferences": user_data.get("preferences", {}),
             "grocery_list": user_data.get("grocery_list", [])
         }},
        upsert=True
    )

def set_preferences(user_id, preferences):
    users.update_one(
        {"user_id": user_id},
        {"$set": {"preferences": preferences}},
        upsert=True
    )

def add_grocery_list(user_id, grocery_list):
    users.update_one(
        {"user_id": user_id},
        {"$push": {"grocery_list": grocery_list}}
    )
