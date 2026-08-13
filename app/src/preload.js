const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("overlay", {
  getSettings: () => ipcRenderer.invoke("settings:get"),
  setSettings: (patch) => ipcRenderer.invoke("settings:set", patch),
  apiGet: (path) => ipcRenderer.invoke("api:get", path),
  login: (creds) => ipcRenderer.invoke("auth:login", creds),
  toggleClickThrough: () => ipcRenderer.invoke("clickthrough:toggle"),
  hide: () => ipcRenderer.invoke("overlay:hide"),
  minimize: () => ipcRenderer.invoke("overlay:minimize"),
  setShortcut: (action, accelerator) => ipcRenderer.invoke("shortcuts:set", { action, accelerator }),
  onClickThroughChanged: (cb) =>
    ipcRenderer.on("clickthrough:changed", (_event, value) => cb(value)),
});
