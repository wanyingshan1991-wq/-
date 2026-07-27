import argparse
import json
import sys
from datetime import date

from config_wizard import (
    ask_person_name,
    ensure_business_month_plan_config,
    ensure_config_exists,
    ensure_personal_month_plan_config,
    ensure_personal_week_day_plan_config,
    ensure_policy_revision_config,
    ensure_resource_plan_config,
    run_config_wizard,
    save_config,
)
from generators.business_month_plan import generate as generate_business_month_plan
from generators.personal_plans import generate_personal_month_plan, generate_personal_week_day_plan
from generators.policy_revision import generate as generate_policy_revision
from generators.resource_plans import SPECS as RESOURCE_PLAN_SPECS
from generators.resource_plans import generate as generate_resource_plan
from lark_client import LarkClient


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")


def ask_month(default: int | None = None) -> int:
    suffix = f" [{default}]" if default else ""
    while True:
        raw = input(f"请输入要生成的月份数字，例如 8{suffix}: ").strip()
        if not raw and default:
            return default
        try:
            return int(raw)
        except ValueError:
            print("请输入数字，例如 8。")


def ask_year(default: int | None = None) -> int:
    default = default or date.today().year
    while True:
        raw = input(f"请输入年份，例如 {default} [{default}]: ").strip()
        if not raw:
            return default
        try:
            value = int(raw)
            if 2000 <= value <= 2100:
                return value
            print("年份必须在 2000-2100 之间。")
        except ValueError:
            print("请输入数字年份，例如 2026。")


def print_result(result: dict) -> None:
    print("")
    print("=== 执行结果 ===")
    print(f"是否新建：{'是' if result['created'] else '否，目标表已存在'}")
    print(f"表格名称：{result['target'].get('name')}")
    print(f"表格链接：{result['url']}")
    print(f"源表选择：{result.get('source_used', '未记录')}")
    print("工作表：")
    for title in result["workbook_sheets"]:
        print(f"- {title}")
    print("")


def check_environment() -> None:
    config = ensure_config_exists()
    client = LarkClient(config)
    status = client.auth_status()
    print(json.dumps(status, ensure_ascii=False, indent=2))


def confirm_policy_generation(config: dict, month: int) -> bool:
    policy = config["policy_revision"]
    source_month = policy.get("source_month") or month - 1
    source_name = policy.get("source_name") or f"经营方针修正-{source_month}月"

    print("")
    print("即将执行：")
    print(f"- 生成表格：经营方针修正-{month}月")
    print(f"- 源表名称：{source_name}")
    print(f"- 源表 token：{policy.get('source_token')}")
    print(f"- 目标文件夹 token：{policy.get('folder_token')}")
    answer = input("是否继续？输入 Y 继续，其他任意键取消: ").strip().lower()
    return answer == "y"


def confirm_business_month_plan_generation(config: dict, month: int) -> bool:
    section = config["business_month_plan"]
    source_month = section.get("source_month") or month - 1
    print("")
    print("即将执行：")
    print(f"- 生成工作表：事业年月计划-{month}月")
    print(f"- 所在表格 token：{section.get('spreadsheet_token')}")
    print(f"- 源 sheet：{source_month}月")
    print(f"- 目标 sheet：{month}月")
    print("- 将设置 Row 6/9/13 的 1月到目标月为白色")
    print("- 将更新 R/S/T 完成率公式，并清空 E14/E15")
    answer = input("是否继续？输入 Y 继续，其他任意键取消: ").strip().lower()
    return answer == "y"


def confirm_resource_plan_generation(config: dict, plan: str, month: int) -> bool:
    spec = RESOURCE_PLAN_SPECS[plan]
    section = config[spec.config_key]
    source_month = section.get("source_month") or month - 1
    print("")
    print("即将执行：")
    print(f"- 生成工作表：{spec.display_name}-{month}月")
    print(f"- 所在表格 token：{section.get('spreadsheet_token')}")
    print(f"- 源 sheet：{source_month}月")
    print(f"- 目标 sheet：{month}月")
    print(f"- 将更新月份标签：{spec.month_label_cell}")
    print("- 将写入上游引用和方针引用公式")
    print(f"- 将清空人工填写区：{spec.clear_range}")
    answer = input("是否继续？输入 Y 继续，其他任意键取消: ").strip().lower()
    return answer == "y"


def confirm_personal_month_generation(person_name: str, month: int, year: int) -> bool:
    print("")
    print("即将执行：")
    print(f"- 生成人员：{person_name}")
    print(f"- 生成工作表：个人月周推移计划-{month}月")
    print(f"- 日期范围：{year}年{month}月1日所在周的周一开始，连续 35 天")
    print("- 将写入 C3/C4 上游公式、日期行、星期行和周标签")
    print("- 将清空 C7:AK7 与 C9:AK30 人工填写区")
    answer = input("是否继续？输入 Y 继续，其他任意键取消: ").strip().lower()
    return answer == "y"


