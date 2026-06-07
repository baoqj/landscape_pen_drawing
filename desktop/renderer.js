const DEFAULT_CONFIG = {
  image: {
    max_size: 1600,
    paper_color: [248, 245, 238],
  },
  analysis: {
    use_clahe: true,
    saliency_weight: 0.35,
    edge_weight: 0.25,
    center_weight: 0.2,
    contrast_weight: 0.2,
  },
  drawing: {
    detail_level: 0.75,
    stroke_density: 0.8,
    contour_strength: 1.0,
    hatch_strength: 0.85,
    texture_strength: 0.65,
    sky_suppression: 0.9,
    background_simplification: 0.7,
    subject_boost: 1.3,
  },
  hatching: {
    min_spacing_px: 4,
    max_spacing_px: 22,
    dark_threshold: 0.35,
    mid_threshold: 0.65,
    building_angle_deg: 45,
    cross_hatch_dark_regions: true,
  },
  stroke: {
    base_width_px: 1.1,
    width_variation: 0.25,
    jitter_px: 0.7,
    building_jitter_px: 0.25,
    vegetation_jitter_px: 1.4,
    opacity_min: 0.45,
    opacity_max: 0.95,
    random_seed: 42,
  },
  architectural_style: {
    preset: "learned_reference",
    learn_from_reference: true,
    style_reference_dir: "../../pics/style",
    structure_boost: 1.25,
    entourage_edge_keep: 0.46,
    line_extend_px: 12,
    corner_tick_px: 9,
    rectilinear_angle_tolerance: 18,
    facade_hatch_spacing_px: 16,
    facade_hatch_angle_deg: 45,
    facade_hatch_opacity: 0.38,
    structure_line_width: 1.08,
    structure_line_opacity: 0.9,
    draw_corner_extensions: true,
    draw_mass_boxes: true,
    draw_facade_hatching: true,
    max_structure_lines: 360,
    max_facade_hatch_lines: 900,
    vegetation_looseness: 1.25,
  },
  svg: {
    export: true,
    simplify_tolerance: 1.2,
    group_by_layer: true,
    scale_to_mm: true,
    page_size: "A4",
  },
};

