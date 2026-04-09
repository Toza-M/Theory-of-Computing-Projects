from js import document, window, decodeURIComponent #type: ignore

class State:
    def __init__(self, state_id):
        self.state_id = state_id
        # This Dict For Save Which State Can Go To With Which Symbol
        self.transitions = {} 

    def add_transition(self, symbol, state):
        if symbol not in self.transitions:
            self.transitions[symbol] = []
        self.transitions[symbol].append(state)


class NFA:
    def __init__(self, start_state, accept_state):
        self.start = start_state
        self.accept = accept_state
        
class StateGenerator:
    def __init__(self):
        self.counter = 0

    def get_new_state(self):
        state_name = f"q{self.counter}"
        self.counter += 1
        
        return State(state_name)

state_gen = StateGenerator()

def create_literal_nfa(symbol):
    # For a Single Symbol
    start = state_gen.get_new_state()
    accept = state_gen.get_new_state()
    start.add_transition(symbol, accept)
    
    return NFA(start, accept)


def concatenate_nfa(nfa1, nfa2):
    # To Concatenate More Than One Nfa
    nfa1.accept.add_transition('ε', nfa2.start)
    
    return NFA(nfa1.start, nfa2.accept)


def union_nfas(nfa1, nfa2):
    # To Union More Than One NFA
    new_start = state_gen.get_new_state()
    new_accept = state_gen.get_new_state()
    
    # Branch From New Start State To Both NFAs
    new_start.add_transition('ε', nfa1.start)
    new_start.add_transition('ε', nfa2.start)
    
    # Merge Accept States Into One
    nfa1.accept.add_transition('ε', new_accept)
    nfa2.accept.add_transition('ε', new_accept)
    
    return NFA(new_start, new_accept)


def kleene_star_nfa(nfa):
    # To Apply Star Operation
    new_start = state_gen.get_new_state()
    new_accept = state_gen.get_new_state()
    
    # Zero Condition
    new_start.add_transition('ε', new_accept)
    
    # Initialize The Start State
    new_start.add_transition('ε', nfa.start)
    
    # Go Back To The Start State
    nfa.accept.add_transition('ε', nfa.start)
    
    # Accept State
    nfa.accept.add_transition('ε', new_accept)
    
    return NFA(new_start, new_accept)

def add_explicit_concat(regex):
    # Add Concatitnation Operator '.'
    new_regex = []
    # Lang Contain Letters, Nums, Epsilon
    operands = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789ε')
    
    for i in range(len(regex)):
        new_regex.append(regex[i])
        if i + 1 < len(regex):
            char1 = regex[i]
            char2 = regex[i+1]
            if (char1 in operands or char1 == '*' or char1 == ')') and \
               (char2 in operands or char2 == '('):
                new_regex.append('.')
                
    return "".join(new_regex)

def infix_to_postfix(regex):
    # Convert Invfix To Postfix Using Shunting Yard Algorithm
    precedence = {'*': 3, '.': 2, '|': 1, '(': 0}
    output = []
    operator_stack = []
    
    regex = add_explicit_concat(regex)
    
    for char in regex:
        if char.isalnum() or char == 'ε':
            output.append(char)
        elif char == '(':
            operator_stack.append(char)
        elif char == ')':
            while operator_stack and operator_stack[-1] != '(':
                output.append(operator_stack.pop())
            if operator_stack:
                operator_stack.pop() # Remove The '('
        else: # Operator (*, ., |)
            while operator_stack and precedence.get(operator_stack[-1], 0) >= precedence.get(char, 0):
                output.append(operator_stack.pop())
            operator_stack.append(char)
            
    while operator_stack:
        output.append(operator_stack.pop())
        
    return "".join(output)


def evaluate_postfix(postfix):
    # Evaluate The Postfix To Build NFA
    stack = []
    for char in postfix:
        if char == '*':
            nfa = stack.pop()
            stack.append(kleene_star_nfa(nfa))
        elif char == '.':
            nfa2 = stack.pop() # Right side
            nfa1 = stack.pop() # Left side
            stack.append(concatenate_nfa(nfa1, nfa2))
        elif char == '|':
            nfa2 = stack.pop() # Right side
            nfa1 = stack.pop() # Left side
            stack.append(union_nfas(nfa1, nfa2))
        else:
            # It Is Standard Character Or Epsilon
            stack.append(create_literal_nfa(char))
            
    return stack.pop()

def get_nfa_info(nfa):
    states, alphabet = set(), set()
    def visit(state):
        if state in states: return
        states.add(state)
        for symbol, targets in state.transitions.items():
            if symbol != 'ε': alphabet.add(symbol)
            for t in targets: visit(t)
    
    visit(nfa.start)
    visit(nfa.accept)  # Ensure accept state is included
    
    # Convert to state_ids for output
    state_ids = sorted([s.state_id for s in states], key=lambda x: int(x[1:]))
    
    transitions = {}
    symbols = ['ε'] + sorted(alphabet)
    for state_id in state_ids:
        # Find the actual State object
        state_obj = next(s for s in states if s.state_id == state_id)
        transitions[state_id] = {
            sym: [t.state_id for t in state_obj.transitions.get(sym, [])]
            for sym in symbols
        }
    
    return {
        'states': state_ids,
        'alphabet': sorted(alphabet),
        'transitions': transitions,
        'start': nfa.start.state_id,
        'accept': nfa.accept.state_id
    }

def generate_dot(nfa):
    info = get_nfa_info(nfa)
    states = info['states']
    dot = 'digraph NFA { rankdir=LR; node [shape=circle, style=filled, fontsize=14];\n'
    for i, state_id in enumerate(states):
        if state_id == info['accept']:
            dot += f'  s{i} [shape=doublecircle, fillcolor=orange, label="{state_id} ✓"];\n'
        elif state_id == info['start']:
            dot += f'  s{i} [shape=circle, fillcolor=limegreen, label="→ {state_id}"];\n'
        else:
            dot += f'  s{i} [shape=circle, fillcolor=lightblue, label="{state_id}"];\n'
    
    symbols = ['ε'] + info['alphabet']  # Consistent with get_nfa_info
    for state_id in info['states']:  # Use info['states'] (state_ids)
        i1 = info['states'].index(state_id)
        for sym in symbols:
            for next_id in info['transitions'][state_id].get(sym, []):
                i2 = info['states'].index(next_id)
                label = '' if sym=='ε' else sym.replace('"', '\\"')  
                color = 'red' if sym=='ε' else 'black'
                style = 'dashed' if sym=='ε' else 'solid'
                dot += f'  s{i1} -> s{i2} [label="{label}", color={color}, style={style}];\n'
    dot += '}'
    return dot

def compile_regex_to_nfa(regex_string):
    global state_gen
    state_gen.counter = 0
    postfix = infix_to_postfix(regex_string)
    nfa = evaluate_postfix(postfix)
    return {'postfix': postfix,'graph': generate_dot(nfa)}

#main script
url_params = str(window.location.search)
if "?regex=" in url_params:
    regex_encoded = url_params.split("regex=")[1].split("&")[0]
    regex = decodeURIComponent(regex_encoded)
    
    result = compile_regex_to_nfa(regex)
    
    document.getElementById("regexDisplay").innerHTML = f"<strong>Regex:</strong> {regex}"
    document.getElementById("postfixDisplay").innerHTML = f"<strong>Postfix:</strong> {result['postfix']}"
    
    window.renderNfaGraph(result['graph'])
else:
    document.getElementById("regexDisplay").innerHTML = "No regex (?regex= required)"