import streamlit as st
import json
import yaml
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple, Optional, Union, cast
from agent import Agent
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get API key from environment variables
ANTHROPIC_API_KEY = os.getenv("API_KEY")
MODEL_NAME = os.getenv("CLAUDE_MODEL")

# Config file path
PROMPTS_CONFIG = os.getenv("PROMPTS_CONFIG", "config/prompts.yaml")

# Page configuration
st.set_page_config(
    page_title="Travel Concierge",
    page_icon="✈️",
    layout="centered"
)

# Initialize session state variables
if 'step' not in st.session_state:
    st.session_state.step = 1  # Start at step 1

if 'places_to_visit' not in st.session_state:
    st.session_state.places_to_visit = []

if 'form_data' not in st.session_state:
    st.session_state.form_data = {}

if 'messages' not in st.session_state:
    st.session_state.messages = []

if 'agent' not in st.session_state:
    st.session_state.agent = None

if 'chain' not in st.session_state:
    st.session_state.chain = None

if 'itinerary' not in st.session_state:
    st.session_state.itinerary = None

# Function to detect and properly format JSON in messages
def display_message(message):
    # Extract the content as a string
    content = str(message["content"])
    
    try:
        # Check if the message might contain JSON
        json_start = content.find('{')
        json_end = content.rfind('}')
        
        if json_start != -1 and json_end != -1 and json_start < json_end:
            # Extract the JSON part
            json_str = content[json_start:json_end+1]
            # Try to parse it
            json_data = json.loads(json_str)
            
            # Store itinerary in session state if it appears to be one
            if "itinerary" in json_data or "days" in json_data or "activities" in json_data:
                st.session_state.itinerary = json_data
            
            # Display text before JSON
            if json_start > 0:
                st.markdown(content[:json_start])
            
            # Display formatted JSON
            st.json(json_data)
            
            # Display text after JSON
            if json_end < len(content) - 1:
                st.markdown(content[json_end+1:])
        else:
            st.markdown(content)
    except (json.JSONDecodeError, TypeError):
        # If parsing fails, display as regular text
        st.markdown(content)

# App title and description
st.title("Travel Concierge")
st.write("Please fill out the following information about your upcoming trip.")

# Default dates
today = datetime.now().date()
next_week = today + timedelta(days=7)

# Define functions for navigation
def go_to_next_step():
    # Save form data before moving to next step
    if st.session_state.step == 1:
        # Validate step 1 data
        if not name or name.strip() == "":
            st.error("Please enter your name.")
            return
        if destination == "Select a country":
            st.error("Please select a destination country.")
            return
        if departure_date >= return_date:
            st.error("Return date must be after departure date.")
            return
        
        # Save step 1 data
        st.session_state.form_data.update({
            "name": name,
            "destination": destination,
            "departure_date": departure_date,
            "return_date": return_date,
            "trip_purpose": trip_purpose,
            "other_purpose": other_purpose if trip_purpose == "Other" else "",
            "activities": activities,
            "cuisine_preference": cuisine_preference,
            "budget_range": budget_range
        })
    
    st.session_state.step += 1
    st.rerun()

def go_back():
    st.session_state.step -= 1
    st.rerun()

def submit_form():
    # Process and create JSON
    create_travel_json()
    st.session_state.step += 1
    
    # Initialize the agent with the travel data
    initialize_agent_with_travel_data()
    st.rerun()

