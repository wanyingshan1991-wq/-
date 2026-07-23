import json
import re
import shutil
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config" / "config.json"
EXAMPLE_CONFIG_PATH = PROJECT_ROOT / "config" / "config.example.json"


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
    print("未找到 config/config.json，将进入首次配置向导。")
    return run_config_wizard()


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


def ask_int(prompt: str, default: int) -> int:
    while True:
        raw = ask(prompt, str(default))
        try:
            return int(raw)
        except ValueError:
            print("请输入数字，例如 8。")


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

    sample_domain = current.get("feishu_domain", "https://gw8xslpm5z.feishu.cn")
    domain_input = ask("请输入飞书域名，或任意飞书表格/文件夹链接", sample_domain)
    current["feishu_domain"] = extract_domain(domain_input, sample_domain)

    folder_default = policy.get("folder_token", "")
    folder_input = ask("请粘贴“方针修正”所在文件夹链接或 folder_token", folder_default)
    policy["folder_token"] = extract_token(folder_input, "folder")

    source_month = ask_int("请输入源月份，例如 7", int(policy.get("source_month", 7)))
    target_month = ask_int("请输入默认目标月份，例如 8", int(policy.get("target_month", source_month + 1)))
    policy["source_month"] = source_month
    policy["target_month"] = target_month

    source_name_default = policy.get("source_name") or f"经营方针修正-{source_month}月"
    policy["source_name"] = ask("请输入源表名称", source_name_default)

    source_token_default = policy.get("source_token", "")
    source_input = ask("请粘贴源表链接或 spreadsheet_token", source_token_default)
    policy["source_token"] = extract_token(source_input, "sheet")

    current.setdefault("lark_cli_path", "")
    save_config(current)
    print("")
    print(f"配置已保存：{DEFAULT_CONFIG_PATH}")
    return current


def reset_config_from_example() -> None:
    DEFAULT_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(EXAMPLE_CONFIG_PATH, DEFAULT_CONFIG_PATH)
