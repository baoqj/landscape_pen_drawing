# Landscape Pen Drawing Analyzer & Renderer

输入一张风景图片，程序会用可解释的 Python 图像分析流程估计亮度、对比度、边缘密度、纹理复杂度、主体、前景/中景/远景和语义区域，然后把画面转换为由轮廓线、结构线、排线、短线和水面波纹组成的黑白钢笔画。

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
  --paper A4 \
  --detail 0.75 \
  --stroke-density 0.8 \
  --building-style learned_reference \
  --style-dir ../../pics/style
```

## 桌面 App

```bash
npm install
npm run desktop
```

桌面界面支持：

- 选择图片目录并列出 JPG、PNG、WebP、BMP、TIFF 图片。
- 查看原图和最近生成的钢笔画预览。
- 单张生成或批量生成。
- 通过模板快速设置风格：平衡钢笔稿、建筑细节强化、植物速写概括、极简留白、浓密交叉排线、水面与远景。
- 通过建筑样式模板快速设置：参考图学习、建筑延长线、现代立面网格、历史建筑竖向速写、浓密建筑阴影、周边留白。
- 通过滑杆、输入框、下拉菜单和复选框调节图像尺寸、纸色、细节等级、笔触密度、轮廓强度、排线强度、纹理强度、天空抑制、远景简化、主体强化、排线间距、暗部阈值、建筑排线角度、线宽、抖动、透明度、随机种子和 SVG 页面选项。

输出目录包含：

- `analysis.json`：图像指标、内容估计和绘画策略。
- `analysis_report.md`：自然语言分析报告。
- `debug/`：灰度图、对比度图、边缘图、显著性图、区域图、主体 mask、语义 mask、排线密度图。
- `pen_drawing.png`：最终钢笔画。
- `pen_drawing.svg`：按图层分组的 SVG polyline 路径。
- `strokes.json`：每条笔触的层、语义区域、点序列、宽度、透明度和绘制顺序。
- `region_preview.png`：语义分区预览。

## 算法流程

1. 图像预处理：限制最大边、去噪、灰度转换和局部对比度分析。
2. 状态分析：计算亮度、RMS 对比度、Michelson 对比度、动态范围、暗部/中间调/高光比例、Laplacian 清晰度、边缘密度、纹理复杂度、饱和度和色彩丰富度。
3. 语义区域估计：用 HSV 颜色规则、边缘密度、纹理、Hough 直线和位置先验估计天空、植物、水面、建筑、道路、人物候选、山体/远景和地面。
4. 主体估计：融合显著性、局部对比度、边缘能量、中心权重和语义权重，输出 `subject_mask`。
5. 风格规划：主体和建筑增强轮廓；植物减少碎边，用短曲线概括；天空抑制线条；水面使用水平短线；远景降低线条密度。
6. 线条生成：Canny/xDoG 多尺度边缘转换为 polyline stroke，建筑额外使用 HoughLinesP 生成结构线。
7. 明暗排线：根据亮度生成 `hatch_density_map`，在 mask 内裁切平行排线，深暗区域叠加 cross-hatch。
8. 渲染导出：用微暖纸色背景和深色钢笔线渲染 PNG，同时导出适合绘图机后处理的 SVG 和 `strokes.json`。

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

CLI 参数会覆盖配置文件。

## 测试

```bash
pytest -q
```