const PRESETS = {
  "平衡钢笔稿": {
    "image.max_size": 1400,
    "drawing.detail_level": 0.72,
    "drawing.stroke_density": 0.78,
    "drawing.contour_strength": 1.0,
    "drawing.hatch_strength": 0.85,
    "drawing.texture_strength": 0.62,
    "drawing.sky_suppression": 0.9,
    "drawing.background_simplification": 0.7,
    "drawing.subject_boost": 1.25,
    "hatching.min_spacing_px": 5,
    "hatching.max_spacing_px": 24,
    "hatching.building_angle_deg": 45,
    "hatching.cross_hatch_dark_regions": true,
    "stroke.base_width_px": 1.05,
    "stroke.jitter_px": 0.7,
    "stroke.building_jitter_px": 0.24,
    "stroke.vegetation_jitter_px": 1.35,
    "svg.simplify_tolerance": 1.2,
    "architectural_style.preset": "learned_reference",
    "architectural_style.learn_from_reference": true,
    "architectural_style.entourage_edge_keep": 0.46,
  },
  "建筑细节强化": {
    "image.max_size": 1600,
    "drawing.detail_level": 0.92,
    "drawing.stroke_density": 0.9,
    "drawing.contour_strength": 1.25,
    "drawing.hatch_strength": 1.0,
    "drawing.texture_strength": 0.42,
    "drawing.sky_suppression": 0.94,
    "drawing.background_simplification": 0.64,
    "drawing.subject_boost": 1.45,
    "hatching.min_spacing_px": 4,
    "hatching.max_spacing_px": 20,
    "hatching.building_angle_deg": 45,
    "hatching.cross_hatch_dark_regions": true,
    "stroke.base_width_px": 1.0,
    "stroke.jitter_px": 0.48,
    "stroke.building_jitter_px": 0.16,
    "stroke.vegetation_jitter_px": 1.05,
    "svg.simplify_tolerance": 0.9,
    "architectural_style.preset": "architectural_extended_line",
    "architectural_style.learn_from_reference": true,
    "architectural_style.line_extend_px": 18,
    "architectural_style.entourage_edge_keep": 0.36,
  },
  "植物速写概括": {
    "image.max_size": 1400,
    "drawing.detail_level": 0.62,
    "drawing.stroke_density": 0.86,
    "drawing.contour_strength": 0.85,
    "drawing.hatch_strength": 0.68,
    "drawing.texture_strength": 1.05,
    "drawing.sky_suppression": 0.9,
    "drawing.background_simplification": 0.72,
    "drawing.subject_boost": 1.15,
    "hatching.min_spacing_px": 6,
    "hatching.max_spacing_px": 28,
    "hatching.building_angle_deg": 38,
    "hatching.cross_hatch_dark_regions": false,
    "stroke.base_width_px": 1.08,
    "stroke.jitter_px": 1.0,
    "stroke.building_jitter_px": 0.28,
    "stroke.vegetation_jitter_px": 1.9,
    "svg.simplify_tolerance": 1.8,
    "architectural_style.preset": "light_entourage_blank",
    "architectural_style.entourage_edge_keep": 0.28,
    "architectural_style.vegetation_looseness": 1.8,
  },
  "极简留白": {
    "image.max_size": 1200,
    "drawing.detail_level": 0.42,
    "drawing.stroke_density": 0.46,
    "drawing.contour_strength": 0.72,
    "drawing.hatch_strength": 0.38,
    "drawing.texture_strength": 0.25,
    "drawing.sky_suppression": 0.98,
    "drawing.background_simplification": 0.88,
    "drawing.subject_boost": 1.1,
    "hatching.min_spacing_px": 10,
    "hatching.max_spacing_px": 36,
    "hatching.building_angle_deg": 35,
    "hatching.cross_hatch_dark_regions": false,
    "stroke.base_width_px": 0.95,
    "stroke.jitter_px": 0.55,
    "stroke.building_jitter_px": 0.18,
    "stroke.vegetation_jitter_px": 1.1,
    "svg.simplify_tolerance": 2.3,
    "architectural_style.preset": "light_entourage_blank",
    "architectural_style.entourage_edge_keep": 0.22,
    "architectural_style.draw_facade_hatching": false,
  },
  "浓密交叉排线": {
    "image.max_size": 1500,
    "drawing.detail_level": 0.82,
    "drawing.stroke_density": 1.15,
    "drawing.contour_strength": 1.1,
    "drawing.hatch_strength": 1.25,
    "drawing.texture_strength": 0.72,
    "drawing.sky_suppression": 0.82,
    "drawing.background_simplification": 0.58,
    "drawing.subject_boost": 1.36,
    "hatching.min_spacing_px": 3,
    "hatching.max_spacing_px": 18,
    "hatching.building_angle_deg": 50,
    "hatching.cross_hatch_dark_regions": true,
    "stroke.base_width_px": 0.9,
    "stroke.jitter_px": 0.62,
    "stroke.building_jitter_px": 0.22,
    "stroke.vegetation_jitter_px": 1.35,
    "svg.simplify_tolerance": 1.0,
    "architectural_style.preset": "dense_architectural_shadow",
    "architectural_style.facade_hatch_spacing_px": 9,
    "architectural_style.entourage_edge_keep": 0.3,
  },
  "水面与远景": {
    "image.max_size": 1400,
    "drawing.detail_level": 0.58,
    "drawing.stroke_density": 0.62,
    "drawing.contour_strength": 0.82,
    "drawing.hatch_strength": 0.52,
    "drawing.texture_strength": 0.7,
    "drawing.sky_suppression": 0.96,
    "drawing.background_simplification": 0.84,
    "drawing.subject_boost": 1.18,
    "hatching.min_spacing_px": 8,
    "hatching.max_spacing_px": 30,
    "hatching.building_angle_deg": 32,
    "hatching.cross_hatch_dark_regions": false,
    "stroke.base_width_px": 0.96,
    "stroke.jitter_px": 0.5,
    "stroke.building_jitter_px": 0.18,
    "stroke.vegetation_jitter_px": 1.05,
    "svg.simplify_tolerance": 1.7,
    "architectural_style.preset": "light_entourage_blank",
    "architectural_style.entourage_edge_keep": 0.26,
  },
  "建筑延长线手绘": {
    "image.max_size": 1600,
    "drawing.detail_level": 0.82,
    "drawing.stroke_density": 0.82,
    "drawing.contour_strength": 1.2,
    "drawing.hatch_strength": 0.86,
    "drawing.texture_strength": 0.48,
    "drawing.sky_suppression": 0.96,
    "drawing.background_simplification": 0.8,
    "drawing.subject_boost": 1.48,
    "hatching.min_spacing_px": 5,
    "hatching.max_spacing_px": 24,
    "hatching.cross_hatch_dark_regions": true,
    "stroke.base_width_px": 1.02,
    "stroke.jitter_px": 0.48,
    "stroke.building_jitter_px": 0.14,
    "stroke.vegetation_jitter_px": 1.65,
    "architectural_style.preset": "architectural_extended_line",
    "architectural_style.learn_from_reference": true,
    "architectural_style.line_extend_px": 20,
    "architectural_style.corner_tick_px": 14,
    "architectural_style.facade_hatch_spacing_px": 18,
    "architectural_style.entourage_edge_keep": 0.32,
  },
  "现代立面网格": {
    "image.max_size": 1600,
    "drawing.detail_level": 0.88,
    "drawing.stroke_density": 0.76,
    "drawing.contour_strength": 1.28,
    "drawing.hatch_strength": 0.72,
    "drawing.texture_strength": 0.36,
    "drawing.sky_suppression": 0.97,
    "drawing.background_simplification": 0.82,
    "drawing.subject_boost": 1.42,
    "hatching.min_spacing_px": 6,
    "hatching.max_spacing_px": 28,
    "hatching.cross_hatch_dark_regions": false,
    "stroke.base_width_px": 0.98,
    "stroke.jitter_px": 0.36,
    "stroke.building_jitter_px": 0.1,
    "stroke.vegetation_jitter_px": 1.45,
    "architectural_style.preset": "modern_facade_grid",
    "architectural_style.learn_from_reference": false,
    "architectural_style.line_extend_px": 10,
    "architectural_style.facade_hatch_angle_deg": 0,
    "architectural_style.facade_hatch_spacing_px": 20,
    "architectural_style.entourage_edge_keep": 0.3,
  },
  "历史建筑竖向速写": {
    "image.max_size": 1700,
    "drawing.detail_level": 0.94,
    "drawing.stroke_density": 0.92,
    "drawing.contour_strength": 1.24,
    "drawing.hatch_strength": 0.98,
    "drawing.texture_strength": 0.5,
    "drawing.sky_suppression": 0.94,
    "drawing.background_simplification": 0.72,
    "drawing.subject_boost": 1.55,
    "hatching.min_spacing_px": 4,
    "hatching.max_spacing_px": 22,
    "hatching.cross_hatch_dark_regions": true,
    "stroke.base_width_px": 0.96,
    "stroke.jitter_px": 0.42,
    "stroke.building_jitter_px": 0.12,
    "stroke.vegetation_jitter_px": 1.25,
    "architectural_style.preset": "historic_vertical_sketch",
    "architectural_style.learn_from_reference": true,
    "architectural_style.facade_hatch_angle_deg": 82,
    "architectural_style.facade_hatch_spacing_px": 12,
    "architectural_style.entourage_edge_keep": 0.4,
  },
  "建筑浓密阴影": {
    "image.max_size": 1500,
    "drawing.detail_level": 0.78,
    "drawing.stroke_density": 1.16,
    "drawing.contour_strength": 1.08,
    "drawing.hatch_strength": 1.32,
    "drawing.texture_strength": 0.62,
    "drawing.sky_suppression": 0.9,
    "drawing.background_simplification": 0.7,
    "drawing.subject_boost": 1.32,
    "hatching.min_spacing_px": 3,
    "hatching.max_spacing_px": 18,
    "hatching.cross_hatch_dark_regions": true,
    "stroke.base_width_px": 0.86,
    "stroke.jitter_px": 0.55,
    "stroke.building_jitter_px": 0.18,
    "stroke.vegetation_jitter_px": 1.2,
    "architectural_style.preset": "dense_architectural_shadow",
    "architectural_style.learn_from_reference": true,
    "architectural_style.facade_hatch_spacing_px": 8,
    "architectural_style.facade_hatch_opacity": 0.52,
    "architectural_style.entourage_edge_keep": 0.28,
  },
};

