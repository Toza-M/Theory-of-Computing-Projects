"""
CYK (Cocke–Younger–Kasami) Parser
==================================

Parses a string using a grammar already in Chomsky Normal Form (CNF).

Input contract
--------------
  cnf_grammar : dict[str, list[list[str]]]
      Every key is a non-terminal.  Every value is a list of productions.
      Each production is a list of symbols:
        - Terminal production:    ['a']           (A -> a)
        - Non-terminal pair:     ['B', 'C']      (A -> BC)

      This matches the output format of CNF_Converter.export_grammar().

      A simpler "compact" format is also accepted for quick manual testing:
        {'S': ['AB'], 'A': ['a'], 'B': ['b']}
      This is auto-detected and normalised internally.

  test_string : str
      The string to parse (e.g. "aabb").

  start_symbol : str
      The start symbol of the grammar (default "S0").

Output
------
  - Whether the string is accepted.
  - A nested parse tree (dict/list structure) suitable for JSON
    serialisation and frontend visualisation.

Algorithm overview
------------------
  The CYK algorithm fills an n×n upper-triangular table T where
  T[i][j] stores the set of non-terminals that can derive the
  substring w[i..j] (inclusive).  We augment each entry with
  *back-pointers* so we can reconstruct one (or all) parse trees.

  Complexity:  O(n³ · |G|)   where n = len(string), |G| = grammar size.

No external libraries are used — only built-in Python data structures.
"""

# ======================================================================
# Helper: Normalise grammar format
# ======================================================================

def _normalise_grammar(grammar):
    """
    Accept either of two input formats and return a uniform one:
        dict[str, list[list[str]]]

    Format 1 (from CNF_Converter):
        {'S': [['A', 'B'], ['a']], ...}          -> returned as-is

    Format 2 (compact / quick-test):
        {'S': ['AB', 'a'], ...}                  -> each string is split
        Rules: uppercase letter = non-terminal,
               lowercase letter = terminal.
        A two-char string like 'AB' becomes ['A','B'].
        A one-char lowercase string like 'a' becomes ['a'].

    The heuristic: if *any* production body is itself a list, we assume
    Format 1 for the entire grammar.  Otherwise we assume Format 2.
    """
    # --- Detect format ---
    is_list_format = False
    for prods in grammar.values():
        for body in prods:
            if isinstance(body, list):
                is_list_format = True
                break
        if is_list_format:
            break

    if is_list_format:
        # Already in list-of-lists form; return a defensive copy
        return {nt: [list(b) for b in prods] for nt, prods in grammar.items()}

    # --- Compact string format: split each body string ---
    normalised = {}
    for nt, prods in grammar.items():
        normalised[nt] = []
        for body_str in prods:
            symbols = list(body_str)        # each char is one symbol
            normalised[nt].append(symbols)
    return normalised


# ======================================================================
# Helper: Build a reverse index for faster lookups
# ======================================================================

def _build_reverse_index(grammar):
    """
    Build two reverse-lookup dictionaries:

    terminal_index:
        Maps a terminal character to the set of non-terminals that
        produce it directly.
        e.g.  {'a': {'A', 'T_a'}, 'b': {'B', 'T_b'}}

    pair_index:
        Maps a (B, C) pair to the set of non-terminals A such that
        A -> BC is a production.
        e.g.  {('A','B'): {'S', 'S0'}, ...}

    These indices eliminate the need to scan the entire grammar during
    each cell computation, reducing the constant factor considerably.
    """
    terminal_index = {}       # terminal char  ->  set of NTs
    pair_index     = {}       # (NT, NT) tuple  ->  set of NTs

    for nt, prods in grammar.items():
        for body in prods:
            if len(body) == 1:
                # Terminal production:  A -> a
                terminal = body[0]
                if terminal not in terminal_index:
                    terminal_index[terminal] = set()
                terminal_index[terminal].add(nt)

            elif len(body) == 2:
                # Pair production:  A -> BC
                pair = (body[0], body[1])
                if pair not in pair_index:
                    pair_index[pair] = set()
                pair_index[pair].add(nt)

    return terminal_index, pair_index


