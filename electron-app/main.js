const { app, BrowserWindow, ipcMain } = require('electron');
const path = require('path');
const { spawn } = require('child_process');

let pyProc = null;
let mainWin = null;
let formWin = null;

function startPythonBackend() {
  const scriptPath = path.join(__dirname, '../backend/app.py');
  const pythonCmd = process.platform === 'win32' ? 'python' : 'python3';

  pyProc = spawn(pythonCmd, [scriptPath]);

  pyProc.stdout.on('data', (data) => {
    console.log(`[Flask]: ${data}`);
  });

  pyProc.stderr.on('data', (data) => {
    console.error(`[Flask Error]: ${data}`);
  });

  pyProc.on('exit', (code) => {
    console.log(`Flask backend exited with code ${code}`);
  });
}

function createFormWindow() {
  formWin = new BrowserWindow({
    width: 600,
    height: 600,
    resizable: true,
    modal: true,
    show: false,
    frame: true,
    webPreferences: {
      contextIsolation: false,
      nodeIntegration: true
    }
  });

  formWin.loadFile(path.join(__dirname, 'form.html'));
  formWin.once('ready-to-show', () => {
    formWin.show();
  });

  formWin.on('closed', () => {
    formWin = null;
  });
}

function createMainWindow() {
  mainWin = new BrowserWindow({
    width: 1200,
    height: 800,
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false
    }
  });

  mainWin.loadFile(path.join(__dirname, 'dist/index.html'));
}

app.whenReady().then(() => {
  startPythonBackend();
  createFormWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createFormWindow();
  });
});

ipcMain.on('config-submitted', () => {
  if (formWin) formWin.close();
  createMainWindow();
});

app.on('window-all-closed', () => {
  if (pyProc) pyProc.kill();
  if (process.platform !== 'darwin') app.quit();
});
