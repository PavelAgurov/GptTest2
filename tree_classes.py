class Node:
    yes_question_id : int
    no_question_id  : int
    document_name   : str
    def __init__(self, yes_question_id : int, no_question_id: int, document_name : str):
        self.yes_question_id = yes_question_id
        self.no_question_id = no_question_id
        self.document_name = document_name
    @classmethod
    def path_node(self, yes_question_id : int, no_question_id: int):
        return Node(yes_question_id, no_question_id, None)
    @classmethod
    def end_node(self, document_name : str):
        return Node(None, None, document_name)

class Step:
    question_id : int
    document    : str
    def __init__(self, question_id : int, document : str):
        self.question_id = question_id
        self.document = document