def initialize_agent_with_travel_data():
    # Create an instance of the Agent
    agent = Agent()
    
    # Load YAML configuration from the configured location
    with open(PROMPTS_CONFIG, 'r') as file:
        yaml_dict = yaml.safe_load(file)
    
    # Initialize the agent
    agent.enable_memory()
    chain = agent.initialise(yaml_dict, model=MODEL_NAME, apiKey=ANTHROPIC_API_KEY)
    
    # Store the agent and chain in session state
    st.session_state.agent = agent
    st.session_state.chain = chain
    
    # Add welcome message to chat
    initial_message = f"Hi {st.session_state.travel_data['personalInfo']['name']}, I'm your travel assistant. I'll help you plan your trip to {st.session_state.travel_data['personalInfo']['destination']}."
    st.session_state.messages.append({"role": "assistant", "content": initial_message})
    
    # Add user prompt to messages
    user_prompt = st.session_state.travel_json
    st.session_state.messages.append({"role": "user", "content": user_prompt})
    
    # Get the first response
    try:
        response = agent.invoke(
            chain, 
            user_prompt,
            session_id=st.session_state.travel_data['personalInfo']['name'],
            destination=st.session_state.travel_data['personalInfo']['destination']
        )
        # Ensure response is a string
        response_str = str(response)
        st.session_state.messages.append({"role": "assistant", "content": response_str})
    except Exception as e:
        error_msg = f"Error getting initial response: {str(e)}"
        st.error(error_msg)
        st.session_state.messages.append({"role": "assistant", "content": "I'm having trouble analyzing your travel data. Please try asking me a specific question about your trip."})

def create_travel_json():
    # Get data from session state
    form_data = st.session_state.form_data
    places = st.session_state.places_to_visit
    activity_preferences = st.session_state.get('activity_preferences', {})
    cuisine_importance = st.session_state.get('cuisine_importance', {})
    special_requests = st.session_state.get('special_requests', "")
    dietary_restrictions = st.session_state.get('dietary_restrictions', "")
    
    # Process places to visit for JSON
    places_list = []
    for place in places:
        if place["place"].strip():
            places_list.append({
                "name": place["place"],
                "fromDate": place["from_date"].strftime("%Y-%m-%d"),
                "toDate": place["to_date"].strftime("%Y-%m-%d"),
                "duration": (place["to_date"] - place["from_date"]).days + 1
            })
    
    # Process activity preferences for JSON
    activity_prefs_list = []
    for activity, importance in activity_preferences.items():
        activity_prefs_list.append({
            "name": activity,
            "importance": importance
        })
    
    # Process cuisine preferences for JSON
    cuisine_prefs_list = []
    for cuisine, importance in cuisine_importance.items():
        cuisine_prefs_list.append({
            "name": cuisine,
            "importance": importance
        })
    
    # Create JSON object with all travel information
    travel_data = {
        "personalInfo": {
            "name": form_data["name"],
            "destination": form_data["destination"],
            "dates": {
                "departure": form_data["departure_date"].strftime("%Y-%m-%d"),
                "return": form_data["return_date"].strftime("%Y-%m-%d"),
                "duration": (form_data["return_date"] - form_data["departure_date"]).days + 1
            },
            "tripPurpose": form_data["trip_purpose"] if form_data["trip_purpose"] != "Other" else form_data["other_purpose"],
            "budget": {
                "min": form_data["budget_range"][0],
                "max": form_data["budget_range"][1],
                "currency": "USD"
            }
        },
        "placesToVisit": places_list,
        "preferences": {
            "activities": activity_prefs_list,
            "dining": {
                "cuisines": cuisine_prefs_list,
                "dietaryRestrictions": dietary_restrictions if dietary_restrictions else None
            },
            "specialRequests": special_requests if special_requests else None
        }
    }
    
    # Convert to JSON string with nice formatting
    travel_json = json.dumps(travel_data, indent=2)
    
    # Store in session state for display on the final step
    st.session_state.travel_json = travel_json
    st.session_state.travel_data = travel_data

# Function to add a new place
def add_place():
    # Get trip dates from session state
    departure_date = st.session_state.form_data["departure_date"]
    return_date = st.session_state.form_data["return_date"]
    
    st.session_state.places_to_visit.append({
        "place": "",
        "from_date": departure_date,
        "to_date": return_date
    })

# Function to remove a place
def remove_place(index):
    st.session_state.places_to_visit.pop(index)
    st.rerun()

