# 原创 Blender 后室 / 废弃医院 / 30 秒连续第一人称实景 CGI

**现在确实是 Blender 自建三维场景、三维材质、灯光和摄影机逐帧渲染，不是视频素材拼贴。**

[直接查看 GitHub Actions 工作流](https://github.com/h1collab/blender/actions/workflows/render-backrooms-hospital.yml)

## 场景
- 6×4 单元互通的废弃医院后室迷宫，由 3D 墙体、病房开口、医院门、医院护墙板、吊顶等构成
- 程序化墙壁裂纹、发霉/剥落、地砖污渍、吊顶老化、医院门牌
- 三维病床、轮椅、推车、散落的病历纸、闪烁的荧光灯和暗角
- 一台在空间内移动的第一人称摄影机：全程连续 30s，不切镜头
- 原创生成的 30 秒脚步、灯光电流和不安静的医院氛围声

完全不依赖图库素材、AI 图片、外部模型或外部视频。
画面是模拟真实摄影的原创 **CGI**，不宣称这是真实医院拍摄。

## GitHub Actions：真正逐帧 Blender 渲染

GitHub Actions 使用 8 个并行 CPU Runner 渲染 **同一 Blender 3D 动画**
的不同帧区间。它们之间没有拼接的素材边界，每个帧编号在统一的相机时间线
上。渲染完后再合并 PNG 序列，借助 OpenCV 去除 Cycles 低采样的 Monte-Carlo
噪点，通过 FFmpeg 编码为 30 秒 MP4。视频画面均来自 Blender 渲染，没有素材拼接。

工作流先执行单帧 Cycles 测试并生成 `backrooms-original-3d-scene`
（含原始 PNG 预览及可编辑 `.blend` 工程）。
随后使用 8 个 Runner 并行执行实际 Cycles 逐帧渲染，最后上传
`backrooms-original-3d-30s`，包含：
- `backrooms_hospital_3d_30s.mp4`（30 秒 H.264 + AAC）
- `backrooms_hospital_3d.blend`（可编辑完整原创 3D 项目）
- `preview.png`（去噪后的真实 Cycles 渲染帧）
- `ambience.wav`（原创程序生成环境音）

### 质量
| 设置 | 真正的 3D 渲染尺寸 | 帧率 | Blender 原始帧 | Cycles 采样 |
|---|---|---|---|---|
| draft | 640 × 360 | 15 fps | 450 | 6 |
| standard（默认） | 960 × 540 | 18 fps | 540 | 12 |
| high | 1280 × 720 | 24 fps | 720 | 18 |

选择更高画质需要更多 CPU / GitHub Actions 资源；
即使并行渲染，也可能耗时较长。每个画质都是真正的 **30 秒 Blender 3D** 动画。

### Blender 命令行本地渲染
```bash
blender --background --factory-startup --python scripts/backrooms_3d.py -- \
  --output-dir output/backrooms --width 960 --height 540 \
  --fps 18 --frames 540 --samples 12
python3 scripts/hospital_audio.py --output output/backrooms/ambience.wav --seconds 30
python3 scripts/denoise_frames.py --input output/backrooms/frames --output output/backrooms/clean
ffmpeg -y -framerate 18 -start_number 1 -i output/backrooms/clean/frame_%04d.png \
  -i output/backrooms/ambience.wav \
  -c:v libx264 -pix_fmt yuv420p -c:a aac -t 30 \
  output/backrooms/backrooms_hospital_3d_30s.mp4
```

源码：`scripts/backrooms_3d.py`。
夏日项目保持不变。
