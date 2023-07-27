import pandas as pd
import json
import os
import streamlit as st
import langchain
from langchain import PromptTemplate
from langchain.chat_models import ChatOpenAI
from langchain.chains import LLMChain
from langchain.cache import SQLiteCache
from datetime import datetime

how_it_work = """\
TBD
"""

extract_facts_prompt_template = """/
You are an advanced solution architect for an IT project.
Your job is to convert the question and answer (separated by XML tags) into one or more useful facts.
You must ignore all information that is not relevant to the IT project architecture (e.g. greetings, polite words, etc.)
For each fact you should add a score of relevance from 0 to 1 (0 - not relevant, 1 - fully relevant).

Provide answer in JSON format with fields: 
- it_project_facts - list of extracted facts that are relevant to the IT project architecture with score
- other_facts - list of other facts that are not relevant to the IT project architecture with score

<question>{question}</question>
<answer>{answer}</answer>
"""

score_prompt_template = """/
You are an advanced solution architect for an IT project.
You have numerated list of questions:
{questions}
###
Project team provides you numerated list of facts:
{facts}
###
Your task is to find a Yes or No answer to each question based on the facts provided. 
But if there is no answer in the given facts, the answer should be set to "None".
If there are two conflicting answers to a question, the answer should be "Issue".
You should also include an explanation as to why you are responding this way.
###
Provide your output in json format with the keys: 
- QuestionID - ID of question
- Answer - answer
- Explanation - explanation of answer
- RefFacts - list of facts related to the answer

Example output:
[ 
{{"QuestionID": 1, "Answer": "Yes",  "Explanation": "Answer based on facts 1 and 3.", "RefFacts": [1, 3]}},
{{"QuestionID": 2, "Answer": "None", "Explanation": "There is no answer in provided facts.", "RefFacts": [] }},
{{"QuestionID": 2, "Answer": "Issue", "Explanation": "There are two conflicting answers in facts 2 and 6.", "RefFacts": [2, 6] }}
]
"""

QUESTIONS = [
    'Is it migration or build new project?',
    'Do you require full control to the environment?',
    'Is project already cloud optimized?',
    'Can project be containerized?'
]

st.set_page_config(page_title="RM Request Demo", page_icon=":robot:")
st.title('RM Request Demo')

tab_main, tab_apikey = st.tabs(["Request", "Settings"])

with tab_main:
    header_container     = st.container()
    question_container   = st.empty()
    input_container      = st.container()
    debug_container      = st.empty()
    clarifications_container = st.container()

with tab_apikey:
    key_header_container   = st.container()
    open_api_key = key_header_container.text_input("OpenAPI Key: ", "", key="open_api_key")

with st.sidebar:
    collected_dialog_container = st.expander(label="Saved dialog")
    collected_facts_container  = st.expander(label="Facts", expanded=True)

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

def get_numerated_list(l):
    result = []
    for index, row in enumerate(l):
        result.append(f'{index+1}. {row}')
    return result

def get_numerated_list_string(l):
    result = get_numerated_list(l)
    return '\n'.join(result)

### -------------- LLM and chains

if open_api_key:
    LLM_OPENAI_API_KEY = open_api_key
else:
    LLM_OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]

langchain.llm_cache = SQLiteCache()
llm = ChatOpenAI(model_name = "gpt-3.5-turbo", openai_api_key = LLM_OPENAI_API_KEY, max_tokens = 1000)

extract_facts_prompt = PromptTemplate.from_template(extract_facts_prompt_template)
extract_facts_chain  = LLMChain(llm=llm, prompt = extract_facts_prompt)
score_prompt = PromptTemplate.from_template(score_prompt_template)
score_chain  = LLMChain(llm=llm, prompt = score_prompt)

### -------------- Sessions

SESSTION_COLLECTED_FACTS = 'collected'

if SESSTION_COLLECTED_FACTS not in st.session_state:
    st.session_state[SESSTION_COLLECTED_FACTS] = []

### ----------------------------------------------------------------------------------------------
# We are working on the project, we need to host a new internal api which needs to have a datastore with 3 environment
# We are working on the project, we need to host a new publicly facing website, Tech used ReactJS, APIs, DB with 3 environment  
### ----------------------------------------------------------------------------------------------

user_input = input_container.text_area("Your answer or request: ", "", key="input")
system_question = "Do you need full control on the environment?"
question_container.markdown(f'<b>Question:</b> {system_question}', unsafe_allow_html=True)

if user_input:
    # extract facts from question and user anwer
    debug_container.markdown('Starting LLM...')
    facts_from_dialog = extract_facts_chain.run(question = system_question, answer = user_input)
    debug_container.markdown('Done.')
    new_fact_list = []
    try:
        facts_from_dialog_json = json.loads(get_json(facts_from_dialog))['it_project_facts']
        new_fact_list = [f['fact'] for f in facts_from_dialog_json]
        # extracted fact list, no errors
        row = [datetime.now(), system_question, user_input, new_fact_list, 0]
    except:
        # register error
        row = [datetime.now(), system_question, user_input, facts_from_dialog, 1]
    st.session_state[SESSTION_COLLECTED_FACTS].append(row)

# extract flags based on collected facts
collected_list = st.session_state[SESSTION_COLLECTED_FACTS]
dfc = pd.DataFrame(collected_list, columns = ['Time', 'Question', 'Answer', 'Facts', 'Error'])
collected_dialog_container.dataframe(dfc, use_container_width=True, hide_index=True)

collected_fact_list = []
for f in dfc[dfc['Error'] == 0].values:
    collected_fact_list.extend(f[3])
collected_fact_list =list(set(collected_fact_list))    
collected_fact_list_str = get_numerated_list_string(collected_fact_list)
collected_facts_container.markdown(collected_fact_list_str)
score_result = score_chain.run(questions = get_numerated_list_string(QUESTIONS), facts = collected_fact_list_str)
score_result_json = json.loads(get_json(score_result))

answer_list = []
for a in score_result_json:
    question_index = int(a["QuestionID"])
    question_str   = QUESTIONS[question_index-1]
    answer_list.append([question_index, question_str, a["Answer"], a["Explanation"], a["RefFacts"]])
dfa = pd.DataFrame(answer_list, columns = ['#', 'Question', 'Answer', 'Explanation', 'References'])
clarifications_container.dataframe(dfa, use_container_width=True, hide_index=True)

    # score_text = score_chain.run(topics = TEMPLATE_LIST, request = user_input)
    # try:
    #     score_json = json.loads(get_json(score_text))

    #     components = score_json["Components"]
    #     clarifications = score_json["Clarifications"]
    #     templates_scores = score_json["Templates"]

    #     components_container.markdown(f'<b>Components</b>:\n\n{components}', unsafe_allow_html=True)
    #     clarifications_container.markdown(f'<b>Clarification requred</b>:\n\n{clarifications}', unsafe_allow_html=True)

    #     result_list = []
    #     for t in templates_scores:
    #         result_list.append([
    #             t["TemplateID"],
    #             t["Template"],
    #             t["Score"],
    #             t["Explanation"]
    #         ])

    #     df = pd.DataFrame(result_list, columns = ['#', 'Template', 'Score', 'Explanation'])
    #     df = df.sort_values(by=['Score'], ascending=False)
    #     output_container.markdown(df.to_html(index=False), unsafe_allow_html=True)

    # except Exception as error:
    #     output_container.markdown(f'Error JSON:\n\n{score_text}\n\nError: {error}\n\n{traceback.format_exc()}', unsafe_allow_html=True)
      