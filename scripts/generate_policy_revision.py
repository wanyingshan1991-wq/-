import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config" / "config.json"
EXAMPLE_CONFIG_PATH = PROJECT_ROOT / "config" / "config.example.json"


@dataclass(frozen=True)
class AdjustmentArea:
    sheet_name: str
    column: str
    rows: str


ADJUSTMENT_AREA_ROWS = [
    ("经营方针计划（营销）", "14:16", 0),
    ("经营方针计划（商品）", "10", -1),
    ("经营方针计划（工具+联动）", "12:13", 0),
    ("经营方针计划（运营）", "14", 0),
]

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")


def resolve_lark_cli(config: dict[str, Any]) -> str:
    configured = config.get("lark_cli_path")
    if configured:
        return configured
    from_env = os.environ.get("LARK_CLI")
    if from_env:
        return from_env
    found = shutil.which("lark-cli") or shutil.which("lark-cli.cmd")
    if found:
        return found
    fallback = r"C:\Users\Administrator\AppData\Roaming\npm\lark-cli.cmd"
    if Path(fallback).exists():
        return fallback
    raise RuntimeError("未找到 lark-cli。请先安装 lark-cli，或在 config/config.json 中设置 lark_cli_path。")


def load_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise RuntimeError(
            f"未找到配置文件：{path}\n"
            f"请先复制 {EXAMPLE_CONFIG_PATH} 为 {path}，再根据 README 填写配置。"
        )
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def policy_config(config: dict[str, Any]) -> dict[str, Any]:
    section = config.get("policy_revision")
    if not isinstance(section, dict):
        raise RuntimeError("config/config.json 缺少 policy_revision 配置段。")
    return section


def run_lark(args: list[str], stdin: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = None
    if stdin is not None:
        payload = json.dumps(stdin, ensure_ascii=False).encode("utf-8")

    last_error = ""
    for attempt in range(1, 4):
        proc = subprocess.run(
            [run_lark.lark_cli, *args, "--format", "json"],
            input=payload,
            capture_output=True,
            timeout=60,
        )
        stdout = proc.stdout.decode("utf-8", errors="replace").strip()
        stderr = proc.stderr.decode("utf-8", errors="replace").strip()

        if proc.returncode == 0:
            break

        detail = stderr or stdout
        last_error = detail
        if "EOF" not in detail and "rate limit" not in detail.lower():
            raise RuntimeError(f"lark-cli failed: {' '.join(args)}\n{detail}")
        time.sleep(attempt * 2)
    else:
        raise RuntimeError(f"lark-cli failed after retries: {' '.join(args)}\n{last_error}")

    try:
        result = json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"lark-cli returned non-JSON output: {stdout}") from exc

    if not result.get("ok"):
        raise RuntimeError(f"lark-cli returned ok=false: {json.dumps(result, ensure_ascii=False)}")
    return result


run_lark.lark_cli = "lark-cli"


def list_folder(folder_token: str) -> list[dict[str, Any]]:
    result = run_lark(["drive", "files", "list", "--folder-token", folder_token])
    return result["data"]["files"]


def find_file(folder_token: str, name: str) -> dict[str, Any] | None:
    for item in list_folder(folder_token):
        if item.get("name") == name and item.get("type") == "sheet":
            return item
    return None


def copy_sheet_file(source_token: str, folder_token: str, target_name: str) -> dict[str, Any]:
    data = {
        "name": target_name,
        "type": "sheet",
        "folder_token": folder_token,
    }
    return run_lark(
        [
            "drive",
            "files",
            "copy",
            "--file-token",
            source_token,
            "--data",
            "-",
        ],
        stdin=data,
    )


def workbook_info(spreadsheet_token: str) -> dict[str, Any]:
    return run_lark(["sheets", "+workbook-info", "--spreadsheet-token", spreadsheet_token])


def sheet_id_by_name(info: dict[str, Any]) -> dict[str, str]:
    sheets = info["data"].get("sheets", [])
    return {sheet["sheet_name"]: sheet["sheet_id"] for sheet in sheets}


