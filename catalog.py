"""Math characters with human names, semantic aliases and Unicode metadata."""

import re
import unicodedata


# glyph | human label | TeX command | additional search terms
_CURATED = {
    "Operators": r"""
∑|Sum|sum|summation,sigma,total
∏|Product|prod|product,pi,multiply all
∐|Coproduct|coprod|disjoint product
∫|Integral|int|integration,integrate
∬|Double integral|iint|surface integral
∭|Triple integral|iiint|volume integral
∮|Contour integral|oint|closed integral
∯|Closed surface integral|oiint|surface contour integral
∰|Closed volume integral|oiiint|volume contour integral
∇|Gradient|nabla|del,nabla,gradient operator
∂|Partial derivative|partial|partial,differentiation
∞|Infinity|infty|infinite
√|Square root|sqrt|radical,root
∛|Cube root||third root
∜|Fourth root||quartic root
±|Plus or minus|pm|plus minus
∓|Minus or plus|mp|minus plus
−|Minus||subtract,subtraction
×|Multiply|times|multiplication,times,cross product
÷|Divide|div|division,obelus
⋅|Dot product|cdot|multiply,multiplication dot
·|Middle dot|cdotp|centered dot
∘|Composition|circ|function composition,ring operator
∙|Bullet operator|bullet|multiplication bullet
⊕|Direct sum|oplus|circled plus,xor
⊖|Circled minus|ominus|circle minus
⊗|Tensor product|otimes|circled times,kronecker product
⊘|Circled division|oslash|circle slash
⊙|Circled dot|odot|circle dot
⊚|Circled ring|circledcirc|circle ring
⊛|Circled asterisk|circledast|circle star
⊞|Box plus|boxplus|boxed plus
⊟|Box minus|boxminus|boxed minus
⊠|Box times|boxtimes|boxed multiply
⊡|Box dot|boxdot|boxed dot
∗|Asterisk operator|ast|star operator
⋆|Star operator|star|star
∧|Logical and|wedge|and,conjunction,meet
∨|Logical or|vee|or,disjunction,join
⋀|Big logical and|bigwedge|big wedge,n ary conjunction
⋁|Big logical or|bigvee|big vee,n ary disjunction
∔|Dot plus|dotplus|dotted plus
∖|Set difference|setminus|backslash,relative complement
⨿|Amalgamation|amalg|amalgam,coproduct
⨁|Big direct sum|bigoplus|big circled plus
⨂|Big tensor product|bigotimes|big circled times
⨀|Big circled dot|bigodot|n ary circled dot
ℓ|Script l|ell|ell,length
ℏ|Reduced Planck constant|hbar|h bar,h slash
ℑ|Imaginary part|Im|imaginary,imag part
ℜ|Real part|Re|real part operator
℘|Weierstrass p|wp|elliptic function
""",
    "Relations": r"""
=|Equals||equal,equality
≠|Not equal|neq|unequal,ne,not equals
≈|Approximately equal|approx|approximate,about,almost equal
≃|Asymptotically equal|simeq|asymptotic,similar equal
≅|Congruent|cong|congruence,approximately equal to
≡|Identical|equiv|equivalence,identical to
≢|Not identical|not\equiv|not equivalent
≜|Defined as|triangleq|definition,delta equals
≔|Colon equals|coloneqq|defined as,definition
≕|Equals colon|eqqcolon|definition
≐|Dot equals|doteq|approaches the limit
≟|Question equals||questioned equality
∝|Proportional|propto|proportional to,proportion
<|Less than||less,lt
>|Greater than||greater,gt
≤|Less or equal|leq|less than or equal,le
≥|Greater or equal|geq|greater than or equal,ge
≪|Much less|ll|much less than
≫|Much greater|gg|much greater than
≲|Less or similar|lesssim|less than or approximately equal
≳|Greater or similar|gtrsim|greater than or approximately equal
≰|Not less or equal|nleq|not less than or equal
≱|Not greater or equal|ngeq|not greater than or equal
≮|Not less|nless|not less than
≯|Not greater|ngtr|not greater than
≺|Precedes|prec|precedence
≻|Succeeds|succ|succession
≼|Precedes or equal|preceq|precedes equal
≽|Succeeds or equal|succeq|succeeds equal
∼|Similar|sim|similarity,tilde operator
≁|Not similar|nsim|not tilde
≍|Equivalent|asymp|asymptotically equivalent
≊|Almost equal or equal||approximately equal or equal
≉|Not almost equal||not approximately equal
∣|Divides|mid|divisibility,vertical bar
∤|Does not divide|nmid|not divides
∥|Parallel|parallel|parallel to
∦|Not parallel|nparallel|not parallel to
⊥|Perpendicular|perp|orthogonal,bottom,falsum
⋈|Bowtie|bowtie|join
""",
    "Sets": r"""
ℝ|Real numbers|mathbb{R}|reals,real,R,bb R,double struck R,blackboard R
ℕ|Natural numbers|mathbb{N}|naturals,natural,N,bb N,double struck N,blackboard N
ℤ|Integers|mathbb{Z}|integer,whole integers,Z,bb Z,double struck Z,blackboard Z
ℚ|Rational numbers|mathbb{Q}|rationals,rational,Q,bb Q,double struck Q,blackboard Q
ℂ|Complex numbers|mathbb{C}|complex,C,bb C,double struck C,blackboard C
ℙ|Double-struck P|mathbb{P}|bb P,blackboard P
ℍ|Quaternions|mathbb{H}|quaternion,bb H,double struck H,blackboard H
∅|Empty set|varnothing|empty,null set,nothing
∈|Element of|in|member of,belongs to,membership
∉|Not an element|notin|not in,not member of
∋|Contains element|ni|such that,contains member
∌|Does not contain element|not\ni|not contains member
⊂|Subset|subset|subset of,proper subset
⊃|Superset|supset|superset of,proper superset
⊆|Subset or equal|subseteq|subset equal
⊇|Superset or equal|supseteq|superset equal
⊊|Strict subset|subsetneq|subset not equal
⊋|Strict superset|supsetneq|superset not equal
⊄|Not a subset|nsubset|not subset
⊅|Not a superset|nsupset|not superset
⊈|Not subset or equal|nsubseteq|not subset equal
⊉|Not superset or equal|nsupseteq|not superset equal
∪|Union|cup|set union
∩|Intersection|cap|set intersection
⋃|Big union|bigcup|union of sets,n ary union
⋂|Big intersection|bigcap|intersection of sets
⊎|Multiset union|uplus|disjoint union
⊔|Square union|sqcup|join,square cup
⊓|Square intersection|sqcap|meet,square cap
⊏|Square subset|sqsubset|square subset of
⊐|Square superset|sqsupset|square superset of
⊑|Square subset or equal|sqsubseteq|square subset equal
⊒|Square superset or equal|sqsupseteq|square superset equal
∁|Complement|complement|set complement
ℵ|Aleph|aleph|aleph,cardinal,infinite cardinal
ℶ|Beth|beth|beth,cardinal
ℷ|Gimel|gimel|gimel,cardinal
ℸ|Daleth|daleth|daleth,cardinal
""",
    "Logic": r"""
∀|For all|forall|universal,all,every
∃|Exists|exists|existential,there exists
∄|Does not exist|nexists|not exists
¬|Not|neg|negation,logical not
⊤|True|top|truth,verum,top
⊢|Proves|vdash|turnstile,entails syntactically,provable
⊣|Left turnstile|dashv|reverse turnstile
⊨|Models|models|semantic entailment,satisfies,double turnstile
⊬|Does not prove|nvdash|not provable
⊭|Does not model|nvDash|does not satisfy,not semantic entailment
⊩|Forces|Vdash|forcing,double vertical turnstile
⊪|Triple turnstile|Vvdash|triple vertical turnstile
⊫|Double vertical double turnstile|VDash|double vertical double dash
∴|Therefore|therefore|thus,hence
∵|Because|because|since
∎|End of proof||qed,tombstone
""",
    "Arrows": r"""
→|Right arrow|rightarrow|right,to,maps
←|Left arrow|leftarrow|left,from
↔|Left-right arrow|leftrightarrow|both directions,bidirectional
↑|Up arrow|uparrow|up
↓|Down arrow|downarrow|down
↕|Up-down arrow|updownarrow|vertical both directions
⇒|Implies|Rightarrow|implication,double right arrow
⇐|Implied by|Leftarrow|double left arrow
⇔|If and only if|Leftrightarrow|iff,equivalence,double arrow
⇑|Double up arrow|Uparrow|double up
⇓|Double down arrow|Downarrow|double down
⇕|Double up-down arrow|Updownarrow|double vertical arrow
↦|Maps to|mapsto|mapsto,function map
↤|Maps from|mapsfrom|mapsfrom
⟶|Long right arrow|longrightarrow|long to
⟵|Long left arrow|longleftarrow|long from
⟷|Long left-right arrow|longleftrightarrow|long bidirectional
⟹|Long implies|Longrightarrow|long implication
⟸|Long implied by|Longleftarrow|long reverse implication
⟺|Long iff|Longleftrightarrow|long equivalence
⟼|Long maps to|longmapsto|long map
↪|Right hook arrow|hookrightarrow|embedding,hook right
↩|Left hook arrow|hookleftarrow|hook left
↗|Northeast arrow|nearrow|up right
↘|Southeast arrow|searrow|down right
↙|Southwest arrow|swarrow|down left
↖|Northwest arrow|nwarrow|up left
↠|Right two-headed arrow|twoheadrightarrow|surjection,two head right
↞|Left two-headed arrow|twoheadleftarrow|two head left
⇀|Right harpoon up|rightharpoonup|right harpoon
⇁|Right harpoon down|rightharpoondown|right lower harpoon
↼|Left harpoon up|leftharpoonup|left harpoon
↽|Left harpoon down|leftharpoondown|left lower harpoon
⇌|Equilibrium|rightleftharpoons|reversible reaction,opposing harpoons
⇋|Left-right harpoons|leftrightharpoons|opposing harpoons
↛|Not right arrow|nrightarrow|not to
↚|Not left arrow|nleftarrow|not from
↮|Not left-right arrow|nleftrightarrow|not bidirectional
⇏|Does not imply|nRightarrow|not implication
⇍|Not implied by|nLeftarrow|not reverse implication
⇎|Not iff|nLeftrightarrow|not equivalence
↝|Right wave arrow|rightsquigarrow|squiggly arrow,right squiggle
↻|Clockwise arrow|circlearrowright|clockwise rotation
↺|Counterclockwise arrow|circlearrowleft|anticlockwise rotation
""",
    "Geometry & punctuation": r"""
∠|Angle|angle|angle sign
∡|Measured angle|measuredangle|measured angle sign
∢|Spherical angle|sphericalangle|sphere angle
°|Degree||degrees
′|Prime|prime|first derivative,prime mark
″|Double prime||second derivative
‴|Triple prime||third derivative
⁗|Quadruple prime||fourth derivative
…|Horizontal ellipsis|ldots|ellipsis,dots,three dots
⋯|Centered ellipsis|cdots|centered dots
⋮|Vertical ellipsis|vdots|vertical dots
⋱|Diagonal ellipsis|ddots|diagonal dots
⋰|Ascending ellipsis||ascending diagonal dots
⌊|Left floor|lfloor|floor left
⌋|Right floor|rfloor|floor right
⌈|Left ceiling|lceil|ceiling left
⌉|Right ceiling|rceil|ceiling right
⟨|Left angle bracket|langle|angle bracket left,bra
⟩|Right angle bracket|rangle|angle bracket right,ket
⟦|Left double bracket|llbracket|double square bracket left
⟧|Right double bracket|rrbracket|double square bracket right
⦃|Left white brace||white curly bracket left
⦄|Right white brace||white curly bracket right
""",
}

