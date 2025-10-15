# 动态壁纸生成器

用几张按时间排好的图片，直接生成 macOS 能识别的动态壁纸 HEIC 文件。

[English](README.md) | 中文版

## 能做什么
- 支持 PNG、JPEG 等 Pillow 能打开的图片。
- 输出带 `apple_desktop:h24` 信息的 HEIC 序列，macOS 会按时间自动切图。
- 可以标记哪张图是浅色模式、深色模式。
- 默认把所有图片的尺寸调整成第一张的大小，也可以改成严格模式。

## 准备工作
- macOS 11 以上，Python 3.10 或更新。
- `pillow-heif` 的 macOS 轮子自带 `libheif`，不用另外安装编码器。

## 快速上手
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .

dynamic-wallpaper --config examples/schedule.json --output ~/Pictures/MyDynamicWall.heic
```

命令会根据 `examples/schedule.json` 里的时间表生成 `MyDynamicWall.heic`。

## 清单格式（manifest）
使用一个 JSON 文件描述图片和时间，按时间排序。每项需要：
- `file`：图片路径，默认相对 manifest 所在目录。
- `time`：24 小时制时间，`HH:MM` 或 `HH:MM:SS`。
- 可选 `appearance`：写 `light` 或 `dark`，告诉 macOS 这张图对应浅色或深色模式。

示例：
```json
{
  "frames": [
    {"file": "sunrise.png", "time": "05:30", "appearance": "light"},
    {"file": "midday.png", "time": "12:00"},
    {"file": "sunset.png", "time": "18:30"},
    {"file": "night.png", "time": "23:00", "appearance": "dark"}
  ]
}
```

## 命令行参数
- `--config`：manifest 路径（必填）。
- `--output`：输出 HEIC 文件路径（必填，会覆盖已有文件）。
- `--quality`：HEVC 质量 1-100，默认 90。
- `--resize-mode`：`fit`（默认）会把图片缩放到第一张大小；`strict` 会在尺寸不一致时直接报错。

## 在 macOS 上启用
1. 把生成的 `.heic` 放到 `~/Pictures/Wallpapers/` 等文件夹。
2. 打开 **系统设置 → 桌面与屏幕保护程序 / 壁纸**。
3. 点 `+` 选中新建的文件，macOS 会按照时间表自动切换。

## 示例素材
`examples/` 目录里有四张占位图和上面的 `schedule.json`。可以替换图片或修改清单里的路径。

## 开发提示
- `pip install -e .[dev]` 可以额外装上 `black`、`ruff` 这些工具。
- 核心逻辑在 `dynamic_wallpaper/builder.py`，命令行入口在 `dynamic_wallpaper/cli.py`。
- 目前没有测试，如果要扩展项目，可以考虑加上打开 HEIC 校验 XMP 的集成测试。