# ======================================================================
# Step 1: Initialise the CYK table
# ======================================================================

def _init_table(n):
    """
    Create an n × n table (list of lists).

    table[i][j] will hold a dictionary:
        { non_terminal: list_of_back_pointers }

    A back-pointer is either:
      - The terminal string itself (for base-case entries), or
      - A tuple (split_k, left_nt, right_nt)
            split_k : the split position (index in the string)
            left_nt : the non-terminal chosen from cell (i, k)
            right_nt: the non-terminal chosen from cell (k+1, j)

    Only the upper triangle (i <= j) is used.
    """
    table = []
    for i in range(n):
        row = []
        for j in range(n):
            row.append({})          # empty dict — no NTs yet
        table.append(row)
    return table


# ======================================================================
# Step 2: Fill the base case (diagonal — substrings of length 1)
# ======================================================================

def _fill_base_case(table, string, terminal_index):
    """
    For every position i in the string, look up which non-terminals
    produce the character string[i] and record them in table[i][i].

    The back-pointer for a terminal production is simply the terminal
    character itself (a leaf in the parse tree).
    """
    n = len(string)
    for i in range(n):
        char = string[i]
        
        # Valid terminals are restricted to lowercase letters and digits
        if not (char.islower() or char.isdigit()):
            continue
            
        # Find all non-terminals A such that A -> char
        producers = terminal_index.get(char, set())
        for nt in producers:
            # Store the terminal as the back-pointer (leaf node)
            if nt not in table[i][i]:
                table[i][i][nt] = []
            table[i][i][nt].append(char)


# ======================================================================
# Step 3: Fill the recursive case (substrings of length 2..n)
# ======================================================================

def _fill_table(table, n, pair_index):
    """
    For each substring length l (from 2 to n):
      For each starting position i (from 0 to n - l):
        j = i + l - 1  (the ending position)
        For each possible split point k (from i to j - 1):
          Look at all NTs in table[i][k] and table[k+1][j].
          For every pair (B, C), check if any A -> BC exists.
          If so, record A in table[i][j] with back-pointer (k, B, C).

    After this procedure, table[0][n-1] contains all NTs that can
    derive the entire input string.
    """
    for length in range(2, n + 1):                     # substring length
        for i in range(n - length + 1):                # start index
            j = i + length - 1                         # end index

            for k in range(i, j):                      # split position
                # Iterate over every pair of NTs from the two sub-cells
                left_cell  = table[i][k]               # NTs for w[i..k]
                right_cell = table[k + 1][j]           # NTs for w[k+1..j]

                for b_nt in left_cell:
                    for c_nt in right_cell:
                        pair = (b_nt, c_nt)
                        # Check which NTs have the production A -> BC
                        producers = pair_index.get(pair, set())
                        for a_nt in producers:
                            if a_nt not in table[i][j]:
                                table[i][j][a_nt] = []
                            # Store back-pointer: (split, left_nt, right_nt)
                            table[i][j][a_nt].append((k, b_nt, c_nt))


# ======================================================================
# Step 4: Check acceptance
# ======================================================================

def _is_accepted(table, n, start_symbol):
    """
    The string is accepted iff the start symbol appears in
    the top-left cell table[0][n-1], which represents the
    full substring w[0..n-1].
    """
    return start_symbol in table[0][n - 1]


# ======================================================================
# Step 5: Backtrack to build the parse tree
# ======================================================================

