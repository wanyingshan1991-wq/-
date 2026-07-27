from typing import Any

from lark_client import LarkClient
from generators.policy_revision import column_from_index, sheet_id_by_name


WHITE_ROWS = [6, 9, 13]
COMPLETION_ROWS = [
    (4, 5, 6),
    (7, 8, 9),
    (10, 11, 13),
]


def month_sheet_name(month: int) -> str:
    return f"{month}月"


def month_end_column(month: int) -> str:
    # 事业年月计划: E:P maps to 1月:12月.
    return column_from_index(5 + month - 1)


def get_sheet_id(client: LarkClient, spreadsheet_token: str, sheet_name: str) -> str | None:
    ids = sheet_id_by_name(client.workbook_info(spreadsheet_token))
    return ids.get(sheet_name)


def set_actual_rows_white(client: LarkClient, spreadsheet_token: str, sheet_id: str, month: int) -> None:
    end_column = month_end_column(month)
    for row in WHITE_ROWS:
        client.set_background(spreadsheet_token, sheet_id, f"E{row}:{end_column}{row}", "#ffffff")


def clear_manual_cells(client: LarkClient, spreadsheet_token: str, sheet_id: str) -> None:
    client.set_cells(
        spreadsheet_token,
        sheet_id,
        "E14:E15",
        [[{"value": ""}], [{"value": ""}]],
    )


def set_completion_formulas(client: LarkClient, spreadsheet_token: str, sheet_id: str, month: int) -> None:
    end_column = month_end_column(month)
    for plan_row, adjusted_row, actual_row in COMPLETION_ROWS:
        client.set_cells(
            spreadsheet_token,
            sheet_id,
            f"R{plan_row}:T{plan_row}",
            [
                [
                    {"formula": f"=SUM(E{actual_row}:{end_column}{actual_row})/Q{plan_row}"},
                    {"formula": f"=SUM(E{actual_row}:{end_column}{actual_row})/Q{adjusted_row}"},
                    {"formula": f"=SUM(E{actual_row}:{end_column}{actual_row})/SUM(E{plan_row}:{end_column}{plan_row})"},
                ]
            ],
        )


def ensure_business_month_plan_config(config: dict[str, Any]) -> dict[str, Any]:
    section = config.setdefault("business_month_plan", {})
    return section


def generate(config: dict[str, Any], month: int | None = None, force_copy: bool = False) -> dict[str, Any]:
    section = ensure_business_month_plan_config(config)
    target_month = month or section.get("target_month")
    if not target_month:
        raise RuntimeError("缺少目标月份。")

    spreadsheet_token = section.get("spreadsheet_token")
    if not spreadsheet_token:
        raise RuntimeError("缺少 business_month_plan.spreadsheet_token。")

    client = LarkClient(config)
    target_sheet = month_sheet_name(target_month)
    source_sheet = month_sheet_name(section.get("source_month") or target_month - 1)

    existing_id = get_sheet_id(client, spreadsheet_token, target_sheet)
    created = False
    if existing_id and not force_copy:
        target_sheet_id = existing_id
        source_used = "未复制：目标月份 sheet 已存在"
    else:
        if target_month <= 1 and not section.get("source_month"):
            raise RuntimeError("生成 1 月时无法自动推断上一月，请先配置源月份。")
        if not get_sheet_id(client, spreadsheet_token, source_sheet):
            raise RuntimeError(f"找不到源 sheet：{source_sheet}")
        client.copy_worksheet(spreadsheet_token, source_sheet, target_sheet)
        target_sheet_id = get_sheet_id(client, spreadsheet_token, target_sheet)
        if not target_sheet_id:
            raise RuntimeError(f"复制完成后未找到目标 sheet：{target_sheet}")
        created = True
        source_used = f"上一月 sheet：{source_sheet}"

    set_actual_rows_white(client, spreadsheet_token, target_sheet_id, target_month)
    set_completion_formulas(client, spreadsheet_token, target_sheet_id, target_month)
    clear_manual_cells(client, spreadsheet_token, target_sheet_id)

    feishu_domain = config.get("feishu_domain", "https://gw8xslpm5z.feishu.cn").rstrip("/")
    sheet_titles = [
        sheet.get("sheet_name")
        for sheet in client.workbook_info(spreadsheet_token)["data"].get("sheets", [])
    ]
    return {
        "created": created,
        "target": {"name": f"事业年月计划-{target_sheet}", "sheet_name": target_sheet},
        "workbook_sheets": sheet_titles,
        "source_used": source_used,
        "styled": True,
        "spreadsheet_token": spreadsheet_token,
        "sheet_id": target_sheet_id,
        "url": f"{feishu_domain}/sheets/{spreadsheet_token}",
    }