_COMMON = set("∑∏∫∇∂∞√±×÷≈≠≤≥∈∉∪∩⊂⊆ℝℕℤℚℂ∀∃¬→⇒⇔")

# Unicode encodes these historical styled letters outside the math alphabet block.
_LETTERLIKE = {
    "ℂ": ("double-struck", "C"), "ℍ": ("double-struck", "H"),
    "ℕ": ("double-struck", "N"), "ℙ": ("double-struck", "P"),
    "ℚ": ("double-struck", "Q"), "ℝ": ("double-struck", "R"),
    "ℤ": ("double-struck", "Z"), "ℬ": ("script", "B"),
    "ℰ": ("script", "E"), "ℱ": ("script", "F"),
    "ℋ": ("script", "H"), "ℐ": ("script", "I"),
    "ℒ": ("script", "L"), "ℳ": ("script", "M"),
    "ℛ": ("script", "R"), "ℯ": ("script", "e"),
    "ℊ": ("script", "g"), "ℴ": ("script", "o"),
    "ℭ": ("fraktur", "C"), "ℌ": ("fraktur", "H"),
    "ℑ": ("fraktur", "I"), "ℜ": ("fraktur", "R"),
    "ℨ": ("fraktur", "Z"), "ℎ": ("italic", "h"),
}