def _build_tree(table, symbol, i, j):
    """
    Recursively reconstruct a parse tree from the back-pointers
    stored in the CYK table.

    Parameters
    ----------
    table   : the filled CYK table
    symbol  : the non-terminal to expand
    i, j    : the substring span [i..j] this symbol covers

    Returns
    -------
    A nested dictionary representing the parse tree:
        {'S': [{'A': 'a'}, {'B': 'b'}]}       (binary branch)
        {'A': 'a'}                              (terminal leaf)

    We use the *first* back-pointer found for each non-terminal.
    This produces *one* valid parse tree (the grammar may be ambiguous).
    """
    # Retrieve the back-pointers for this symbol at span [i, j]
    pointers = table[i][j].get(symbol, [])

    if not pointers:
        # Should never happen if the caller checked acceptance first
        return None

    # Take the first back-pointer
    bp = pointers[0]

    if isinstance(bp, str):
        # ----------------------------------------------------------
        # Base case: bp is a terminal character (leaf node)
        # The production was  symbol -> terminal
        # ----------------------------------------------------------
        return {symbol: bp}

    else:
        # ----------------------------------------------------------
        # Recursive case: bp is (split_k, left_nt, right_nt)
        # The production was  symbol -> left_nt  right_nt
        # Left  child covers  w[i .. k]
        # Right child covers  w[k+1 .. j]
        # ----------------------------------------------------------
        split_k, left_nt, right_nt = bp

        left_subtree  = _build_tree(table, left_nt,  i,           split_k)
        right_subtree = _build_tree(table, right_nt, split_k + 1, j)

        return {symbol: [left_subtree, right_subtree]}


# ======================================================================
# Step 6 (bonus): Build ALL parse trees (for ambiguous grammars)
# ======================================================================

def _build_all_trees(table, symbol, i, j):
    """
    Like _build_tree, but returns a *list* of all possible parse trees
    for the given symbol over span [i..j].

    Useful for inspecting ambiguity in the grammar.
    """
    pointers = table[i][j].get(symbol, [])
    if not pointers:
        return []

    trees = []
    for bp in pointers:
        if isinstance(bp, str):
            trees.append({symbol: bp})
        else:
            split_k, left_nt, right_nt = bp
            left_options  = _build_all_trees(table, left_nt,  i,           split_k)
            right_options = _build_all_trees(table, right_nt, split_k + 1, j)
            for ltree in left_options:
                for rtree in right_options:
                    trees.append({symbol: [ltree, rtree]})
    return trees


# ======================================================================
# Pretty-print helpers
# ======================================================================

def _pretty_tree(tree, indent=0):
    """
    Return a human-readable, indented string representation of a
    nested parse-tree dictionary.

    Example output:
        S
        +-- A
        |   +-- 'a'
        +-- B
            +-- 'b'
    """
    lines = []
    _pretty_tree_recursive(tree, lines, prefix="", is_last=True, is_root=True)
    return "\n".join(lines)


def _pretty_tree_recursive(node, lines, prefix, is_last, is_root):
    """Recursive helper for _pretty_tree."""

    # Determine the connector characters
    if is_root:
        connector = ""
        child_prefix = ""
    else:
        connector = "+-- " if is_last else "+-- "
        child_prefix = "    " if is_last else "|   "

    if isinstance(node, dict):
        for symbol, children in node.items():
            # Print the non-terminal name
            lines.append(f"{prefix}{connector}{symbol}")

            new_prefix = prefix + child_prefix

            if isinstance(children, str):
                # Terminal leaf
                lines.append(f"{new_prefix}+-- '{children}'")
            elif isinstance(children, list):
                # Two children (binary branch)
                for idx, child in enumerate(children):
                    is_child_last = (idx == len(children) - 1)
                    _pretty_tree_recursive(
                        child, lines, new_prefix, is_child_last, False
                    )
    elif isinstance(node, str):
        # Should not normally be reached at top level
        lines.append(f"{prefix}{connector}'{node}'")


# ======================================================================
# Pretty-print the CYK table (for debugging / educational purposes)
# ======================================================================