def confirm_personal_week_day_generation(person_name: str, month: int, year: int) -> bool:
    print("")
    print("即将执行：")
    print(f"- 生成人员：{person_name}")
    print(f"- 生成内容：个人周日推移计划-{month}月对应 5 个周 sheet")
    print(f"- 周范围：{year}年{month}月1日所在周起连续 5 周")
    print("- 将写入 C3 周计划公式、C6:I6 日期、C7:I7 星期")
    print("- 将清空 C4:C5、C8:I8、C9:I12 人工填写区")
    answer = input("是否继续？输入 Y 继续，其他任意键取消: ").strip().lower()
    return answer == "y"


def confirm_all_core_generation(month: int, include_person: bool, person_name: str | None, year: int | None) -> bool:
    print("")
    print("即将统一生成：")
    print(f"- 目标月份：{month}月")
    print(f"- 依赖：经营方针修正-{month - 1}月 已存在或可由配置定位")
    print("- 1. 事业年月计划")
    print("- 2. 事业资源分配计划")
    print("- 3. 营销资源分配计划")
    print("- 4. 研发资源分配计划")
    if include_person and person_name and year:
        print(f"- 5. {person_name} 的个人月周推移计划（{year}年{month}月）")
        print(f"- 6. {person_name} 的个人周日推移计划（{year}年{month}月）")
    else:
        print("- 个人计划：本次跳过")
    answer = input("是否继续？输入 Y 继续，其他任意键取消: ").strip().lower()
    return answer == "y"


def run_resource_plan_flow(config: dict, plan: str, default_month: int | None) -> None:
    spec = RESOURCE_PLAN_SPECS[plan]
    config = ensure_policy_revision_config(config)
    config = ensure_resource_plan_config(config, spec.config_key)
    section = config.setdefault(spec.config_key, {})
    month = ask_month(section.get("target_month") or default_month)
    section["target_month"] = month
    save_config(config)
    if not confirm_resource_plan_generation(config, plan, month):
        print("已取消。")
        return
    result = generate_resource_plan(config, plan=plan, month=month)
    print_result(result)


def run_personal_month_flow(config: dict, default_month: int | None) -> None:
    person_name = ask_person_name(config)
    config = ensure_personal_month_plan_config(config, person_name)
    person = config.setdefault("people", {}).setdefault(person_name, {})
    month = ask_month(person.get("target_month") or default_month)
    year = ask_year(person.get("target_year"))
    person["target_month"] = month
    person["target_year"] = year
    save_config(config)
    if not confirm_personal_month_generation(person_name, month, year):
        print("已取消。")
        return
    result = generate_personal_month_plan(config, person_name, month, year)
    print_result(result)


def run_personal_week_day_flow(config: dict, default_month: int | None) -> None:
    person_name = ask_person_name(config)
    config = ensure_personal_week_day_plan_config(config, person_name)
    person = config.setdefault("people", {}).setdefault(person_name, {})
    month = ask_month(person.get("target_month") or default_month)
    year = ask_year(person.get("target_year"))
    person["target_month"] = month
    person["target_year"] = year
    save_config(config)
    if not confirm_personal_week_day_generation(person_name, month, year):
        print("已取消。")
        return
    result = generate_personal_week_day_plan(config, person_name, month, year)
    print_result(result)


def run_all_core_flow(config: dict, default_month: int | None) -> None:
    month = ask_month(default_month)
    include_person_answer = input("是否同时生成某个人的个人月周和周日计划？输入 Y 继续，其他任意键跳过: ").strip().lower()
    include_person = include_person_answer == "y"
    person_name = None
    year = None

    config = ensure_policy_revision_config(config)
    config = ensure_business_month_plan_config(config)
    for plan in ("business", "marketing", "rd"):
        spec = RESOURCE_PLAN_SPECS[plan]
        config = ensure_resource_plan_config(config, spec.config_key)
        config.setdefault(spec.config_key, {})["target_month"] = month

    config.setdefault("business_month_plan", {})["target_month"] = month

    if include_person:
        person_name = ask_person_name(config)
        config = ensure_personal_week_day_plan_config(config, person_name)
        person = config.setdefault("people", {}).setdefault(person_name, {})
        year = ask_year(person.get("target_year"))
        person["target_month"] = month
        person["target_year"] = year

    save_config(config)
    if not confirm_all_core_generation(month, include_person, person_name, year):
        print("已取消。")
        return

    steps = [
        ("事业年月计划", lambda: generate_business_month_plan(config, month=month)),
        ("事业资源分配计划", lambda: generate_resource_plan(config, plan="business", month=month)),
        ("营销资源分配计划", lambda: generate_resource_plan(config, plan="marketing", month=month)),
        ("研发资源分配计划", lambda: generate_resource_plan(config, plan="rd", month=month)),
    ]
    if include_person and person_name and year:
        steps.extend(
            [
                ("个人月周推移计划", lambda: generate_personal_month_plan(config, person_name, month, year)),
                ("个人周日推移计划", lambda: generate_personal_week_day_plan(config, person_name, month, year)),
            ]
        )

    print("")
    print("=== 开始统一生成 ===")
    for label, action in steps:
        print(f"正在生成：{label}...")
        result = action()
        print_result(result)
    print("统一生成完成。")


