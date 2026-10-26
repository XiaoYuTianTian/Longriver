[English](../README.md) · [中文](README.zh-CN.md)

<p align="center">
  <img src="images/logo.png" width="128" alt="长河">
</p>

# 长河

想看看某一年的世界，就把时间停在那一年。

![时间停住，再打开一条记述，时间尺让开](images/atlas.gif)

疆域顺着年份换上颜色。右边分开两栏：事件，和人物。标签只列出这一年真正有的东西，战争、条约、科学家、文学家各归其位。点一条，地图先飞到那个地方，并勾出当时的疆域。长文先不打开。

![1521 年，地图和时间摊在一起](images/atlas-year.jpg)

再点「阅读」，这一条被画成一张图：年份、地名、标题、一句话。更长的摘录和出处收在「原文」里。配图只在打开这一条之后才去要，要到了就留下来；没有配图时，这张字图自己就立得住。合上以后，时间尺从下方回来，年份和地图还停在原地。

![打开沃尔姆斯会议时，时间尺让开](images/atlas-reading.jpg)

手机里可以不联网翻完。浏览器打开的是同一条河，收藏各自留在自己的设备上。

现在这条河里大约有 9737 条记述、5130 位人物、3617 个地点。公元前 3000 年到 1911 年的疆域来自 Cliopatria；1912 年以后的陆地和国界来自 Natural Earth，台湾、香港、澳门并入中国。人物按寿命出现：只有生年的，不把寿命往后推。配图只收公有领域、CC0、CC BY 和 CC BY-SA，作者和许可随图走。

## 数据从哪来

| 内容 | 来源 | 协议 |
| --- | --- | --- |
| 1911 年及以前的疆域 | [Cliopatria](https://doi.org/10.5281/zenodo.13363121) | CC BY 4.0，轮廓已简化和按年切分 |
| 1912 年以后的陆地与国界 | [Natural Earth](https://www.naturalearthdata.com/) | 公共领域 |
| 人物、地点、事件事实 | [维基数据](https://www.wikidata.org/) | CC0 |
| 详情摘录 | 中文维基百科 | CC BY-SA 4.0，页内标明 |
| 人物与地点图片 | [维基共享资源](https://commons.wikimedia.org/) | 仅 PD / CC0 / CC BY / CC BY-SA |

维基数据里、1949 年以后且地点在中国的条目留在待审批次 `china-1949-plus`，不写入安装包。受版权保护的书籍只保留书目，不收录正文。配置天地图密钥后，1912 年以后可以改用天地图在线底图；密钥不进仓库。

地图尚未取得审图号，应用内标为内测版。历史疆域是公开数据的近似示意，不代表对现实边界的认定。

## 仓库里不会出现的东西

- `android/local.properties`：本机 SDK 路径、接口地址、天地图密钥
- `android/keystore.properties` 和 `*.jks`：签名密钥
- `.env`：环境变量，也包括 `LONGRIVER_IMAGE_KEY`
- `backend/db.sqlite3`：本地数据库
- `content/dist/media/`：体积很大的配图文件
- `content/dist/detail-art/`：按需生成的详情图
- `content/raw/`：维基数据查询缓存

应用不收集姓名、手机号、位置或设备标识，也不接入广告和统计 SDK。

## 在浏览器里沿河走

需要 Node.js。在 `web/` 目录：

```powershell
npm install
npm run dev
```

打开 http://127.0.0.1:5173 。页面用 Vue 3 写成。收藏和备注存在这个浏览器的 IndexedDB 里。若希望缺图的记述在第一次打开时生成一张示意，启动前设置环境变量 `LONGRIVER_IMAGE_KEY`。没有这把钥匙时，字图照常画，不会空等。

## 构建 Android 应用

需要 JDK 17 和 Android SDK。在 `android/local.properties` 里按需填写（此文件不要提交）：

```properties
sdk.dir=C:\\Android\\Sdk
longriver.apiBaseUrl=http://10.0.2.2:8000
tianditu.key=
```

```powershell
cd android
.\gradlew.bat :app:assembleDebug
```

调试包在 `android/app/build/outputs/apk/debug/app-debug.apk`。知识、疆域和配图来自 `content/dist/`，由 Gradle 打进安装包。

## 知识从哪重新生成

```powershell
python content/build_wikidata.py
python content/build_android_package.py
```

这些脚本把阅读包写到 `content/dist/`。手机和浏览器都读这一份。
