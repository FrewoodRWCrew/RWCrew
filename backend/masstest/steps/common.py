# What every step shares: pointing an issue back to its source lines and
# logging a refused API call with its code, screen text and solution.

from datetime import datetime

from masstest.client import CallResult
from masstest.messages import split_detail, translate
from masstest.report import BLOCKER, ERROR, IssueLog
from masstest.solutions import RULES


def source_fields(rows: list[dict]) -> dict[str, str]:
    """The issue columns that point back to the source lines."""
    return {
        "source_file": str(rows[0].get("source_file") or "") if rows else "",
        "source_rows": ", ".join(str(row.get("source_row") or "") for row in rows),
        "source_values": "\n".join(str(row.get("source_values") or "") for row in rows),
    }


def log_refusal(
    log: IssueLog,
    step: str,
    module: str,
    result: CallResult,
    description: str,
    rows: list[dict],
    context: dict,
    severity: str = ERROR,
) -> None:
    """Log a call that didn't succeed, with the API's code, the text the
    screen would show and the rule's proposed solution. No answer at all is a
    blocker; a 5xx is a bug; a 422 without a known code is unexpected."""
    request = f"{result.method} {result.path}"
    if result.status == 0:
        code, params, text = "network", [str(result.body)], str(result.body)
        severity = BLOCKER
    elif result.status >= 500:
        code, params, text = "server_error", [], str(result.body)[:500]
        context = {**context, "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    else:
        code, params = split_detail(result.detail)
        text = translate(module, result.detail)
        if code not in RULES and result.status == 422:
            code, params = "unexpected_response", []
    log.add(
        step,
        code,
        f"{description} {text}".strip(),
        severity=severity,
        params=params,
        context=context,
        module=module,
        text=text,
        request=request,
        http_status=result.status,
        **source_fields(rows),
    )