def menu() -> int:
    while True:
        config = ensure_config_exists()
        policy = config.get("policy_revision", {})
        default_month = policy.get("target_month")

        print("")
        print("=== 业绩表格生成工具 ===")
        print("1. 生成经营方针修正-X月")
        print("2. 生成事业年月计划-X月")
        print("3. 生成事业资源分配计划-X月")
        print("4. 生成营销资源分配计划-X月")
        print("5. 生成研发资源分配计划-X月")
        print("6. 生成个人月周推移计划-姓名-X月")
        print("7. 生成个人周日推移计划-姓名-X月")
        print("8. 统一生成X月核心表格")
        print("88. 按需重新配置链接")
        print("9. 检查环境和飞书授权")
        print("0. 退出")
        choice = input("请输入选项: ").strip()

        if choice == "1":
            month = ask_month(default_month)
            config = ensure_policy_revision_config(config)
            if not confirm_policy_generation(config, month):
                print("已取消。")
                continue
            result = generate_policy_revision(config, month=month)
            print_result(result)
        elif choice == "2":
            config = ensure_business_month_plan_config(config)
            default_business_month = config.get("business_month_plan", {}).get("target_month") or default_month
            month = ask_month(default_business_month)
            config.setdefault("business_month_plan", {})["target_month"] = month
            save_config(config)
            if not confirm_business_month_plan_generation(config, month):
                print("已取消。")
                continue
            result = generate_business_month_plan(config, month=month)
            print_result(result)
        elif choice == "3":
            run_resource_plan_flow(config, "business", default_month)
        elif choice == "4":
            run_resource_plan_flow(config, "marketing", default_month)
        elif choice == "5":
            run_resource_plan_flow(config, "rd", default_month)
        elif choice == "6":
            run_personal_month_flow(config, default_month)
        elif choice == "7":
            run_personal_week_day_flow(config, default_month)
        elif choice == "8":
            run_all_core_flow(config, default_month)
        elif choice == "88":
            config = run_config_wizard()
            print("配置完成。")
        elif choice == "9":
            check_environment()
        elif choice == "0":
            return 0
        else:
            print("无效选项，请重新输入。")


