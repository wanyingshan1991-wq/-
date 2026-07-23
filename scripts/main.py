import argparse
import json
import sys

from config_wizard import ensure_config_exists, load_config, run_config_wizard
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
    print("工作表：")
    for title in result["workbook_sheets"]:
        print(f"- {title}")
    print("")


def check_environment() -> None:
    config = ensure_config_exists()
    client = LarkClient(config)
    status = client.auth_status()
    print(json.dumps(status, ensure_ascii=False, indent=2))


def menu() -> int:
    while True:
        config = ensure_config_exists()
        policy = config.get("policy_revision", {})
        default_month = policy.get("target_month")

        print("")
        print("=== 业绩表格生成工具 ===")
        print("1. 生成经营方针修正-X月")
        print("2. 配置/更新飞书 token")
        print("3. 检查环境和飞书授权")
        print("0. 退出")
        choice = input("请输入选项: ").strip()

        if choice == "1":
            month = ask_month(default_month)
            result = generate_policy_revision(config, month=month)
            print_result(result)
        elif choice == "2":
            config = run_config_wizard()
            print("配置完成。")
        elif choice == "3":
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

    args = parser.parse_args()

    if args.command == "configure":
        run_config_wizard()
        return 0
    if args.command == "check":
        check_environment()
        return 0
    if args.command == "generate-policy":
        config = ensure_config_exists()
        result = generate_policy_revision(config, month=args.month, force_copy=args.force_copy)
        print_result(result)
        return 0
    return menu()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