def _print_table(table, n, string):
    """
    Print the CYK table in a readable grid format.
    Rows represent starting positions; columns represent ending positions.
    Only the upper triangle is meaningful.
    """
    print("\n" + "=" * 60)
    print("CYK TABLE  (rows = start i, cols = end j)")
    print("=" * 60)

    # Header: column indices with the corresponding character
    header = "      "
    for j in range(n):
        header += f"  {j}:'{string[j]}'  "
    print(header)
    print("      " + "-" * (n * 10))

    for i in range(n):
        row_str = f"  {i}  |"
        for j in range(n):
            if j < i:
                row_str += "   ---   "
            else:
                nts = sorted(table[i][j].keys())
                cell = ",".join(nts) if nts else "-"
                row_str += f" {cell:^8}"
        print(row_str)
    print()


# ======================================================================
# Main CYK parser function (public API)
# ======================================================================

def cyk_parse(grammar, test_string, start_symbol="S0", verbose=True):
    """
    Run the CYK algorithm on the given CNF grammar and test string.

    Parameters
    ----------
    grammar : dict
        A CNF grammar (see module docstring for accepted formats).
    test_string : str
        The input string to parse.
    start_symbol : str
        The start symbol of the grammar (default "S0" to match
        the output of CNF_Converter).
    verbose : bool
        If True, print the CYK table and detailed results.

    Returns
    -------
    accepted : bool
        True if the string belongs to the language.
    tree : dict or None
        A nested parse tree (dict of dicts/lists), or None if rejected.
    all_trees : list[dict]
        All possible parse trees (may contain more than one if the
        grammar is ambiguous).
    """
    # ------------------------------------------------------------------
    # 0. Normalise the grammar to a uniform internal format
    # ------------------------------------------------------------------
    grammar = _normalise_grammar(grammar)

    # Handle the trivial edge case of an empty string
    n = len(test_string)
    if n == 0:
        # An empty string is accepted only if S -> ε exists.
        # In strict CNF (from our converter), epsilon is removed except
        # potentially from the start symbol during Step 2.
        # We check if the start symbol has an empty production.
        has_epsilon = False
        for body in grammar.get(start_symbol, []):
            if len(body) == 0 or body == ['']:
                has_epsilon = True
                break
        if verbose:
            if has_epsilon:
                print(f"[ACCEPTED] The empty string epsilon is in the language.")
            else:
                print(f"[REJECTED] The empty string epsilon is NOT in the language.")
        return has_epsilon, None, []

    # ------------------------------------------------------------------
    # 1. Build reverse indices for efficient lookups
    # ------------------------------------------------------------------
    terminal_index, pair_index = _build_reverse_index(grammar)

    if verbose:
        print("\n" + "=" * 60)
        print(f"  CYK PARSER")
        print(f"  Input string : \"{test_string}\"  (length {n})")
        print(f"  Start symbol : {start_symbol}")
        print("=" * 60)

    # ------------------------------------------------------------------
    # 2. Initialise the n × n CYK table
    # ------------------------------------------------------------------
    table = _init_table(n)

    # ------------------------------------------------------------------
    # 3. Fill the base case (diagonal: substrings of length 1)
    # ------------------------------------------------------------------
    _fill_base_case(table, test_string, terminal_index)

    if verbose:
        print("\n[Step 1] Base case filled (substrings of length 1).")
        for i in range(n):
            nts = sorted(table[i][i].keys())
            print(f"  table[{i}][{i}]  char='{test_string[i]}'  ->  {{ {', '.join(nts)} }}")

    # ------------------------------------------------------------------
    # 4. Fill the recursive case (lengths 2 .. n)
    # ------------------------------------------------------------------
    _fill_table(table, n, pair_index)

    if verbose:
        print(f"\n[Step 2] Recursive case filled (substrings of length 2..{n}).")
        _print_table(table, n, test_string)

    # ------------------------------------------------------------------
    # 5. Check acceptance
    # ------------------------------------------------------------------
    accepted = _is_accepted(table, n, start_symbol)

    if verbose:
        top_cell = sorted(table[0][n - 1].keys())
        print(f"Top cell table[0][{n-1}] = {{ {', '.join(top_cell)} }}")
        if accepted:
            print(f"\n[ACCEPTED] '{start_symbol}' found in top cell.")
        else:
            print(f"\n[REJECTED] '{start_symbol}' NOT found in top cell.")

    # ------------------------------------------------------------------
    # 6. Build parse tree(s) via backtracking
    # ------------------------------------------------------------------
    tree = None
    all_trees = []

    if accepted:
        tree = _build_tree(table, start_symbol, 0, n - 1)
        all_trees = _build_all_trees(table, start_symbol, 0, n - 1)

        if verbose:
            print("\n" + "=" * 60)
            print("PARSE TREE")
            print("=" * 60)
            print(_pretty_tree(tree))

            if len(all_trees) > 1:
                print(f"\n[INFO] Grammar is ambiguous for this string: "
                      f"{len(all_trees)} distinct parse tree(s) found.")

            print("\n" + "=" * 60)
            print("NESTED PARSE TREE (for JSON / frontend)")
            print("=" * 60)
            _print_nested(tree, indent=2)
            print()

    return accepted, tree, all_trees


