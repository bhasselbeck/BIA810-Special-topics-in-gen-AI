from agent import create_agent

import streamlit as st
if "messages" not in st.session_state:
    st.session_state.messages = []

agent = create_agent()

def run_query():
    results = agent.invoke({"input": st.session_state.query})
    st.write(results['output'])

st.write("Welcome to BIA-810 Search Tool")
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