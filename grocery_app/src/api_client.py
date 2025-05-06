import os
import requests
import base64
from dotenv import load_dotenv
from database import get_user

load_dotenv()

API_KEY = os.getenv('API_KEY')
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

def get_nutritional_info(food_name):
    """Use Gemini 1.5 to generate nutritional facts for a given food item."""

    prompt = f"""
    Provide the nutritional information for {food_name}.
    Format it in this structured way:

    Calories: X kcal
    Total_fat: X g
    Protein: X g
    Carbohydrate: X g
    Sugars: X g
    Fiber: X g
    Sodium: X mg

    Keep the response short and in this format only.
    """

    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    response = requests.post(API_URL, json=payload).json()

    if "candidates" in response and response["candidates"]:
        raw_text = response["candidates"][0]["content"]["parts"][0]["text"].strip()

        # Extract using regex
        import re
        nutrition_data = {}
        matches = re.findall(r"([\w\s]+):\s*([\d.]+)\s*(\w+)", raw_text)

        for nutrient, value, unit in matches:
            formatted_key = nutrient.strip().lower().replace(" ", "_")
            nutrition_data[formatted_key] = f"{value} {unit}"

        return food_name, nutrition_data

    return food_name, {}

def generate_dish_ingredients_or_recipes(user_id, dish_or_ingredients, mode="dish_to_ingredients"):
    """
    Generate either:
    1. Required ingredients for a specified dish (dish_to_ingredients mode)
    2. Possible recipes and missing ingredients based on available ingredients (ingredients_to_recipes mode)
    
    Args:
        dish_or_ingredients (str): Either a dish name or a comma-separated list of ingredients
        mode (str): "dish_to_ingredients" or "ingredients_to_recipes"
    
    Returns:
        str: AI-generated response with ingredients or recipe suggestions
    """
    # Get user preferences 
    user_doc = get_user(user_id)
    user_info = user_doc.get("preferences", {}) if user_doc else {}
    
    # Build a personalized AI prompt
    if mode == "dish_to_ingredients":
        full_prompt = f"""
        User Information:
        - Dietary Preference: {user_info.get('dietary_preference', 'None')}
        - Food Allergies: {', '.join(user_info.get('food_allergies', [])) or 'None'}
        - Disliked Foods: {user_info.get('disliked_foods', 'None')}
        - Health Conditions: {', '.join(user_info.get('health_conditions', [])) or 'None'}
        - Health Goal: {user_info.get('health_goal', 'Not specified')}

        The user wants to cook: {dish_or_ingredients}

        **Instructions for AI:**
        - Provide a comprehensive list of ingredients needed to make this dish
        - Include quantities when possible
        - Suggest alternatives for ingredients that conflict with user's dietary preferences or allergies
        - Organize ingredients by category (produce, proteins, pantry items, etc.)
        - Mention any optional ingredients that could enhance the dish
        - Keep the response concise and actionable
        """
    else:  # ingredients_to_recipes mode
        ingredients_list = [ingredient.strip() for ingredient in dish_or_ingredients.split(',')]
        ingredients_text = ', '.join(ingredients_list)
        
        full_prompt = f"""
        User Information:
        - Dietary Preference: {user_info.get('dietary_preference', 'None')}
        - Food Allergies: {', '.join(user_info.get('food_allergies', [])) or 'None'}
        - Disliked Foods: {user_info.get('disliked_foods', 'None')}
        - Health Conditions: {', '.join(user_info.get('health_conditions', [])) or 'None'}
        - Health Goal: {user_info.get('health_goal', 'Not specified')}

        Available Ingredients: {ingredients_text}

        **Instructions for AI:**
        - Suggest 2-3 recipes that can be made with these ingredients, possibly with a few additional items
        - For each recipe, list the ingredients the user already has and what they still need to purchase
        - Ensure recipes align with user's dietary preferences and avoid allergens
        - Keep recipes practical and relatively simple
        - Focus on healthy options that align with their health goals when possible
        - Format the response clearly with recipe names as headers, followed by Already Have and Need to Buy sections
        """

    # Request AI-generated response
    payload = {"contents": [{"parts": [{"text": full_prompt}]}]}
    response = requests.post(API_URL, json=payload).json()

    return response.get('text', "No information generated.")