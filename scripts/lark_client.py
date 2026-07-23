import json
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any


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


class LarkClient:
    def __init__(self, config: dict[str, Any]) -> None:
        self.lark_cli = resolve_lark_cli(config)

    def run(self, args: list[str], stdin: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = None
        if stdin is not None:
            payload = json.dumps(stdin, ensure_ascii=False).encode("utf-8")

        last_error = ""
        for attempt in range(1, 4):
            proc = subprocess.run(
                [self.lark_cli, *args, "--format", "json"],
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

    def auth_status(self) -> dict[str, Any]:
        return self.run(["auth", "status", "--verify"])

    def list_folder(self, folder_token: str) -> list[dict[str, Any]]:
        result = self.run(["drive", "files", "list", "--folder-token", folder_token])
        return result["data"]["files"]

    def find_sheet_file(self, folder_token: str, name: str) -> dict[str, Any] | None:
        for item in self.list_folder(folder_token):
            if item.get("name") == name and item.get("type") == "sheet":
                return item
        return None

    def copy_sheet_file(self, source_token: str, folder_token: str, target_name: str) -> dict[str, Any]:
        data = {
            "name": target_name,
            "type": "sheet",
            "folder_token": folder_token,
        }
        return self.run(
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

    def workbook_info(self, spreadsheet_token: str) -> dict[str, Any]:
        return self.run(["sheets", "+workbook-info", "--spreadsheet-token", spreadsheet_token])

    def set_background(self, spreadsheet_token: str, sheet_id: str, range_a1: str, color: str) -> None:
        self.run(
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
                color,
            ]
        )
