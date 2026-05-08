"""
CFG to CNF Converter.

Input:  A Python dict representing a Context-Free Grammar.
        Non-terminals are SINGLE uppercase letters; terminals are single lowercase letters.
        The string 'e' represents epsilon.
        Example: {'S': ['aSb', 'e'], 'A': ['a']}

Output: A Python dict in strict Chomsky Normal Form:
        Every rule is either  A -> BC  (two non-terminals)
                          or  A -> a   (one terminal).

Algorithm steps (applied in order):
  1. Add new start symbol   S0 -> S
  2. Eliminate epsilon-productions
  3. Eliminate unit productions
  4. Eliminate useless symbols (non-generating & unreachable)
  5. Replace terminals in mixed bodies
  6. Break down long bodies (len > 2)
"""

# ======================================================================
# Internal Representation
# ======================================================================
#
# Internally, a grammar is:
#   dict[str, list[tuple[str, ...]]]
#
# Each key is a non-terminal name (str), and each value is a list of
# productions, where each production is a *tuple of symbols*.
#   - An empty tuple () represents epsilon.
#   - A terminal is a lowercase single char like 'a', 'b'.
#   - A non-terminal is an uppercase string like 'S', 'S0', 'X_a', 'Y1'.
#
# The raw user input uses compact strings like 'aSb'.  We parse those
# once at the boundary and work with tuples everywhere internally.
# ======================================================================


# ------------------------------------------------------------------
# Parsing / formatting helpers
# ------------------------------------------------------------------

def parse_body(body_str):
    """
    Parse a compact body string into a tuple of symbols.

    Raw input convention:
      - Each uppercase letter is a non-terminal.
      - Each lowercase letter is a terminal.
      - 'e' alone means epsilon.

    Examples:
        'aSb'  -> ('a', 'S', 'b')
        'ASB'  -> ('A', 'S', 'B')
        'e'    -> ()
        'a'    -> ('a',)
    """
    if body_str == "e":
        return ()
    return tuple(ch for ch in body_str)


def parse_grammar(raw):
    """Convert the user-facing dict[str, list[str]] into internal form."""
    grammar = {}
    for nt, bodies in raw.items():
        grammar[nt] = [parse_body(b) for b in bodies]
    return grammar


def is_nonterminal(sym):
    """A non-terminal starts with an uppercase letter (S, S0, X_a, Y1, ...)."""
    return sym[0].isupper()


def is_terminal(sym):
    """A terminal is a single lowercase letter."""
    return len(sym) == 1 and sym.islower()


def format_production(body_tuple):
    """Format a tuple of symbols into a readable string like 'A S B'."""
    if not body_tuple:
        return "epsilon"
    return " ".join(body_tuple)


def format_grammar(grammar):
    """Return a sorted, readable multi-line string of the grammar."""
    lines = []
    for nt in sorted(grammar.keys()):
        bodies = grammar[nt]
        rhs = " | ".join(format_production(b) for b in bodies)
        lines.append(f"  {nt} -> {rhs}")
    return "\n".join(lines)


def export_grammar(grammar):
    """
    Convert internal form back to a user-facing dict.

    Format:  dict[str, list[list[str]]]
    Each production body is a list of individual symbol strings.
    Examples:
        ('T_a', 'Z3')  ->  ['T_a', 'Z3']     (A -> BC)
        ('a',)         ->  ['a']              (A -> a)

    This avoids ambiguity when non-terminal names are multi-character.
    """
    result = {}
    for nt in sorted(grammar.keys()):
        result[nt] = [list(body) for body in grammar[nt]]
    return result


def _deduplicate(grammar):
    """
    Remove duplicate productions for every non-terminal.
    Preserves first-occurrence order.
    """
    deduped = {}
    for nt, prods in grammar.items():
        seen = set()
        unique = []
        for body in prods:
            if body not in seen:
                seen.add(body)
                unique.append(body)
        deduped[nt] = unique
    return deduped


# ------------------------------------------------------------------
# Step 1: Add a new start symbol
# ------------------------------------------------------------------

def step1_new_start(grammar, start):
    """
    Create S0 -> <start> so the start symbol never appears on any
    right-hand side.  Returns (new_grammar, new_start).
    """
    new_start = start + "0"
    # Make sure the name is unique
    while new_start in grammar:
        new_start += "0"
    new_grammar = {new_start: [(start,)]}
    new_grammar.update(grammar)
    return new_grammar, new_start


