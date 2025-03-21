import streamlit as st
import agent

aiAgent = agent.Agent()

st.set_page_config(
    page_title="Personality Creator Agent", 
    page_icon="🤖")

def startChat(): 
    st.balloons()
    st.session_state.chatStarted = True
    st.session_state.agent = aiAgent.initialise()
    firstMessage = st.session_state.agent.run("Please commence the conversation and begin with your first question.")
    st.session_state.messages.append({"role": "assistant", "content": firstMessage})

if "chatStarted" not in st.session_state:
    st.session_state.chatStarted = False

if "messages" not in st.session_state:
    st.session_state.messages = []

# Page title
st.title("Personality Creator Agent")

# Show start button if chat hasn't started
if not st.session_state.chatStarted:
    st.write("Click the button below to create a personality for your AI assistant.")
    st.button("Start Chat", on_click=startChat)

# Show chat interface if chat has started
if st.session_state.chatStarted and st.session_state.agent:
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    if prompt := st.chat_input("What would you like to know?"):
        with st.chat_message("user"):
            st.markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        with st.chat_message("assistant"):
            try:
                response = st.session_state.agent.run(prompt)
                st.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": response})
            except Exception as e:
                st.error(f"An error occurred: {str(e)}")