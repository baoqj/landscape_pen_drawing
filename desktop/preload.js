const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("studio", {
  defaults: () => ipcRenderer.invoke("paths:defaults"),
  chooseDirectory: (initialPath) => ipcRenderer.invoke("dialog:chooseDirectory", initialPath),
  listImages: (options) => ipcRenderer.invoke("images:list", options),
  startRender: (payload) => ipcRenderer.invoke("render:start", payload),
  cancelRender: () => ipcRenderer.invoke("render:cancel"),
  openPath: (targetPath) => ipcRenderer.invoke("shell:openPath", targetPath),
  onRenderItemStart: (callback) => ipcRenderer.on("render:itemStart", (_event, data) => callback(data)),
  onRenderItemDone: (callback) => ipcRenderer.on("render:itemDone", (_event, data) => callback(data)),
  onRenderItemError: (callback) => ipcRenderer.on("render:itemError", (_event, data) => callback(data)),
  onRenderAllDone: (callback) => ipcRenderer.on("render:allDone", (_event, data) => callback(data)),
  onRenderLog: (callback) => ipcRenderer.on("render:log", (_event, text) => callback(text)),
});

