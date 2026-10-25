# The karcode formula: the lock on every kar opens with a code derived from
# its kar number, e.g. LEFT(kar*500+3118; 4) -> kar 36 = 21118 -> "2111".
# The formula is an Excel-like expression an admin edits on KarTracker's
# "Instellingen" screen (stored in KarTracker_settings); this file is the
# only place that checks and computes it.
#
# Syntax (case-insensitive): the variable `kar`, numbers (`,` or `.` as the
# decimal separator), + - * / ^, parentheses and the functions LEFT, RIGHT,
# MID, MOD, INT, ROUND and ABS, with `;` between arguments as in the Belgian
# Excel. A leading "=" is allowed. Evaluated by walking a whitelist of
# Python AST nodes — never eval() — so nothing else can run.

import ast
import math
import re
from decimal import ROUND_HALF_UP, Decimal

# The formula used until an admin saves another one (the old Excel sheet).
DEFAULT_KARCODE_FORMULA = "LEFT(kar*500+3118; 4)"

# Guards against abuse: formula length, size of any number along the way,
# and the exponent of ^ (10^9999 would otherwise take ages).
MAX_FORMULA_LENGTH = 500
MAX_ABS_VALUE = 1e15
MAX_EXPONENT = 64
MAX_KAR_LENGTH = 20

# Only these characters may appear in a formula (everything else, such as
# quotes, underscores or brackets, is refused before parsing).
_ALLOWED_CHARACTERS = re.compile(r"[A-Za-z0-9\s+\-*/^(),;.=]")


class KarcodeError(Exception):
    """A formula or kar number that can't give a code. `code` is a stable key
    the frontend translates (karTracker.karcode.errors.<code>); `params` fill
    in the details (the unknown name, the function...).
    """

    def __init__(self, code: str, *params: object) -> None:
        super().__init__(code)
        self.code = code
        self.params = [str(param) for param in params]

    @property
    def detail(self) -> str:
        """"code|param|param" — what the API returns as its error detail."""
        return "|".join([self.code, *self.params])


# ---------------------------------------------------------------------------
# Value helpers (Excel-like coercion between numbers and text)
# ---------------------------------------------------------------------------


def _checked(value: float | int) -> float | int:
    """Refuse numbers that are too large (or not a number at all)."""
    if isinstance(value, float) and not math.isfinite(value):
        raise KarcodeError("number_too_large")
    if abs(value) > MAX_ABS_VALUE:
        raise KarcodeError("number_too_large")
    return value


def _to_number(value: float | int | str) -> float | int:
    """A number as is; text (e.g. the result of LEFT) read back as a number,
    like Excel does when text is used in a calculation.
    """
    if not isinstance(value, str):
        return value
    try:
        number = float(value) if "." in value else int(value)
    except ValueError as error:
        raise KarcodeError("not_a_number", value) from error
    return _checked(number)


def _to_text(value: float | int | str) -> str:
    """Text as is; a whole number without decimals ("21118", not "21118.0"),
    any other number with at most 15 significant digits like Excel.
    """
    if isinstance(value, str):
        return value
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    if isinstance(value, float):
        return f"{value:.15g}"
    return str(value)


def _to_count(value: float | int | str, function: str) -> int:
    """A whole, non-negative number of characters (Excel truncates decimals)."""
    count = int(_to_number(value))
    if count < 0:
        raise KarcodeError("wrong_arguments", function)
    return count


# ---------------------------------------------------------------------------
# Functions
# ---------------------------------------------------------------------------


def _left(text: object, count: object = 1) -> str:
    return _to_text(text)[: _to_count(count, "LEFT")]


def _right(text: object, count: object = 1) -> str:
    characters = _to_count(count, "RIGHT")
    value = _to_text(text)
    return value[-characters:] if characters else ""


def _mid(text: object, start: object, count: object) -> str:
    first = int(_to_number(start))
    if first < 1:
        raise KarcodeError("wrong_arguments", "MID")
    return _to_text(text)[first - 1 : first - 1 + _to_count(count, "MID")]


def _mod(number: object, divisor: object) -> float | int:
    divide_by = _to_number(divisor)
    if divide_by == 0:
        raise KarcodeError("division_by_zero")
    # Python's % takes the divisor's sign, exactly like Excel's MOD.
    return _to_number(number) % divide_by


def _int(number: object) -> int:
    # Excel's INT rounds down (also for negative numbers).
    return math.floor(_to_number(number))


def _round(number: object, digits: object = 0) -> float | int:
    # Excel rounds halves away from zero (Python's round() would go to even).
    places = int(_to_number(digits))
    if abs(places) > 15:
        raise KarcodeError("wrong_arguments", "ROUND")
    rounded = Decimal(str(_to_number(number))).quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP)
    return int(rounded) if places <= 0 else float(rounded)