const PARAM_GROUPS = [
  {
    name: "图像",
    params: [
      { path: "image.max_size", label: "最大边长", type: "int", min: 600, max: 2200, step: 50 },
      { path: "image.paper_color.0", label: "纸色 R", type: "int", min: 225, max: 255, step: 1 },
      { path: "image.paper_color.1", label: "纸色 G", type: "int", min: 225, max: 255, step: 1 },
      { path: "image.paper_color.2", label: "纸色 B", type: "int", min: 215, max: 255, step: 1 },
    ],
  },
  {
    name: "绘制",
    params: [
      { path: "drawing.detail_level", label: "细节等级", type: "float", min: 0.1, max: 1.3, step: 0.01 },
      { path: "drawing.stroke_density", label: "笔触密度", type: "float", min: 0.1, max: 1.4, step: 0.01 },
      { path: "drawing.contour_strength", label: "轮廓强度", type: "float", min: 0.2, max: 1.8, step: 0.01 },
      { path: "drawing.hatch_strength", label: "排线强度", type: "float", min: 0.1, max: 1.6, step: 0.01 },
      { path: "drawing.texture_strength", label: "纹理强度", type: "float", min: 0.1, max: 1.5, step: 0.01 },
      { path: "drawing.sky_suppression", label: "天空抑制", type: "float", min: 0, max: 1, step: 0.01 },
      { path: "drawing.background_simplification", label: "远景简化", type: "float", min: 0, max: 1, step: 0.01 },
      { path: "drawing.subject_boost", label: "主体强化", type: "float", min: 0.6, max: 2.0, step: 0.01 },
    ],
  },
  {
    name: "排线",
    params: [
      { path: "hatching.min_spacing_px", label: "最小线距", type: "int", min: 2, max: 18, step: 1 },
      { path: "hatching.max_spacing_px", label: "最大线距", type: "int", min: 10, max: 48, step: 1 },
      { path: "hatching.dark_threshold", label: "暗部阈值", type: "float", min: 0.1, max: 0.7, step: 0.01 },
      { path: "hatching.mid_threshold", label: "中间调阈值", type: "float", min: 0.3, max: 0.9, step: 0.01 },
      { path: "hatching.building_angle_deg", label: "建筑排线角度", type: "float", min: -80, max: 80, step: 1 },
      { path: "hatching.cross_hatch_dark_regions", label: "深暗交叉排线", type: "bool" },
    ],
  },
  {
    name: "笔触",
    params: [
      { path: "stroke.base_width_px", label: "基础线宽", type: "float", min: 0.3, max: 2.6, step: 0.01 },
      { path: "stroke.width_variation", label: "线宽变化", type: "float", min: 0, max: 0.8, step: 0.01 },
      { path: "stroke.jitter_px", label: "手绘抖动", type: "float", min: 0, max: 2.5, step: 0.01 },
      { path: "stroke.building_jitter_px", label: "建筑抖动", type: "float", min: 0, max: 1.2, step: 0.01 },
      { path: "stroke.vegetation_jitter_px", label: "植物抖动", type: "float", min: 0, max: 3.2, step: 0.01 },
      { path: "stroke.opacity_min", label: "最小透明度", type: "float", min: 0.05, max: 1, step: 0.01 },
      { path: "stroke.opacity_max", label: "最大透明度", type: "float", min: 0.1, max: 1, step: 0.01 },
      { path: "stroke.random_seed", label: "随机种子", type: "entry-int" },
    ],
  },
  {
    name: "建筑样式",
    params: [
      { path: "architectural_style.preset", label: "建筑模板", type: "select", values: ["learned_reference", "architectural_extended_line", "modern_facade_grid", "historic_vertical_sketch", "dense_architectural_shadow", "light_entourage_blank"] },
      { path: "architectural_style.learn_from_reference", label: "学习参考图", type: "bool" },
      { path: "architectural_style.style_reference_dir", label: "参考目录", type: "entry-text" },
      { path: "architectural_style.structure_boost", label: "建筑结构强化", type: "float", min: 0.6, max: 2.0, step: 0.01 },
      { path: "architectural_style.entourage_edge_keep", label: "周边保留", type: "float", min: 0.05, max: 1.0, step: 0.01 },
      { path: "architectural_style.line_extend_px", label: "结构线外伸", type: "float", min: 0, max: 30, step: 0.5 },
      { path: "architectural_style.corner_tick_px", label: "边角短线", type: "float", min: 0, max: 24, step: 0.5 },
      { path: "architectural_style.facade_hatch_spacing_px", label: "立面线距", type: "int", min: 4, max: 36, step: 1 },
      { path: "architectural_style.facade_hatch_angle_deg", label: "立面角度", type: "float", min: -90, max: 90, step: 1 },
      { path: "architectural_style.facade_hatch_opacity", label: "立面透明度", type: "float", min: 0.05, max: 0.8, step: 0.01 },
      { path: "architectural_style.structure_line_width", label: "结构线宽", type: "float", min: 0.3, max: 2.4, step: 0.01 },
      { path: "architectural_style.structure_line_opacity", label: "结构透明度", type: "float", min: 0.1, max: 1.0, step: 0.01 },
      { path: "architectural_style.draw_corner_extensions", label: "绘制边角外伸", type: "bool" },
      { path: "architectural_style.draw_mass_boxes", label: "绘制体块边线", type: "bool" },
      { path: "architectural_style.draw_facade_hatching", label: "绘制立面排线", type: "bool" },
      { path: "architectural_style.vegetation_looseness", label: "景物自由度", type: "float", min: 0.6, max: 2.4, step: 0.01 },
    ],
  },
  {
    name: "SVG",
    params: [
      { path: "svg.export", label: "导出 SVG", type: "bool" },
      { path: "svg.simplify_tolerance", label: "路径简化", type: "float", min: 0.1, max: 4, step: 0.01 },
      { path: "svg.group_by_layer", label: "按图层分组", type: "bool" },
      { path: "svg.scale_to_mm", label: "按毫米页面", type: "bool" },
      { path: "svg.page_size", label: "纸张", type: "select", values: ["A4", "A3", "Letter"] },
    ],
  },
];

