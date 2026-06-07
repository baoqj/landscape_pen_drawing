const { app, BrowserWindow, dialog, ipcMain, nativeImage, shell } = require("electron");
const { spawn } = require("child_process");
const fs = require("fs");
const path = require("path");

const ROOT = path.resolve(__dirname, "..");
const IMAGE_EXTENSIONS = new Set([".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"]);

let mainWindow = null;
let runningProcess = null;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1500,
    height: 960,
    minWidth: 1180,
    minHeight: 760,
    title: "Landscape Pen Drawing Studio",
    backgroundColor: "#f4f1ea",
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  mainWindow.loadFile(path.join(__dirname, "renderer.html"));
}

app.whenReady().then(createWindow);

app.on("window-all-closed", () => {
  if (runningProcess) {
    runningProcess.kill();
  }
  if (process.platform !== "darwin") {
    app.quit();
  }
});

app.on("activate", () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow();
  }
});

ipcMain.handle("paths:defaults", () => ({
  inputDir: path.resolve(ROOT, "../../pics"),
  outputDir: path.join(ROOT, "outputs", "desktop"),
  root: ROOT,
}));

ipcMain.handle("dialog:chooseDirectory", async (_event, initialPath) => {
  const result = await dialog.showOpenDialog(mainWindow, {
    defaultPath: initialPath || ROOT,
    properties: ["openDirectory"],
  });
  if (result.canceled || !result.filePaths.length) {
    return null;
  }
  return result.filePaths[0];
});

ipcMain.handle("images:list", async (_event, options) => {
  const dir = path.resolve(options.dir);
  const recursive = Boolean(options.recursive);
  if (!fs.existsSync(dir)) {
    throw new Error(`Directory does not exist: ${dir}`);
  }
  const files = listImageFiles(dir, recursive);
  return files.map((filePath) => {
    const stat = fs.statSync(filePath);
    const dimensions = readImageDimensions(filePath);
    return {
      path: filePath,
      name: path.basename(filePath),
      ext: path.extname(filePath).slice(1).toLowerCase(),
      size: stat.size,
      dimensions,
      modified: stat.mtimeMs,
      url: toFileUrl(filePath),
    };
  });
});

ipcMain.handle("render:start", async (_event, payload) => {
  if (runningProcess) {
    throw new Error("A render job is already running.");
  }
  const images = payload.images || [];
  if (!images.length) {
    throw new Error("No images selected.");
  }
  runRenderQueue(images, payload);
  return { started: true, count: images.length };
});

ipcMain.handle("render:cancel", async () => {
  if (runningProcess) {
    runningProcess.kill();
    runningProcess = null;
    return { cancelled: true };
  }
  return { cancelled: false };
});

ipcMain.handle("shell:openPath", async (_event, targetPath) => {
  fs.mkdirSync(targetPath, { recursive: true });
  return shell.openPath(targetPath);
});

function listImageFiles(dir, recursive) {
  const out = [];
  const entries = fs.readdirSync(dir, { withFileTypes: true });
  for (const entry of entries) {
    const fullPath = path.join(dir, entry.name);
    if (entry.isDirectory() && recursive) {
      out.push(...listImageFiles(fullPath, recursive));
    } else if (entry.isFile() && IMAGE_EXTENSIONS.has(path.extname(entry.name).toLowerCase())) {
      out.push(fullPath);
    }
  }
  return out.sort((a, b) => a.localeCompare(b));
}

function readImageDimensions(filePath) {
  const image = nativeImage.createFromPath(filePath);
  const size = image.getSize();
  if (!size.width || !size.height) {
    return "";
  }
  return `${size.width}x${size.height}`;
}

async function runRenderQueue(images, payload) {
  const total = images.length;
  for (let index = 0; index < images.length; index += 1) {
    const inputPath = images[index];
    const outputDir = outputDirFor(inputPath, payload.outputDir, payload.outputSuffix);
    const configPath = writeJobConfig(payload.config, outputDir);
    const args = [
      path.join(ROOT, "main.py"),
      "--input",
      inputPath,
      "--output",
      outputDir,
      "--mode",
      payload.mode || "pure",
      "--config",
      configPath,
    ];
    mainWindow.webContents.send("render:itemStart", {
      index: index + 1,
      total,
      inputPath,
      outputDir,
    });
    const started = Date.now();
    try {
      const output = await runPython(args);
      mainWindow.webContents.send("render:itemDone", {
        index: index + 1,
        total,
        inputPath,
        outputDir,
        output,
        elapsedSeconds: (Date.now() - started) / 1000,
        previewUrl: toFileUrl(path.join(outputDir, "pen_drawing.png")),
      });
    } catch (error) {
      mainWindow.webContents.send("render:itemError", {
        index: index + 1,
        total,
        inputPath,
        outputDir,
        message: error.message,
      });
    }
  }
  runningProcess = null;
  mainWindow.webContents.send("render:allDone", {});
}

function runPython(args) {
  return new Promise((resolve, reject) => {
    const python = pythonExecutable();
    const child = spawn(python, args, { cwd: ROOT });
    runningProcess = child;
    let stdout = "";
    let stderr = "";

    child.stdout.on("data", (chunk) => {
      const text = chunk.toString();
      stdout += text;
      mainWindow.webContents.send("render:log", text);
    });
    child.stderr.on("data", (chunk) => {
      const text = chunk.toString();
      stderr += text;
      mainWindow.webContents.send("render:log", text);
    });
    child.on("error", (error) => {
      runningProcess = null;
      reject(error);
    });
    child.on("close", (code) => {
      runningProcess = null;
      if (code === 0) {
        resolve(stdout.trim());
      } else {
        reject(new Error(stderr.trim() || stdout.trim() || `Python exited with code ${code}`));
      }
    });
  });
}

function pythonExecutable() {
  const venvPython = process.platform === "win32"
    ? path.join(ROOT, ".venv", "Scripts", "python.exe")
    : path.join(ROOT, ".venv", "bin", "python");
  if (fs.existsSync(venvPython)) {
    return venvPython;
  }
  return process.platform === "win32" ? "python" : "python3";
}

function outputDirFor(inputPath, outputRoot, suffix) {
  const safeSuffix = (suffix || "pen").replace(/[^a-zA-Z0-9_-]/g, "_");
  return path.join(path.resolve(outputRoot), `${path.parse(inputPath).name}_${safeSuffix}`);
}

function writeJobConfig(config, outputDir) {
  fs.mkdirSync(outputDir, { recursive: true });
  const configPath = path.join(outputDir, "desktop_config.yaml");
  fs.writeFileSync(configPath, toYaml(config), "utf8");
  return configPath;
}

function toYaml(value, indent = 0) {
  const pad = " ".repeat(indent);
  if (Array.isArray(value)) {
    return `[${value.map((item) => JSON.stringify(item)).join(", ")}]`;
  }
  if (value && typeof value === "object") {
    return Object.entries(value)
      .map(([key, val]) => {
        if (val && typeof val === "object" && !Array.isArray(val)) {
          return `${pad}${key}:\n${toYaml(val, indent + 2)}`;
        }
        return `${pad}${key}: ${toYaml(val, 0)}`;
      })
      .join("\n");
  }
  if (typeof value === "string") {
    return value;
  }
  if (typeof value === "boolean") {
    return value ? "true" : "false";
  }
  return String(value);
}

function toFileUrl(filePath) {
  return `file://${filePath.split(path.sep).map(encodeURIComponent).join("/")}`;
}

