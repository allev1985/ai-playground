import streamlit as st

def page():
    st.title("Personal Details")
    name = st.text_input("Name")
    age = st.number_input("Age", min_value=0, max_value=100)
    return {"name": name, "age": age}