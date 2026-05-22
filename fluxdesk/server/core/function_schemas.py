CREATE_WINDOW_SCHEMA = {
    "type": "function",
    "function": {
        "name": "create_window",
        "description": "在桌面上创建一个浮动工具窗口",
        "parameters": {
            "type": "object",
            "properties": {
                "type": {
                    "type": "string",
                    "description": "窗口类型，可以是已安装模板的 ID（如 todo、habit-tracker）"
                },
                "position": {
                    "type": "object",
                    "properties": {
                        "x": {"type": "number", "description": "X坐标，不传则自动居中"},
                        "y": {"type": "number", "description": "Y坐标，不传则自动居中"}
                    }
                },
                "size": {
                    "type": "object",
                    "properties": {
                        "width": {"type": "number", "default": 400},
                        "height": {"type": "number", "default": 300}
                    }
                },
                "data": {
                    "type": "object",
                    "description": "窗口初始化数据",
                    "properties": {
                        "duration": {"type": "number", "description": "番茄钟时长（分钟），默认25"},
                        "title": {"type": "string", "description": "笔记标题"},
                        "content": {"type": "string", "description": "笔记/待办初始内容"},
                        "label": {"type": "string", "description": "自定义标签"}
                    }
                }
            },
            "required": ["type"]
        }
    }
}

MANAGE_TODO_SCHEMA = {
    "type": "function",
    "function": {
        "name": "manage_todo",
        "description": "管理待办事项",
        "parameters": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["add", "complete", "delete", "list"],
                    "description": "操作类型"
                },
                "content": {"type": "string", "description": "待办内容"},
                "todo_id": {"type": "string", "description": "待办ID，complete/delete时需要"}
            },
            "required": ["action"]
        }
    }
}

SET_REMINDER_SCHEMA = {
    "type": "function",
    "function": {
        "name": "set_reminder",
        "description": "设置提醒",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "提醒标题"},
                "time": {"type": "string", "description": "提醒时间，ISO 8601 格式"},
                "repeat": {"type": "string", "enum": ["once", "daily", "weekly"], "default": "once"}
            },
            "required": ["title", "time"]
        }
    }
}

ASK_CLARIFICATION_SCHEMA = {
    "type": "function",
    "function": {
        "name": "ask_clarification",
        "description": "当用户意图不明确时，向用户请求澄清",
        "parameters": {
            "type": "object",
            "properties": {
                "question": {"type": "string", "description": "向用户提出的问题"},
                "suggestions": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "建议的选项"
                }
            },
            "required": ["question"]
        }
    }
}

CREATE_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "create_tool",
        "description": "在工作区网格中创建一个新工具卡片。工作区是多列网格布局，每个工具占据若干单元格。AI可自动决定位置。",
        "parameters": {
            "type": "object",
            "properties": {
                "tool_type": {
                    "type": "string",
                    "description": "工具类型 ID，可以是已安装模板的 ID（如 todo、pomodoro、habit-tracker）"
                },
                "title": {
                    "type": "string",
                    "description": "工具标题，默认为类型名"
                },
                "config": {
                    "type": "object",
                    "description": "工具初始化配置",
                    "properties": {
                        "duration": {"type": "number", "description": "番茄钟时长（分钟），默认25"},
                        "content": {"type": "string", "description": "笔记/待办初始内容"},
                        "label": {"type": "string", "description": "自定义标签"}
                    }
                },
                "column": {
                    "type": "integer",
                    "description": "网格列位置(1-4)，不传则自动放置",
                    "minimum": 1,
                    "maximum": 4
                },
                "row": {
                    "type": "integer",
                    "description": "网格行位置，不传则自动放置",
                    "minimum": 1
                }
            },
            "required": ["tool_type"]
        }
    }
}

UPDATE_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "update_tool",
        "description": "修改工作区中已有工具的配置，例如更改标题、内容等。",
        "parameters": {
            "type": "object",
            "properties": {
                "tool_id": {"type": "string", "description": "工具ID"},
                "title": {"type": "string", "description": "新标题"},
                "config": {
                    "type": "object",
                    "description": "更新的配置项，会合并到现有配置中"
                }
            },
            "required": ["tool_id"]
        }
    }
}