# Function to create itinerary download button if itinerary is available
def add_itinerary_download():
    if st.session_state.itinerary is not None:
        itinerary_json = json.dumps(st.session_state.itinerary, indent=2)
        name = st.session_state.form_data["name"]
        destination = st.session_state.form_data["destination"]
        
        st.download_button(
            label="⬇️ Download Itinerary",
            data=itinerary_json,
            file_name=f"{name.replace(' ', '_').lower()}_{destination.replace(' ', '_').lower()}_itinerary.json",
            mime="application/json",
            key="download_itinerary"
        )

# Function to handle sending a new message to the agent
def send_message():
    if st.session_state.user_input and st.session_state.user_input.strip():
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": st.session_state.user_input})
        
        # Get response from agent
        user_input = st.session_state.user_input
        
        # Invoke agent to get response
        agent = st.session_state.agent
        chain = st.session_state.chain
        
        # Add a placeholder for the response
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            message_placeholder.markdown("Thinking...")
            
            try:
                # Get response from agent
                response = agent.invoke(
                    chain,
                    user_input,
                    session_id=st.session_state.travel_data['personalInfo']['name'],
                    destination=st.session_state.travel_data['personalInfo']['destination']
                )
                
                # Ensure response is a string
                response_str = str(response)
                
                # Try to detect and parse JSON in the response
                try:
                    json_start = response_str.find('{')
                    json_end = response_str.rfind('}')
                    
                    if json_start != -1 and json_end != -1 and json_start < json_end:
                        # Extract the JSON part
                        json_str = response_str[json_start:json_end+1]
                        # Try to parse it
                        json_data = json.loads(json_str)
                        
                        # Store itinerary in session state if it appears to be one
                        if "itinerary" in json_data or "days" in json_data or "activities" in json_data:
                            st.session_state.itinerary = json_data
                        
                        # Display text before JSON
                        if json_start > 0:
                            message_placeholder.markdown(response_str[:json_start])
                            
                        # Display formatted JSON
                        json_placeholder = st.container()
                        with json_placeholder:
                            st.json(json_data)
                        
                        # Display text after JSON
                        if json_end < len(response_str) - 1:
                            st.markdown(response_str[json_end+1:])
                    else:
                        message_placeholder.markdown(response_str)
                except json.JSONDecodeError:
                    # If parsing fails, display as regular text
                    message_placeholder.markdown(response_str)
                
                # Add assistant response to chat history
                st.session_state.messages.append({"role": "assistant", "content": response_str})
            except Exception as e:
                error_msg = f"Error getting response: {str(e)}"
                message_placeholder.markdown(error_msg)
                st.session_state.messages.append({"role": "assistant", "content": error_msg})
        
        st.rerun()

