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
from langchain.callbacks import get_openai_callback
from tree import get_step_by_tree, Step
from tree_json import QUESTIONS
from main_prompt import extract_facts_prompt_template, score_prompt_template
from main_utils import get_numerated_list_string

how_it_work = """\
Please provide details of your project and I will ask you some question if needed.
"""

### -------------- Sessions

SESSTION_INIT_INFO_PROVIDED = 'init_info_provided'
SESSTION_COLLECTED_DIALOG = 'collected_dialog'
SESSTION_SYSTEM_QUESTION_INDEX = 'system_question_index'
SESSION_SAVED_USER_INPUT = 'saved_user_input'
SESSION_TOKEN_COUNT = 'token_count'
SESSTION_COLLECTED_ANSWERS = 'collected_answers'
SESSTION_DOCUMENT_FOUND = 'document_found'

if SESSTION_INIT_INFO_PROVIDED not in st.session_state:
    st.session_state[SESSTION_INIT_INFO_PROVIDED] = False
if SESSTION_COLLECTED_DIALOG not in st.session_state:
    st.session_state[SESSTION_COLLECTED_DIALOG] = []
if SESSTION_SYSTEM_QUESTION_INDEX not in st.session_state:
    st.session_state[SESSTION_SYSTEM_QUESTION_INDEX] = -1
if SESSION_SAVED_USER_INPUT not in st.session_state:
    st.session_state[SESSION_SAVED_USER_INPUT] = ""
if SESSION_TOKEN_COUNT not in st.session_state:
    st.session_state[SESSION_TOKEN_COUNT] = 0
if SESSTION_COLLECTED_ANSWERS not in st.session_state:
    st.session_state[SESSTION_COLLECTED_ANSWERS] = None
if SESSTION_DOCUMENT_FOUND not in st.session_state:
    st.session_state[SESSTION_DOCUMENT_FOUND] = None

def submit_user_input():
    st.session_state[SESSION_SAVED_USER_INPUT] = st.session_state.user_input
    st.session_state.user_input = ""

### ---------------- UI
st.set_page_config(page_title="RM Request Demo", page_icon=":robot:")
st.title('RM Request Demo')

tab_main, tab_apikey = st.tabs(["Request", "Settings"])
with tab_main:
    header_container     = st.container()
    question_container   = st.empty()
    input_container      = st.container()
    debug_container      = st.empty()
    clarifications_container = st.container()
    input_container.text_area("Your answer or request: ", "", key="user_input", on_change= submit_user_input)

with tab_apikey:
    key_header_container   = st.container()
    open_api_key = key_header_container.text_input("OpenAPI Key: ", "", key="open_api_key")

with st.sidebar:
    collected_dialog_container = st.expander(label="Saved dialog")
    collected_facts_container  = st.expander(label="Facts", expanded=True)
    token_count_container      = st.empty()

header_container.markdown(how_it_work, unsafe_allow_html=True)

def get_json(text : str) -> str:
    text = text.replace(", ]", "]").replace(",]", "]").replace(",\n]", "]")
    open_bracket = min(text.find('['), text.find('{'))
    if open_bracket == -1:
        return text
            
    close_bracket = max(text.rfind(']'), text.rfind('}'))
    if close_bracket == -1:
        return text
    return text[open_bracket:close_bracket+1]

def get_question_by_index(index : int) -> str:
    result = ""
    if index != -1:
        result = QUESTIONS[index]
    return result

def show_current_question_or_answer():
    index    = st.session_state[SESSTION_SYSTEM_QUESTION_INDEX]
    document = st.session_state[SESSTION_DOCUMENT_FOUND]

    if document:
        question_container.markdown(f'<b>Document:</b> {document}', unsafe_allow_html=True)
    else:
        question = get_question_by_index(index)
        if index != -1:
            question_container.markdown(f'<b>Question:</b> [{index+1}] {question}', unsafe_allow_html=True)
        else:
            question_container.markdown(f'Please provide details of your project', unsafe_allow_html=True)

def get_answer_by_ID(dfa, id):
    answer = dfa[dfa['#'] == id].values[0]
    return answer[2]

