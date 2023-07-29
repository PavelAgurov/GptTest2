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
Don't try to make up an answer, if there is no DIRECT answer in the given facts, the answer should be set to "None".
If there are two conflicting answers to a question, the answer should be "Clash" and you should add a detailed explanation of the problem.
You should also include spep by step explanation as to why you are responding this way.
###
Provide your output in json format with the keys: 
- QuestionID - ID of question
- Answer - answer
- Explanation - explanation of answer, do not repeat question, but explain in details reasons of answer
- Score - score of your confidence in the answer from 0 to 1 (0 - not sure, 1 - absolutely sure)
- RefFacts - list of facts related to the answer

Example output:
[ 
{{"QuestionID": 1, "Answer": "Yes",  "Explanation": "Answer based on facts 1 and 3.", "Score": 1, "RefFacts": [1, 3]}},
{{"QuestionID": 2, "Answer": "None", "Explanation": "There is no answer in provided facts.", "Score": 0.5, "RefFacts": [] }},
{{"QuestionID": 2, "Answer": "Issue", "Explanation": "There are two conflicting answers in facts 2 and 6.", "Score": 0.7, "RefFacts": [2, 6] }}
]
"""