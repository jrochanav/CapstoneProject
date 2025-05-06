import streamlit as st
from uuid import uuid4
from database import get_user, save_user, set_preferences

def get_user_id():
    # Input field for user ID
    user_id_input = st.text_input("Enter your User ID:")

    user_id = None
    # Button to generate new User ID
    if st.button("Get new User ID"):
        user_id = str(uuid4())
        st.success(f"Generated new User ID: {user_id}")
        st.info("Please copy and save this ID for future use.")

    # Button to continue with provided ID
    elif st.button("Continue"):
        if user_id_input:
            user_id = user_id_input
            st.success(f"Logged in as: {user_id}")
        else:
            st.warning("Please enter a valid User ID.")

    return user_id  # Will return None if neither button clicked

def load_user(user_id):
    user_doc = get_user(user_id)
    if user_doc is None:
        user_doc = {
            "user_id": user_id,
            "preferences": {},
            "grocery_list": []
        }
        save_user(user_doc)
    return user_doc

def save_user_preferences(user_id, preferences):
    set_preferences(user_id, preferences)

def load_grocery_list(user_id):
    user_doc = get_user(user_id)
    return user_doc.get("grocery_list", []) if user_doc else []

def save_grocery_list(user_id, grocery_list):
    # Fetch existing user
    user_doc = get_user(user_id)
    if not user_doc:
        user_doc = {"user_id": user_id, "preferences": {}, "grocery_list": grocery_list}
    else:
        user_doc["grocery_list"] = grocery_list

    save_user(user_doc)