# STEP 1: Basic Information
if st.session_state.step == 1:
    st.write("### Step 1: Basic Information")
    
    # Get previously entered values from session_state if available
    form_data = st.session_state.form_data
    
    # 1. Name input
    name = st.text_input("Your Name", form_data.get("name", ""))
    
    # 2. Country selector
    countries = [
        "Select a country", "Australia", "Brazil", "Canada", "China", "France", 
        "Poland", "Germany", "India", "Italy", "Japan", "Mexico", "New Zealand", 
        "Singapore", "South Africa", "Spain", "Thailand", "United Kingdom", 
        "United States"
    ]
    destination = st.selectbox("Where are you travelling to?", countries, index=countries.index(form_data.get("destination", "Select a country")) if form_data.get("destination") in countries else 0)
    
    # 3. Overall trip date picker
    col1, col2 = st.columns(2)
    
    with col1:
        departure_date = st.date_input(
            "Overall Trip Departure Date", 
            form_data.get("departure_date", today)
        )
    
    with col2:
        return_date = st.date_input(
            "Overall Trip Return Date", 
            form_data.get("return_date", next_week)
        )
    
    # Trip purpose
    trip_purpose = st.radio(
        "Purpose of your trip:",
        ["Leisure", "Business", "Family Visit", "Adventure", "Other"],
        index=["Leisure", "Business", "Family Visit", "Adventure", "Other"].index(form_data.get("trip_purpose", "Leisure"))
    )
    
    # Initialize other_purpose
    other_purpose = ""
    
    if trip_purpose == "Other":
        other_purpose = st.text_input("Please specify:", form_data.get("other_purpose", ""))
    
    # Activity preferences
    st.write("#### Activity Preferences")
    activities = st.multiselect(
        "What activities are you interested in?",
        ["Sightseeing", "Shopping", "Museums/Art Galleries", "Food Tours", 
         "Adventure Sports", "Beach Activities", "Hiking", "Local Culture", 
         "Nightlife", "Relaxation/Spa"],
        default=form_data.get("activities", [])
    )
    
    # Dining preferences
    st.write("#### Dining Preferences")
    cuisine_preference = st.multiselect(
        "Preferred cuisines:",
        ["Local/Traditional", "International", "Fine Dining", "Street Food", 
         "Vegetarian/Vegan", "Seafood", "Any"],
        default=form_data.get("cuisine_preference", [])
    )
    
    # Budget
    st.write("#### Budget")
    budget_range = st.slider(
        "What's your approximate budget per day (USD)?",
        min_value=50,
        max_value=1000,
        value=form_data.get("budget_range", (100, 300)),
        step=50
    )
    
    # Next button
    st.button("Next Step", on_click=go_to_next_step)

# STEP 2: Detailed Preferences
elif st.session_state.step == 2:
    st.write("### Step 2: Detailed Trip Information")
    
    # Display a summary of the basic information
    form_data = st.session_state.form_data
    
    with st.expander("Trip Summary (click to expand)", expanded=False):
        st.write(f"**Name:** {form_data['name']}")
        st.write(f"**Destination:** {form_data['destination']}")
        st.write(f"**Dates:** {form_data['departure_date'].strftime('%B %d, %Y')} to {form_data['return_date'].strftime('%B %d, %Y')}")
        st.write(f"**Purpose:** {form_data['trip_purpose'] if form_data['trip_purpose'] != 'Other' else form_data['other_purpose']}")
    
    # Places to visit section
    st.write("#### Places to Visit")
    st.write("Add the places you plan to visit during your trip, with specific dates for each place:")
    
    # Add place button
    st.button("Add Another Place", on_click=add_place)
    
    # If no places exist, add the first one automatically
    if not st.session_state.places_to_visit:
        add_place()
    
    # Get trip dates from session state for validation
    trip_start = form_data["departure_date"]
    trip_end = form_data["return_date"]
    
    # Display all places with their date inputs
    updated_places = []
    for i, place_data in enumerate(st.session_state.places_to_visit):
        st.write(f"##### Place {i+1}")
        col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
        
        with col1:
            place = st.text_input("Place name", place_data["place"], key=f"place_{i}")
        
        with col2:
            from_date = st.date_input(
                "From", 
                place_data["from_date"],
                key=f"from_{i}"
            )
        
        with col3:
            to_date = st.date_input(
                "To", 
                place_data["to_date"],
                key=f"to_{i}"
            )
        
        with col4:
            if st.button("Remove", key=f"remove_{i}"):
                remove_place(i)
        
        # Update the place data
        updated_places.append({
            "place": place,
            "from_date": from_date,
            "to_date": to_date
        })
    
    # Update the session state with the current values
    st.session_state.places_to_visit = updated_places
    
    # Activity importance sliders
    if form_data["activities"]:
        st.write("#### Activity Importance")
        st.write("How important is each activity to you? (1 = minimal, 10 = very important)")
        
        activity_preferences = {}
        for activity in form_data["activities"]:
            activity_preferences[activity] = st.slider(
                f"{activity}", 
                min_value=1, 
                max_value=10, 
                value=5,
                key=f"activity_{activity}"
            )
        
        # Store in session state
        st.session_state.activity_preferences = activity_preferences
    
    # Cuisine importance sliders
    if form_data["cuisine_preference"]:
        st.write("#### Cuisine Importance")
        st.write("How important is each cuisine type to you? (1 = minimal, 10 = very important)")
        
        cuisine_importance = {}
        for cuisine in form_data["cuisine_preference"]:
            cuisine_importance[cuisine] = st.slider(
                f"{cuisine}", 
                min_value=1, 
                max_value=10, 
                value=5,
                key=f"cuisine_{cuisine}"
            )
        
        # Store in session state
        st.session_state.cuisine_importance = cuisine_importance
    
    # Dietary restrictions
    st.write("#### Dietary Restrictions")
    dietary_restrictions = st.text_area(
        "Any dietary restrictions or allergies?",
        st.session_state.get("dietary_restrictions", ""),
        height=100
    )
    st.session_state.dietary_restrictions = dietary_restrictions
    
    # Special requests
    st.write("#### Special Requests")
    special_requests = st.text_area(
        "Any special requests or additional information?",
        st.session_state.get("special_requests", ""),
        height=100
    )
    st.session_state.special_requests = special_requests
    
    # Navigation buttons
    col1, col2 = st.columns(2)
    with col1:
        st.button("Back", on_click=go_back)
    with col2:
        submit = st.button("Submit", on_click=submit_form)

