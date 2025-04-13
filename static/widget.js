const socket = io();
socket.on('connect', () => {
  console.log('Socket.IO 已连接');
});
socket.on('playlist_update', data => {
  console.log('收到待播清单更新:', data);
  updatePlaylist(data);
});
socket.on('message_update', data => {
  console.log('收到消息数据:', data);
  showmessage(data);
});

const albumImg = document.querySelector(".cover img");
albumImg.onload = () => {
  if (typeof Vibrant === "undefined") {
    console.error("Vibrant 库加载失败！");
    return;
  }
  Vibrant.from(albumImg).getPalette()
    .then(palette => {
      console.log("提取到的调色板:", palette);
      const container = document.getElementById("swatches");
      const keys = ["Vibrant", "Muted", "DarkVibrant", "DarkMuted", "LightVibrant", "LightMuted"];
      keys.forEach(key => {
        const swatch = palette[key];
        const swatchDiv = document.createElement("div");
        swatchDiv.className = "swatch";
        if (swatch) {
          const hex = swatch.getHex();
          const textColor = swatch.getTitleTextColor();
          swatchDiv.style.backgroundColor = hex;
          swatchDiv.style.color = textColor;
          swatchDiv.innerHTML = `<div>${key}</div><div>${hex}</div>`;
        } else {
          swatchDiv.style.backgroundColor = "#000";
          swatchDiv.style.color = "#fff";
          swatchDiv.innerHTML = `<div>${key}</div><div>N/A</div>`;
        }
        container.appendChild(swatchDiv);
      });

      if (palette.DarkMuted) {
        document.getElementById('root').style.backgroundColor = palette.DarkMuted.getHex();
      }
      if (palette.LightVibrant) {
        document.querySelector(".name").style.color = palette.LightVibrant.getHex();
      }
      if (palette.LightMuted) {
        document.querySelector(".artist").style.color = palette.LightMuted.getHex();
      }
    })
    .catch(error => {
      console.error("调色板提取失败：", error);
    });
};

if (albumImg.complete) {
  albumImg.onload();
}

function initScrollingText(selector, margin = 50, speed = 1) {
  const textEl = document.querySelector(selector);
  if (!textEl) return;
  const containerEl = textEl.parentElement;
  if (!containerEl) return;

  function measureTextWidth(text, className) {
    const temp = document.createElement("div");
    temp.style.position = "absolute";
    temp.style.whiteSpace = "nowrap";
    temp.style.visibility = "hidden";
    if (className) temp.className = className;
    temp.textContent = text;
    document.body.appendChild(temp);
    const width = temp.offsetWidth;
    document.body.removeChild(temp);
    return width;
  }

  const containerWidth = containerEl.offsetWidth;
  let textWidth = measureTextWidth(textEl.textContent, textEl.className);

  if (textWidth <= containerWidth - margin) {
    textEl.style.transform = "translateX(0)";
    return;
  }

  let offset = containerWidth;
  let direction = "left";

  function animate() {
    textWidth = measureTextWidth(textEl.textContent, textEl.className);
    if (textWidth <= containerWidth - margin) {
      textEl.style.transform = "translateX(0)";
      return;
    }

    if (direction === "left") {
      offset -= speed;
      if (offset <= -textWidth) {
        direction = "right";
      }
    } else {
      offset += speed;
      if (offset >= containerWidth) {
        direction = "left";
      }
    }
    containerEl.classList.add("scrolling");
    textEl.style.transform = `translate3d(${offset}px, 0, 0)`;
    requestAnimationFrame(animate);
  }

  animate();
}

document.addEventListener("DOMContentLoaded", function() {
  initScrollingText('.name', 50, 1);
  initScrollingText('.artist', 50, 1);
});