# ------------------------------------------------------------------
# Step 2: Eliminate epsilon-productions
# ------------------------------------------------------------------

def _find_nullable(grammar):
    """
    Return the set of nullable non-terminals (those that can derive epsilon).
    Uses a fixed-point algorithm.
    """
    nullable = set()

    # Seed: any NT with an explicit epsilon production
    for nt, prods in grammar.items():
        for body in prods:
            if body == ():
                nullable.add(nt)

    # Iterate until stable
    changed = True
    while changed:
        changed = False
        for nt, prods in grammar.items():
            if nt in nullable:
                continue
            for body in prods:
                if len(body) > 0 and all(s in nullable for s in body):
                    nullable.add(nt)
                    changed = True
                    break
    return nullable


def _subsets_without_nullable(body, nullable):
    """
    Generate all variants of `body` obtained by omitting every possible
    non-empty subset of nullable positions.  Always includes the
    original body itself.  Never includes the empty body.
    """
    nullable_positions = [i for i, s in enumerate(body) if s in nullable]
    n = len(nullable_positions)
    results = set()
    for mask in range(1 << n):          # 0 = omit nothing = original
        omit = set()
        for bit in range(n):
            if mask & (1 << bit):
                omit.add(nullable_positions[bit])
        variant = tuple(body[i] for i in range(len(body)) if i not in omit)
        if variant:                      # never add epsilon
            results.add(variant)
    return results


def step2_eliminate_epsilon(grammar, start):
    """
    Remove all epsilon-productions and add compensating productions
    that omit nullable symbols in every combination.
    """
    nullable = _find_nullable(grammar)

    new_grammar = {}
    for nt, prods in grammar.items():
        new_prods = set()
        for body in prods:
            if body == ():
                continue                  # drop epsilon production
            new_prods |= _subsets_without_nullable(body, nullable)
        new_grammar[nt] = list(new_prods)

    # NOTE: If the language includes the empty string, the only place
    # epsilon is allowed in CNF is on the start symbol.  We leave that
    # out here; a CYK parser can check for it separately.

    return new_grammar


# ------------------------------------------------------------------
# Step 3: Eliminate unit productions (A -> B)
# ------------------------------------------------------------------

def step3_eliminate_unit(grammar):
    """
    For every unit production A -> B, transitively replace it with
    B's non-unit productions.
    """
    # Build the transitive closure of unit-reachable NTs for each NT.
    unit_closure = {}
    for nt in grammar:
        reachable = set()
        stack = [nt]
        while stack:
            cur = stack.pop()
            if cur in reachable:
                continue
            reachable.add(cur)
            for body in grammar.get(cur, []):
                if len(body) == 1 and is_nonterminal(body[0]):
                    stack.append(body[0])
        unit_closure[nt] = reachable

    new_grammar = {}
    for nt in grammar:
        new_prods = set()
        for reachable_nt in unit_closure[nt]:
            for body in grammar.get(reachable_nt, []):
                # Skip unit productions themselves
                if len(body) == 1 and is_nonterminal(body[0]):
                    continue
                new_prods.add(body)
        new_grammar[nt] = list(new_prods)

    return new_grammar


# ------------------------------------------------------------------
# Step 4: Eliminate useless symbols
# ------------------------------------------------------------------

def _find_generating(grammar):
    """Return the set of generating (productive) non-terminals."""
    generating = set()
    changed = True
    while changed:
        changed = False
        for nt, prods in grammar.items():
            if nt in generating:
                continue
            for body in prods:
                if all(is_terminal(s) or s in generating for s in body):
                    generating.add(nt)
                    changed = True
                    break
    return generating


def _find_reachable(grammar, start):
    """Return the set of symbols reachable from `start`."""
    reachable = set()
    stack = [start]
    while stack:
        sym = stack.pop()
        if sym in reachable:
            continue
        reachable.add(sym)
        for body in grammar.get(sym, []):
            for s in body:
                if s not in reachable:
                    stack.append(s)
    return reachable


