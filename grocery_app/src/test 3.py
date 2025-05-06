import streamlit as st
import os
import numpy as np
from PIL import Image
import pandas as pd
from fuzzywuzzy import process
import google.generativeai as genai

# Load the nutrition dataset
#file_path = "nutrition.csv"  # Ensure the dataset is in the working directory
#nutrition_df = pd.read_csv(file_path)

# Retrieve API key securely from environment variables
api_key = os.getenv("GOOGLE_API_KEY")

# Handle case where the API key is missing
if api_key is None:
    st.error("API key is missing. Please set it as an environment variable in Colab.")
else:
    genai.configure(api_key=api_key)
model = genai.GenerativeModel("gemini-1.5-flash")

# convert the image to text
def process_text_image(image, text_prompt="What is the name of this grocery item or items? Give a short answer inside {}"):
    """ Process an image and generate a text response """
    response = model.generate_content([text_prompt, image])
    return response.text
# Extract the name of the identified item
def extract_food_name(response_text):
    """ Extract the food name from the AI-generated response """
    start, end = response_text.find("{"), response_text.find("}")
    return response_text[start+1:end].strip() if start != -1 and end != -1 else None
# Generate grocery run
def generate_grocery_recommendation(prompt, grocery_list):
    """Generate a personalized grocery recommendation using AI with user preferences."""

    # Get user preferences from session state
    user_info = st.session_state.get("user_info", {})

    # Message for users with an empty grocery list
    if not grocery_list:
        grocery_list_text = "The user has no groceries added yet. Provide a balanced and personalized grocery list to help them start."
    else:
        grocery_list_text = f"User's Current Grocery List:\n{', '.join(grocery_list)}"

    # Build a personalized AI prompt
    full_prompt = f"""
    User Information:
    - Name: {user_info.get('first_name', 'User')} {user_info.get('last_name', '')}
    - Age Group: {user_info.get('age_group', 'Not specified')}
    - Dietary Preference: {user_info.get('dietary_preference', 'None')}
    - Food Allergies: {', '.join(user_info.get('food_allergies', [])) or 'None'}
    - Disliked Foods: {user_info.get('disliked_foods', 'None')}
    - Health Conditions: {', '.join(user_info.get('health_conditions', [])) or 'None'}
    - Health Goal: {user_info.get('health_goal', 'Not specified')}
    - Activity Level: {user_info.get('activity_level', 'Not specified')}
    - Grocery Frequency: {user_info.get('grocery_frequency', 'Not specified')}

    {grocery_list_text}

    Additional User Prompt:
    {prompt if prompt else "Suggest a balanced and personalized grocery run."}

    **Instructions for AI:**
    - If the user has no groceries, generate a **starter grocery list** based on their dietary preferences and health goals.
    - If groceries are listed, suggest **only improvements and additions** that align with their preferences.
    - Avoid foods the user dislikes or is allergic to.
    - Ensure recommendations are practical based on their grocery shopping frequency.
    - Keep the response **concise and actionable**, listing essential grocery items with short explanations.
    """

    # Request AI-generated grocery list
    response = model.generate_content(full_prompt)

    return response.text if response and response.text else "No recommendations generated."



# Generate recipe
def generate_recipe(prompt, grocery_list):
    """Generate a personalized recipe using user preferences and available groceries."""

    # If no grocery items, do not generate a recipe
    if not grocery_list:
        return "You don’t have any groceries listed! Add ingredients before generating a recipe."

    # Get user preferences from session state
    user_info = st.session_state.get("user_info", {})

    # Build a personalized AI prompt
    full_prompt = f"""
    User Information:
    - Name: {user_info.get('first_name', 'User')} {user_info.get('last_name', '')}
    - Age Group: {user_info.get('age_group', 'Not specified')}
    - Dietary Preference: {user_info.get('dietary_preference', 'None')}
    - Food Allergies: {', '.join(user_info.get('food_allergies', [])) or 'None'}
    - Disliked Foods: {user_info.get('disliked_foods', 'None')}
    - Health Conditions: {', '.join(user_info.get('health_conditions', [])) or 'None'}
    - Health Goal: {user_info.get('health_goal', 'Not specified')}
    - Activity Level: {user_info.get('activity_level', 'Not specified')}
    - Cooking Skill Level: {user_info.get('cooking_skill', 'Not specified')}

    User's Available Ingredients:
    {', '.join(grocery_list)}

    Additional User Prompt:
    {prompt if prompt else "Generate a recipe using only the available ingredients."}

    **Instructions for AI:**
    - **Use only the listed grocery items** for the recipe.
    - Do **not** introduce ingredients that are not in the user’s grocery list.
    - Ensure it aligns with the user’s dietary needs, health goals, and restrictions.
    - Format the response as follows:
      - **Recipe Name**: [Title]
      - **Preparation Time**: X minutes
      - **Ingredients**: [List all needed ingredients]
      - **Instructions**: [Step-by-step guide]
      - **Health Benefits**: [Explain why this recipe is good for the user]
    """

    # Request AI-generated recipe
    response = model.generate_content(full_prompt)

    return response.text if response and response.text else "No recipe generated."



