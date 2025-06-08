# Bilibili-Spotilive
B站直播弹幕点播Spotiy

# 如何使用

- 下载Bilibili-Spotilive-v3.0.4
- 运行v3.0.4.exe
- 配置点歌机
  - Bilibili的cookies
  - 浏览器登陆Bilibili，F12开发者模式可以获取到对应cookies
![](https://github.com/jo4rchy/Bilibili-Spotilive/blob/main/resources/bilibili_cookies.png)

  - Spotify API
  - 前往[Spotify Developer](https://developer.spotify.com/dashboard) 如图页面创建Spotify 的API
  - Redirect Url填写 `http://127.0.0.1:8888/callback`,api和sdk不需要勾选
  - 创建好后可以获得Spotify 的client ID和secret
![](https://github.com/jo4rchy/Bilibili-Spotilive/blob/main/resources/spotify_api.png)

  - 房间号，点歌权限等

# 点歌指令
- 点歌 歌名 歌手(可选)
  - 点亮粉丝图灯牌后可点歌
- 下一首
  - 大航海，房管，主播可以下一首
  - 普通用户可以跳过自己点歌
  - 下一首不能跳过大航海的点歌

# 鸣谢
bilibil-api-python
仓库地址：
[https://github.com/Nemo2011/bilibili-api/tree/main](https://github.com/Nemo2011/bilibili-api/tree/main)
