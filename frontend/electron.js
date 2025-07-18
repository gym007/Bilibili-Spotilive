const { app, BrowserWindow } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const fs = require('fs');

// let mainWindow = null;
// let backendProcess = null;

// function startBackend() {
//   const exePath = path.join(__dirname, 'backend', 'main.exe');
//   console.log('[DEBUG] 启动后端 exe:', exePath);

//   if (!fs.existsSync(exePath)) {
//     console.error('❌ 找不到后端 exe：', exePath);
//     return;
//   }

//   backendProcess = spawn(exePath, [], {
//     cwd: path.dirname(exePath),
//     shell: false,
//     windowsHide: true,
//     stdio: 'ignore'
//   });

//   backendProcess.on('error', err => {
//     console.error('后端启动失败:', err);
//   });
// }

// function stopBackend() {
//   if (backendProcess) {
//     backendProcess.kill();
//     backendProcess = null;
//   }
// }

function createWindow() {
  console.log("Creating Electron window...");

  mainWindow = new BrowserWindow({
    width: 800,
    height: 600,
    autoHideMenuBar: true,
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
    }
  });

  if (process.env.NODE_ENV === 'development') {
    mainWindow.loadURL('http://localhost:5173');
  } else {
    mainWindow.loadFile(path.join(__dirname, 'dist/index.html'));
  }
}

app.whenReady().then(() => {
  // startBackend();
  createWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', () => {
  // stopBackend();
  if (process.platform !== 'darwin') app.quit();
});
