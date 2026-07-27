import argparse
import json
import sys

from config_wizard import (
    ensure_business_month_plan_config,
    ensure_config_exists,
    ensure_policy_revision_config,
    run_config_wizard,
    save_config,
    validate_config,
)
from generators.business_month_plan import generate as generate_business_month_plan
from generators.policy_revision import generate as generate_policy_revision
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


def menu() -> int:
    while True:
        config = ensure_config_exists()
        policy = config.get("policy_revision", {})
        default_month = policy.get("target_month")

        print("")
        print("=== 业绩表格生成工具 ===")
        print("1. 生成经营方针修正-X月")
        print("2. 生成事业年月计划-X月")
        print("8. 按需重新配置链接")
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
        elif choice == "8":
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
    return menu()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
