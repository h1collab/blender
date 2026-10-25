# 真实夏日海滩视频 / Real Summer Film

**新版：真实摄影素材、电影感剪辑，而不是卡通 Blender 3D 动画。**

这个项目通过 **Blender 命令行（Video Sequence Editor）** 将真实摄影的
热带海滩、浪花和椰树镜头合成为写实风格的夏日短片，GitHub Actions
自动生成 **1920×1080 / 25fps / H.264 MP4**。没有玩具模型、三维卡通小岛或
漂浮文字。为了保证真实性，画面来自实拍素材，而非声称纯 3D 做到照片级。

## 一键生成 / GitHub Actions

1. 打开 [Actions → Render Real Summer Film](https://github.com/h1collab/blender/actions/workflows/render-summer.yml)。
2. 点击 **Run workflow**，画质选 **1080p**（或快一点的 720p）。
3. 运行成功后，在底部 **Artifacts → real-summer-1080p-video** 下载。
4. 解压获得：
   - `summer_real.mp4` — 真实海滩镜头构成的成片，约 11.2 秒
   - `preview.jpg` — 真人摄影视频中的预览帧
   - `summer_real_edit.blend` — Blender VSE 可编辑剪辑工程
   - `credits.json` — 实际使用的摄影师与原素材链接

每次修改视频脚本、工作流或素材列表并 push 到 main，也会自动渲染。
默认素材下载自 Pexels，仅在构建时缓存；不将原始素材上传到仓库。

## 素材版权和真实性

- [Pexels License](https://www.pexels.com/license/)：素材允许免费编辑使用。
- 摄影师及原素材完整链接见 [sources.json](sources.json)。
- 这段视频**不是 Blender 程序生成的真实感 CGI，而是真实拍摄的视频合成**。
- 不添加 AI 生成的人物/椰树、水体动画，也不加合成画面来冒充真实摄影。
- 无音乐，以便自行配音或选择有明确许可的音乐。

## 在本地用 Blender 命令行

需要系统装好 `blender`、`ffmpeg`、`curl` 和 Python 3。

```bash
python3 scripts/get_footage.py --source-list sources.json --output-dir output/source \
  --width 1920 --height 1080 --fps 25 --seconds 4 --max-clips 3

blender -b --factory-startup --python scripts/real_summer.py -- \
  --shots-dir output/source --output output/summer_real.mp4 \
  --width 1920 --height 1080 --fps 25 --shot-seconds 4 --fade-frames 10
```

The edit uses genuine filmed shots, a restrained grade, and short dissolves.
Video rendering is done by Blender's command-line Video Sequence Editor (VSE).

旧版卡通脚本已移除，默认工作流只会输出真实摄影风格视频。