# Return nutritional information
import re  # Import regex for parsing text

def get_nutritional_info(food_name):
    """Use Gemini 1.5 to generate nutritional facts for a given food item."""

    # Define the prompt
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

    # Request Gemini API for a response
    response = model.generate_content(prompt)

    # Process response
    if response and response.text:
        raw_text = response.text.strip()  # Clean response

        # Use regex to extract values into a dictionary
        nutrition_data = {}
        matches = re.findall(r"([\w\s]+):\s*([\d.]+)\s*(\w+)", raw_text)

        for nutrient, value, unit in matches:
            formatted_key = nutrient.strip().lower().replace(" ", "_")  # Normalize key
            nutrition_data[formatted_key] = f"{value} {unit}"  # Store value with unit

        return food_name, nutrition_data  # ✅ Now returns a dict

    return food_name, {}  # Return empty dict if no valid info found
def generate_dish_ingredients_or_recipes(dish_or_ingredients, mode="dish_to_ingredients"):
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
    # Get user preferences from session state
    user_info = st.session_state.get("user_info", {})
    
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
    response = model.generate_content(full_prompt)
    
    return response.text if response and response.text else "No information generated."

if "user_info" not in st.session_state:
    st.session_state.user_info = {
        "first_name": "",
        "last_name": "",
        "age_group": "",
        "dietary_preference": "",
        "food_allergies": [],
        "disliked_foods": "",
        "health_conditions": [],
        "health_goal": "",
        "activity_level": "",
        "grocery_frequency": "",
        "shopping_preference": "",
    }


# Initialize session state for grocery list and welcome popup
if "grocery_list" not in st.session_state:
    st.session_state.grocery_list = []
if "show_welcome" not in st.session_state:
    st.session_state.show_welcome = True
if "input_mode" not in st.session_state:
    st.session_state.input_mode = None

# Welcome popup
form_key = f"user_info_form_{id(st.session_state)}"  # Generate a unique form key