def get_next_step() -> Step:
    init_info_provided = st.session_state[SESSTION_INIT_INFO_PROVIDED]
    # columns = ['#', 'Question', 'Answer', 'Explanation', 'References']
    dfa = (pd.DataFrame)(st.session_state[SESSTION_COLLECTED_ANSWERS])
    if init_info_provided and not dfa.empty:
        step = get_step_by_tree(dfa, get_answer_by_ID)
        return Step(step.question_id, step.document)
    else:
        return Step(0, None)

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

### ----------------------------------------------------------------------------------------------
# We are working on the project, we need to host a new internal api which needs to have a datastore with 3 environment
# We are working on the project, we need to host a new publicly facing website, Tech used ReactJS, APIs, DB with 3 environment  
### ----------------------------------------------------------------------------------------------

show_current_question_or_answer()

user_input = str(st.session_state[SESSION_SAVED_USER_INPUT]).strip()
if len(user_input) > 0:
    question_index  = st.session_state[SESSTION_SYSTEM_QUESTION_INDEX]
    system_question = get_question_by_index(question_index)

    debug_container.markdown('Starting LLM to extract facts...')
    with get_openai_callback() as cb:
        facts_from_dialog = extract_facts_chain.run(question = system_question, answer = user_input)
    st.session_state[SESSION_TOKEN_COUNT] += cb.total_tokens
    debug_container.markdown(f'Done. Used {cb.total_tokens} tokens.')

    # register new dialog
    new_fact_list = []
    try:
        facts_from_dialog_json = json.loads(get_json(facts_from_dialog))['it_project_facts']
        new_fact_list = [f['fact'] for f in facts_from_dialog_json]
        # extracted fact list, no errors
        row = [datetime.now(), system_question, user_input, new_fact_list, 0]
    except:
        # register error
        row = [datetime.now(), system_question, user_input, facts_from_dialog, 1]
    st.session_state[SESSTION_COLLECTED_DIALOG].append(row)

    if question_index == -1: # initial information was provided
        st.session_state[SESSTION_INIT_INFO_PROVIDED] = True

    # move to the next dialog
    st.session_state[SESSION_SAVED_USER_INPUT] = ""

# collected dialog
dfc = pd.DataFrame(st.session_state[SESSTION_COLLECTED_DIALOG], columns = ['Time', 'Question', 'Answer', 'Facts', 'Error'])
collected_dialog_container.dataframe(dfc, use_container_width=True, hide_index=True) # show

# get collected facts without errors
collected_fact_list = []
for f in dfc[dfc['Error'] == 0].values:
    collected_fact_list.extend(f[3])
collected_fact_list =list(set(collected_fact_list))    
collected_fact_list_str = get_numerated_list_string(collected_fact_list)
collected_facts_container.markdown(collected_fact_list_str)

# extract answers from facts
debug_container.markdown('Starting LLM to extract answers...')
with get_openai_callback() as cb:
    score_result = score_chain.run(questions = get_numerated_list_string(QUESTIONS), facts = collected_fact_list_str)
st.session_state[SESSION_TOKEN_COUNT] += cb.total_tokens
debug_container.markdown(f'Done. Used {cb.total_tokens} tokens.')

try:
    # get answers
    score_result_json = json.loads(get_json(score_result))
    answer_list = []
    for a in score_result_json:
        question_index = int(a["QuestionID"])
        question_str   = QUESTIONS[question_index-1]
        answer_list.append([question_index, question_str, a["Answer"], a["Explanation"], a["RefFacts"]])
    dfa = pd.DataFrame(answer_list, columns = ['#', 'Question', 'Answer', 'Explanation', 'References'])
    st.session_state[SESSTION_COLLECTED_ANSWERS] = dfa
    # show answers
    clarifications_container.dataframe(dfa, use_container_width=True, hide_index=True)
except Exception as error:
    clarifications_container.markdown(f'Error parsing answers. JSON:\n{score_result}\n\n{error}')

token_count_container.markdown(f'Tokens used: {st.session_state[SESSION_TOKEN_COUNT]}')

# find next dialog
next_step = get_next_step()
if next_step.document:
    st.session_state[SESSTION_DOCUMENT_FOUND] = next_step.document
    st.session_state[SESSTION_SYSTEM_QUESTION_INDEX] = -1
else:
    st.session_state[SESSTION_DOCUMENT_FOUND] = None
    st.session_state[SESSTION_SYSTEM_QUESTION_INDEX] = next_step.question_id-1
show_current_question_or_answer()