def main() -> int:
    parser = argparse.ArgumentParser(description="业绩表格生成工具")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("configure")
    subparsers.add_parser("check")
    generate_parser = subparsers.add_parser("generate-policy")
    generate_parser.add_argument("--month", type=int)
    generate_parser.add_argument("--force-copy", action="store_true")
    business_parser = subparsers.add_parser("generate-business-month")
    business_parser.add_argument("--month", type=int)
    business_parser.add_argument("--force-copy", action="store_true")
    resource_parser = subparsers.add_parser("generate-resource")
    resource_parser.add_argument("plan", choices=sorted(RESOURCE_PLAN_SPECS))
    resource_parser.add_argument("--month", type=int)
    resource_parser.add_argument("--force-copy", action="store_true")
    personal_month_parser = subparsers.add_parser("generate-personal-month")
    personal_month_parser.add_argument("person_name")
    personal_month_parser.add_argument("--month", type=int)
    personal_month_parser.add_argument("--year", type=int)
    personal_month_parser.add_argument("--force-copy", action="store_true")
    personal_week_parser = subparsers.add_parser("generate-personal-week")
    personal_week_parser.add_argument("person_name")
    personal_week_parser.add_argument("--month", type=int)
    personal_week_parser.add_argument("--year", type=int)
    personal_week_parser.add_argument("--force-copy", action="store_true")
    all_parser = subparsers.add_parser("generate-all-core")
    all_parser.add_argument("--month", type=int)
    all_parser.add_argument("--year", type=int)
    all_parser.add_argument("--person-name")

    args = parser.parse_args()

    if args.command == "configure":
        run_config_wizard()
        return 0
    if args.command == "check":
        check_environment()
        return 0
    if args.command == "generate-policy":
        config = ensure_config_exists()
        config = ensure_policy_revision_config(config)
        month = args.month or config.get("policy_revision", {}).get("target_month")
        if not month:
            month = ask_month()
        if not confirm_policy_generation(config, month):
            print("已取消。")
            return 1
        result = generate_policy_revision(config, month=month, force_copy=args.force_copy)
        print_result(result)
        return 0
    if args.command == "generate-business-month":
        config = ensure_config_exists()
        config = ensure_business_month_plan_config(config)
        month = args.month or config.get("business_month_plan", {}).get("target_month")
        if not month:
            month = ask_month()
        config.setdefault("business_month_plan", {})["target_month"] = month
        save_config(config)
        if not confirm_business_month_plan_generation(config, month):
            print("已取消。")
            return 1
        result = generate_business_month_plan(config, month=month, force_copy=args.force_copy)
        print_result(result)
        return 0
    if args.command == "generate-resource":
        config = ensure_config_exists()
        spec = RESOURCE_PLAN_SPECS[args.plan]
        config = ensure_policy_revision_config(config)
        config = ensure_resource_plan_config(config, spec.config_key)
        month = args.month or config.get(spec.config_key, {}).get("target_month")
        if not month:
            month = ask_month()
        config.setdefault(spec.config_key, {})["target_month"] = month
        save_config(config)
        if not confirm_resource_plan_generation(config, args.plan, month):
            print("已取消。")
            return 1
        result = generate_resource_plan(config, plan=args.plan, month=month, force_copy=args.force_copy)
        print_result(result)
        return 0
    if args.command == "generate-personal-month":
        config = ensure_config_exists()
        config = ensure_personal_month_plan_config(config, args.person_name)
        person = config.setdefault("people", {}).setdefault(args.person_name, {})
        month = args.month or person.get("target_month")
        if not month:
            month = ask_month()
        year = args.year or person.get("target_year") or ask_year()
        person["target_month"] = month
        person["target_year"] = year
        save_config(config)
        if not confirm_personal_month_generation(args.person_name, month, year):
            print("已取消。")
            return 1
        result = generate_personal_month_plan(config, args.person_name, month, year, force_copy=args.force_copy)
        print_result(result)
        return 0
    if args.command == "generate-personal-week":
        config = ensure_config_exists()
        config = ensure_personal_week_day_plan_config(config, args.person_name)
        person = config.setdefault("people", {}).setdefault(args.person_name, {})
        month = args.month or person.get("target_month")
        if not month:
            month = ask_month()
        year = args.year or person.get("target_year") or ask_year()
        person["target_month"] = month
        person["target_year"] = year
        save_config(config)
        if not confirm_personal_week_day_generation(args.person_name, month, year):
            print("已取消。")
            return 1
        result = generate_personal_week_day_plan(config, args.person_name, month, year, force_copy=args.force_copy)
        print_result(result)
        return 0
    if args.command == "generate-all-core":
        config = ensure_config_exists()
        month = args.month or config.get("policy_revision", {}).get("target_month")
        if not month:
            month = ask_month()
        include_person = bool(args.person_name)
        person_name = args.person_name
        year = args.year
        config = ensure_policy_revision_config(config)
        config = ensure_business_month_plan_config(config)
        for plan in ("business", "marketing", "rd"):
            spec = RESOURCE_PLAN_SPECS[plan]
            config = ensure_resource_plan_config(config, spec.config_key)
            config.setdefault(spec.config_key, {})["target_month"] = month
        config.setdefault("business_month_plan", {})["target_month"] = month
        if include_person and person_name:
            config = ensure_personal_week_day_plan_config(config, person_name)
            person = config.setdefault("people", {}).setdefault(person_name, {})
            year = year or person.get("target_year") or ask_year()
            person["target_month"] = month
            person["target_year"] = year
        save_config(config)
        if not confirm_all_core_generation(month, include_person, person_name, year):
            print("已取消。")
            return 1
        for _, action in [
            ("事业年月计划", lambda: generate_business_month_plan(config, month=month)),
            ("事业资源分配计划", lambda: generate_resource_plan(config, plan="business", month=month)),
            ("营销资源分配计划", lambda: generate_resource_plan(config, plan="marketing", month=month)),
            ("研发资源分配计划", lambda: generate_resource_plan(config, plan="rd", month=month)),
        ]:
            print_result(action())
        if include_person and person_name and year:
            print_result(generate_personal_month_plan(config, person_name, month, year))
            print_result(generate_personal_week_day_plan(config, person_name, month, year))
        return 0
    return menu()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
