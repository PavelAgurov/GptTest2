from tree_classes import Step
from tree_json import get_json

# find next unanswered question and it's end of path
def get_step_by_tree(dfa, get_answer_by_ID) -> Step:
    id = 1

    while (True):
        path = get_json()[id]
        if path.document_name: # document found - end node
            return Step(id, path.document_name)
        
        # trying to navigate by tree
        answer = get_answer_by_ID(dfa, id)
        if answer == "Yes":
            id = path.yes_question_id
            continue
        elif answer == "No":
            id = path.no_question_id
            continue
        #elif answer == "Clash":
        #    return  TODO

        # None - we have no answer yet
        return Step(id, path.document_name)