# ======================================================================
# Pretty-print the nested dict structure
# ======================================================================

def _print_nested(obj, indent=2, level=0):
    """
    Print a nested dict/list/str structure with indentation,
    so the developer can inspect the exact JSON-ready output.
    """
    pad = " " * (indent * level)

    if isinstance(obj, dict):
        print(f"{pad}{{")
        items = list(obj.items())
        for idx, (key, val) in enumerate(items):
            comma = "," if idx < len(items) - 1 else ""
            if isinstance(val, str):
                print(f"{pad}  \"{key}\": \"{val}\"{comma}")
            elif isinstance(val, list):
                print(f"{pad}  \"{key}\": [")
                for vi, v in enumerate(val):
                    vcomma = "," if vi < len(val) - 1 else ""
                    _print_nested_inline(v, indent, level + 2, vcomma)
                print(f"{pad}  ]{comma}")
        print(f"{pad}}}")

    elif isinstance(obj, str):
        print(f"{pad}\"{obj}\"")


def _print_nested_inline(obj, indent, level, trailing_comma):
    """Print a nested structure with a trailing comma for list items."""
    pad = " " * (indent * level)

    if isinstance(obj, dict):
        items = list(obj.items())
        if len(items) == 1:
            key, val = items[0]
            if isinstance(val, str):
                # Compact leaf:  {"A": "a"}
                print(f"{pad}{{\"{key}\": \"{val}\"}}{trailing_comma}")
                return
            elif isinstance(val, list):
                print(f"{pad}{{\"{key}\": [")
                for vi, v in enumerate(val):
                    vcomma = "," if vi < len(val) - 1 else ""
                    _print_nested_inline(v, indent, level + 1, vcomma)
                print(f"{pad}]}}{trailing_comma}")
                return
        # General dict
        print(f"{pad}{{")
        for idx, (key, val) in enumerate(items):
            comma = "," if idx < len(items) - 1 else ""
            if isinstance(val, str):
                print(f"{pad}  \"{key}\": \"{val}\"{comma}")
            elif isinstance(val, list):
                print(f"{pad}  \"{key}\": [")
                for vi, v in enumerate(val):
                    vcomma = "," if vi < len(val) - 1 else ""
                    _print_nested_inline(v, indent, level + 2, vcomma)
                print(f"{pad}  ]{comma}")
        print(f"{pad}}}{trailing_comma}")


# ======================================================================
# Convenience: import-friendly JSON export
# ======================================================================

def tree_to_json_string(tree):
    """
    Convert a parse tree (nested dicts/lists) to a JSON string.
    Uses only built-in Python — no 'json' import needed, but we
    *do* use the json module from the standard library since it's
    built-in and not an external package.
    """
    import json
    return json.dumps(tree, indent=2)


# ======================================================================
# MAIN EXECUTION BLOCK
# ======================================================================

