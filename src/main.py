from agent import create_agent
from random import shuffle
import streamlit as st

app_title = "BIA810 Project"
llm_models=['llama3:8b']


if "messages" not in st.session_state:
    st.session_state.messages = []

@st.dialog("About")
def about_box():
    st.write(f"**{app_title}**")
    names = ["Mick Twohig", "Matt Kelly", "Brian Hasselbeck"]
    shuffle(names) # all equal here!
    for name in names:
        st.write(name)
    st.info("Version 0.0.1",icon="ℹ️")

st.set_page_config(page_title=app_title, layout='wide')

st.sidebar.markdown("## Main Menu")
model = st.sidebar.selectbox("Model Name", llm_models)
temperature = st.sidebar.slider("Temperature", min_value=0.0, max_value=2.0, value=0.0, step=0.05)
st.sidebar.button("About", on_click=about_box)

st.write("Welcome to BIA-810 Search Tool")

agent = create_agent(model=model, temperature=temperature)
def run_query():
    results = agent.invoke({"input": st.session_state.query})
    st.write(results['output'])

for message in st.session_state.messages:
    with st.chat_message(message['role']):
        st.markdown(message['content'])

if prompt := st.chat_input("Enter a query"):
    with st.chat_message('user'):
        st.markdown(prompt)
    st.session_state.messages.append({'role': 'user', 'content': prompt})
    resp = agent.invoke({'input': prompt})
    st.write_stream(resp)
# st.text_input("Enter a query", key='query')
#
# st.button("Submit", on_click=run_query)





# def main():
#     agent = create_agent()
#
#     query = """
#     Find evidence about mRNA vaccines for influenza and summarize the findings
#     """
#
#     results = agent.invoke({"input": query})
#
#     print("\nFINAL REPORT\n")
#     print(results["output"])
#
# if __name__=="__main__":
#     main()