def _abs(number: object) -> float | int:
    return abs(_to_number(number))


# Name -> (function, minimum arguments, maximum arguments).
_FUNCTIONS = {
    "LEFT": (_left, 1, 2),
    "RIGHT": (_right, 1, 2),
    "MID": (_mid, 3, 3),
    "MOD": (_mod, 2, 2),
    "INT": (_int, 1, 1),
    "ROUND": (_round, 1, 2),
    "ABS": (_abs, 1, 1),
}

# The list shown in the formula help on the Instellingen screen.
FUNCTION_NAMES = list(_FUNCTIONS)


# ---------------------------------------------------------------------------
# Parsing + evaluation
# ---------------------------------------------------------------------------


def _parse(formula: str) -> ast.expr:
    """Check the characters, turn the Excel notation into Python's and parse
    it into an expression tree (not yet checked node by node).
    """
    text = (formula or "").strip()
    if text.startswith("="):
        text = text[1:].strip()
    if not text:
        raise KarcodeError("empty_formula")
    if len(text) > MAX_FORMULA_LENGTH:
        raise KarcodeError("too_long", MAX_FORMULA_LENGTH)
    for character in text:
        if not _ALLOWED_CHARACTERS.fullmatch(character):
            raise KarcodeError("invalid_character", character)
    # Excel -> Python: decimal comma -> point, ";" between arguments -> ",",
    # "^" -> "**". A stray "=" inside the formula is a syntax error below.
    python_text = text.replace(",", ".").replace(";", ",").replace("^", "**")
    try:
        return ast.parse(python_text, mode="eval").body
    except SyntaxError as error:
        raise KarcodeError("invalid_syntax") from error


def _evaluate(node: ast.expr, kar: int) -> float | int | str:
    """Compute one node of the tree; any node type not handled here is refused."""
    # A plain number.
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
        return _checked(node.value)

    # The only variable: the kar number.
    if isinstance(node, ast.Name):
        if node.id.lower() != "kar":
            raise KarcodeError("unknown_name", node.id)
        return kar

    # -x / +x
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
        value = _to_number(_evaluate(node.operand, kar))
        return -value if isinstance(node.op, ast.USub) else value

    # x + y, x - y, x * y, x / y, x ^ y
    if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow)):
        left = _to_number(_evaluate(node.left, kar))
        right = _to_number(_evaluate(node.right, kar))
        if isinstance(node.op, ast.Add):
            return _checked(left + right)
        if isinstance(node.op, ast.Sub):
            return _checked(left - right)
        if isinstance(node.op, ast.Mult):
            return _checked(left * right)
        if isinstance(node.op, ast.Div):
            if right == 0:
                raise KarcodeError("division_by_zero")
            return _checked(left / right)
        # Power: cap the exponent before computing, then the result.
        if abs(right) > MAX_EXPONENT:
            raise KarcodeError("number_too_large")
        if left == 0 and right < 0:
            raise KarcodeError("division_by_zero")
        try:
            result = left**right
        except OverflowError as error:
            raise KarcodeError("number_too_large") from error
        if isinstance(result, complex):
            raise KarcodeError("not_a_number", _to_text(left))
        return _checked(result)

    # FUNCTION(argument; argument)
    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name):
            raise KarcodeError("invalid_syntax")
        name = node.func.id.upper()
        if name not in _FUNCTIONS:
            raise KarcodeError("unknown_function", node.func.id)
        function, minimum, maximum = _FUNCTIONS[name]
        if node.keywords or not minimum <= len(node.args) <= maximum:
            raise KarcodeError("wrong_arguments", name)
        return function(*[_evaluate(argument, kar) for argument in node.args])

    # Anything else (attributes, comparisons, lists, text...) isn't allowed.
    raise KarcodeError("invalid_syntax")


def parse_kar_number(kar: str) -> int:
    """The kar number as a whole number ("36", " 036 "); anything else can't
    go through the formula.
    """
    text = (kar or "").strip()
    if not text or len(text) > MAX_KAR_LENGTH or not text.isdigit():
        raise KarcodeError("kar_not_numeric", text)
    return int(text)


def compute_code(formula: str, kar: str) -> str:
    """The lock code of kar number `kar` according to `formula`."""
    kar_number = parse_kar_number(kar)
    code = _to_text(_evaluate(_parse(formula), kar_number))
    if not code:
        raise KarcodeError("empty_result")
    return code


def validate_formula(formula: str) -> str:
    """Check a formula before saving it (syntax + a trial run with kar 1) and
    return it trimmed. Raises KarcodeError when it can't be used.
    """
    compute_code(formula, "1")
    return formula.strip()
