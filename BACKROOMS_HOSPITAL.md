# BACKROOMS — Original Blender 3D / Abandoned Hospital / First-person POV (30 s)

**这次是真正的 Blender 三维场景与逐帧渲染，不是实拍素材拼接。**

[GitHub Actions：Render Original 3D Backrooms (30s POV)](https://github.com/h1collab/blender/actions/workflows/render-backrooms-hospital.yml)

## 原创内容与场景

- 所有建筑均用 `bpy` 生成：6×4 相互连通的迷宫式医院病房与走廊。
- Cycles 路径追踪渲染；真实阴影和灯光。程序化 PBR：旧墙纸、破损塑料地板、
  水渍吊顶、医院护墙板、楼道防护扶手、刷旧金属。
- 三维病床、轮椅、药品手推车、医疗看板、病房门、荧光灯灯箱。
- **一台第一人称摄像机，沿连续曲线探索整整 30 秒；没有剪辑点和跳切。**
- 物理灯光不规律闪烁、轻微步行头部晃动和自然动态视角。
- 原创脚本合成的空调低频电流、脚步与遥远金属声（没有下载音视频）。
- **没有 stock 视频、在线模型、预渲染图片、AI 图像/纹理**。全部图像像素由
  Blender 的 mesh / shaders / lights / camera 自行产生。

这是原创写实风格 CGI，不是真实废弃医院的摄影纪录。

## 渲染并下载 MP4

进入 [Actions](https://github.com/h1collab/blender/actions)，选择
**Render Original 3D Backrooms (30s POV)** → **Run workflow**。
完成后下载 `backrooms-original-3d-30s` artifact：
- `backrooms_hospital_3d_30s.mp4`：30 秒原创 3D 后室视频 + 环境声
- `backrooms_hospital_3d.blend`：完整可编辑 3D 场景与第一人称镜头路径
- `preview.png`：直接从 Cycles 渲染出的实际截图
- `ambience.wav`：原创合成氛围声

工作流先进行单帧 Cycles 测试，上传 `backrooms-real-blender-preview`
作为确凿的 Blender 渲染证据，然后渲染所有动画帧并用 FFmpeg
**编码这些 Blender 渲染 PNG** 为 MP4；FFmpeg 只负责视频编码和轻度降噪，
**不产生任何场景画面**。

| quality | 源渲染分辨率 | 帧率 | 真实 Blender 帧数 | Cycles Samples |
|---|---|---|---|---|
| draft | 640×360 | 15 fps | 450 | 4 |
| standard（默认） | 960×540 | 18 fps | 540 | 7 |
| high | 1280×720 | 24 fps | 720 | 12 |

均为**完整 30 秒**。在 GitHub Actions CPU 环境下，高画质很耗时间；可自行改
源码提高采样或使用本地 GPU 渲染。工作流的默认模式兼顾真实画面和 CI 成本。

## 自己使用 Blender 命令行

```bash
mkdir -p output/backrooms/frames
blender -b --factory-startup --threads 4 --python scripts/backrooms_3d.py -- \
  --output-dir output/backrooms --width 960 --height 540 \
  --fps 18 --frames 540 --samples 7
python3 scripts/hospital_audio.py --output output/backrooms/ambience.wav --seconds 30
ffmpeg -y -framerate 18 -start_number 1 -i output/backrooms/frames/frame_%04d.png \
  -i output/backrooms/ambience.wav -map 0:v:0 -map 1:a:0 \
  -c:v libx264 -pix_fmt yuv420p -c:a aac -t 30 \
  output/backrooms/backrooms_hospital_3d_30s.mp4
```

Source: [scripts/backrooms_3d.py](scripts/backrooms_3d.py).
The previous stock-footage hospital script and material-source list were deleted.
The unrelated summer project remains unchanged.
