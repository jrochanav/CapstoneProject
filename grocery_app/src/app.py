import streamlit as st
import requests
import base64
import numpy as np
from PIL import Image
import io

# Gemini API Configuration
API_KEY = "AIzaSyCfpV-W8HOZ61pAj8shqcuYI_yQcNxphVo"
URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={API_KEY}"

def process_image_with_gemini(image, prompt="What is the name of this object? Give a short answer inside {}"):
    # Convert PIL Image to base64
    buffered = io.BytesIO()
    image.save(buffered, format="JPEG")
    img_str = base64.b64encode(buffered.getvalue()).decode('utf-8')
    
    payload = {
        "contents": [{
            "parts": [
                {"text": prompt},
                {"inlineData": {
                    "mimeType": "image/jpeg",
                    "data": img_str
                }}
            ]
        }]
    }
    
    try:
        response = requests.post(URL, json=payload)
        response_json = response.json()
        
        # Extract text response
        if 'candidates' in response_json and response_json['candidates']:
            text_response = response_json['candidates'][0]['content']['parts'][0]['text']
            return text_response
        else:
            st.error("Unable to get response from the API")
            return None
    except Exception as e:
        st.error(f"API call error: {e}")
        return None

def extract_food_name(response_text):
    """ Extract the food name from the AI-generated response """
    if not response_text:
        return None
    
    start, end = response_text.find("{"), response_text.find("}")
    return response_text[start+1:end].strip() if start != -1 and end != -1 else None

# Initialize session state for grocery list if not already present
if "grocery_list" not in st.session_state:
    st.session_state.grocery_list = []

st.title("Grocery Image Recognizer")

uploaded_file = st.file_uploader("Upload an image of a grocery item", type=["jpg", "png", "jpeg"])

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, caption="Uploaded Image", use_column_width=True)

    st.write("Identifying...")
    response_text = process_image_with_gemini(image)
    food_name = extract_food_name(response_text)

    if food_name:
        # User input fields to modify name, add description, and quantity
        new_name = st.text_input("Item Name", value=food_name)
        description = st.text_area("Description (Optional)", "")
        quantity = st.number_input("Quantity", min_value=1, value=1, step=1)

        if st.button("Add to List"):
            item = {"name": new_name, "description": description, "quantity": quantity}
            st.session_state.grocery_list.append(item)
            st.success(f"Added {new_name} to the list!")
    else:
        st.error("Could not identify the grocery item. Try another image.")

# Display the updated grocery list
st.write("### Current Grocery List:")
for item in st.session_state.grocery_list:
    st.write(f"- **{item['name']}** (x{item['quantity']}) - {item['description']}")

# Add a clear list button
if st.button("Clear List"):
    st.session_state.grocery_list = []
    st.success("Grocery list cleared!")
