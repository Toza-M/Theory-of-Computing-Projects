# Import the pure math functions from your NFA file without changing it!
from NFA_Back import infix_to_postfix, evaluate_postfix, state_gen

# --- 1. DFA DATA STRUCTURES ---
class DFAState:
    def __init__(self, nfa_states, state_id):
        self.nfa_states = nfa_states  # frozenset of NFA States
        self.state_id = f"D{state_id}" # Label them D0, D1, D2
        self.transitions = {}
        self.is_accept = False
        self.is_start = False

class DFA:
    def __init__(self):
        self.states = []
        self.start_state = None
        self.accept_states = []

# --- 2. SUBSET CONSTRUCTION ALGORITHMS ---
def epsilon_closure(states):
    stack = list(states)
    closure = set(states)
    
    while stack:
        state = stack.pop()
        for nxt in state.transitions.get('ε', []):
            if nxt not in closure:
                closure.add(nxt)
                stack.append(nxt)
    return closure

def move(states, symbol):
    result = set()
    for state in states:
        result.update(state.transitions.get(symbol, []))
    return result

def get_alphabet(nfa_start):
    visited = set()
    stack = [nfa_start]
    alphabet = set()

    while stack:
        state = stack.pop()
        if state in visited:
            continue
        visited.add(state)

        for sym, next_states in state.transitions.items():
            if sym != 'ε':
                alphabet.add(sym)
            for nxt in next_states:
                if nxt not in visited:
                    stack.append(nxt)
    return alphabet

# --- 3. CONVERTER LOGIC ---
def nfa_to_dfa(nfa):
    dfa = DFA()
    alphabet = get_alphabet(nfa.start)
    
    state_map = {} 
    state_id_counter = 0
    queue = []
    
    # Initialize start state
    start_nfa_states = epsilon_closure({nfa.start})
    start_frozen = frozenset(start_nfa_states)
    
    start_dfa_state = DFAState(start_frozen, state_id_counter)
    start_dfa_state.is_start = True
    if nfa.accept in start_nfa_states:
        start_dfa_state.is_accept = True
        dfa.accept_states.append(start_dfa_state)
        
    state_map[start_frozen] = start_dfa_state
    dfa.states.append(start_dfa_state)
    dfa.start_state = start_dfa_state
    queue.append(start_dfa_state)
    state_id_counter += 1

    # Process queue
    while queue:
        current_dfa_state = queue.pop(0)

        for symbol in alphabet:
            moved_states = move(current_dfa_state.nfa_states, symbol)
            if not moved_states:
                continue 
                
            next_nfa_states = epsilon_closure(moved_states)
            next_frozen = frozenset(next_nfa_states)

            if next_frozen not in state_map:
                new_dfa_state = DFAState(next_frozen, state_id_counter)
                
                if nfa.accept in next_nfa_states:
                    new_dfa_state.is_accept = True
                    dfa.accept_states.append(new_dfa_state)

                state_map[next_frozen] = new_dfa_state
                dfa.states.append(new_dfa_state)
                queue.append(new_dfa_state)
                state_id_counter += 1

            current_dfa_state.transitions[symbol] = state_map[next_frozen]

    return dfa

# --- 4. VISUALIZATION (For the Frontend Teammate) ---
def generate_dfa_dot(dfa):
    """Generates the DOT language string specifically for the DFA graph."""
    dot = 'digraph DFA { rankdir=LR; node [shape=circle, style=filled, fontsize=14];\n'
    
    # Draw States
    for state in dfa.states:
        if state.is_accept and state.is_start:
            dot += f'  {state.state_id} [shape=doublecircle, fillcolor=limegreen, label="→ {state.state_id} ✓"];\n'
        elif state.is_accept:
            dot += f'  {state.state_id} [shape=doublecircle, fillcolor=orange, label="{state.state_id} ✓"];\n'
        elif state.is_start:
            dot += f'  {state.state_id} [shape=circle, fillcolor=limegreen, label="→ {state.state_id}"];\n'
        else:
            dot += f'  {state.state_id} [shape=circle, fillcolor=lightblue, label="{state.state_id}"];\n'
            
    # Draw Transitions
    for state in dfa.states:
        for symbol, next_state in state.transitions.items():
            label = symbol.replace('"', '\\"')
            dot += f'  {state.state_id} -> {next_state.state_id} [label="{label}", color=black, style=solid];\n'
    dot += '}'
    return dot

# --- 5. THE MASTER WRAPPER ---
def compile_regex_to_dfa(regex_string):
    """
    This is the ONLY function the frontend needs to call.
    It returns the exact same dictionary structure as the NFA page!
    """
    # 1. Reset state counter and build raw NFA
    global state_gen
    state_gen.counter = 0
    postfix = infix_to_postfix(regex_string)
    raw_nfa = evaluate_postfix(postfix)
    
    # 2. Convert raw NFA to DFA
    dfa = nfa_to_dfa(raw_nfa)
    
    # 3. Generate DFA visual graph
    dfa_dot_graph = generate_dfa_dot(dfa)
    
    # 4. Return identical structure so frontend code doesn't break
    return {
        'postfix': postfix,
        'graph': dfa_dot_graph
    }