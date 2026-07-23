# 业绩表格生成工具

这是一个给团队内部使用的飞书业绩表格自动生成项目。第一版只支持：

- 生成 `经营方针修正-X月`
- 从上一月表格复制新表
- 设置当月“经营方针调整”区域为白色背景
- 回读校验目标表格和工作表结构

## 适合谁使用

会用电脑的人：按下面步骤配置后，双击 `run.bat`。

不会命令行的人：把这个项目交给 WorkBuddy/Codex，并让它按本 README 帮你安装、授权、配置和运行。

## 第一次使用

1. 安装 Python 3.10 或更新版本。
2. 安装飞书 CLI：`lark-cli`。
3. 登录并授权飞书 CLI：

```bash
lark-cli auth login --domain docs --domain drive
```

4. 复制配置文件：

```bash
copy config\config.example.json config\config.json
```

5. 检查 `config\config.json` 里的配置。
6. 双击 `run.bat`，输入月份，例如 `8`。

## 配置说明

`config/config.example.json` 提供了一份可参考的示例配置：

```json
{
  "feishu_domain": "https://gw8xslpm5z.feishu.cn",
  "lark_cli_path": "",
  "policy_revision": {
    "folder_token": "GXa5fxrfPlL8dDdt0sXct4eJnDc",
    "source_month": 7,
    "source_name": "经营方针修正-7月",
    "source_token": "AVZss1qKOhoUb4tMCuFcMeltnjf",
    "target_month": 8
  }
}
```

- `feishu_domain`：飞书文档域名。
- `lark_cli_path`：一般留空。只有系统找不到 `lark-cli` 时才填写完整路径。
- `folder_token`：方针修正文件所在文件夹 token。
- `source_month`：源月份，通常是目标月份减 1。
- `source_name`：源表名称。
- `source_token`：源表 token。脚本会优先按 `source_name` 在文件夹里查找，找不到时使用这个 token。
- `target_month`：默认生成月份。也可以运行时输入或用 `--month` 覆盖。

真实配置文件是 `config/config.json`，不会提交到 GitHub。

## 常用运行方式

双击：

```text
run.bat
```

命令行：

```bash
python scripts/generate_policy_revision.py --month 8
```

环境检查：

```text
setup_check.bat
```

## 让 Agent 帮你执行

可以直接对 WorkBuddy/Codex 说：

```text
请根据 README 帮我检查 Python、安装或检查 lark-cli、完成飞书授权，并运行 run.bat 生成经营方针修正-8月。
```

如果授权失败，让 Agent 读取 `lark-cli auth status --json --verify` 的结果，并按缺失权限提示处理。

## 安全说明

- 不要提交 `config/config.json`。
- 不要把 access token、refresh token、app secret 放进 GitHub。
- `config.example.json` 只放示例 token，团队外公开前请确认这些示例 token 是否允许暴露。

## 当前限制

- 第一版只支持 `经营方针修正-X月`。
- 目前通过 `lark-cli` 操作飞书，不是纯 OpenAPI 独立程序。
- 新电脑需要先安装并授权 `lark-cli`。