const state = {
  config: structuredClone(DEFAULT_CONFIG),
  images: [],
  selectedPaths: new Set(),
  currentImage: null,
  lastOutputDir: null,
  activeTab: PARAM_GROUPS[0].name,
  running: false,
};

const el = {};

document.addEventListener("DOMContentLoaded", init);

async function init() {
  cacheElements();
  buildPresetSelect();
  buildParamPanels();
  bindEvents();
  bindRenderEvents();

  const defaults = await window.studio.defaults();
  el.inputDir.value = defaults.inputDir;
  el.outputDir.value = defaults.outputDir;
  applyPreset("平衡钢笔稿");
  await refreshImages();
}

function cacheElements() {
  for (const id of [
    "inputDir",
    "outputDir",
    "chooseInput",
    "chooseOutput",
    "recursive",
    "refresh",
    "mode",
    "outputSuffix",
    "imageTable",
    "renderSelected",
    "renderAll",
    "originalPreview",
    "outputPreview",
    "openOutput",
    "presetSelect",
    "applyPreset",
    "tabs",
    "paramPanels",
    "resetConfig",
    "cancelRender",
    "status",
    "progress",
    "log",
  ]) {
    el[id] = document.getElementById(id);
  }
}

function bindEvents() {
  el.chooseInput.addEventListener("click", async () => {
    const selected = await window.studio.chooseDirectory(el.inputDir.value);
    if (selected) {
      el.inputDir.value = selected;
      refreshImages();
    }
  });
  el.chooseOutput.addEventListener("click", async () => {
    const selected = await window.studio.chooseDirectory(el.outputDir.value);
    if (selected) {
      el.outputDir.value = selected;
    }
  });
  el.refresh.addEventListener("click", refreshImages);
  el.recursive.addEventListener("change", refreshImages);
  el.applyPreset.addEventListener("click", () => applyPreset(el.presetSelect.value));
  el.resetConfig.addEventListener("click", () => {
    state.config = structuredClone(DEFAULT_CONFIG);
    syncControlsFromConfig();
    setStatus("Config restored");
  });
  el.renderSelected.addEventListener("click", renderSelected);
  el.renderAll.addEventListener("click", renderAll);
  el.cancelRender.addEventListener("click", () => window.studio.cancelRender());
  el.openOutput.addEventListener("click", () => {
    const target = state.lastOutputDir || outputDirFor(state.currentImage?.path);
    if (target) {
      window.studio.openPath(target);
    }
  });
}

