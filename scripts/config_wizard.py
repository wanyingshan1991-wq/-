import json
import re
import shutil
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config" / "config.json"
EXAMPLE_CONFIG_PATH = PROJECT_ROOT / "config" / "config.example.json"

PLACEHOLDER_MARKERS = ["请", "YOUR_", "<", ">"]


def load_config(path: Path = DEFAULT_CONFIG_PATH) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(path)
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_config(config: dict[str, Any], path: Path = DEFAULT_CONFIG_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
        f.write("\n")


def load_example_config() -> dict[str, Any]:
    with EXAMPLE_CONFIG_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def ensure_config_exists() -> dict[str, Any]:
    if DEFAULT_CONFIG_PATH.exists():
        return load_config(DEFAULT_CONFIG_PATH)
    print("未找到 config/config.json，将创建本地配置文件。")
    config = load_example_config() if EXAMPLE_CONFIG_PATH.exists() else {}
    save_config(config)
    return config


def extract_token(value: str, kind: str) -> str:
    value = value.strip()
    if not value:
        return ""
    patterns = {
        "folder": r"/drive/folder/([^/?#]+)",
        "sheet": r"/sheets/([^/?#]+)",
    }
    match = re.search(patterns[kind], value)
    if match:
        return match.group(1)
    return value


def extract_domain(value: str, fallback: str) -> str:
    value = value.strip()
    if not value:
        return fallback
    match = re.match(r"(https?://[^/]+)", value)
    if match:
        return match.group(1)
    return value.rstrip("/")


def ask(prompt: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    raw = input(f"{prompt}{suffix}: ").strip()
    return raw or default


def ask_required(prompt: str, default: str = "") -> str:
    while True:
        value = ask(prompt, default)
        if value and not is_placeholder(value):
            return value
        print("此项必填，请输入有效内容。")


def ask_int(prompt: str, default: int | None = None) -> int:
    while True:
        raw = ask(prompt, "" if default is None else str(default))
        try:
            value = int(raw)
            if 1 <= value <= 12:
                return value
            print("月份必须在 1-12 之间。")
        except ValueError:
            print("请输入数字，例如 8。")


def is_placeholder(value: Any) -> bool:
    if value is None:
        return True
    if not isinstance(value, str):
        return False
    text = value.strip()
    if not text:
        return True
    return any(marker in text for marker in PLACEHOLDER_MARKERS)


def is_month(value: Any) -> bool:
    return isinstance(value, int) and 1 <= value <= 12


def validate_config(config: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    policy = config.get("policy_revision")
    if not isinstance(policy, dict):
        return ["缺少 policy_revision 配置段。"]

    if is_placeholder(config.get("feishu_domain")):
        errors.append("缺少 feishu_domain。")
    if is_placeholder(policy.get("folder_token")):
        errors.append("缺少方针修正文件夹 token。")
    if is_placeholder(policy.get("source_token")):
        errors.append("缺少源表 token。")
    if not is_month(policy.get("source_month")):
        errors.append("source_month 必须是 1-12 的数字。")
    if not is_month(policy.get("target_month")):
        errors.append("target_month 必须是 1-12 的数字。")
    return errors


def is_config_valid(config: dict[str, Any]) -> bool:
    return not validate_config(config)


def print_config_summary(config: dict[str, Any]) -> None:
    policy = config.get("policy_revision", {})
    business = config.get("business_month_plan", {})
    print("")
    print("当前配置摘要：")
    print(f"- 飞书域名：{config.get('feishu_domain') or '(未配置)'}")
    print(f"- 方针修正文件夹 token：{policy.get('folder_token') or '(未配置)'}")
    print(f"- 方针修正源表 token：{policy.get('source_token') or '(未配置)'}")
    print(f"- 事业年月计划表 token：{business.get('spreadsheet_token') or '(未配置)'}")


def run_config_wizard() -> dict[str, Any]:
    if DEFAULT_CONFIG_PATH.exists():
        current = load_config(DEFAULT_CONFIG_PATH)
    elif EXAMPLE_CONFIG_PATH.exists():
        current = load_example_config()
    else:
        current = {}

    policy = current.setdefault("policy_revision", {})

    print("")
    print("=== 业绩表格生成工具配置向导 ===")
    print("可以粘贴完整飞书链接，也可以只粘贴 token。")
    print("")
    print_config_summary(current)

    sample_domain = current.get("feishu_domain") or "https://gw8xslpm5z.feishu.cn"
    domain_input = ask_required("请输入飞书域名，或任意飞书表格/文件夹链接", sample_domain)
    current["feishu_domain"] = extract_domain(domain_input, sample_domain)

    folder_default = policy.get("folder_token", "")
    folder_input = ask_required("请粘贴“方针修正”所在文件夹链接或 folder_token", folder_default)
    policy["folder_token"] = extract_token(folder_input, "folder")

    existing_source_month = policy.get("source_month") if is_month(policy.get("source_month")) else None
    source_month = ask_int("请输入源月份，例如 7", existing_source_month)
    existing_target_month = policy.get("target_month") if is_month(policy.get("target_month")) else source_month + 1
    target_month = ask_int("请输入默认目标月份，例如 8", existing_target_month)
    policy["source_month"] = source_month
    policy["target_month"] = target_month

    source_name_default = policy.get("source_name") or f"经营方针修正-{source_month}月"
    policy["source_name"] = ask("请输入源表名称", source_name_default)

    source_token_default = policy.get("source_token", "")
    source_input = ask_required("请粘贴源表链接或 spreadsheet_token", source_token_default)
    policy["source_token"] = extract_token(source_input, "sheet")

    current.setdefault("lark_cli_path", "")
    errors = validate_config(current)
    if errors:
        print("")
        print("配置仍不完整：")
        for error in errors:
            print(f"- {error}")
        raise RuntimeError("配置未保存，请重新运行配置向导。")

    save_config(current)
    print("")
    print(f"配置已保存：{DEFAULT_CONFIG_PATH}")
    return current


def ensure_feishu_domain(config: dict[str, Any]) -> dict[str, Any]:
    if not is_placeholder(config.get("feishu_domain")):
        return config
    sample_domain = "https://gw8xslpm5z.feishu.cn"
    domain_input = ask_required("请输入飞书域名，或任意飞书表格/文件夹链接", sample_domain)
    config["feishu_domain"] = extract_domain(domain_input, sample_domain)
    save_config(config)
    return config


def ensure_business_month_plan_config(config: dict[str, Any]) -> dict[str, Any]:
    config = ensure_feishu_domain(config)
    section = config.setdefault("business_month_plan", {})
    if not is_placeholder(section.get("spreadsheet_token")):
        return config

    print("")
    print("首次生成事业年月计划，需要提供这张表的飞书链接。")
    print("以后会自动保存到本机 config/config.json，同一台电脑不用重复输入。")
    sheet_input = ask_required("请粘贴“事业年月计划”表格链接或 spreadsheet_token", section.get("spreadsheet_token", ""))
    section["spreadsheet_token"] = extract_token(sheet_input, "sheet")
    save_config(config)
    return config


def ensure_policy_revision_config(config: dict[str, Any]) -> dict[str, Any]:
    errors = validate_config(config)
    if not errors:
        return config

    print("")
    print("生成经营方针修正需要先补充相关链接。")
    return run_config_wizard()


def reset_config_from_example() -> None:
    DEFAULT_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(EXAMPLE_CONFIG_PATH, DEFAULT_CONFIG_PATH)
