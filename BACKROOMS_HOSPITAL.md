# The Backrooms: Abandoned Hospital — 30s POV Exploration

**30 秒第一人称、实拍写实、废弃医院探索氛围。**

新建的独立 GitHub Action：
[Render Backrooms Hospital POV (30s)](https://github.com/h1collab/blender/actions/workflows/render-backrooms-hospital.yml)

## 效果

- 0–9s：破败的真实废弃疗养院 / 医院内部
- 9–16s：逐步进入长走廊，轻微第一人称头部晃动
- 16–21s：空荡的医院护士站 / 医疗走廊
- 21–30s：阴暗走廊的第一人称深入探索
- 冷绿灰色调、轻微暗角和真实摄影的纹理；没有游戏 HUD、卡通角色或 AI 合成场景
- 原创合成环境音：低频通风/荧光灯嗡鸣、脚步、远处金属声

**真实性说明**：这是由多个真实地点的摄影素材剪辑而成的虚构
“废弃医院探索”短片；*不是在同一座废弃医院连续拍摄的纪录片*。
其中部分镜头来自废弃疗养院，另一些来自真实医院或长廊，
均不被误称为拍摄于同一医院。我们使用 **Blender VSE 做真实视频剪辑**，
而非通过 3D 建模生成“拟真医院”。

## 如何获取 MP4

1. 进入上方工作流，点击 **Run workflow**，选择 **1080p**（默认）或 **720p**。
2. 完成后在运行详情下方的 **Artifacts** 下载 `backrooms-hospital-pov-30s`。
3. 压缩包包含 `backrooms_hospital_30s.mp4`（30s / H.264 / AAC）、
   `preview.jpg`、`backrooms_hospital_edit.blend`、原创音效 WAV、
   `sources_used.json` 和全部用于编辑的标准化实拍镜头。

修改脚本和工作流推送到 main 也会自动生成新的视频。旧夏日视频工作流保留，互不干扰。

## 技术路线

```bash
sudo apt-get install blender ffmpeg curl
python3 scripts/prepare_hospital.py --spec hospital_sources.json --output-dir output/backrooms --width 1920 --height 1080
python3 scripts/hospital_audio.py --seconds 30 --output output/backrooms/ambience.wav
blender -b --factory-startup --threads 4 --python scripts/backrooms_hospital.py -- \
  --manifest output/backrooms/sources_used.json --audio output/backrooms/ambience.wav --output-dir output/backrooms
ffmpeg -y -i output/backrooms/backrooms_silent.mp4 -i output/backrooms/ambience.wav \
  -map 0:v:0 -map 1:a:0 -c:v copy -c:a aac -b:a 160k -t 30 \
  -movflags +faststart output/backrooms/backrooms_hospital_30s.mp4
```

场景素材：见 [hospital_sources.json](hospital_sources.json)；运行时精确的使用记录见
`sources_used.json`。素材许可：[Pexels License](https://www.pexels.com/license/)：
允许免费使用和编辑。仍应保留来源以便追溯。没有第三方音乐。

## 文件
- `hospital_sources.json`：镜头规划、拍摄来源和备用来源。
- `scripts/prepare_hospital.py`：下载 / 校验实拍素材，自动标准化及电影色调。
- `scripts/hospital_audio.py`：生成 30 秒原创氛围声。
- `scripts/backrooms_hospital.py`：Blender CLI 剪辑、保存工程并渲染。
- `.github/workflows/render-backrooms-hospital.yml`：Actions 自动化工作流。

夏日视频内容和工作流保持不变。
