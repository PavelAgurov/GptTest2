import pandas as pd
import json
import os
import streamlit as st
import langchain
from langchain import PromptTemplate
from langchain.llms import OpenAI
from langchain.chat_models import ChatOpenAI
from langchain.chains import LLMChain
from langchain.cache import SQLiteCache
import traceback
from datetime import datetime

how_it_work = """\
TBD - how to use it
"""

data_prompt_template = """/
You are a helpful assistant. Based on a conversation with the project's technical team, you must complete a set of fields. 
If the information has already been provided, then it is not necessary to request it again.

Collected information:
{collected_information}

List of fields to fill in:
- Migration: Yes, if project is about migration, No if it's about build new environment. None, if information was not collected yet.
- Control: Yes, if team should have full control on the environment. None, if information was not collected yet.
- Cloud optimized: Yes, if solution should be сloud optimized after migration. No, if optimization is not required or it's not migration project. None, if information was not collected yet.
- Lift and shift: Yes, if migration is lift and shift. No, if migration is required cloud optimization or or it's not migration project. None, if information was not collected yet.
- Containererized: Yes, if solution can be containererized. No, if not. None, if information was not collected yet.
 
Output contains currently collected information and next question to ask the team to have answers in JSON format with fields:
{{
  "fields":[
    "migration": "Yes", "No" or "None",
    "control": "Yes", "No" or "None",
    ....
  ],
  "question": question to the project team
}}

Information from technical team:
{request}
"""

collection_prompt_template = """
You are a helpful assistant. Based on provided question and short answer should should create full answer.
Example1:
Question: Is this project about migration?
Answer: Yes
Output: This project is about migration.

Example2:
Question: Is this project about migration?
Answer: No, we want to build new environment.
Output: This project is not about migration, it's about build new environment.

Question: {question}
Answer: {answer}
Output:
"""

st.set_page_config(page_title="RM Request Demo", page_icon=":robot:")
st.title('RM Request Demo')

header_container = st.container()

tab_main, tab_apikey = st.tabs(["Request", "Settings"])

with tab_main:
    input_container      = st.container()
    debug_container      = st.empty()
    dialog_container     = st.container()

with tab_apikey:
    key_header_container   = st.container()
    open_api_key = key_header_container.text_input("OpenAPI Key: ", "", key="open_api_key")

with st.sidebar:
    question_container  = st.container()
    collected_container = st.container()

header_container.markdown(how_it_work, unsafe_allow_html=True)

def get_json(text):
    text = text.replace(", ]", "]").replace(",]", "]").replace(",\n]", "]")
    open_bracket = min(text.find('['), text.find('{'))
    if open_bracket == -1:
        return text
            
    close_bracket = max(text.rfind(']'), text.rfind('}'))
    if close_bracket == -1:
        return text
    return text[open_bracket:close_bracket+1]

if open_api_key:
    LLM_OPENAI_API_KEY = open_api_key
else:
    LLM_OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]

#langchain.llm_cache = SQLiteCache()

llm = ChatOpenAI(model_name = "gpt-3.5-turbo", openai_api_key = LLM_OPENAI_API_KEY, max_tokens = 1000)

data_prompt = PromptTemplate.from_template(data_prompt_template)
data_chain  = LLMChain(llm=llm, prompt = data_prompt)

coll_prompt = PromptTemplate.from_template(collection_prompt_template)
coll_chain  = LLMChain(llm=llm, prompt = coll_prompt)

input_request = input_container.text_input("Project request or answer: ", "")

if 'collected' not in st.session_state:
    st.session_state['collected'] = []
if 'previous_question' not in st.session_state:
    st.session_state['previous_question'] = None
if 'current_question' not in st.session_state:
    st.session_state['current_question'] = None

if input_request:
    debug_container.markdown('Starting LLM...')
    current_resonse = data_chain.run(collected_information = "Not yet", request = input_request)
    debug_container.markdown('Done.')
    try:
        current_resonse_json = json.loads(get_json(current_resonse))
        current_question = current_resonse_json["question"]
        st.session_state['current_question'] = current_question
    except:
        st.session_state['current_question'] = current_resonse

    previous_question = st.session_state['previous_question']
    if previous_question:
        row = [datetime.now(), previous_question, input_request]
        st.session_state['collected'].append(row)
    st.session_state['previous_question'] = current_resonse

question_container.text_area(label ='Current question:', disabled  = True, value = st.session_state['current_question'])

collected_list = st.session_state['collected']
df = pd.DataFrame(collected_list, columns = ['Time', 'Question', 'Answer'])
collected_container.markdown(df.to_html(index=False), unsafe_allow_html=True)


#     debug_container.markdown('Starting LLM...')
#     data_text = data_chain.run(collected_information = "Not yet", request = input_request)
#     debug_container.markdown('Done.')
#     try:
#         data_json = json.loads(get_json(data_text))
#         output_container.markdown(data_json, unsafe_allow_html=True)

#         answer = str(c_question_container.value)
#         if len(answer) > 0:
#             question  = data_json["question"]
#             coll_text = coll_chain.run(question = question, answer = input_request)
# #            collected_container.markdown(coll_text, unsafe_allow_html=True)

#         c_question_container.markdown(input_request)
        

#     except Exception as error:
#         output_container.markdown(f'Error JSON:\n\n{data_text}\n\nError: {error}\n\n{traceback.format_exc()}', unsafe_allow_html=True)
      
    