DELETE_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "delete_tool",
        "description": "从工作区中删除一个工具卡片。",
        "parameters": {
            "type": "object",
            "properties": {
                "tool_id": {"type": "string", "description": "要删除的工具ID"}
            },
            "required": ["tool_id"]
        }
    }
}

MOVE_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "move_tool",
        "description": "移动工作区中工具的位置或调整其大小。",
        "parameters": {
            "type": "object",
            "properties": {
                "tool_id": {"type": "string", "description": "工具ID"},
                "column": {"type": "integer", "description": "新列位置(1-4)", "minimum": 1, "maximum": 4},
                "row": {"type": "integer", "description": "新行位置", "minimum": 1},
                "width": {"type": "integer", "description": "新宽度(占几列)", "minimum": 1, "maximum": 4},
                "height": {"type": "integer", "description": "新高度(占几行)", "minimum": 1}
            },
            "required": ["tool_id"]
        }
    }
}

SEARCH_NOTES_SCHEMA = {
    "type": "function",
    "function": {
        "name": "search_notes",
        "description": "搜索用户的历史笔记，用于回答'我之前记的...'类问题。调用后会自动检索相关笔记并返回摘要。",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "搜索关键词或语义查询"},
            },
            "required": ["query"]
        }
    }
}

INSTALL_TEMPLATE_SCHEMA = {
    "type": "function",
    "function": {
        "name": "install_template",
        "description": "安装一个新的卡片模板。当用户要求创建一种全新类型的卡片（如习惯追踪器、记账本、倒计时器等）时使用。你需要生成一个完整的 Vue 3 组件 JavaScript 代码。",
        "parameters": {
            "type": "object",
            "properties": {
                "template_id": {
                    "type": "string",
                    "description": "模板唯一标识，小写字母和连字符，如 habit-tracker"
                },
                "name": {
                    "type": "string",
                    "description": "模板显示名称"
                },
                "icon": {
                    "type": "string",
                    "description": "一个 emoji 图标"
                },
                "description": {
                    "type": "string",
                    "description": "模板功能描述"
                },
                "accent_color": {
                    "type": "string",
                    "description": "主题色 CSS 变量，如 var(--color-dai) 或 var(--color-success)"
                },
                "default_width": {
                    "type": "integer",
                    "default": 1,
                    "minimum": 1,
                    "maximum": 4,
                    "description": "默认占几列"
                },
                "default_height": {
                    "type": "integer",
                    "default": 1,
                    "minimum": 1,
                    "maximum": 4,
                    "description": "默认占几行"
                },
                "vue_code": {
                    "type": "string",
                    "description": "完整的 Vue 3 组件 JS 代码。使用 __fluxdesk 全局对象：{ windowId: string, data: Record<string,any>, updateConfig(config) }。模板使用 Tailwind CSS 类名。导出为一个可直接执行的 JS 字符串。示例格式：const Component = { setup() { const { windowId, data, updateConfig } = __fluxdesk; ... return { ... }; }, template: `...` }; createApp(Component).mount('#app');"
                },
                "config_schema": {
                    "type": "object",
                    "description": "data 的 JSON Schema，描述可配置字段"
                }
            },
            "required": ["template_id", "name", "vue_code"]
        }
    }
}

UNINSTALL_TEMPLATE_SCHEMA = {
    "type": "function",
    "function": {
        "name": "uninstall_template",
        "description": "卸载一个已安装的自定义卡片模板。",
        "parameters": {
            "type": "object",
            "properties": {
                "template_id": {"type": "string", "description": "要卸载的模板ID"}
            },
            "required": ["template_id"]
        }
    }
}

LIST_TEMPLATES_SCHEMA = {
    "type": "function",
    "function": {
        "name": "list_templates",
        "description": "列出当前已安装的所有卡片模板。",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    }
}

TOOLS = [
    CREATE_TOOL_SCHEMA, UPDATE_TOOL_SCHEMA, DELETE_TOOL_SCHEMA, MOVE_TOOL_SCHEMA,
    MANAGE_TODO_SCHEMA, SET_REMINDER_SCHEMA,
    SEARCH_NOTES_SCHEMA, ASK_CLARIFICATION_SCHEMA,
    INSTALL_TEMPLATE_SCHEMA, UNINSTALL_TEMPLATE_SCHEMA, LIST_TEMPLATES_SCHEMA,
]
