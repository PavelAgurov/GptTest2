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

how_it_work = """\
TBD
"""

score_prompt_template = """/
You are a advanced Solution Architect of IT project. 
You have numerated list of typical architecture templates:
{topics}
###
Project team will provide you a request with project information (delimited with XML tags).
Your task is to check which of the given templates matches the provided request and explain why.

Do it step by step

In the first step, you must read a the provided request and extract all components of the requested solution.

In the second step, you must read all the patterns and perform a match. Please add a score of relevance from 0 to 1 (0 - not relevant, 1 - fully relevant). Provide as many arguments as you can as to why the request is or is not relevant to the templates.

As a final step, consider what clarification and additional information about each component you can ask the project team to improve the score. Be creative to ask additional clarification.

You have to check ALL provided templates.
###
Provide your output in json format with the keys: TemplateID, Template, Components, Score, Explanation, Clarifications.

Example output:
{{ 
"Components": "Database, API", 
"Clarifications": "request for clarification here",
"Templates": [
{{"TemplateID": 1, "Template": "Web App",  "Score": 0.5, "Explanation": "some text here"}},
{{"TemplateID": 2, "Template": "Function App",  "Score": 0, "Explanation": "some text here" }}
]
}}

<request>{request}</request>
"""

TEMPLATE_LIST = [
  [1, "Web App", "A typical modern application might include both a website and one or more RESTful web APIs. A web API might be consumed by browser clients through AJAX, by native client applications, or by server-side applications."], 
  [2, "Function App",  "Use Function Apps to run background tasks. Functions are invoked by triggers, such as a timer event or a message placed on the queue."],
  [3, "Relational Data storage",  "Any relational data storage, for example it can be Azure SQL Database or other."],
  [4, "Non-relational Data storage", "Any non-relational data and noSQL databases, for example it can be Azure Cosmos DB or any other."],
]

st.set_page_config(page_title="RM Request Demo", page_icon=":robot:")
st.title('RM Request Demo')

tab_main, tab_apikey = st.tabs(["Request", "Settings"])

with tab_main:
    header_container     = st.container()
    input_container      = st.container()
    debug_container      = st.empty()
    components_container = st.container()
    clarifications_container = st.container()
    scores_container     = st.container()
    output_container     = st.container()

with tab_apikey:
    key_header_container   = st.container()
    open_api_key = key_header_container.text_input("OpenAPI Key: ", "", key="open_api_key")

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

langchain.llm_cache = SQLiteCache()

llm_score = ChatOpenAI(model_name = "gpt-3.5-turbo", openai_api_key = LLM_OPENAI_API_KEY, max_tokens = 1000)
score_prompt = PromptTemplate.from_template(score_prompt_template)
    
input_request = input_container.text_input("Project request: ", "", key="input")

if input_request:
    debug_container.markdown('Starting LLM...')
    score_chain  = LLMChain(llm=llm_score, prompt = score_prompt)
    score_text = score_chain.run(topics = TEMPLATE_LIST, request = input_request)
    debug_container.markdown('Done.')
    try:
        score_json = json.loads(get_json(score_text))

        components = score_json["Components"]
        clarifications = score_json["Clarifications"]
        templates_scores = score_json["Templates"]

        components_container.markdown(f'<b>Components</b>:\n\n{components}', unsafe_allow_html=True)
        clarifications_container.markdown(f'<b>Clarification requred</b>:\n\n{clarifications}', unsafe_allow_html=True)

        result_list = []
        for t in templates_scores:
            result_list.append([
                t["TemplateID"],
                t["Template"],
                t["Score"],
                t["Explanation"]
            ])

        df = pd.DataFrame(result_list, columns = ['#', 'Template', 'Score', 'Explanation'])
        df = df.sort_values(by=['Score'], ascending=False)
        output_container.markdown(df.to_html(index=False), unsafe_allow_html=True)

    except Exception as error:
        output_container.markdown(f'Error JSON:\n\n{score_text}\n\nError: {error}\n\n{traceback.format_exc()}', unsafe_allow_html=True)
      