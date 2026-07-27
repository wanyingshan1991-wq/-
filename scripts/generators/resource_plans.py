from dataclasses import dataclass
from typing import Any

from lark_client import LarkClient
from generators.business_month_plan import get_sheet_id, month_sheet_name
from generators.policy_revision import column_from_index


@dataclass(frozen=True)
class ResourcePlanSpec:
    config_key: str
    display_name: str
    month_label_cell: str
    clear_range: str
    static_cells: list[tuple[str, str]]
    formula_cells: list[tuple[str, str, str, int]]
    upstream_formula: tuple[str, str, str] | None = None


SPECS = {
    "business": ResourcePlanSpec(
        config_key="business_resource_plan",
        display_name="事业资源分配计划",
        month_label_cell="C12",
        clear_range="C13:C14",
        upstream_formula=("C3", "business_month_plan", "E15:U15"),
        static_cells=[
            ("C4", "联动营销-首购"),
            ("C5", "联动营销-增购"),
            ("C6", "机构营销-首购"),
            ("C7", "制造业项目产品企划能力构建"),
            ("C8", "SAAS产品研发设计"),
            ("C9", "AI工具研发"),
            ("C10", "项目运营标准化"),
        ],
        formula_cells=[
            ("D4", "经营方针计划（营销）", "common", 14),
            ("D5", "经营方针计划（营销）", "common", 15),
            ("D6", "经营方针计划（营销）", "common", 16),
            ("D7", "经营方针计划（商品）", "product", 10),
            ("D8", "经营方针计划（工具+联动）", "common", 12),
            ("D9", "经营方针计划（工具+联动）", "common", 13),
            ("D10", "经营方针计划（运营）", "common", 14),
        ],
    ),
    "marketing": ResourcePlanSpec(
        config_key="marketing_resource_plan",
        display_name="营销资源分配计划",
        month_label_cell="C8",
        clear_range="C9:C9",
        upstream_formula=("C3", "business_resource_plan", "C14"),
        static_cells=[
            ("C4", "联动营销-首购"),
            ("C5", "联动营销-增购"),
            ("C6", "机构营销-首购"),
        ],
        formula_cells=[
            ("D4", "经营方针计划（营销）", "common", 14),
            ("D5", "经营方针计划（营销）", "common", 15),
            ("D6", "经营方针计划（营销）", "common", 16),
        ],
    ),
    "rd": ResourcePlanSpec(
        config_key="rd_resource_plan",
        display_name="研发资源分配计划",
        month_label_cell="C9",
        clear_range="C10:C10",
        upstream_formula=("C3", "business_resource_plan", "C13"),
        static_cells=[
            ("C4", "制造业项目产品企划能力构建"),
            ("C5", "SAAS产品研发设计"),
            ("C6", "AI工具研发"),
            ("C7", "项目运营标准化"),
        ],
        formula_cells=[
            ("D4", "经营方针计划（商品）", "product", 10),
            ("D5", "经营方针计划（工具+联动）", "common", 12),
            ("D6", "经营方针计划（工具+联动）", "common", 13),
            ("D7", "经营方针计划（运营）", "common", 14),
        ],
    ),
}


def full_sheet_url(config: dict[str, Any], spreadsheet_token: str) -> str:
    domain = config.get("feishu_domain", "https://gw8xslpm5z.feishu.cn").rstrip("/")
    return f"{domain}/sheets/{spreadsheet_token}"


def policy_column(month: int, kind: str) -> str:
    start_index = 8 if kind == "product" else 9
    return column_from_index(start_index + month - 1)


def importrange_formula(url: str, sheet_name: str, range_a1: str) -> str:
    return f'=IMPORTRANGE("{url}","\'{sheet_name}\'!{range_a1}")'


def find_policy_token(client: LarkClient, config: dict[str, Any], month: int) -> str | None:
    policy = config.get("policy_revision", {})
    folder_token = policy.get("folder_token")
    if folder_token:
        target = client.find_sheet_file(folder_token, f"经营方针修正-{month - 1}月")
        if target:
            return target.get("token")
    return policy.get("source_token")