if __name__ == "__main__":

    # ==================================================================
    #  EXAMPLE 1: Simple grammar   S -> AB,  A -> a,  B -> b
    # ==================================================================

    print("=" * 60)
    print("  EXAMPLE 1:  Simple grammar  (string = \"ab\")")
    print("=" * 60)

    grammar_1 = {
        'S':  [['A', 'B']],
        'A':  [['a']],
        'B':  [['b']],
    }

    accepted_1, tree_1, all_1 = cyk_parse(
        grammar_1, "ab", start_symbol="S"
    )

    # ==================================================================
    #  EXAMPLE 2:  a^n b^n  grammar from CNF_Converter Example 1
    #              Test string: "aabb" (should be ACCEPTED)
    # ==================================================================

    print("\n\n" + "=" * 60)
    print("  EXAMPLE 2:  a^n b^n  grammar  (string = \"aabb\")")
    print("=" * 60)

    # This is the CNF output from your CNF_Converter for  S -> aSb | e
    grammar_2 = {
        'S':   [['T_a', 'T_b'], ['T_a', 'Z1']],
        'S0':  [['T_a', 'T_b'], ['T_a', 'Z1']],
        'T_a': [['a']],
        'T_b': [['b']],
        'Z1':  [['S', 'T_b']],
    }

    accepted_2, tree_2, all_2 = cyk_parse(
        grammar_2, "aabb", start_symbol="S0"
    )

    # ==================================================================
    #  EXAMPLE 3:  Same grammar, REJECTED string "aab"
    # ==================================================================

    print("\n\n" + "=" * 60)
    print("  EXAMPLE 3:  a^n b^n  grammar  (string = \"aab\" — REJECTED)")
    print("=" * 60)

    accepted_3, tree_3, _ = cyk_parse(
        grammar_2, "aab", start_symbol="S0"
    )

    # ==================================================================
    #  EXAMPLE 4:  Compact string format (auto-detected)
    # ==================================================================

    print("\n\n" + "=" * 60)
    print("  EXAMPLE 4:  Compact format  (string = \"ab\")")
    print("=" * 60)

    grammar_4_compact = {
        'S': ['AB'],
        'A': ['a'],
        'B': ['b'],
    }

    accepted_4, tree_4, _ = cyk_parse(
        grammar_4_compact, "ab", start_symbol="S"
    )

    # ==================================================================
    #  EXAMPLE 5:  Complex grammar from CNF_Converter Example 2
    #              S -> ASB | e,  A -> aAS | a,  B -> SbS | A | bb
    #              Test string: "aab"
    # ==================================================================

    print("\n\n" + "=" * 60)
    print("  EXAMPLE 5:  Complex grammar  (string = \"aab\")")
    print("=" * 60)

    grammar_5 = {
        'A':   [['a'], ['T_a', 'Z2'], ['T_a', 'A']],
        'B':   [['T_b', 'S'], ['S', 'Z3'], ['T_b', 'T_b'],
                ['T_a', 'Z2'], ['T_a', 'A'], ['a'], ['b'], ['S', 'T_b']],
        'S':   [['A', 'B'], ['A', 'Z1']],
        'S0':  [['A', 'B'], ['A', 'Z1']],
        'T_a': [['a']],
        'T_b': [['b']],
        'Z1':  [['S', 'B']],
        'Z2':  [['A', 'S']],
        'Z3':  [['T_b', 'S']],
    }

    accepted_5, tree_5, all_5 = cyk_parse(
        grammar_5, "aab", start_symbol="S0"
    )

    if all_5:
        print(f"\n[INFO] Total parse trees: {len(all_5)}")

    # ==================================================================
    #  SUMMARY
    # ==================================================================

    print("\n\n" + "=" * 60)
    print("  SUMMARY")
    print("=" * 60)
    results = [
        ("Example 1", "ab",   accepted_1),
        ("Example 2", "aabb", accepted_2),
        ("Example 3", "aab",  accepted_3),
        ("Example 4", "ab",   accepted_4),
        ("Example 5", "aab",  accepted_5),
    ]
    for name, string, acc in results:
        status = "ACCEPTED" if acc else "REJECTED"
        print(f"  {name:12s}  \"{string:6s}\"  ->  {status}")
