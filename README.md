# Landscape Pen/Pencil Drawing Analyzer & Renderer

输入一张风景图片，程序会用可解释的 Python 图像分析流程估计亮度、对比度、边缘密度、纹理复杂度、主体、前景/中景/远景和语义区域，然后把画面转换为黑白钢笔画或铅笔素描。钢笔画由轮廓线、建筑结构线、排线、短线和水面波纹组成；铅笔画由方向性笔触图、色调图和程序化纸纹/铅笔纹理合成。

默认模式是 `pure`，只依赖 OpenCV、NumPy、Pillow、PyYAML 和 svgwrite，不调用外部 AI 生图 API。

## 安装

```bash
cd /Users/aibao/Documents/Project/AI-Art/Code/landscape_pen_drawing
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 运行

```bash
python main.py \
  --input ../../pics/01.jpeg \
  --output outputs/01_pen \
  --mode pure \
  --effect pen \
  --paper A4 \
  --detail 0.75 \
  --stroke-density 0.8 \
  --building-style learned_reference \
  --style-dir ../../pics/style \
  --structure-line-type sketch \
  --facade-line-type straight \
  --entourage-line-type loose_curve
```

铅笔画示例：

```bash
python main.py \
  --input ../../pics/01.jpeg \
  --output outputs/01_pencil \
  --mode pure \
  --effect pencil \
  --pencil-directions 8 \
  --pencil-stroke-darkness 1.65 \
  --pencil-tone-darkness 1.25 \
  --pencil-texture-strength 0.42
```

## 桌面 App

```bash
npm install
npm run desktop
```

桌面界面支持：

- 选择图片目录并列出 JPG、PNG、WebP、BMP、TIFF 图片。
- 查看原图和最近生成的钢笔画/铅笔画预览。
- 单张生成或批量生成。
- 通过模板快速设置风格：平衡钢笔稿、建筑细节强化、植物速写概括、极简留白、浓密交叉排线、水面与远景、铅笔素描、深色铅笔阴影、轻描淡写铅笔。
- 通过建筑样式模板快速设置：参考图学习、建筑延长线、现代立面网格、历史建筑竖向速写、浓密建筑阴影、周边留白。
- 通过滑杆、输入框、下拉菜单和复选框调节图像尺寸、纸色、转换效果、细节等级、笔触密度、轮廓强度、排线强度、纹理强度、天空抑制、远景简化、主体强化、排线间距、暗部阈值、建筑排线角度、线宽、抖动、透明度、随机种子、铅笔方向数、铅笔笔触深度、铅笔阴影深度、纸面颗粒、纹理尺度、色调分组和 SVG 页面选项。

输出目录包含：

- `analysis.json`：图像指标、内容估计和绘画策略。
- `analysis_report.md`：自然语言分析报告。
- `debug/`：灰度图、对比度图、边缘图、显著性图；钢笔模式会额外输出区域图、主体 mask、语义 mask、排线密度图；铅笔模式会额外输出笔触图、色调图、纹理图和合成图。
- `pen_drawing.png`：最终钢笔画；铅笔模式下也会写入同名兼容预览图。
- `pencil_drawing.png`：铅笔模式下的最终铅笔画。
- `pen_drawing.svg`：钢笔模式下按图层分组的 SVG polyline 路径。
- `strokes.json`：钢笔模式下记录每条笔触；铅笔模式下记录效果类型和铅笔参数。
- `region_preview.png`：钢笔模式下的语义分区预览。

## 算法流程

1. 图像预处理：限制最大边、去噪、灰度转换和局部对比度分析。
2. 状态分析：计算亮度、RMS 对比度、Michelson 对比度、动态范围、暗部/中间调/高光比例、Laplacian 清晰度、边缘密度、纹理复杂度、饱和度和色彩丰富度。
3. 语义区域估计：用 HSV 颜色规则、边缘密度、纹理、Hough 直线和位置先验估计天空、植物、水面、建筑、道路、人物候选、山体/远景和地面。
4. 主体估计：融合显著性、局部对比度、边缘能量、中心权重和语义权重，输出 `subject_mask`。
5. 风格规划：主体和建筑增强轮廓；植物减少碎边，用短曲线概括；天空抑制线条；水面使用水平短线；远景降低线条密度。
6. 线条生成：Canny/xDoG 多尺度边缘转换为 polyline stroke，建筑额外使用 HoughLinesP 生成结构线。
7. 明暗排线：根据亮度生成 `hatch_density_map`，在 mask 内裁切平行排线，深暗区域叠加 cross-hatch。
8. 钢笔渲染导出：用微暖纸色背景和深色钢笔线渲染 PNG，同时导出适合绘图机后处理的 SVG 和 `strokes.json`。
9. 铅笔渲染导出：将灰度图平滑后提取梯度，按多个方向的线核生成笔触图；将亮度直方图映射到铅笔明暗色调图；叠加程序化方向纹理和纸面颗粒，输出 `pencil_drawing.png` 及调试图。

## 调参

主要参数位于 `config.yaml`：

- `image.max_size`：处理最大边长。
- `drawing.detail_level`：轮廓和细节保留强度。
- `drawing.stroke_density`：排线和纹理笔触密度。
- `hatching.min_spacing_px` / `hatching.max_spacing_px`：排线间距范围。
- `stroke.jitter_px`：手绘抖动强度。
- `stroke.building_jitter_px`：建筑结构线抖动强度。
- `architectural_style.preset`：建筑风格模板，支持 `learned_reference`、`architectural_extended_line`、`modern_facade_grid`、`historic_vertical_sketch`、`dense_architectural_shadow`、`light_entourage_blank`。
- `architectural_style.style_reference_dir`：参考钢笔画目录，默认读取 `../../pics/style` 并分析线条方向、墨色密度和结构线长度。
- `architectural_style.line_extend_px`：建筑结构线端点外伸长度。
- `architectural_style.facade_hatch_spacing_px`：建筑立面直线排线间距。
- `architectural_style.structure_line_type`：建筑结构线线型，支持 `straight`、`slight_curve`、`loose_curve`、`sketch`、`broken`、`broken_curve`。
- `architectural_style.facade_hatch_line_type`：建筑立面排线线型。
- `architectural_style.entourage_line_type`：周边景物线型，用于曲线、省略和留白。
- `effect.type`：转换效果，支持 `pen` 和 `pencil`。
- `pencil.auto_kernel`：是否按图片尺寸自动计算方向笔触核大小。
- `pencil.kernel_size` / `pencil.kernel_scale`：手动核大小或自动核比例。
- `pencil.stroke_width`：方向线核宽度，影响铅笔线束的实度。
- `pencil.num_directions`：铅笔笔触方向数，越多越细腻，越少越有明确排线方向。
- `pencil.smooth_kernel`：铅笔预平滑方式，支持 `gauss`、`median`、`bilateral`。
- `pencil.gradient_method`：轮廓和笔触响应梯度，支持 `forward`、`sobel`、`scharr`。
- `pencil.tone_group` / `pencil.tone_smoothing`：铅笔明暗分布模板和明暗平滑强度。
- `pencil.stroke_darkness` / `pencil.tone_darkness`：线条深度和阴影深度。
- `pencil.texture_strength` / `pencil.grain_scale` / `pencil.paper_grain`：铅笔纹理、纹理尺度和纸面颗粒。
- `pencil.contrast` / `pencil.gamma`：最终明暗对比和伽马。
- `pencil.preserve_color`：是否把铅笔明暗应用回原图色彩。

CLI 参数会覆盖配置文件。

## 测试

```bash
pytest -q
```
