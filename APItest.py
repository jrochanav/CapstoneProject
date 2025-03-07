import streamlit as st
import os
import numpy as np
import requests
import base64
from PIL import Image

API_KEY = "AIzaSyCfpV-W8HOZ61pAj8shqcuYI_yQcNxphVo"
API_URL = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={API_KEY}"

def get_gemini_response(image_path, text_prompt="What is the name of this object? Give a short answer inside {}"):
    """ Process an image and generate a text response using the Google API directly. """
    
    with open(image_path, "rb") as image_file:
        encoded_image = base64.b64encode(image_file.read()).decode("utf-8")
    
    payload = {
        "contents": [
            {"parts": [{"text": text_prompt}]},
            {"parts": [{"inlineData": {"mimeType": "image/jpeg", "data": encoded_image}}]}
        ]
    }
    
    response = requests.post(API_URL, json=payload)
    response_data = response.json()
    
    if "candidates" in response_data and response_data["candidates"]:
        return response_data["candidates"][0]["content"]["parts"][0]["text"]
    return None

def extract_food_name(response_text):
    """ Extract the food name from the AI-generated response """
    start, end = response_text.find("{"), response_text.find("}")
    return response_text[start+1:end].strip() if start != -1 and end != -1 else None

def generate_grocery_recommendation(prompt, grocery_list):
    """ Generate a grocery recommendation using AI """
    full_prompt = f"User's current grocery list: {', '.join(grocery_list)}. {prompt}. Suggest improvements for a healthier and more complete grocery run."
    payload = {"contents": [{"parts": [{"text": full_prompt}]}]}
    response = requests.post(API_URL, json=payload).json()
    return response["candidates"][0]["content"]["parts"][0]["text"] if "candidates" in response else None

def generate_recipe(prompt, grocery_list):
    """ Generate a recipe using only items in the grocery list """
    if not grocery_list:
        return "Not enough ingredients."
    
    full_prompt = f"User's grocery list: {', '.join(grocery_list)}. {prompt}. Create a recipe using only these ingredients."
    payload = {"contents": [{"parts": [{"text": full_prompt}]}]}
    response = requests.post(API_URL, json=payload).json()
    return response["candidates"][0]["content"]["parts"][0]["text"] if "candidates" in response else None

# Initialize session state for grocery list and welcome popup
if "grocery_list" not in st.session_state:
    st.session_state.grocery_list = []
if "show_welcome" not in st.session_state:
    st.session_state.show_welcome = True
if "input_mode" not in st.session_state:
    st.session_state.input_mode = None

# Welcome popup
if st.session_state.show_welcome:
    st.markdown("""
        ## Welcome to Grocery Image Recognizer! 🛒
        Our mission is to help you effortlessly track and manage your groceries. 
        Simply upload a photo of your grocery items or manually input them, and we'll take care of the rest!
    """)
    
    if st.button("Continue"):
        st.session_state.show_welcome = False
        st.rerun()
else:
    st.title("Grocery Image Recognizer")
    
    st.markdown("""
        <style>
        .button-container {
            display: flex;
            justify-content: center;
            gap: 20px;
        }
        .big-button {
            width: 200px;
            height: 200px;
            font-size: 20px !important;
            text-align: center;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 10px;
        }
        </style>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📸\n**Upload a Photo**", key="upload_btn", help="Upload an image of your groceries"):
            st.session_state.input_mode = "upload"
    with col2:
        if st.button("✍️\n**Input Manually**", key="manual_btn", help="Manually enter grocery details"):
            st.session_state.input_mode = "manual"
    
    if st.session_state.input_mode == "upload":
        uploaded_files = st.file_uploader("Upload images of grocery items", type=["jpg", "png", "jpeg"], accept_multiple_files=True)
        
        if uploaded_files:
            for uploaded_file in uploaded_files:
                image = Image.open(uploaded_file)
                st.image(image, caption=f"Uploaded Image: {uploaded_file.name}", use_container_width=True)
                
                response_text = process_text_image(image)
                food_name = extract_food_name(response_text)
                
                if food_name:
                    new_name = st.text_input(f"Item Name for {uploaded_file.name}", value=food_name, key=f"name_{uploaded_file.name}")
                    description = st.text_area(f"Description (Optional) for {uploaded_file.name}", "", key=f"desc_{uploaded_file.name}")
                    quantity = st.number_input(f"Quantity for {uploaded_file.name}", min_value=1, value=1, step=1, key=f"qty_{uploaded_file.name}")
                    
                    if st.button(f"Add", key=f"btn_{uploaded_file.name}"):
                        item = {"name": new_name, "description": description, "quantity": quantity}
                        st.session_state.grocery_list.append(item)
                        st.session_state.input_mode = None  # Hide input section after adding
                        st.success(f"Added {new_name} to the list!")
                        st.rerun()
                else:
                    st.error(f"Could not identify the grocery item in {uploaded_file.name}. Try another image.")
    
    elif st.session_state.input_mode == "manual":
        st.write("### Manually Add an Item")
        manual_name = st.text_input("Item Name", key="manual_name")
        manual_description = st.text_area("Description (Optional)", "", key="manual_desc")
        manual_quantity = st.number_input("Quantity", min_value=1, value=1, step=1, key="manual_qty")
        
        if st.button("Add Item"):
            if manual_name:
                st.session_state.grocery_list.append({"name": manual_name, "description": manual_description, "quantity": manual_quantity})
                st.session_state.input_mode = None  # Hide input section after adding
                st.success(f"Added {manual_name} to the list!")
                st.rerun()
            else:
                st.error("Please provide a name for the item.")
    # Display the grocery list
    st.write("### Current Grocery List:")
    for i, item in enumerate(st.session_state.grocery_list):
        with st.expander(f"{item['name']} (x{item['quantity']})"):
            edited_name = st.text_input("Edit Name", value=item["name"], key=f"edit_name_{i}")
            edited_description = st.text_area("Edit Description", value=item["description"], key=f"edit_desc_{i}")
            edited_quantity = st.number_input("Edit Quantity", min_value=1, value=item["quantity"], step=1, key=f"edit_qty_{i}")
            
            if st.button("Save Changes", key=f"save_{i}"):
                st.session_state.grocery_list[i] = {"name": edited_name, "description": edited_description, "quantity": edited_quantity}
                st.success("Item updated!")
            
            if st.button("Delete Item", key=f"delete_{i}"):
                del st.session_state.grocery_list[i]
                st.success("Item removed!")
                st.rerun()
    # AI Recommendation Section
    st.write("## AI Recommendation")
    col1, col2 = st.columns(2)
    with col1:
        grocery_prompt = st.text_area("Enter a prompt for grocery improvement (optional)")
        if st.button("🛒 Future Grocery Run Recommendation"):
            recommendation = generate_grocery_recommendation(grocery_prompt, [item["name"] for item in st.session_state.grocery_list])
            st.write(recommendation)
    with col2:
        recipe_prompt = st.text_area("Enter a prompt for recipe generation (optional)")
        if st.button("🍽️ Generate Recipe"):
            recipe = generate_recipe(recipe_prompt, [item["name"] for item in st.session_state.grocery_list])
            st.write(recipe)