function updatePlaylist(data) {
  const playlistContainer = document.getElementById('playlist');
  if (playlistContainer) {
    playlistContainer.innerHTML = '';
  }

  if (data.length < 1) {
    const albumImg = document.querySelector(".cover img");
    if (albumImg) {
      albumImg.src = "/static/images/Spotify.png";
      albumImg.onload = () => {
        updateColors();
      };
    }
    const nameEl = document.querySelector(".name");
    if (nameEl) {
      nameEl.textContent = "目前无点歌";
      setTimeout(() => {
        initScrollingText('.name', 50, 1);
      }, 0);
    }
    const artistEl = document.querySelector(".artist");
    if (artistEl) {
      artistEl.textContent = "发送：点歌 + 歌名 即可点歌";
      setTimeout(() => {
        initScrollingText('.artist', 50, 1);
      }, 0);
    }
    return;
  }

  const albumImg = document.querySelector(".cover img");
  if (data.length > 0 && albumImg) {
    albumImg.src = data[0].albumCover;
    albumImg.onload = () => {
      updateColors();
    };
  }

  const nameEl = document.querySelector(".name");
  if (data.length > 0 && nameEl) {
    nameEl.textContent = `列队1: ${data[0].name}`;
    setTimeout(() => {
      initScrollingText('.name', 50, 1);
    }, 0);
  }

  const artistEl = document.querySelector(".artist");
  if (artistEl) {
    if (data.length > 1) {
      artistEl.textContent = `列队2: ${data[1].name}`;
    } else {
      artistEl.textContent = "发送：点歌 + 歌名 即可点歌";
    }
    setTimeout(() => {
      initScrollingText('.artist', 50, 1);
    }, 0);
  }
}

function showmessage(data) {
  const albumImg = document.querySelector(".cover img");
  if (data.result != "没有找到匹配歌曲") {
    albumImg.src = data.albumCover;
    albumImg.onload = () => {
      updateColors();
    };
  }
  const messageEl = document.querySelector(".name");
  if (messageEl) {
    messageEl.textContent = data.message;
    setTimeout(() => {
      initScrollingText('.name', 50, 1);
    }, 0);
  } else {
    console.error("消息元素不存在！");
  }
  const resultEl = document.querySelector(".artist");
  if (resultEl) {
    resultEl.textContent = data.result;
    setTimeout(() => {
      initScrollingText('.artist', 50, 1);
    }, 0);
  } else {
    console.error("结果元素不存在！");
  }
}

function updateColors() {
  const albumImg = document.querySelector(".cover img");
  if (!albumImg || typeof Vibrant === "undefined") {
    console.error("专辑封面图片不存在或者 Vibrant 库未加载！");
    return;
  }
  Vibrant.from(albumImg).getPalette()
    .then(palette => {
      console.log("重新提取的调色板:", palette);
      const swatchesContainer = document.getElementById("swatches");
      if (swatchesContainer) {
        swatchesContainer.innerHTML = '';
        const keys = ["Vibrant", "Muted", "DarkVibrant", "DarkMuted", "LightVibrant", "LightMuted"];
        keys.forEach(key => {
          const swatch = palette[key];
          const swatchDiv = document.createElement("div");
          swatchDiv.className = "swatch";
          if (swatch) {
            const hex = swatch.getHex();
            const textColor = swatch.getTitleTextColor();
            swatchDiv.style.backgroundColor = hex;
            swatchDiv.style.color = textColor;
            swatchDiv.innerHTML = `<div>${key}</div><div>${hex}</div>`;
          } else {
            swatchDiv.style.backgroundColor = "#000";
            swatchDiv.style.color = "#fff";
            swatchDiv.innerHTML = `<div>${key}</div><div>N/A</div>`;
          }
          swatchesContainer.appendChild(swatchDiv);
        });
      }

      const rootEl = document.getElementById("root");
      if (palette.DarkMuted && rootEl) {
        rootEl.style.backgroundColor = palette.DarkMuted.getHex();
      }
      const nameEl = document.querySelector(".name");
      if (palette.LightVibrant && nameEl) {
        nameEl.style.color = palette.LightVibrant.getHex();
      }
      const artistEl = document.querySelector(".artist");
      if (palette.LightMuted && artistEl) {
        artistEl.style.color = palette.LightMuted.getHex();
      }
    })
    .catch(err => {
      console.error("颜色提取失败：", err);
    });
}
