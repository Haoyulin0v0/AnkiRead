# Anki 今日学习记录

程序读取桌面 Anki 同步后的本地 collection，提取当天实际发生的学习/复习记录，并更新 `today.md`。手机不需要导出文件。

## 推荐流程：手机同步，电脑读取

1. 在桌面 Anki 安装 [AnkiConnect](https://github.com/FooSoft/anki-connect)，并保持桌面 Anki 打开。
2. 手机完成学习后点击同步。
3. 桌面 Anki 点击同步，或运行下面的命令让程序请求同步：

```powershell
python .\anki_today.py --anki-connect --sync
```

程序会请求桌面 Anki 同步，然后自动读取桌面 Anki 的本地 collection，更新 `today.md`。如果已经手动同步，可以省略 `--sync`：

```powershell
python .\anki_today.py --anki-connect
```

如果有多个 Anki 配置，可指定配置名：

```powershell
python .\anki_today.py --anki-connect --profile "User 1"
```

## 不使用 AnkiConnect

也可以完全不安装 AnkiConnect。先在桌面 Anki 中完成同步，再让程序直接读取桌面 Anki 的本地数据库：

```powershell
python .\anki_today.py --local
```

如果有多个 Anki 配置：

```powershell
python .\anki_today.py --local --profile "User 1"
```

这个模式不会触发同步；它只读取桌面 Anki 已经同步好的数据。因此步骤是：手机点击同步 → 桌面 Anki 点击同步 → 运行命令。运行程序时建议暂时不要在桌面 Anki 中进行复习或编辑，以免数据库正在写入。

## 自动启动并生成五天报告

桌面 Anki 自带“启动时自动同步”功能。打开 `工具 → 首选项 → 同步`，启用“打开/关闭配置文件时自动同步”。Anki 官方手册说明，启用后打开或关闭配置文件时会自动与 AnkiWeb 同步。[同步设置说明](https://docs.ankiweb.net/preferences.html?highlight=sync)

本项目提供了等待同步后生成报告的脚本：

```powershell
powershell -ExecutionPolicy Bypass -File .\update_anki_report.ps1 -Days 5
```

脚本会启动 Anki，默认等待 45 秒，然后正常关闭 Anki 以释放数据库锁，最后生成 `last_5_days.md`。如果网络较慢，可以增加等待时间：

```powershell
powershell -ExecutionPolicy Bypass -File .\update_anki_report.ps1 -WaitSeconds 90 -Days 5
```

如果脚本提示找不到 `anki.exe`，请在 Anki 已打开时从任务管理器中右键 Anki，选择“打开文件所在位置”，复制 `anki.exe` 的完整路径，然后运行：

```powershell
powershell -ExecutionPolicy Bypass -File .\update_anki_report.ps1 -AnkiPath "C:\你的实际路径\anki.exe" -Days 5
```

如果 Anki 已经在运行，脚本会停止并提示你先关闭 Anki；不要在 Anki 正在使用时读取 collection。要自动运行它，可以把上面的命令创建成快捷方式，使用这个脚本启动 Anki，而不是直接启动 `anki.exe`。这个方案不需要 AnkiConnect；Anki 自己负责同步，脚本只读取同步后的本地数据库。

程序默认按电脑本地时区判断“今天”。查看其他日期：

```powershell
python .\anki_today.py --anki-connect --date 2026-08-20
```

## 备用流程：读取导出文件

也支持 `.colpkg`、`.apkg`、`collection.anki2` 和 `collection.anki21`：

```powershell
python .\anki_today.py .\collection.colpkg
```

程序按卡片去重，但保留同一张卡片当天的多次学习/复习事件，并显示牌组、正面、背面、标签、评分、间隔和耗时。

导出的 collection 包含完整卡片内容，请不要把它上传到公开仓库。

## AnkiRead.exe

使用 PyInstaller 打包后，可以直接运行 Windows 程序：

```powershell
.\AnkiRead.exe --days 5
```

程序会自动查找 `D:\Anki\anki.exe` 以及常见安装位置，启动 Anki、等待自动同步、正常关闭 Anki，并生成 `last_5_days.md`。如果安装位置特殊：

```powershell
.\AnkiRead.exe --anki-path "D:\Apps\Anki\anki.exe" --days 5
```

