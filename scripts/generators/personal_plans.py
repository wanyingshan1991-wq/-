import re
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

from lark_client import LarkClient
from generators.business_month_plan import get_sheet_id, month_sheet_name
from generators.policy_revision import column_from_index
from generators.resource_plans import full_sheet_url, importrange_formula


WEEKDAYS = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
WEEK_START_COLUMNS = ["C", "J", "Q", "X", "AE"]


@dataclass(frozen=True)
class WeekBlock:
    week_number: int
    start_column: str
    dates: list[date]


def month_plan_start_date(year: int, month: int) -> date:
    first_day = date(year, month, 1)
    return first_day - timedelta(days=first_day.weekday())


def month_plan_dates(year: int, month: int) -> list[date]:
    start = month_plan_start_date(year, month)
    return [start + timedelta(days=offset) for offset in range(35)]


def week_blocks(year: int, month: int) -> list[WeekBlock]:
    dates = month_plan_dates(year, month)
    blocks = []
    for index, column in enumerate(WEEK_START_COLUMNS):
        block_dates = dates[index * 7 : index * 7 + 7]
        blocks.append(WeekBlock(block_dates[0].isocalendar().week, column, block_dates))
    return blocks


def a1_row_values(values: list[Any], key: str = "value") -> list[list[dict[str, Any]]]:
    return [[{key: value} for value in values]]


def clear_table_range(client: LarkClient, spreadsheet_token: str, sheet_id: str, range_a1: str) -> None:
    start, _, end = range_a1.partition(":")
    start_col = "".join(ch for ch in start if ch.isalpha())
    end_col = "".join(ch for ch in (end or start) if ch.isalpha())
    start_row = int("".join(ch for ch in start if ch.isdigit()))
    end_row = int("".join(ch for ch in (end or start) if ch.isdigit()))
    width = column_to_index(end_col) - column_to_index(start_col) + 1
    cells = [[{"value": ""} for _ in range(width)] for _ in range(start_row, end_row + 1)]
    client.set_cells(spreadsheet_token, sheet_id, range_a1, cells)


def column_to_index(column: str) -> int:
    index = 0
    for char in column:
        index = index * 26 + (ord(char.upper()) - ord("A") + 1)
    return index


def copy_sheet_if_needed(
    client: LarkClient,
    spreadsheet_token: str,
    source_sheet: str,
    target_sheet: str,
    force_copy: bool,
) -> tuple[str, bool, str]:
    existing_id = get_sheet_id(client, spreadsheet_token, target_sheet)
    if existing_id and not force_copy:
        return existing_id, False, "未复制：目标 sheet 已存在"
    if not get_sheet_id(client, spreadsheet_token, source_sheet):
        raise RuntimeError(f"找不到源 sheet：{source_sheet}")
    client.copy_worksheet(spreadsheet_token, source_sheet, target_sheet)
    target_id = get_sheet_id(client, spreadsheet_token, target_sheet)
    if not target_id:
        raise RuntimeError(f"复制完成后未找到目标 sheet：{target_sheet}")
    return target_id, True, f"源 sheet：{source_sheet}"


def sheet_titles(client: LarkClient, spreadsheet_token: str) -> list[str]:
    return [
        sheet.get("sheet_name")
        for sheet in client.workbook_info(spreadsheet_token)["data"].get("sheets", [])
    ]


def last_sheet_name(client: LarkClient, spreadsheet_token: str) -> str:
    titles = sheet_titles(client, spreadsheet_token)
    if not titles:
        raise RuntimeError("目标表格中没有可复制的模板 sheet。")
    return titles[-1]


def week_label_number(value: str) -> int:
    match = re.search(r"(\d+)", value)
    if not match:
        raise RuntimeError(f"无法识别周标签：{value}")
    return int(match.group(1))


