import os
import re
import yaml
from pathlib import Path
from typing import Optional

RULES_DIR = Path(__file__).parent.parent / "rules"


class RuleEngine:
    def __init__(self):
        self.rules = []
        self.load_rules()

    def load_rules(self):
        self.rules = []
        if not RULES_DIR.exists():
            return
        for f in sorted(RULES_DIR.glob("*.yaml")):
            try:
                with open(f, "r", encoding="utf-8") as fh:
                    data = yaml.safe_load(fh)
                    for rule in data.get("rules", []):
                        self.rules.append(rule)
            except Exception as e:
                print(f"Failed to load rule {f}: {e}")
        self.rules.sort(key=lambda r: r.get("priority", 0), reverse=True)

    def match(self, text: str) -> Optional[dict]:
        text_lower = text.lower()
        for rule in self.rules:
            matched = False
            captures = {}
            for pat in rule.get("patterns", []):
                regex = pat.get("regex", "")
                m = re.search(regex, text_lower)
                if m:
                    matched = True
                    captures.update(m.groupdict())
                    for i, g in enumerate(m.groups(), 1):
                        captures[str(i)] = g
                    break
            if matched:
                return self._build_action(rule, captures, text)
        return None

    def _eval_params(self, params: dict, captures: dict, text: str) -> dict:
        result = {}
        for k, v in params.items():
            if isinstance(v, str) and v.startswith("{{") and v.endswith("}}"):
                expr = v[2:-2].strip()
                result[k] = self._eval_expr(expr, captures, text)
            elif isinstance(v, dict):
                result[k] = self._eval_params(v, captures, text)
            elif isinstance(v, list):
                result[k] = [self._eval_params(item, captures, text) if isinstance(item, dict) else item for item in v]
            else:
                result[k] = v
        return result

    def _build_action(self, rule: dict, captures: dict, text: str) -> dict:
        action = rule.get("action", {})
        action_type = action.get("type", "unknown")
        params = self._eval_params(action.get("params", {}), captures, text)
        return {
            "rule": rule.get("name"),
            "action": action_type,
            "params": params,
            "reply": self._generate_reply(rule, params),
        }

    def _eval_expr(self, expr: str, captures: dict, text: str) -> any:
        if "|" in expr:
            var, func = expr.split("|", 1)
            var = var.strip()
            func = func.strip()
            val = captures.get(var, "")
            if func.startswith("default:"):
                default = func.split(":", 1)[1].strip()
                return val if val else default
        return captures.get(expr, "")

    def _generate_reply(self, rule: dict, params: dict) -> str:
        # reply-type actions carry their message in params
        if rule.get("action", {}).get("type") == "reply":
            return params.get("message", "好的，已为您处理。")
        replies = {
            "create_pomodoro": f"已创建 {params.get('duration', 25)} 分钟番茄钟",
            "create_todo": "已添加待办列表",
            "create_note": "已创建新笔记",
            "create_calendar": "已打开日历",
        }
        return replies.get(rule.get("name"), "好的，已为您处理。")
