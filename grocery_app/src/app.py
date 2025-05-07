#import uuid
import streamlit as st
from uuid import uuid4
import numpy as np
from PIL import Image
from user_management import get_user_id, load_user, save_user_preferences, load_grocery_list, save_grocery_list
from api_client import (get_nutritional_info, get_gemini_response, generate_grocery_recommendation, 
                        generate_recipe, extract_food_name, generate_dish_ingredients_or_recipes)
from helper_functions import parse_missing_ingredients_from_text

st.title("Smart Pantry: AI Recommendations & Recipe Helper")

user_id = get_user_id()

# Load user data from MongoDB
user_doc = load_user(user_id)
preferences = user_doc.get("preferences", {})

# Inject CSS globally
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
    background-color: #F5E6C4 !important;
    color: #4CAF50 !important;
    border: 2px solid #4CAF50 !important;
    border-radius: 25px !important;
    font-size: 18px !important;
    padding: 12px 24px !important;
}

button div, .stButton>button div, .stFileUploader>div>div>button div {
    background: transparent !important;
}

button:hover, .stButton>button:hover, .stFileUploader>div>div>button:hover {
    background-color: #A6E22E !important;
    color: black !important;
    box-shadow: 0px 0px 8px rgba(166, 226, 46, 0.8) !important;
}

button:hover div, .stButton>button:hover div, .stFileUploader>div>div>button:hover div {
    background: transparent !important;
}

button:active, .stButton>button:active, .stFileUploader>div>div>button:active {
    background-color: #8DC81C !important;
    transform: scale(0.98) !important;
}

button:focus, .stButton>button:focus, .stFileUploader>div>div>button:focus {
    outline: none !important;
}

