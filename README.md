# Summer Paradise — Blender CLI + GitHub Actions

A procedural, stylized 3D summer-island animation: turquoise sea, golden sand, palm trees, striped parasol, a beach ball, starfish, soft clouds, and moving camera.

## Render in GitHub Actions

Open **Actions → Render Summer Paradise → Run workflow** (or push to `main`). The workflow installs Blender and FFmpeg, renders a PNG image sequence with **Cycles on CPU**, encodes H.264 MP4, and uploads:

- `summer_paradise.mp4` — the finished video
- `preview.png` — a frame from the video
- `summer_paradise.blend` — the generated editable Blender project

Download the artifact named **summer-paradise-video** from the workflow run.

Defaults: **854 × 480**, **24 fps**, **96 frames (4 s)**. All visual assets are generated from Python; no external assets are required. A hosted GitHub Actions runner renders on CPU, so rendering may take a while.

## Local command-line render

```bash
mkdir -p output/frames
blender --background --factory-startup --threads 4 --python scripts/summer_paradise.py -- \
  --output-dir output/frames --width 854 --height 480 --fps 24 --frames 96 --samples 16
ffmpeg -y -framerate 24 -i output/frames/frame_%04d.png \
  -c:v libx264 -pix_fmt yuv420p -crf 20 -movflags +faststart output/summer_paradise.mp4
```

Change CLI arguments to trade rendering time for quality. The Blender script works with Cycles in Blender 3.6+ / 4.x and uses built-in meshes and materials.

## Files

- `scripts/summer_paradise.py`: scene building, camera and object animation, Blender CLI rendering.
- `.github/workflows/render-summer.yml`: GitHub Actions render and video upload.
- `README.md`: workflow and local instructions.

No music is included in the video; the MP4 is a silent visual loop.
