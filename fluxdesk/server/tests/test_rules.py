import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.rule_engine import RuleEngine


def test_pomodoro_rule():
    engine = RuleEngine()
    result = engine.match("创建一个25分钟的番茄钟")
    assert result is not None
    assert result["action"] == "create_window"
    assert result["params"]["type"] == "pomodoro"


def test_todo_rule():
    engine = RuleEngine()
    result = engine.match("添加一个待办任务")
    assert result is not None
    assert result["action"] == "create_window"
    assert result["params"]["type"] == "todo"


def test_greeting():
    engine = RuleEngine()
    result = engine.match("你好")
    assert result is not None
    assert result["action"] == "reply"


if __name__ == "__main__":
    test_pomodoro_rule()
    test_todo_rule()
    test_greeting()
    print("All rule tests passed!")