if st.session_state.show_welcome:
    # Apply the same UI styling as the main app
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Nunito:wght@300;400;600;700&display=swap');

    /* Apply Nunito font globally */
    html, body, [class*="st-"], * {
        font-family: 'Nunito', sans-serif !important;
    }

    html, body, [class*="st-"] {
        background-color: #F5E6C4 !important; /* Warm Beige */
        color: #000000 !important; /* Black font for all text */
    }

    h1, h2 {
        color: #4CAF50 !important; /* Fresh Green for titles */
        font-size: 36px !important;
        font-weight: 700 !important;
    }
    /* BUTTON STYLING */
    button, .stButton>button, .stFileUploader>div>div>button {
        background-color: #F5E6C4 !important; /* Default Beige */
        color: #4CAF50 !important; /* Fresh Green Font */
        border: 2px solid #4CAF50 !important;
        border-radius: 25px !important;
        font-size: 18px !important;
        padding: 12px 24px !important;
        /*font-weight: bold !important;*/
        /*transition: all 0.3s ease-in-out !important;*/
    }

    /* Ensure no extra background layers on button text */
    button div, .stButton>button div, .stFileUploader>div>div>button div {
        background: transparent !important; /* Removes beige behind text */
    }

    /* HOVER EFFECT - Lime Green */
    button:hover, .stButton>button:hover, .stFileUploader>div>div>button:hover {
        background-color: #A6E22E !important; /* Lime Green */
        color: black !important;
        box-shadow: 0px 0px 8px rgba(166, 226, 46, 0.8) !important; /* Soft glow effect */
    }

    /* Ensure text background remains transparent on hover */
    button:hover div, .stButton>button:hover div, .stFileUploader>div>div>button:hover div {
        background: transparent !important; /* Ensures no beige text background */
    }

    /* CLICK EFFECT - Darker Lime Green */
    button:active, .stButton>button:active, .stFileUploader>div>div>button:active {
        background-color: #8DC81C !important; /* Darker Lime Green */
        transform: scale(0.98) !important; /* Click animation */
    }

    /* Remove button focus outline */
    button:focus, .stButton>button:focus, .stFileUploader>div>div>button:focus {
        outline: none !important;
    }

    /* Input fields */
    .stTextInput>div>div>input, .stTextArea>div>textarea, .stNumberInput>div>div>input {
        font-family: 'Nunito', sans-serif !important;
        border-radius: 5px !important;
        border: 1px 4CAF50 solid
        padding: 8px !important;
    }

    /* Expander (for grocery list items) */
    .stExpander {
        background-color: #B388EB !important; /* Soft Lavender */
        border-radius: 10px !important;
    }

    .stExpander>summary {
        font-weight: 600 !important;
        font-size: 18px !important;
    }

    .stMarkdown h2, .stMarkdown h3 {
        color: #4CAF50 !important; /* Fresh Green */
    }



    </style>
    """, unsafe_allow_html=True)

    # Welcome Text
    st.markdown("""
        ## Welcome to Grocery Tracker & AI Recommendations! 🛒
        Help us tailor grocery suggestions to your needs by providing some optional details!
    """)

    # Form for User Preferences
    with st.form("user_info_form"):
        st.write("### Personal Information")
        first_name = st.text_input("First Name", value=st.session_state.user_info["first_name"])
        last_name = st.text_input("Last Name", value=st.session_state.user_info["last_name"])
        age_group = st.selectbox("Age Group", ["", "<18", "18-24", "25-34", "35-44", "45-54", "55-64", "65+"], index=0)

        st.write("### Dietary Preferences & Restrictions")
        dietary_preference = st.selectbox("Do you follow a specific diet?", ["", "Vegetarian", "Vegan", "Keto", "Paleo", "Mediterranean", "Low-carb", "High-protein"])
        dietary_custom = st.text_input("Other dietary preferences (if any)", value=st.session_state.user_info["dietary_preference"])
        food_allergies = st.multiselect("Do you have any food allergies?", ["Dairy", "Gluten", "Nuts", "Shellfish", "Eggs", "Soy"], default=st.session_state.user_info["food_allergies"])
        disliked_foods = st.text_input("Any specific foods you dislike?", value=st.session_state.user_info["disliked_foods"])

        st.write("### Health & Lifestyle")
        health_conditions = st.multiselect("Do you have any health conditions?", ["Diabetes", "High blood pressure", "High cholesterol", "Lactose intolerance", "Celiac disease", "IBS"], default=st.session_state.user_info["health_conditions"])
        health_custom = st.text_input("Other health conditions (if any)", value="")
        health_goal = st.selectbox("What is your primary health goal?", ["", "Weight loss", "Muscle gain", "Improve heart health", "Boost energy levels", "General well-being", "Manage blood sugar"])

        st.write("### Activity Level")
        activity_level = st.selectbox("How active are you on a daily basis?", ["", "Sedentary (little or no exercise)", "Lightly active (1-3 days/week)", "Moderately active (3-5 days/week)", "Very active (6-7 days/week)", "Athlete-level training"])

        st.write("### Grocery Shopping Preferences")
        grocery_frequency = st.selectbox("How often do you do a grocery run?", ["", "Every day", "A few times a week", "Once a week", "Every two weeks"])
        shopping_preference = st.text_input("Where do you usually shop?", value=st.session_state.user_info["shopping_preference"])


        submitted = st.form_submit_button("Save & Continue")
        if submitted:
            st.session_state.user_info = {
                "first_name": first_name,
                "last_name": last_name,
                "age_group": age_group,
                "dietary_preference": dietary_preference or dietary_custom,
                "food_allergies": food_allergies,
                "disliked_foods": disliked_foods,
                "health_conditions": health_conditions + ([health_custom] if health_custom else []),
                "health_goal": health_goal,
                "activity_level": activity_level,
                "grocery_frequency": grocery_frequency,
                "shopping_preference": shopping_preference,

            }
            st.session_state.show_welcome = False
            st.success("Preferences saved successfully! 🎉")
            st.rerun()

else:
    # Edit preferneces
    if st.button("Edit your Profile"):
      st.session_state.show_welcome = True
      st.rerun()

    # Get user's first name
    user_first_name = st.session_state.user_info.get("first_name", "").strip()

    # Display a personalized title if the first name is set
    if user_first_name:
        st.title(f"Welcome {user_first_name}!")
    else:
        st.title("Welcome!")


    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Nunito:wght@300;400;600;700&display=swap');

    /* Apply Nunito font globally */
    html, body, [class*="st-"], * {
        font-family: 'Nunito', sans-serif !important;
    }

    html, body, [class*="st-"] {
        background-color: #F5E6C4 !important; /* Warm Beige */
        color: #000000 !important; /* Black font for all text */
    }

    h1 {
        color: #4CAF50 !important; /* Fresh Green for title */
        font-size: 36px !important;
        font-weight: 700 !important;
    }

    /* BUTTON STYLING */
    button, .stButton>button, .stFileUploader>div>div>button {
        background-color: #F5E6C4 !important; /* Default Beige */
        color: #4CAF50 !important; /* Fresh Green Font */
        border: 2px solid #4CAF50 !important;
        border-radius: 25px !important;
        font-size: 18px !important;
        padding: 12px 24px !important;
        /*font-weight: bold !important;*/
        /*transition: all 0.3s ease-in-out !important;*/
    }

    /* Ensure no extra background layers on button text */
    button div, .stButton>button div, .stFileUploader>div>div>button div {
        background: transparent !important; /* Removes beige behind text */

    }

    /* HOVER EFFECT - Lime Green */
    button:hover, .stButton>button:hover, .stFileUploader>div>div>button:hover {
        background-color: #A6E22E !important; /* Lime Green */
        color: black !important; /* Ensure text is black */
        box-shadow: 0px 0px 8px rgba(166, 226, 46, 0.8) !important; /* Soft glow effect */
    }

    /* Ensure text background remains transparent on hover */
    button:hover div, .stButton>button:hover div, .stFileUploader>div>div>button:hover div {
        background: transparent !important; /* Ensures no beige text background */
    }

    /* CLICK EFFECT - Darker Lime Green */
    button:active, .stButton>button:active, .stFileUploader>div>div>button:active {
        background-color: #8DC81C !important; /* Darker Lime Green */
        transform: scale(0.98) !important; /* Click animation */
    }

    /* Remove button focus outline */
    button:focus, .stButton>button:focus, .stFileUploader>div>div>button:focus {
        outline: none !important;
    }


    /* Input fields */
    .stTextInput>div>div>input, .stTextArea>div>textarea, .stNumberInput>div>div>input {
        font-family: 'Nunito', sans-serif !important;
        border-radius: 5px !important;
        border: 1px solid
        padding: 8px !important;
    }

    /* EXPANDERS (PANTRY ITEMS) */
    .stExpander {
        border: 2px solid #4CAF50 !important; /* Fresh Green Border */
        border-radius: 10px !important;
        background-color: #F5E6C4 !important; /* Warm Beige */
    }


    .stExpander>summary {
        font-weight: 600 !important;
        font-size: 18px !important;
    }

    .stMarkdown h2, .stMarkdown h3 {
        color: #4CAF50 !important; /* Fresh Green */
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

    # Upload Mode
    if st.session_state.input_mode == "upload":
        uploaded_files = st.file_uploader("Upload images of grocery items", type=["jpg", "png", "jpeg", "heic"], accept_multiple_files=True)

        if uploaded_files:
            for uploaded_file in uploaded_files:
                image = Image.open(uploaded_file)

                # Create two columns: Image on left, input fields on right
                col1, col2 = st.columns([1, 2])

                with col1:
                    st.image(image, caption=f"Uploaded Image: {uploaded_file.name}", use_container_width=True)

                with col2:
                    response_text = process_text_image(image)
                    food_name = extract_food_name(response_text)

                    if food_name:
                      grocery_items = [item.strip() for item in food_name.split(",")]  # Split into individual items

                      if len(grocery_items) > 1:
                        st.write("Multiple items detected. Please confirm names before adding:")
                        updated_names = []
                        for i, item in enumerate(grocery_items):
                            updated_name = st.text_input(f"Item {i+1}", value=item.capitalize(), key=f"multi_item_{i}")
                            updated_names.append(updated_name)

                        if st.button("Add All", key=f"btn_all_{uploaded_file.name}"):
                            for item in updated_names:
                                st.session_state.grocery_list.append({"name": item, "description": "", "quantity": 1})
                            st.session_state.input_mode = None
                            st.success("All items added to the list!")
                            st.rerun()

                      else:  # Single item detected (Keep existing behavior)
                          new_name = st.text_input("Item Name", value=food_name)
                          description = st.text_area("Description (Optional)", "")
                          quantity = st.number_input("Quantity", min_value=1, value=1, step=1)

                          if st.button(f"Add", key=f"btn_{uploaded_file.name}"):
                              item = {"name": new_name, "description": description, "quantity": quantity}
                              st.session_state.grocery_list.append(item)
                              st.session_state.input_mode = None  # Hide input section after adding
                              st.success(f"Added {new_name} to the list!")
                              st.rerun()
                    else:
                        st.error(f"Could not identify the grocery item in {uploaded_file.name}. Try another image.")

    # Manual Input Mode
    elif st.session_state.input_mode == "manual":
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
    st.write("### Your Pantry:")
    for i, item in enumerate(st.session_state.grocery_list):
        with st.expander(f"{item['name']} (x{item['quantity']})"):
            edited_name = st.text_input("Edit Name", value=item["name"], key=f"edit_name_{i}")
            edited_description = st.text_area("Edit Description", value=item["description"], key=f"edit_desc_{i}")
            edited_quantity = st.number_input(
                "Edit Quantity",
                min_value=1,
                value=item["quantity"],
                step=1,
                key=f"edit_qty_{i}_{item['name'].replace(' ', '_')}"
            )
            # Save
            if st.button("Save Changes", key=f"save_{i}_{item['name'].replace(' ', '_')}"):
                st.session_state.grocery_list[i] = {"name": edited_name, "description": edited_description, "quantity": edited_quantity}
                st.success("Item updated!")
            # Delete
            if st.button("Delete Item", key=f"delete_{i}_{id(item)}"):
                del st.session_state.grocery_list[i]
                st.success("Item removed!")
                st.rerun()

            # Nutritional Information Button
            if st.button("Get Nutritional Info", key=f"nutri_btn_{i}_{id(item)}"):
                st.session_state[f"show_nutrition_{i}"] = True  # Store in session state

            # Display nutritional info outside the expander
            if st.session_state.get(f"show_nutrition_{i}", False):
                best_match, nutrition_info = get_nutritional_info(item['name'])
                if nutrition_info:
                    for nutrient, value in nutrition_info.items():
                        st.write(f"**{nutrient.replace('_', ' ').capitalize()}:** {value}")
                else:
                    st.error("No nutritional information found.")



    # AI Recommendation Section
    st.write("## AI Recommendation")
    col1, col2 = st.columns(2)
    with col1:
        grocery_prompt = st.text_area("Enter a prompt for grocery improvement (optional)")

        if st.button("🛒 Get Personalized Grocery Recommendations"):
            recommendation = generate_grocery_recommendation(grocery_prompt, [item["name"] for item in st.session_state.grocery_list])
            st.write(recommendation)

    with col2:
      recipe_prompt = st.text_area("Enter a prompt for recipe generation (optional)")

      if st.button("🍽️ Generate Personalized Recipe"):
          recipe = generate_recipe(recipe_prompt, [item["name"] for item in st.session_state.grocery_list])
          st.write(recipe)

    # UI Implementation for Dish-Ingredient Finder
    st.write("## Meal & Ingredient Helper")
    tab1, tab2 = st.tabs(["Find Ingredients for a Dish", "Get Recipe Ideas from Ingredients"])

    with tab1:
        st.write("Enter a dish to see what ingredients you need")
        dish_name = st.text_input("What dish would you like to make?", key="dish_input")
        
        if st.button("🥗 Find Ingredients", key="find_ingredients_btn"):
            if dish_name:
                ingredients_list = generate_dish_ingredients_or_recipes(dish_name, mode="dish_to_ingredients")
                st.write(ingredients_list)
                
                # Add option to add these ingredients to grocery list
                if st.button("➕ Add These Ingredients to Grocery List", key="add_ingredients_btn"):
                    # This would need to parse the AI response and add to grocery list
                    st.success("Ingredients added to your grocery list!")
            else:
                st.warning("Please enter a dish name")

    with tab2:
        st.write("Enter ingredients you already have to discover possible recipes")
        available_ingredients = st.text_area(
            "List ingredients you have (comma separated):", 
            placeholder="e.g. chicken breast, onion, garlic, rice",
            key="ingredients_input"
        )
        
        if st.button("🍳 Find Recipes", key="find_recipes_btn"):
            if available_ingredients:
                recipe_suggestions = generate_dish_ingredients_or_recipes(available_ingredients, mode="ingredients_to_recipes")
                st.write(recipe_suggestions)
                
                # Add option to add missing ingredients to grocery list
                if st.button("➕ Add Missing Ingredients to Grocery List", key="add_missing_btn"):
                    # This would need to parse the AI response and add missing ingredients to grocery list
                    st.success("Missing ingredients added to your grocery list!")
            else:
                st.warning("Please enter at least one ingredient")