# STEP 3: Chat with Travel Assistant
elif st.session_state.step == 3:
    st.write("### Your Travel Assistant")
    
    # Display a summary of the basic information in an expander
    form_data = st.session_state.form_data
    with st.expander("Trip Details (click to expand)", expanded=False):
        st.write(f"**Name:** {form_data['name']}")
        st.write(f"**Destination:** {form_data['destination']}")
        st.write(f"**Dates:** {form_data['departure_date'].strftime('%B %d, %Y')} to {form_data['return_date'].strftime('%B %d, %Y')}")
        st.write(f"**Purpose:** {form_data['trip_purpose'] if form_data['trip_purpose'] != 'Other' else form_data['other_purpose']}")
        st.write("#### Travel Information (JSON)")
        st.code(st.session_state.travel_json, language="json")
    
    # Chat interface
    st.write("#### Chat with Your Travel Assistant")
    st.write("Ask questions or get recommendations about your trip:")
    
    # Display chat messages with JSON formatting
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            display_message(message)
    
    # Show download button for itinerary if available
    add_itinerary_download()
    
    # Chat input
    st.chat_input(
        "Ask me anything about your trip...",
        key="user_input",
        on_submit=send_message
    )
    
    # Download buttons
    col1, col2 = st.columns(2)
    with col1:
        # Download button for profile JSON
        name = st.session_state.form_data["name"]
        st.download_button(
            label="⬇️ Download Travel Profile",
            data=st.session_state.travel_json,
            file_name=f"{name.replace(' ', '_').lower()}_travel_profile.json",
            mime="application/json"
        )
    
    # Restart button
    if st.button("Start a New Plan"):
        # Reset session state
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.session_state.step = 1
        st.rerun()

# Add some styling
st.markdown("""
<style>
div.stButton > button {
    background-color: #4CAF50;
    color: white;
    padding: 10px 24px;
}
div.stButton > button[data-testid*="remove"] {
    background-color: #f44336;
    padding: 10px 15px;
}
div.stButton > button[data-testid*="download"] {
    background-color: #2196F3;
    padding: 10px 15px;
}
h3 {
    margin-top: 20px;
    color: #1E88E5;
}
h4 {
    margin-top: 15px;
    color: #0D47A1;
}
h5 {
    margin-top: 10px;
    color: #333;
}
.stExpander {
    background-color: #f5f5f5;
    margin-bottom: 20px;
}
</style>
""", unsafe_allow_html=True)