function bindRenderEvents() {
  window.studio.onRenderItemStart((data) => {
    state.running = true;
    el.progress.removeAttribute("value");
    setStatus(`Rendering ${data.index}/${data.total}: ${fileName(data.inputPath)}`);
  });
  window.studio.onRenderItemDone((data) => {
    state.lastOutputDir = data.outputDir;
    log(`[${data.index}/${data.total}] ${fileName(data.inputPath)} ${data.elapsedSeconds.toFixed(1)}s`);
    setStatus(`Rendered ${data.index}/${data.total}`);
    if (state.currentImage && data.inputPath === state.currentImage.path) {
      el.outputPreview.src = `${data.previewUrl}?t=${Date.now()}`;
    }
  });
  window.studio.onRenderItemError((data) => {
    log(`ERROR ${fileName(data.inputPath)}: ${data.message}`);
  });
  window.studio.onRenderAllDone(() => {
    state.running = false;
    el.progress.value = 0;
    setStatus("Render complete");
  });
  window.studio.onRenderLog((text) => log(text.trim()));
}

function buildPresetSelect() {
  for (const name of Object.keys(PRESETS)) {
    const option = document.createElement("option");
    option.value = name;
    option.textContent = name;
    el.presetSelect.appendChild(option);
  }
}

function buildParamPanels() {
  el.tabs.innerHTML = "";
  el.paramPanels.innerHTML = "";

  for (const group of PARAM_GROUPS) {
    const tab = document.createElement("button");
    tab.className = `tab${group.name === state.activeTab ? " active" : ""}`;
    tab.textContent = group.name;
    tab.addEventListener("click", () => activateTab(group.name));
    el.tabs.appendChild(tab);

    const panel = document.createElement("div");
    panel.className = `param-panel${group.name === state.activeTab ? " active" : ""}`;
    panel.dataset.panel = group.name;
    for (const param of group.params) {
      panel.appendChild(createParamControl(param));
    }
    el.paramPanels.appendChild(panel);
  }
}

