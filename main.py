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
    'Can project be containerized?',
    'High-performance computing (HPC) workload?',
    'Using Spring Boot apps?',
    'Is it commercial off-the-shelf (COTS) software?',
    'Event-driven workload with short-jived processes?',
    'Managed web hosting platform and features?',
    'Need full-fledged orchestration?',
    'Need a managed service?',
    'Familiar with Service Fabric or older .NET Framework?',
    'Using Red Hat Openshift?',
    'Need access to Kubernetes API?'
]

### -------------- Sessions

SESSTION_COLLECTED_DIALOG = 'collected_dialog'
SESSTION_SYSTEM_QUESTION_INDEX = 'system_question_index'
SESSION_SAVED_USER_INPUT = 'saved_user_input'
SESSION_TOKEN_COUNT = 'token_count'
SESSTION_COLLECTED_ANSWERS = 'collected_answers'

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

def get_question_by_index(index):
    result = ""
    if index != -1:
        result = QUESTIONS[index]
    return result

def show_current_question():
    index = st.session_state[SESSTION_SYSTEM_QUESTION_INDEX]
    question = get_question_by_index(index)
    if index != -1:
        question_container.markdown(f'<b>Question:</b> [{index+1}] {question}', unsafe_allow_html=True)
    else:
        question_container.markdown(f'Please provide details of your project', unsafe_allow_html=True)

def get_next_question_index():
    index = st.session_state[SESSTION_SYSTEM_QUESTION_INDEX]
    return index+1

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

show_current_question()

user_input = st.session_state[SESSION_SAVED_USER_INPUT]
if user_input:
    system_question = get_question_by_index(st.session_state[SESSTION_SYSTEM_QUESTION_INDEX])

    debug_container.markdown('Starting LLM...')
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

    # find next dialog
    st.session_state[SESSTION_SYSTEM_QUESTION_INDEX] = get_next_question_index()

    # move to the next dialog
    st.session_state[SESSION_SAVED_USER_INPUT] = ""
    show_current_question()

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
debug_container.markdown('Starting LLM...')
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
except:
    clarifications_container.markdown(f'Error parsing answers. JSON:\n{score_result}')

token_count_container.markdown(f'Tokens used: {st.session_state[SESSION_TOKEN_COUNT]}')

# if user_input:
#     # extract facts from question and user anwer
#     debug_container.markdown('Starting LLM...')
#     facts_from_dialog = extract_facts_chain.run(question = system_question, answer = user_input)
#     debug_container.markdown('Done.')
#     new_fact_list = []
#     try:
#         facts_from_dialog_json = json.loads(get_json(facts_from_dialog))['it_project_facts']
#         new_fact_list = [f['fact'] for f in facts_from_dialog_json]
#         # extracted fact list, no errors
#         row = [datetime.now(), system_question, user_input, new_fact_list, 0]
#     except:
#         # register error
#         row = [datetime.now(), system_question, user_input, facts_from_dialog, 1]
#     st.session_state[SESSTION_COLLECTED_FACTS].append(row)

#     # extract flags based on collected facts
#     dfc = pd.DataFrame(st.session_state[SESSTION_COLLECTED_FACTS], columns = ['Time', 'Question', 'Answer', 'Facts', 'Error'])
#     collected_dialog_container.dataframe(dfc, use_container_width=True, hide_index=True)

#     collected_fact_list = []
#     for f in dfc[dfc['Error'] == 0].values:
#         collected_fact_list.extend(f[3])
#     collected_fact_list =list(set(collected_fact_list))    
#     collected_fact_list_str = get_numerated_list_string(collected_fact_list)
#     collected_facts_container.markdown(collected_fact_list_str)
#     score_result = score_chain.run(questions = get_numerated_list_string(QUESTIONS), facts = collected_fact_list_str)
#     score_result_json = json.loads(get_json(score_result))

#     # show answers
#     answer_list = []
#     for a in score_result_json:
#         question_index = int(a["QuestionID"])
#         question_str   = QUESTIONS[question_index-1]
#         answer_list.append([question_index, question_str, a["Answer"], a["Explanation"], a["RefFacts"]])
#     dfa = pd.DataFrame(answer_list, columns = ['#', 'Question', 'Answer', 'Explanation', 'References'])
#     clarifications_container.dataframe(dfa, use_container_width=True, hide_index=True)

#     # find next unanswered question
#     unanswered = dfa[dfa['Answer'] == 'None']
#     if unanswered.values.any():
#         first_unanswered = unanswered.values[0]
#         first_unanswered_index = first_unanswered[0]-1
#         clarifications_container.markdown(first_unanswered_index)
#         st.session_state[SESSTION_SYSTEM_QUESTION_INDEX] = first_unanswered_index
#     else:
#         clarifications_container.markdown("We have all answers")
#         st.session_state[SESSTION_SYSTEM_QUESTION_INDEX] = -1

