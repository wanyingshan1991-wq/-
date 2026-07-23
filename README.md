# 业绩表格生成工具

这是一个给团队内部使用的飞书业绩表格自动生成项目。当前阶段目标是让使用者可以自己完成配置，并跑通第一版功能：

- 生成 `经营方针修正-X月`
- 从源月份表格复制新表
- 设置 `1月` 到 `X月` 的“经营方针调整”区域为白色背景
- 回读校验目标表格和工作表结构

## 推荐使用方式

### 会用电脑的人

1. 打开 GitHub 仓库。
2. 点击 `Code`。
3. 选择 `Download ZIP`。
4. 解压到桌面或常用文件夹。
5. 打开解压后的项目文件夹。
6. 双击 `first_time_setup.bat`。
7. 按提示完成配置。
8. 桌面会出现 `业绩表格生成工具` 入口。
9. 之后直接双击桌面入口运行。

如果系统安全策略禁止创建 `.lnk` 快捷方式，工具会自动改为创建：

```text
业绩表格生成工具.bat
```

这个 `.bat` 也是桌面入口，可以双击运行。

### 使用 WorkBuddy/Codex 的人

把 GitHub 链接发给 WorkBuddy/Codex，然后说：

```text
请打开这个 GitHub 项目，下载或 clone 到本地，按 README 检查 Python 和 lark-cli，完成飞书授权，然后运行 first_time_setup.bat。配置时请让我粘贴自己的飞书文件夹链接、源表链接，并输入源月份和目标月份。完成后请确认桌面是否出现“业绩表格生成工具”快捷方式或 bat 启动器。
```

以后只需要说：

```text
请运行桌面的“业绩表格生成工具”，帮我生成经营方针修正-X月。
```

## 第一次配置需要准备什么

配置向导会要求你提供：

- 飞书域名，或任意飞书表格/文件夹链接
- “方针修正”所在文件夹链接或 `folder_token`
- 源月份，例如 `8`
- 默认目标月份，例如 `9`
- 源表名称，例如 `经营方针修正-8月`
- 源表链接或 `spreadsheet_token`

配置会保存到本地：

```text
config/config.json
```

这个文件只属于使用者自己，不要发给别人，也不要上传 GitHub。

## 链接和 token 怎么填

可以粘贴完整飞书链接，也可以只粘贴 token。

表格链接示例：

```text
https://gw8xslpm5z.feishu.cn/sheets/AVZss1qKOhoUb4tMCuFcMeltnjf
```

工具会自动提取：

```text
AVZss1qKOhoUb4tMCuFcMeltnjf
```

文件夹链接示例：

```text
https://gw8xslpm5z.feishu.cn/drive/folder/GXa5fxrfPlL8dDdt0sXct4eJnDc
```

工具会自动提取：

```text
GXa5fxrfPlL8dDdt0sXct4eJnDc
```

## 日常运行

双击桌面入口：

```text
业绩表格生成工具
```

或在项目文件夹里双击：

```text
run.bat
```

主菜单：

```text
1. 生成经营方针修正-X月
2. 配置/更新飞书 token
3. 检查环境和飞书授权
0. 退出
```

生成前工具会显示执行摘要：

```text
即将执行：
- 生成表格：经营方针修正-9月
- 源表名称：经营方针修正-8月
- 源表 token：...
- 目标文件夹 token：...

是否继续？输入 Y 继续，其他任意键取消
```

只有确认后才会执行。

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

创建桌面入口：

```text
create_desktop_shortcut.bat
```

首次设置：

```text
first_time_setup.bat
```

## 安装和授权

需要本机安装：

- Python 3.10 或更新版本
- 飞书 CLI：`lark-cli`

飞书 CLI 授权命令：

```bash
lark-cli auth login --domain docs --domain drive
```

如果授权失败，让 WorkBuddy/Codex 读取：

```bash
lark-cli auth status --json --verify
```

并按缺失权限提示处理。

## 安全说明

- 不要提交 `config/config.json`。
- 不要把 access token、refresh token、app secret 放进 GitHub。
- `config/config.example.json` 是空模板，不能直接运行。
- 每个使用者都应该配置自己的飞书文件夹和源表链接。

## 当前限制

- 当前只支持 `经营方针修正-X月`。
- 目前通过 `lark-cli` 操作飞书，不是纯 OpenAPI 独立程序。
- 新电脑需要先安装并授权 `lark-cli`。
