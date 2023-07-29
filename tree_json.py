from tree_classes import Node

QUESTIONS = [
    'Is it migration of existed project?',
    'Do you require full control to the environment?',
    'Is project already cloud optimized?',
    'Can project be containerized?',
    'Is it high-performance computing (HPC) workload application?',
    'Do you use Spring Boot apps?',
    'Is it commercial off-the-shelf (COTS) software?',
    'Event-driven workload with short-jived processes?',
    'Do you need a managed web hosting platform and features?',
    'Do you need full-fledged orchestration?',
    'Do you need a managed service?',
    'Do you use Service Fabric or older .NET Framework?',
    'Do you use Red Hat Openshift?',
    'Do you need access to Kubernetes API?'
]

tree_json = {
        1: Node.path_node(3, 2),
        2: Node.path_node(100, 5),
        3: Node.path_node(5, 4),
        4: Node.path_node(6, 7),
        5: Node.path_node(101, 6),
        6: Node.path_node(102, 8),
        7: Node.path_node(110, 111),
        8: Node.path_node(103, 9),
        9: Node.path_node(104, 10),
        10: Node.path_node(11, 105),
        11: Node.path_node(12, 112),
        12: Node.path_node(106, 13),
        13: Node.path_node(107, 14),
        14: Node.path_node(108, 109),

        100: Node.end_node('Doc100'),
        101: Node.end_node('Doc101'),
        102: Node.end_node('Doc102'),
        103: Node.end_node('Doc103'),
        104: Node.end_node('Doc104'),
        105: Node.end_node('Doc105'),
        106: Node.end_node('Doc106'),
        107: Node.end_node('Doc107'),
        108: Node.end_node('Doc108'),
        109: Node.end_node('Doc109'),
        110: Node.end_node('Doc110'),
        111: Node.end_node('Doc111'),
        112: Node.end_node('Doc112')
    }

def get_json():
    return tree_json