import argparse
import json
import sys
from pathlib import Path

from config_wizard import DEFAULT_CONFIG_PATH, load_config
from generators.policy_revision import generate


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate monthly policy revision sheet by copying the prior month.")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG_PATH))
    parser.add_argument("--month", type=int)
    parser.add_argument("--force-copy", action="store_true", help="Create another copy even if target exists.")
    args = parser.parse_args()

    config = load_config(Path(args.config))
    result = generate(config, month=args.month, force_copy=args.force_copy)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