_STYLES = {
    "bold": "mathbf", "italic": "mathit", "bold italic": "boldsymbol",
    "script": "mathcal", "bold script": "", "fraktur": "mathfrak",
    "double-struck": "mathbb", "bold fraktur": "", "sans-serif": "mathsf",
    "sans-serif bold": "", "sans-serif italic": "",
    "sans-serif bold italic": "", "monospace": "mathtt",
}
_DIGITS = dict(zip("zero one two three four five six seven eight nine".split(), "0123456789"))
_GREEK = "alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu nu xi omicron pi rho sigma tau upsilon phi chi psi omega".split()


def _entry(glyph, label, category, aliases=(), priority=30, latex=""):
    name = unicodedata.name(glyph)
    return {"glyph": glyph, "label": label, "category": category,
            "aliases": list(dict.fromkeys(a for a in aliases if a)),
            "priority": priority, "name": name,
            "codepoint": f"U+{ord(glyph):04X}", "latex": latex}


def _styled(glyph, style, letter, capital=False):
    """Keep Latin case explicit: mathematical A and a are separate characters."""
    if letter in _DIGITS:
        letter = _DIGITS[letter]
    special_commands = {"dotless i": "imath", "dotless j": "jmath", "final sigma": "varsigma"}
    latex_letter = "\\" + letter if letter in _GREEK else letter
    if letter in special_commands:
        latex_letter = "\\" + special_commands[letter]
    if capital and letter in _GREEK:
        latex_letter = "\\" + letter.title()
    command = _STYLES.get(style, "")
    if style == "bold" and (letter in _GREEK or letter == "final sigma"):
        command = "boldsymbol"
    latex = f"\\{command}{{{latex_letter}}}" if command and " " not in latex_letter else ""
    case = "capital " if capital and len(letter) > 1 else ""
    label = f"{style.title()} {case}{letter}"
    aliases = [f"{style} {case}{letter}", f"{style} {'uppercase' if capital else 'lowercase'} {letter}"]
    if style == "double-struck":
        aliases.extend([f"bb {letter}", f"blackboard {letter}", f"double struck {letter}"])
    if style == "script":
        aliases.extend([f"calligraphic {letter}", f"cal {letter}"])
    if style == "fraktur":
        aliases.append(f"gothic {letter}")
    if latex:
        aliases.extend([latex, latex.lstrip("\\")])
    return _entry(glyph, label, "Styled letters", aliases, 15, latex)