function createParamControl(param) {
  const row = document.createElement("div");
  row.className = "param";
  const label = document.createElement("label");
  label.textContent = param.label;
  row.appendChild(label);

  const value = getByPath(state.config, param.path);
  if (param.type === "float" || param.type === "int") {
    const range = document.createElement("input");
    range.type = "range";
    range.min = param.min;
    range.max = param.max;
    range.step = param.step;
    range.value = value;

    const number = document.createElement("input");
    number.type = "number";
    number.min = param.min;
    number.max = param.max;
    number.step = param.step;
    number.value = value;

    const update = (raw) => {
      const parsed = param.type === "int" ? Math.round(Number(raw)) : Number(raw);
      range.value = parsed;
      number.value = parsed;
      setByPath(state.config, param.path, parsed);
    };
    range.addEventListener("input", () => update(range.value));
    number.addEventListener("change", () => update(number.value));
    row.appendChild(range);
    row.appendChild(number);
  } else if (param.type === "bool") {
    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.checked = Boolean(value);
    checkbox.addEventListener("change", () => setByPath(state.config, param.path, checkbox.checked));
    row.appendChild(checkbox);
  } else if (param.type === "select") {
    const select = document.createElement("select");
    for (const optionValue of param.values) {
      const option = document.createElement("option");
      option.value = optionValue;
      option.textContent = optionValue;
      select.appendChild(option);
    }
    select.value = value;
    select.addEventListener("change", () => setByPath(state.config, param.path, select.value));
    row.appendChild(select);
  } else if (param.type === "entry-int" || param.type === "entry-text") {
    const input = document.createElement("input");
    input.type = param.type === "entry-int" ? "number" : "text";
    input.value = value;
    input.addEventListener("change", () => {
      const nextValue = param.type === "entry-int" ? Math.round(Number(input.value)) : input.value;
      setByPath(state.config, param.path, nextValue);
    });
    row.appendChild(input);
  }
  return row;
}

function activateTab(name) {
  state.activeTab = name;
  for (const tab of el.tabs.querySelectorAll(".tab")) {
    tab.classList.toggle("active", tab.textContent === name);
  }
  for (const panel of el.paramPanels.querySelectorAll(".param-panel")) {
    panel.classList.toggle("active", panel.dataset.panel === name);
  }
}

function applyPreset(name) {
  const preset = PRESETS[name];
  if (!preset) {
    return;
  }
  for (const [path, value] of Object.entries(preset)) {
    setByPath(state.config, path, value);
  }
  syncControlsFromConfig();
  setStatus(`Preset: ${name}`);
}

function syncControlsFromConfig() {
  buildParamPanels();
}

async function refreshImages() {
  try {
    setStatus("Loading images");
    const images = await window.studio.listImages({
      dir: el.inputDir.value,
      recursive: el.recursive.checked,
    });
    state.images = images;
    state.selectedPaths.clear();
    renderImageRows();
    if (images.length) {
      selectImage(images[0].path, false);
    }
    setStatus(`${images.length} images`);
  } catch (error) {
    setStatus(error.message);
    log(`ERROR ${error.message}`);
  }
}

