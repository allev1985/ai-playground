import streamlit as st
import agent
import forms.personal_form as personal_form

aiAgent = agent.Agent()

st.set_page_config(
    page_title="Personality Creator Agent", 
    page_icon="🤖")

personalDetails = personal_form.page()

print(personalDetails)