def get_numerated_list(l : list) -> list:
    result = []
    for index, row in enumerate(l):
        result.append(f'{index+1}. {row}')
    return result

def get_numerated_list_string(l : list) -> str:
    result = get_numerated_list(l)
    return '\n'.join(result)