/* Input fields */
.stTextInput>div>div>input, .stTextArea>div>textarea, .stNumberInput>div>div>input {
    font-family: 'Nunito', sans-serif !important;
    border-radius: 5px !important;
    border: 1px 4CAF50 solid;
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

# Check if the user is new or not
is_new_user = not preferences or not preferences.get("first_name")

grocery_list = load_grocery_list(user_id)

if is_new_user:
    st.markdown("""
        ## Welcome to Grocery Tracker & AI Recommendations! 🛒
        Help us tailor grocery suggestions to your needs by providing some optional details!
    """)
    # Form for User Preferences
    with st.form("user_info_form"):
        st.write("### Personal Information")
        first_name = st.text_input("First Name", value=preferences.get("first_name", ""))
        last_name = st.text_input("Last Name", value=preferences.get("last_name", ""))
        age_group = st.selectbox("Age Group", ["", "<18", "18-24", "25-34", "35-44", "45-54", "55-64", "65+"], index=0)

        st.write("### Dietary Preferences & Restrictions")
        dietary_preference = st.selectbox("Do you follow a specific diet?", ["", "Vegetarian", "Vegan", "Keto", "Paleo", "Mediterranean", "Low-carb", "High-protein"])
        dietary_custom = st.text_input("Other dietary preferences (if any)", value=preferences.get("dietary_custom", ""))
        food_allergies = st.multiselect("Do you have any food allergies?", ["Dairy", "Gluten", "Nuts", "Shellfish", "Eggs", "Soy"], default=preferences.get("food_allergies", []))
        disliked_foods = st.text_input("Any specific foods you dislike?", value=preferences.get("disliked_foods", ""))

        st.write("### Health & Lifestyle")
        health_conditions = st.multiselect("Do you have any health conditions?", ["Diabetes", "High blood pressure", "High cholesterol", "Lactose intolerance", "Celiac disease", "IBS"], default=preferences.get("health_conditions", []))
        health_custom = st.text_input("Other health conditions (if any)", value=preferences.get("health_custom", ""))
        health_goal = st.selectbox("What is your primary health goal?", ["", "Weight loss", "Muscle gain", "Improve heart health", "Boost energy levels", "General well-being", "Manage blood sugar"])

        st.write("### Activity Level")
        activity_level = st.selectbox("How active are you on a daily basis?", ["", "Sedentary (little or no exercise)", "Lightly active (1-3 days/week)", "Moderately active (3-5 days/week)", "Very active (6-7 days/week)", "Athlete-level training"])

        st.write("### Grocery Shopping Preferences")
        grocery_frequency = st.selectbox("How often do you do a grocery run?", ["", "Every day", "A few times a week", "Once a week", "Every two weeks"])
        shopping_preference = st.text_input("Where do you usually shop?", value=preferences.get("shopping_preference", ""))

        submitted = st.form_submit_button("Save & Continue")

        if submitted:
            updated_preferences = {
                "first_name": first_name,
                "last_name": last_name,
                "age_group": age_group,
                "dietary_preference": dietary_preference or dietary_custom,
                "dietary_custom": dietary_custom,
                "food_allergies": food_allergies,
                "disliked_foods": disliked_foods,
                "health_conditions": health_conditions + ([health_custom] if health_custom else []),
                "health_custom": health_custom,
                "health_goal": health_goal,
                "activity_level": activity_level,
                "grocery_frequency": grocery_frequency,
                "shopping_preference": shopping_preference
            }

            save_user_preferences(user_id, updated_preferences)

            st.success("Preferences saved successfully! 🎉")
            st.session_state.show_welcome = True  # Show welcome popup after saving
            st.rerun()



else:
    if "input_mode" not in st.session_state:
        st.session_state.input_mode = "manual" 

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
                    response_text = get_gemini_response(image)
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
                                grocery_list.append({"name": item, "description": "", "quantity": 1})
                                save_grocery_list(user_id, grocery_list)
                                st.success("All items added to the list!")
                                st.experimental_rerun()

                      else:  # Single item detected (Keep existing behavior)
                          new_name = st.text_input("Item Name", value=food_name)
                          description = st.text_area("Description (Optional)", "")
                          quantity = st.number_input("Quantity", min_value=1, value=1, step=1)

                          if st.button(f"Add", key=f"btn_{uploaded_file.name}"):
                                item = {"name": new_name, "description": description, "quantity": quantity}
                                grocery_list.append(item)
                                save_grocery_list(user_id, grocery_list)
                                st.success(f"Added {new_name} to the list!")
                                st.experimental_rerun() 
                    else:
                        st.error(f"Could not identify the grocery item in {uploaded_file.name}. Try another image.")

    # Manual Input Mode
    elif st.session_state.input_mode == "manual":
        manual_name = st.text_input("Item Name", key="manual_name")
        manual_description = st.text_area("Description (Optional)", "", key="manual_desc")
        manual_quantity = st.number_input("Quantity", min_value=1, value=1, step=1, key="manual_qty")

        if st.button("Add Item"):
            if manual_name:
                grocery_list.append({"name": manual_name, "description": manual_description, "quantity": manual_quantity})
                save_grocery_list(user_id, grocery_list)
                st.session_state.input_mode = None  # Hide input section after adding
                st.success(f"Added {manual_name} to the list!")
                st.rerun()
            else:
                st.error("Please provide a name for the item.")

    # Display the grocery list
    st.write("### Your Pantry:")
    for i, item in enumerate(grocery_list):
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
                grocery_list[i] = {"name": edited_name, "description": edited_description, "quantity": edited_quantity}
                st.success("Item updated!")
            # Delete
            if st.button("Delete Item", key=f"delete_{i}_{id(item)}"):
                del grocery_list[i]
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
            grocery_list = load_grocery_list(user_id)  # Fetch grocery list from MongoDB
            recommendation = generate_grocery_recommendation(grocery_prompt, [item["name"] for item in grocery_list])
            st.write(recommendation)

    with col2:
        recipe_prompt = st.text_area("Enter a prompt for recipe generation (optional)")

        if st.button("🍽️ Generate Personalized Recipe"):
            grocery_list = load_grocery_list(user_id)  # Fetch grocery list from MongoDB
            recipe = generate_recipe(recipe_prompt, [item["name"] for item in grocery_list])
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
                if st.button("Add These Ingredients to Grocery List", key="add_ingredients_btn"):
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
                # Call the function to get recipe suggestions based on ingredients
                recipe_suggestions = generate_dish_ingredients_or_recipes(user_id, available_ingredients, mode="ingredients_to_recipes")
        
                st.write(recipe_suggestions)

                # Here we assume that recipe_suggestions contains a list of missing ingredients.
                # You'll need to adapt this part if the structure of the response is different
                missing_ingredients = []  # This should be populated from the AI response
                if isinstance(recipe_suggestions, str):
                    missing_ingredients = parse_missing_ingredients_from_text(recipe_suggestions)
                else:
                    # If the response is structured, for example as JSON or dict
                    missing_ingredients = recipe_suggestions.get("missing_ingredients", [])

                # Show a button for adding missing ingredients to grocery list
                if missing_ingredients:
                    if st.button("Add Missing Ingredients to Grocery List", key="add_missing_btn"):
                        # Here, we're adding the missing ingredients to the grocery list
                        current_grocery_list = load_grocery_list(user_id)
                        updated_grocery_list = list(set(current_grocery_list + missing_ingredients))
                        save_grocery_list(user_id, updated_grocery_list)
                        st.success("Missing ingredients added to your grocery list!")
            else:
                st.info("No missing ingredients for the suggested recipes.")
        else:
            st.warning("Please enter at least one ingredient.")