def build_catalog():
    """Return independent records; glyphs and codepoints are unique."""
    entries = {}
    for category, data in _CURATED.items():
        for line in data.strip().splitlines():
            glyph, label, command, aliases = line.split("|")
            latex = "\\" + command if command else ""
            terms = aliases.split(",") + ([latex, command] if command else [])
            entries[glyph] = _entry(glyph, label, category, terms,
                                    100 if glyph in _COMMON else 40, latex)

    for code in range(0x391, 0x3CA):
        glyph = chr(code)
        name = unicodedata.name(glyph, "")
        match = re.fullmatch(r"GREEK (CAPITAL|SMALL) LETTER (\w+)", name)
        if not match:
            continue
        capital, letter = match.groups()
        letter = letter.lower()
        if letter == "lamda":
            letter = "lambda"
        if letter not in _GREEK:
            continue
        capital = capital == "CAPITAL"
        label = ("Capital " if capital else "") + letter.title()
        command = letter.title() if capital else letter
        # Uppercase Greek letters identical to Latin have no standard TeX macro.
        latex = "\\" + command if not capital or letter in "gamma delta theta lambda xi pi sigma upsilon phi psi omega".split() else ""
        aliases = [letter, f"{'uppercase' if capital else 'lowercase'} {letter}", f"Greek {letter}"]
        if latex:
            aliases.extend([latex, command])
        entries[glyph] = _entry(glyph, label, "Greek", aliases, 65, latex)

    for glyph, letter, command in [("ς", "final sigma", "varsigma"),
                                   ("ϵ", "epsilon symbol", "epsilon"),
                                   ("ϑ", "theta symbol", "vartheta"),
                                   ("ϰ", "kappa symbol", "varkappa"),
                                   ("ϕ", "phi symbol", "phi"),
                                   ("ϱ", "rho symbol", "varrho"),
                                   ("ϖ", "pi symbol", "varpi")]:
        entries[glyph] = _entry(glyph, letter.title(), "Greek",
                                [letter, command, "\\" + command], 35, "\\" + command)
    # Traditional TeX epsilon and phi use the symbol forms; letter forms are variants.
    entries["ε"]["latex"] = "\\varepsilon"
    entries["ε"]["aliases"] = ["epsilon", "lowercase epsilon", "Greek epsilon", "varepsilon", "\\varepsilon"]
    entries["φ"]["latex"] = "\\varphi"
    entries["φ"]["aliases"] = ["phi", "lowercase phi", "Greek phi", "varphi", "\\varphi"]

    for code in range(0x1D400, 0x1D800):
        glyph = chr(code)
        name = unicodedata.name(glyph, "")
        match = re.fullmatch(r"MATHEMATICAL (.+?) (CAPITAL|SMALL|DIGIT) (.+)", name)
        if match:
            style, case, letter = match.groups()
            letter = letter.lower().replace("lamda", "lambda")
            if case != "DIGIT" and len(letter) == 1 and case == "CAPITAL":
                letter = letter.upper()
            entries[glyph] = _styled(glyph, style.lower(), letter, case == "CAPITAL")
        elif name.startswith("MATHEMATICAL "):
            # Styled partial, nabla, final sigma and Greek symbol variants.
            words = name.removeprefix("MATHEMATICAL ").lower()
            entries[glyph] = _entry(glyph, words.title(), "Styled letters", [words], 10)

    for glyph, (style, letter) in _LETTERLIKE.items():
        record = _styled(glyph, style, letter, letter.isupper())
        if glyph in entries:
            entries[glyph]["aliases"] = list(dict.fromkeys(entries[glyph]["aliases"] + record["aliases"]))
        else:
            entries[glyph] = record

    scripts = {
        "Superscripts": "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁼⁽⁾ⁿⁱ",
        "Subscripts": "₀₁₂₃₄₅₆₇₈₉₊₋₌₍₎ₐₑₕᵢⱼₖₗₘₙₒₚᵣₛₜᵤᵥₓ",
    }
    for category, glyphs in scripts.items():
        style = category[:-1].lower()
        for glyph in glyphs:
            base = unicodedata.normalize("NFKC", glyph)
            aliases = [f"{style} {base}"]
            if base.isdigit():
                aliases.extend([f"{'sup' if style == 'superscript' else 'sub'} {base}"])
                aliases.append(f"{'power' if style == 'superscript' else 'index'} {base}")
            if glyph == "²":
                aliases.append("squared")
            elif glyph == "³":
                aliases.append("cubed")
            entries[glyph] = _entry(glyph, f"{style.title()} {base}", category, aliases, 30)
    return list(entries.values())