def copy_month_sheet_if_needed(
    client: LarkClient,
    spreadsheet_token: str,
    target_month: int,
    configured_source_month: int | None,
    force_copy: bool,
) -> tuple[str, bool, str]:
    target_sheet = month_sheet_name(target_month)
    existing_id = get_sheet_id(client, spreadsheet_token, target_sheet)
    if existing_id and not force_copy:
        return existing_id, False, "未复制：目标月份 sheet 已存在"

    source_month = configured_source_month or target_month - 1
    if target_month <= 1 and not configured_source_month:
        raise RuntimeError("生成 1 月时无法自动推断上一月，请先配置源月份。")
    source_sheet = month_sheet_name(source_month)
    if not get_sheet_id(client, spreadsheet_token, source_sheet):
        raise RuntimeError(f"找不到源 sheet：{source_sheet}")
    client.copy_worksheet(spreadsheet_token, source_sheet, target_sheet)
    target_id = get_sheet_id(client, spreadsheet_token, target_sheet)
    if not target_id:
        raise RuntimeError(f"复制完成后未找到目标 sheet：{target_sheet}")
    return target_id, True, f"上一月 sheet：{source_sheet}"


def set_single_value(client: LarkClient, spreadsheet_token: str, sheet_id: str, cell: str, value: str) -> None:
    client.set_cells(spreadsheet_token, sheet_id, cell, [[{"value": value}]])


def set_single_formula(client: LarkClient, spreadsheet_token: str, sheet_id: str, cell: str, formula: str) -> None:
    client.set_cells(spreadsheet_token, sheet_id, cell, [[{"formula": formula}]])


def clear_range(client: LarkClient, spreadsheet_token: str, sheet_id: str, range_a1: str) -> None:
    start, _, end = range_a1.partition(":")
    start_row = int("".join(ch for ch in start if ch.isdigit()))
    end_row = int("".join(ch for ch in (end or start) if ch.isdigit()))
    rows = [[{"value": ""}] for _ in range(start_row, end_row + 1)]
    client.set_cells(spreadsheet_token, sheet_id, range_a1, rows)


def apply_resource_plan_formulas(
    client: LarkClient,
    config: dict[str, Any],
    spec: ResourcePlanSpec,
    spreadsheet_token: str,
    sheet_id: str,
    month: int,
) -> str:
    policy_token = find_policy_token(client, config, month)
    if not policy_token:
        raise RuntimeError("缺少方针修正表链接或 token，无法写入方针计划公式。")

    if spec.upstream_formula:
        cell, upstream_key, upstream_range = spec.upstream_formula
        upstream_token = config.get(upstream_key, {}).get("spreadsheet_token")
        if not upstream_token:
            raise RuntimeError(f"缺少 {upstream_key}.spreadsheet_token。")
        set_single_formula(
            client,
            spreadsheet_token,
            sheet_id,
            cell,
            importrange_formula(full_sheet_url(config, upstream_token), month_sheet_name(month), upstream_range),
        )

    for cell, value in spec.static_cells:
        set_single_value(client, spreadsheet_token, sheet_id, cell, value)

    policy_url = full_sheet_url(config, policy_token)
    for cell, source_sheet, column_kind, row in spec.formula_cells:
        column = policy_column(month, column_kind)
        set_single_formula(
            client,
            spreadsheet_token,
            sheet_id,
            cell,
            importrange_formula(policy_url, source_sheet, f"{column}{row}"),
        )

    return policy_token


def generate(config: dict[str, Any], plan: str, month: int | None = None, force_copy: bool = False) -> dict[str, Any]:
    spec = SPECS[plan]
    section = config.get(spec.config_key, {})
    target_month = month or section.get("target_month")
    if not target_month:
        raise RuntimeError("缺少目标月份。")

    spreadsheet_token = section.get("spreadsheet_token")
    if not spreadsheet_token:
        raise RuntimeError(f"缺少 {spec.config_key}.spreadsheet_token。")

    client = LarkClient(config)
    sheet_id, created, source_used = copy_month_sheet_if_needed(
        client,
        spreadsheet_token,
        target_month,
        section.get("source_month"),
        force_copy,
    )
    set_single_value(client, spreadsheet_token, sheet_id, spec.month_label_cell, month_sheet_name(target_month))
    policy_token = apply_resource_plan_formulas(client, config, spec, spreadsheet_token, sheet_id, target_month)
    clear_range(client, spreadsheet_token, sheet_id, spec.clear_range)

    sheet_titles = [
        sheet.get("sheet_name")
        for sheet in client.workbook_info(spreadsheet_token)["data"].get("sheets", [])
    ]
    return {
        "created": created,
        "target": {"name": f"{spec.display_name}-{target_month}月", "sheet_name": month_sheet_name(target_month)},
        "workbook_sheets": sheet_titles,
        "source_used": source_used,
        "policy_token": policy_token,
        "spreadsheet_token": spreadsheet_token,
        "sheet_id": sheet_id,
        "url": full_sheet_url(config, spreadsheet_token),
    }