function renderImageRows() {
  el.imageTable.innerHTML = "";
  for (const image of state.images) {
    const row = document.createElement("tr");
    row.dataset.path = image.path;
    row.innerHTML = `
      <td title="${escapeHtml(image.path)}">${escapeHtml(image.name)}</td>
      <td>${escapeHtml(image.dimensions || "-")}</td>
      <td>${formatBytes(image.size)}</td>
    `;
    row.addEventListener("click", (event) => selectImage(image.path, event.metaKey || event.ctrlKey));
    row.addEventListener("dblclick", renderSelected);
    el.imageTable.appendChild(row);
  }
}

function selectImage(imagePath, toggle) {
  const image = state.images.find((item) => item.path === imagePath);
  if (!image) {
    return;
  }
  if (toggle) {
    if (state.selectedPaths.has(imagePath)) {
      state.selectedPaths.delete(imagePath);
    } else {
      state.selectedPaths.add(imagePath);
    }
  } else {
    state.selectedPaths.clear();
    state.selectedPaths.add(imagePath);
  }
  state.currentImage = image;
  el.originalPreview.src = image.url;
  const outputPreview = `${fileUrl(outputDirFor(image.path))}/pen_drawing.png`;
  el.outputPreview.src = `${outputPreview}?t=${Date.now()}`;
  for (const row of el.imageTable.querySelectorAll("tr")) {
    row.classList.toggle("selected", state.selectedPaths.has(row.dataset.path));
  }
  setStatus(image.path);
}

async function renderSelected() {
  const images = Array.from(state.selectedPaths);
  if (!images.length) {
    setStatus("Select an image first");
    return;
  }
  await startRender(images);
}

async function renderAll() {
  if (!state.images.length) {
    setStatus("No images");
    return;
  }
  await startRender(state.images.map((image) => image.path));
}

async function startRender(images) {
  if (state.running) {
    setStatus("Render job is already running");
    return;
  }
  try {
    state.running = true;
    el.progress.removeAttribute("value");
    log(`Start render: ${images.length} image(s)`);
    await window.studio.startRender({
      images,
      outputDir: el.outputDir.value,
      outputSuffix: el.outputSuffix.value || "pen",
      mode: el.mode.value,
      config: state.config,
    });
  } catch (error) {
    state.running = false;
    el.progress.value = 0;
    setStatus(error.message);
    log(`ERROR ${error.message}`);
  }
}

function outputDirFor(imagePath) {
  if (!imagePath) {
    return el.outputDir.value;
  }
  const suffix = (el.outputSuffix.value || "pen").replace(/[^a-zA-Z0-9_-]/g, "_");
  const stem = fileName(imagePath).replace(/\.[^.]+$/, "");
  return joinPath(el.outputDir.value, `${stem}_${suffix}`);
}

function getByPath(object, path) {
  return path.split(".").reduce((current, part) => current[Number.isInteger(Number(part)) ? Number(part) : part], object);
}

function setByPath(object, path, value) {
  const parts = path.split(".");
  let current = object;
  for (const part of parts.slice(0, -1)) {
    current = current[Number.isInteger(Number(part)) ? Number(part) : part];
  }
  const final = parts[parts.length - 1];
  current[Number.isInteger(Number(final)) ? Number(final) : final] = value;
}

function formatBytes(bytes) {
  const units = ["B", "KB", "MB", "GB"];
  let value = bytes;
  for (const unit of units) {
    if (value < 1024 || unit === units[units.length - 1]) {
      return unit === "B" ? `${value}B` : `${value.toFixed(1)}${unit}`;
    }
    value /= 1024;
  }
  return `${bytes}B`;
}

function fileName(filePath) {
  return filePath.split(/[\\/]/).pop();
}

function joinPath(base, leaf) {
  const separator = base.includes("\\") ? "\\" : "/";
  return `${base.replace(/[\\/]+$/, "")}${separator}${leaf}`;
}

function fileUrl(filePath) {
  const normalized = filePath.split("\\").join("/");
  return `file://${normalized.split("/").map(encodeURIComponent).join("/")}`;
}

function setStatus(text) {
  el.status.textContent = text;
}

function log(text) {
  if (!text) {
    return;
  }
  el.log.textContent += `${text}\n`;
  el.log.scrollTop = el.log.scrollHeight;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}
