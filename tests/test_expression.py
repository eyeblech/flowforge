"""Tests for Jinja2 template and expression evaluation."""

import pytest
from flowforge.core.expression import ExpressionEvaluator


def test_evaluate_simple_variable():
    evaluator = ExpressionEvaluator()
    context = {"name": "World", "count": 42}

    assert evaluator.evaluate_string("Hello, {{ name }}!", context) == "Hello, World!"
    assert evaluator.evaluate_string("{{ count }}", context) == 42


def test_evaluate_dot_notation():
    evaluator = ExpressionEvaluator()
    context = {
        "steps": {
            "fetch": {
                "output": {
                    "data": {
                        "user": {"email": "alex@example.com", "id": 101}
                    }
                }
            }
        }
    }

    assert evaluator.evaluate_string("{{ steps.fetch.output.data.user.email }}", context) == "alex@example.com"
    assert evaluator.evaluate_string("{{ steps.fetch.output.data.user.id }}", context) == 101


def test_evaluate_nested_dictionary():
    evaluator = ExpressionEvaluator()
    context = {"val": 100, "flag": True}
    raw = {
        "num": "{{ val }}",
        "nested": {
            "text": "Score is {{ val }}",
            "bool": "{{ flag }}",
        },
        "list": ["{{ val }}", 200],
    }
    res = evaluator.evaluate(raw, context)
    assert res["num"] == 100
    assert res["nested"]["text"] == "Score is 100"
    assert res["nested"]["bool"] is True
    assert res["list"] == [100, 200]


def test_evaluate_filters():
    evaluator = ExpressionEvaluator()
    context = {"raw": "  hello world  ", "obj": {"a": 1, "b": 2}}

    assert evaluator.evaluate_string("{{ raw | trim }}", context) == "hello world"
    assert evaluator.evaluate_string("{{ raw | trim | upper }}", context) == "HELLO WORLD"
    assert evaluator.evaluate_string("{{ obj | to_json }}", context) == '{"a": 1, "b": 2}'


def test_evaluate_condition():
    evaluator = ExpressionEvaluator()
    context = {
        "steps": {
            "check": {
                "output": {"status": "ok", "code": 200}
            }
        }
    }

    assert evaluator.evaluate_condition("{{ steps.check.output.status == 'ok' }}", context) is True
    assert evaluator.evaluate_condition("steps.check.output.code == 200", context) is True
    assert evaluator.evaluate_condition("steps.check.output.code == 500", context) is False