def normalize_range(column: str, rows: str) -> str:
    if ":" not in rows:
        return f"{column}{rows}:{column}{rows}"
    start, end = rows.split(":", 1)
    return f"{column}{start}:{column}{end}"


def column_from_index(index: int) -> str:
    if index < 1:
        raise ValueError(f"Invalid column index: {index}")
    letters = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        letters = chr(ord("A") + remainder) + letters
    return letters


def adjustment_areas_for_month(month: int) -> list[AdjustmentArea]:
    # Based on the current policy revision workbook: 7月 common column is O, 8月 is P.
    common_column_index = 8 + month
    return [
        AdjustmentArea(sheet_name, column_from_index(common_column_index + offset), rows)
        for sheet_name, rows, offset in ADJUSTMENT_AREA_ROWS
    ]


def set_adjustment_area_white(spreadsheet_token: str, month: int) -> None:
    ids = sheet_id_by_name(workbook_info(spreadsheet_token))
    for area in adjustment_areas_for_month(month):
        sheet_id = ids.get(area.sheet_name)
        if not sheet_id:
            raise RuntimeError(f"Sheet not found: {area.sheet_name}")
        range_a1 = normalize_range(area.column, area.rows)
        run_lark(
            [
                "sheets",
                "+cells-set-style",
                "--spreadsheet-token",
                spreadsheet_token,
                "--sheet-id",
                sheet_id,
                "--range",
                range_a1,
                "--background-color",
                "#ffffff",
            ]
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate monthly policy revision sheet by copying the prior month.")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG_PATH))
    parser.add_argument("--month", type=int)
    parser.add_argument("--folder-token")
    parser.add_argument("--source-token")
    parser.add_argument("--source-name")
    parser.add_argument("--force-copy", action="store_true", help="Create another copy even if target exists.")
    args = parser.parse_args()

    config = load_config(Path(args.config))
    run_lark.lark_cli = resolve_lark_cli(config)
    section = policy_config(config)

    month = args.month or section.get("target_month")
    if not month:
        raw = input("请输入要生成的月份数字，例如 8：").strip()
        month = int(raw)

    source_month = section.get("source_month") or month - 1
    folder_token = args.folder_token or section.get("folder_token")
    source_token = args.source_token or section.get("source_token")
    source_name = args.source_name or section.get("source_name") or f"经营方针修正-{source_month}月"
    feishu_domain = config.get("feishu_domain", "https://gw8xslpm5z.feishu.cn").rstrip("/")

    if not folder_token:
        raise RuntimeError("缺少 policy_revision.folder_token。")
    if not source_token and not source_name:
        raise RuntimeError("缺少 source_token 或 source_name，无法定位源表。")

    target_name = f"经营方针修正-{month}月"
    existing = find_file(folder_token, target_name)
    if existing and not args.force_copy:
        token = existing["token"]
        print(json.dumps({"created": False, "target": existing}, ensure_ascii=False, indent=2))
    else:
        source = find_file(folder_token, source_name) if source_name else None
        resolved_source_token = source["token"] if source else source_token
        copy_result = copy_sheet_file(resolved_source_token, folder_token, target_name)
        target = find_file(folder_token, target_name)
        if not target:
            raise RuntimeError(f"Copy succeeded but {target_name} was not found in folder.")
        token = target["token"]
        print(json.dumps({"created": True, "copy_result": copy_result, "target": target}, ensure_ascii=False, indent=2))

    info = workbook_info(token)
    sheet_titles = [sheet.get("sheet_name") for sheet in info["data"].get("sheets", [])]
    print(json.dumps({"workbook_sheets": sheet_titles}, ensure_ascii=False, indent=2))

    set_adjustment_area_white(token, month)
    print(json.dumps({"styled": True, "spreadsheet_token": token, "url": f"{feishu_domain}/sheets/{token}"}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