def generate_personal_month_plan(
    config: dict[str, Any],
    person_name: str,
    month: int,
    year: int,
    force_copy: bool = False,
) -> dict[str, Any]:
    person = config.get("people", {}).get(person_name, {})
    spreadsheet_token = person.get("personal_month_plan_token")
    if not spreadsheet_token:
        raise RuntimeError(f"缺少 {person_name} 的个人月周计划表链接。")

    rd_token = config.get("rd_resource_plan", {}).get("spreadsheet_token")
    marketing_token = config.get("marketing_resource_plan", {}).get("spreadsheet_token")
    if not rd_token or not marketing_token:
        raise RuntimeError("缺少研发或营销资源分配计划表链接。")

    client = LarkClient(config)
    target_sheet = month_sheet_name(month)
    source_sheet = month_sheet_name(month - 1)
    sheet_id, created, source_used = copy_sheet_if_needed(client, spreadsheet_token, source_sheet, target_sheet, force_copy)

    client.set_cells(
        spreadsheet_token,
        sheet_id,
        "C3:C3",
        [[{"formula": importrange_formula(full_sheet_url(config, rd_token), target_sheet, "C10")}]],
    )
    client.set_cells(
        spreadsheet_token,
        sheet_id,
        "C4:C4",
        [[{"formula": importrange_formula(full_sheet_url(config, marketing_token), target_sheet, "C9")}]],
    )

    dates = month_plan_dates(year, month)
    client.set_cells(spreadsheet_token, sheet_id, "C5:AK5", a1_row_values([f"{d.month}/{d.day}" for d in dates]))
    client.set_cells(spreadsheet_token, sheet_id, "C6:AK6", a1_row_values([WEEKDAYS[d.weekday()] for d in dates]))
    clear_table_range(client, spreadsheet_token, sheet_id, "C7:AK7")

    blocks = week_blocks(year, month)
    for block in blocks:
        client.set_cells(spreadsheet_token, sheet_id, f"{block.start_column}8:{block.start_column}8", [[{"value": f"第{block.week_number}周"}]])

    clear_table_range(client, spreadsheet_token, sheet_id, "C9:AK30")
    return {
        "created": created,
        "target": {"name": f"个人月周推移计划-{person_name}-{month}月", "sheet_name": target_sheet},
        "workbook_sheets": sheet_titles(client, spreadsheet_token),
        "source_used": source_used,
        "spreadsheet_token": spreadsheet_token,
        "sheet_id": sheet_id,
        "url": full_sheet_url(config, spreadsheet_token),
    }


def generate_personal_week_day_plan(
    config: dict[str, Any],
    person_name: str,
    month: int,
    year: int,
    force_copy: bool = False,
) -> dict[str, Any]:
    person = config.get("people", {}).get(person_name, {})
    week_token = person.get("personal_week_day_plan_token")
    month_token = person.get("personal_month_plan_token")
    if not week_token or not month_token:
        raise RuntimeError(f"缺少 {person_name} 的个人月周或周日计划表链接。")

    client = LarkClient(config)
    template_sheet = last_sheet_name(client, week_token)
    created_any = False
    updated_sheets = []
    source_used = f"模板 sheet：{template_sheet}"

    for block in week_blocks(year, month):
        target_sheet = f"{block.week_number}周"
        sheet_id, created, _ = copy_sheet_if_needed(client, week_token, template_sheet, target_sheet, force_copy)
        created_any = created_any or created
        updated_sheets.append(target_sheet)

        client.set_cells(
            week_token,
            sheet_id,
            "C3:C3",
            [[{"formula": importrange_formula(full_sheet_url(config, month_token), month_sheet_name(month), f"{block.start_column}9:{block.start_column}30")}]],
        )
        client.set_cells(week_token, sheet_id, "C6:I6", a1_row_values([f"{d.month}月{d.day}日" for d in block.dates]))
        client.set_cells(week_token, sheet_id, "C7:I7", a1_row_values([WEEKDAYS[d.weekday()] for d in block.dates]))
        clear_table_range(client, week_token, sheet_id, "C8:I8")
        clear_table_range(client, week_token, sheet_id, "C9:I12")
        client.set_cells(week_token, sheet_id, "C4:C5", [[{"value": ""}], [{"value": ""}]])

    return {
        "created": created_any,
        "target": {"name": f"个人周日推移计划-{person_name}-{month}月", "sheet_name": ", ".join(updated_sheets)},
        "workbook_sheets": sheet_titles(client, week_token),
        "source_used": source_used,
        "spreadsheet_token": week_token,
        "url": full_sheet_url(config, week_token),
    }