def step4_eliminate_useless(grammar, start):
    """
    Phase 1: remove non-generating symbols.
    Phase 2: remove unreachable symbols.
    """
    # Phase 1 -- generating
    generating = _find_generating(grammar)
    g1 = {}
    for nt, prods in grammar.items():
        if nt not in generating:
            continue
        kept = [b for b in prods
                if all(is_terminal(s) or s in generating for s in b)]
        if kept:
            g1[nt] = kept

    # Phase 2 -- reachable
    reachable = _find_reachable(g1, start)
    g2 = {}
    for nt, prods in g1.items():
        if nt not in reachable:
            continue
        kept = [b for b in prods
                if all(is_terminal(s) or s in reachable for s in b)]
        if kept:
            g2[nt] = kept

    return g2


# ------------------------------------------------------------------
# Step 5: Replace terminals in mixed / long bodies
# ------------------------------------------------------------------

def step5_replace_terminals(grammar):
    """
    For every production with body length >= 2, replace each terminal 'a'
    with a dedicated non-terminal X_a and add X_a -> a.
    """
    term_map = {}       # terminal char -> generated NT name

    new_grammar = {}
    for nt, prods in grammar.items():
        new_prods = []
        for body in prods:
            if len(body) >= 2:
                new_body = []
                for s in body:
                    if is_terminal(s):
                        if s not in term_map:
                            term_map[s] = f"T_{s}"
                        new_body.append(term_map[s])
                    else:
                        new_body.append(s)
                new_prods.append(tuple(new_body))
            else:
                new_prods.append(body)
        new_grammar[nt] = new_prods

    # Add helper rules  T_a -> a
    for terminal, nt_name in sorted(term_map.items()):
        new_grammar[nt_name] = [(terminal,)]

    return new_grammar


# ------------------------------------------------------------------
# Step 6: Break down long bodies (length > 2)
# ------------------------------------------------------------------

def step6_break_long(grammar):
    """
    Replace A -> B1 B2 ... Bn  (n > 2) with a right-linear chain:
      A  -> B1 Z1
      Z1 -> B2 Z2
      ...
      Z_{n-3} -> B_{n-2} Z_{n-2}
      Z_{n-2} -> B_{n-1} Bn

    Uses a reverse-mapping (pair_map) so that if the same pair of symbols
    has already been assigned a helper variable, it is reused instead of
    creating a duplicate.
    """
    counter = [0]       # mutable counter in a list for closure access

    # Maps a (sym1, sym2) pair -> the Z variable already assigned to it.
    pair_map = {}

    def get_or_create(pair, new_grammar):
        """Return an existing Z for `pair`, or create a fresh one."""
        if pair in pair_map:
            return pair_map[pair]
        counter[0] += 1
        name = f"Z{counter[0]}"
        pair_map[pair] = name
        new_grammar[name] = [pair]
        return name

    new_grammar = {}
    for nt, prods in grammar.items():
        new_prods = []
        for body in prods:
            if len(body) <= 2:
                new_prods.append(body)
            else:
                # Build the chain from right to left.
                symbols = list(body)

                # Start with the last pair
                last_pair = (symbols[-2], symbols[-1])
                prev = get_or_create(last_pair, new_grammar)

                # Middle pairs (if any)
                for i in range(len(symbols) - 3, 0, -1):
                    mid_pair = (symbols[i], prev)
                    prev = get_or_create(mid_pair, new_grammar)

                # First symbol paired with the chain variable
                new_prods.append((symbols[0], prev))

        # Use setdefault so we don't overwrite chain NTs already inserted
        if nt in new_grammar:
            new_grammar[nt] = new_prods + new_grammar[nt]
        else:
            new_grammar[nt] = new_prods

    return new_grammar


# ------------------------------------------------------------------
# Validation: verify the result is valid CNF
# ------------------------------------------------------------------

def validate_cnf(grammar):
    """
    Check that every production is either:
      - A -> a   (single terminal)
      - A -> BC  (exactly two non-terminals)
    Returns a list of violations (empty means valid).
    """
    violations = []
    for nt, prods in grammar.items():
        for body in prods:
            if len(body) == 1:
                if not is_terminal(body[0]):
                    violations.append(
                        f"  {nt} -> {format_production(body)}  "
                        f"[UNIT non-terminal, not allowed]")
            elif len(body) == 2:
                if not (is_nonterminal(body[0]) and is_nonterminal(body[1])):
                    violations.append(
                        f"  {nt} -> {format_production(body)}  "
                        f"[mixed or terminal pair, not allowed]")
            elif len(body) == 0:
                violations.append(
                    f"  {nt} -> epsilon  [epsilon not allowed (except start)]")
            else:
                violations.append(
                    f"  {nt} -> {format_production(body)}  "
                    f"[body length {len(body)} > 2]")
    return violations


