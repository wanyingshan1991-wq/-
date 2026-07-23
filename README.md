# 业绩表格生成工具

这是一个给团队内部使用的飞书业绩表格自动生成项目。第一阶段目标是让使用者可以自己完成配置，并跑通第一版功能：

- 生成 `经营方针修正-X月`
- 从源月份表格复制新表
- 设置当月“经营方针调整”区域为白色背景
- 回读校验目标表格和工作表结构

## 适合谁使用

会用电脑的人：按下面步骤配置后，双击 `run.bat`，按菜单操作。

不会命令行的人：把这个项目交给 WorkBuddy/Codex，并让它按本 README 帮你安装、授权、配置和运行。

## 第一次使用

1. 安装 Python 3.10 或更新版本。
2. 安装飞书 CLI：`lark-cli`。
3. 登录并授权飞书 CLI：

```bash
lark-cli auth login --domain docs --domain drive
```

4. 双击 `run.bat`。
5. 如果没有 `config/config.json`，工具会自动进入配置向导。
6. 按提示粘贴飞书文件夹链接、源表链接或 token。
7. 回到主菜单，选择 `1. 生成经营方针修正-X月`。

## 主菜单

双击 `run.bat` 后会出现：

```text
1. 生成经营方针修正-X月
2. 配置/更新飞书 token
3. 检查环境和飞书授权
0. 退出
```

## 配置向导

可以运行：

```bash
python scripts/main.py configure
```

也可以在主菜单选择：

```text
2. 配置/更新飞书 token
```

配置向导支持两种输入方式：

- 粘贴完整飞书链接
- 只粘贴 token

例如表格链接：

```text
https://gw8xslpm5z.feishu.cn/sheets/AVZss1qKOhoUb4tMCuFcMeltnjf
```

工具会自动提取：

```text
AVZss1qKOhoUb4tMCuFcMeltnjf
```

例如文件夹链接：

```text
https://gw8xslpm5z.feishu.cn/drive/folder/GXa5fxrfPlL8dDdt0sXct4eJnDc
```

工具会自动提取：

```text
GXa5fxrfPlL8dDdt0sXct4eJnDc
```

## 配置文件

真实配置文件是：

```text
config/config.json
```

示例配置文件是：

```text
config/config.example.json
```

示例配置：

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

字段说明：

- `feishu_domain`：飞书文档域名。
- `lark_cli_path`：一般留空。只有系统找不到 `lark-cli` 时才填写完整路径。
- `folder_token`：方针修正文件所在文件夹 token。
- `source_month`：源月份，通常是目标月份减 1。
- `source_name`：源表名称。
- `source_token`：源表 token。脚本会优先按 `source_name` 在文件夹里查找，找不到时使用这个 token。
- `target_month`：默认生成月份。运行时也可以重新输入。

## 常用命令

启动主菜单：

```bash
python scripts/main.py
```

配置/更新 token：

```bash
python scripts/main.py configure
```

检查环境和飞书授权：

```bash
python scripts/main.py check
```

直接生成方针修正：

```bash
python scripts/main.py generate-policy --month 8
```

兼容旧入口：

```bash
python scripts/generate_policy_revision.py --month 8
```

## 让 Agent 帮你执行

可以直接对 WorkBuddy/Codex 说：

```text
请根据 README 帮我检查 Python、安装或检查 lark-cli、完成飞书授权，然后运行 python scripts/main.py configure 配置 token，最后生成经营方针修正-8月。
```

如果授权失败，让 Agent 读取：

```bash
lark-cli auth status --json --verify
```

并按缺失权限提示处理。

## 安全说明

- 不要提交 `config/config.json`。
- 不要把 access token、refresh token、app secret 放进 GitHub。
- `config.example.json` 只放示例 token，团队外公开前请确认这些示例 token 是否允许暴露。

## 当前限制

- 第一阶段只支持 `经营方针修正-X月`。
- 目前通过 `lark-cli` 操作飞书，不是纯 OpenAPI 独立程序。
- 新电脑需要先安装并授权 `lark-cli`。
