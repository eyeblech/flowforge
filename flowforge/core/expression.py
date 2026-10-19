"""Expression evaluation and template engine for dynamic workflow values."""

import json
import re
from datetime import datetime, timezone
from typing import Any, Dict
import jinja2
from jinja2 import Environment, select_autoescape


class DotAccessibleDict(dict):
    """Dictionary subclass enabling attribute dot notation access."""

    def __getattr__(self, item: str) -> Any:
        try:
            val = self[item]
            if isinstance(val, dict) and not isinstance(val, DotAccessibleDict):
                return DotAccessibleDict(val)
            return val
        except KeyError:
            return None

    def __getitem__(self, item: Any) -> Any:
        try:
            val = super().__getitem__(item)
            if isinstance(val, dict) and not isinstance(val, DotAccessibleDict):
                return DotAccessibleDict(val)
            return val
        except KeyError:
            return None


def _to_dot_accessible(obj: Any) -> Any:
    """Recursively wrap dicts into DotAccessibleDict."""
    if isinstance(obj, dict):
        return DotAccessibleDict({k: _to_dot_accessible(v) for k, v in obj.items()})
    elif isinstance(obj, list):
        return [_to_dot_accessible(item) for item in obj]
    return obj


class ExpressionEvaluator:
    """Evaluates expressions and templates within a workflow execution context."""

    def __init__(self) -> None:
        self.env = Environment(
            autoescape=select_autoescape(default=False),
            variable_start_string="{{",
            variable_end_string="}}",
            undefined=jinja2.Undefined,
        )
        # Register useful built-in filters & helpers
        self.env.filters["to_json"] = lambda v: json.dumps(v, default=str)
        self.env.filters["from_json"] = lambda v: json.loads(v) if isinstance(v, str) else v
        self.env.filters["upper"] = lambda s: str(s).upper() if s is not None else ""
        self.env.filters["lower"] = lambda s: str(s).lower() if s is not None else ""
        self.env.filters["trim"] = lambda s: str(s).strip() if s is not None else ""
        self.env.filters["regex_search"] = lambda s, pat: bool(re.search(pat, str(s)))

        self.env.globals["now"] = lambda: datetime.now(timezone.utc)
        self.env.globals["utc_timestamp"] = lambda: int(datetime.now(timezone.utc).timestamp())

    def evaluate_string(self, template_str: str, context: Dict[str, Any]) -> Any:
        """Evaluate a template string against the given context.
        
        If the template is exactly '{{ some_expr }}' and the expression resolves to
        a non-string type (such as int, dict, list, bool), that native object is returned.
        """
        if not isinstance(template_str, str):
            return template_str

        stripped = template_str.strip()
        # Direct exact expression match: {{ expr }}
        if stripped.startswith("{{") and stripped.endswith("}}") and stripped.count("{{") == 1:
            inner_expr = stripped[2:-2].strip()
            # Try to compile and eval in native mode if possible
            try:
                wrapped_ctx = _to_dot_accessible(context)
                res = self.env.compile_expression(inner_expr)(wrapped_ctx)
                if not isinstance(res, jinja2.Undefined):
                    return res
            except Exception:
                pass  # Fallback to standard string rendering

        try:
            wrapped_ctx = _to_dot_accessible(context)
            template = self.env.from_string(template_str)
            rendered = template.render(**wrapped_ctx)
            return rendered
        except Exception as e:
            # If rendering fails, return template string or re-raise
            return template_str

    def evaluate(self, value: Any, context: Dict[str, Any]) -> Any:
        """Recursively evaluate templates in arbitrary structures (dict, list, str)."""
        if isinstance(value, str):
            return self.evaluate_string(value, context)
        elif isinstance(value, dict):
            return {k: self.evaluate(v, context) for k, v in value.items()}
        elif isinstance(value, list):
            return [self.evaluate(elem, context) for elem in value]
        else:
            return value

    def evaluate_condition(self, condition_expr: str, context: Dict[str, Any]) -> bool:
        """Evaluate a condition string (e.g. '{{ steps.a.output.ok == true }}') to boolean."""
        if not condition_expr:
            return True

        expr = condition_expr.strip()
        # Strip outer {{ }} if present
        if expr.startswith("{{") and expr.endswith("}}"):
            expr = expr[2:-2].strip()

        try:
            wrapped_ctx = _to_dot_accessible(context)
            compiled = self.env.compile_expression(expr)
            res = compiled(wrapped_ctx)
            return bool(res)
        except Exception:
            # Fallback: render template and check truthiness
            try:
                rendered = self.evaluate_string(f"{{{{ {expr} }}}}", context)
                if isinstance(rendered, bool):
                    return rendered
                if isinstance(rendered, str):
                    s = rendered.strip().lower()
                    if s in ("true", "1", "yes"):
                        return True
                    if s in ("false", "0", "no", "", "none"):
                        return False
                return bool(rendered)
            except Exception:
                return False