# ------------------------------------------------------------------
# Master pipeline
# ------------------------------------------------------------------

def cfg_to_cnf(raw_grammar, start="S"):
    """
    Convert a CFG dictionary into Chomsky Normal Form.

    Parameters
    ----------
    raw_grammar : dict[str, list[str]]
        The CFG.  Keys = non-terminals, values = lists of production body
        strings.  Use 'e' for epsilon.  Example: {'S': ['aSb', 'e']}
    start : str
        The start symbol of the original grammar.

    Returns
    -------
    cnf_dict : dict[str, list[str]]
        The grammar in CNF (user-facing format).
    new_start : str
        The (possibly renamed) start symbol.
    """
    # Parse raw input into internal tuple-based form
    grammar = parse_grammar(raw_grammar)

    print("=== Original Grammar ===")
    print(format_grammar(grammar))

    # Step 1: New start symbol
    grammar, start = step1_new_start(grammar, start)
    grammar = _deduplicate(grammar)
    print("\n--- Step 1: Add new start symbol ---")
    print(format_grammar(grammar))

    # Step 2: Eliminate epsilon-productions
    grammar = step2_eliminate_epsilon(grammar, start)
    grammar = _deduplicate(grammar)
    print("\n--- Step 2: Eliminate epsilon-productions ---")
    print(format_grammar(grammar))

    # Step 3: Eliminate unit productions
    grammar = step3_eliminate_unit(grammar)
    grammar = _deduplicate(grammar)
    print("\n--- Step 3: Eliminate unit productions ---")
    print(format_grammar(grammar))

    # Step 4: Eliminate useless symbols
    grammar = step4_eliminate_useless(grammar, start)
    grammar = _deduplicate(grammar)
    print("\n--- Step 4: Eliminate useless symbols ---")
    print(format_grammar(grammar))

    # Step 5: Replace terminals in mixed bodies
    grammar = step5_replace_terminals(grammar)
    grammar = _deduplicate(grammar)
    print("\n--- Step 5: Replace terminals in mixed bodies ---")
    print(format_grammar(grammar))

    # Step 6: Break long bodies
    grammar = step6_break_long(grammar)
    grammar = _deduplicate(grammar)
    print("\n--- Step 6: Break long bodies -- FINAL CNF ---")
    print(format_grammar(grammar))

    # Validate
    violations = validate_cnf(grammar)
    if violations:
        print("\n[WARNING] CNF violations detected:")
        for v in violations:
            print(v)
    else:
        print("\n[OK] All productions are in valid CNF.")

    # Export to user-facing format
    cnf_dict = export_grammar(grammar)
    return cnf_dict, start


# ------------------------------------------------------------------
# Pretty-print the final dict
# ------------------------------------------------------------------

def print_cnf_dict(cnf_dict):
    """Print the CNF grammar as a copy-paste-ready Python dict."""
    print("\ncnf_grammar = {")
    for nt in sorted(cnf_dict.keys()):
        print(f"    {nt!r}: {cnf_dict[nt]!r},")
    print("}")


# ==================================================================
# Main -- test with sample grammars
# ==================================================================

if __name__ == "__main__":

    # ---- Example 1: S -> aSb | e  (generates a^n b^n) ----
    print("=" * 60)
    print("Example 1:  S -> aSb | e")
    print("=" * 60)

    grammar1 = {
        "S": ["aSb", "e"],
    }

    cnf1, start1 = cfg_to_cnf(grammar1, start="S")

    print("\n" + "=" * 50)
    print(f"FINAL CNF  (start = {start1})")
    print("=" * 50)
    print_cnf_dict(cnf1)

    # ---- Example 2: a more complex grammar ----
    print("\n\n" + "=" * 60)
    print("Example 2:  S -> ASB | e,  A -> aAS | a,  B -> SbS | A | bb")
    print("=" * 60)

    grammar2 = {
        "S": ["ASB", "e"],
        "A": ["aAS", "a"],
        "B": ["SbS", "A", "bb"],
    }

    cnf2, start2 = cfg_to_cnf(grammar2, start="S")

    print("\n" + "=" * 50)
    print(f"FINAL CNF  (start = {start2})")
    print("=" * 50)
    print_cnf_dict(cnf2)
