# AnkiRead

一个面向 Windows 的 Anki 学习记录工具：手机完成 Anki 学习并同步到 AnkiWeb 后，电脑端 Anki 自动同步，AnkiRead 读取桌面 Anki 的本地数据库，生成最近几天的学习与复习词汇 Markdown 报告。

## 功能

- 自动查找并启动 `anki.exe`；
- 等待桌面 Anki 从 AnkiWeb 同步；
- 正常关闭 Anki，避免数据库锁定；
- 输出学习、复习和重新学习过的卡片；
- 支持最近任意天数，例如 1 天、5 天或 30 天；
- 可按 Anki 配置和牌组筛选；
- 输出正面、背面、标签、评分、间隔和复习耗时；
- 生成等报告md文件；
- 提供图形界面和命令行两种使用方式。

## 图形界面

从仓库的 [Releases](https://github.com/Haoyulin0v0/AnkiRead/releases) 下载 `AnkiRead.exe`，双击打开。

在界面中填写：

- 统计天数：例如 `5`；
- Anki 配置：多个用户配置时填写，例如 `User 1`；
- 牌组：填写完整牌组名，留空表示全部牌组；
- 等待同步秒数：默认 `45`，网络较慢时可改成 `90`；
- 输出文件：例如 `last_5_days.md`；
- `anki.exe` 路径：默认会尝试查找 `D:\Anki\anki.exe`。

点击“启动 Anki、同步并生成报告”即可。

使用前请先在桌面 Anki 中开启：

```text
工具 → 首选项 → 同步 → 打开/关闭配置文件时自动同步
```

推荐流程：

```text
手机 Anki 学习并同步
        ↓
打开 AnkiRead.exe
        ↓
桌面 Anki 自动同步
        ↓
AnkiRead 关闭 Anki 并读取数据库
        ↓
生成 Markdown 报告
```

## 命令行方式

如果不使用 GUI，可以运行打包程序：

```powershell
.\AnkiRead.exe --days 5
```

指定 Anki 路径：

```powershell
.\AnkiRead.exe --anki-path "D:\Anki\anki.exe" --days 5
```

源代码运行方式：

```powershell
python .\anki_today.py --local --days 5
```

只生成某个牌组：

```powershell
python .\anki_today.py --local --days 5 --deck "托福绿宝书"
```

指定 Anki 配置：

```powershell
python .\anki_today.py --local --days 5 --profile "User 1"
```

## 报告内容

报告会同时包含：

- 新卡学习；
- 已学卡片的复习；
- 失败后的重新学习；
- 每张卡片当天的多次复习记录。

例如：

```text
复习（评分 4，间隔 8 天，耗时 3.0 秒）
重新学习（评分 3，间隔 1 天，耗时 2.0 秒）
```

## 常见问题

### `anki.exe was not found`

在界面中点击“浏览”选择 `anki.exe`，或者命令行指定：

```powershell
.\AnkiRead.exe --anki-path "D:\你的实际路径\anki.exe" --days 5
```

### `database is locked`

不要在 Anki 正在运行时直接读取数据库。关闭已经打开的 Anki，再运行 AnkiRead。GUI 会自动等待同步并正常关闭 Anki。

### 报告没有数据

确认手机已经同步、桌面 Anki 已登录同一个 AnkiWeb 账户，并适当增加等待时间。

## 从源码打包

需要 Python 和 PyInstaller：

```powershell
python -m pip install pyinstaller
pyinstaller --noconfirm --clean --onefile --windowed --name AnkiRead .\anki_read_gui.py
```

GitHub Actions 也会自动构建 Windows 程序。可以在仓库的 Actions 页面运行发布流程，生成带有 `AnkiRead.exe` 的 Release。

