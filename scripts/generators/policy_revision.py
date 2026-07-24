from dataclasses import dataclass
from typing import Any

from lark_client import LarkClient


@dataclass(frozen=True)
class AdjustmentArea:
    sheet_name: str
    start_column: str
    end_column: str
    rows: str


ADJUSTMENT_AREA_ROWS = [
    ("经营方针计划（营销）", "14:16", 0),
    ("经营方针计划（商品）", "10", -1),
    ("经营方针计划（工具+联动）", "12:13", 0),
    ("经营方针计划（运营）", "14", 0),
]


def normalize_range(start_column: str, end_column: str, rows: str) -> str:
    if ":" not in rows:
        return f"{start_column}{rows}:{end_column}{rows}"
    start, end = rows.split(":", 1)
    return f"{start_column}{start}:{end_column}{end}"


def column_from_index(index: int) -> str:
    if index < 1:
        raise ValueError(f"Invalid column index: {index}")
    letters = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        letters = chr(ord("A") + remainder) + letters
    return letters


def adjustment_areas_for_month(month: int) -> list[AdjustmentArea]:
    # Current workbook layout: common sheets use I:T for 1月:12月;
    # 商品 is shifted one column left and uses H:S for 1月:12月.
    common_start_index = 9
    common_end_index = common_start_index + month - 1
    return [
        AdjustmentArea(
            sheet_name,
            column_from_index(common_start_index + offset),
            column_from_index(common_end_index + offset),
            rows,
        )
        for sheet_name, rows, offset in ADJUSTMENT_AREA_ROWS
    ]


def sheet_id_by_name(info: dict[str, Any]) -> dict[str, str]:
    sheets = info["data"].get("sheets", [])
    return {sheet["sheet_name"]: sheet["sheet_id"] for sheet in sheets}


def set_adjustment_area_white(client: LarkClient, spreadsheet_token: str, month: int) -> None:
    ids = sheet_id_by_name(client.workbook_info(spreadsheet_token))
    for area in adjustment_areas_for_month(month):
        sheet_id = ids.get(area.sheet_name)
        if not sheet_id:
            raise RuntimeError(f"Sheet not found: {area.sheet_name}")
        client.set_background(
            spreadsheet_token,
            sheet_id,
            normalize_range(area.start_column, area.end_column, area.rows),
            "#ffffff",
        )


def resolve_source_file(
    client: LarkClient,
    folder_token: str,
    target_month: int,
    configured_source_name: str,
    configured_source_token: str,
) -> tuple[str, str]:
    previous_month = target_month - 1
    previous_name = f"经营方针修正-{previous_month}月"
    previous_source = client.find_sheet_file(folder_token, previous_name)
    if previous_source:
        return previous_source["token"], f"上一月表：{previous_name}"

    configured_source = client.find_sheet_file(folder_token, configured_source_name) if configured_source_name else None
    if configured_source:
        return configured_source["token"], f"配置源表：{configured_source_name}"

    if configured_source_token:
        return configured_source_token, "配置源表 token"

    raise RuntimeError(f"找不到上一月表 {previous_name}，且没有可用的配置源表。")


def generate(config: dict[str, Any], month: int | None = None, force_copy: bool = False) -> dict[str, Any]:
    section = config.get("policy_revision")
    if not isinstance(section, dict):
        raise RuntimeError("config/config.json 缺少 policy_revision 配置段。")

    target_month = month or section.get("target_month")
    if not target_month:
        raise RuntimeError("缺少目标月份。")

    source_month = section.get("source_month") or target_month - 1
    folder_token = section.get("folder_token")
    source_token = section.get("source_token")
    source_name = section.get("source_name") or f"经营方针修正-{source_month}月"
    feishu_domain = config.get("feishu_domain", "https://gw8xslpm5z.feishu.cn").rstrip("/")

    if not folder_token:
        raise RuntimeError("缺少 policy_revision.folder_token。")
    if not source_token and not source_name:
        raise RuntimeError("缺少 source_token 或 source_name，无法定位源表。")

    client = LarkClient(config)
    target_name = f"经营方针修正-{target_month}月"
    created = False
    existing = client.find_sheet_file(folder_token, target_name)
    if existing and not force_copy:
        target = existing
        token = target["token"]
        source_used = "未复制：目标表已存在"
    else:
        resolved_source_token, source_used = resolve_source_file(
            client,
            folder_token,
            target_month,
            source_name,
            source_token,
        )
        client.copy_sheet_file(resolved_source_token, folder_token, target_name)
        target = client.find_sheet_file(folder_token, target_name)
        if not target:
            raise RuntimeError(f"Copy succeeded but {target_name} was not found in folder.")
        token = target["token"]
        created = True

    info = client.workbook_info(token)
    sheet_titles = [sheet.get("sheet_name") for sheet in info["data"].get("sheets", [])]
    set_adjustment_area_white(client, token, target_month)

    return {
        "created": created,
        "target": target,
        "workbook_sheets": sheet_titles,
        "source_used": source_used,
        "styled": True,
        "spreadsheet_token": token,
        "url": f"{feishu_domain}/sheets/{token}",
    }
