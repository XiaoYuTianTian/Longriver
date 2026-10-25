# Longriver

Longriver 是一款离线可用的世界历史地图。拖动时间，疆域、事件和人物一起变化。点开一条记述，看到的是一张档案：地图、事实、摘录、同时代的其他事件、相关人物和出处。

## 亮点

- **时间拉着地图走。** 公元前 3000 年到 1911 年使用 Cliopatria 历史疆域；1912 年以后使用 Natural Earth 陆地与国界，台湾、香港、澳门并入中国。点一个国家，只列出当前时段里和它有关的事件。
- **事件是档案，不是一句标题。** 列表只留一句事实。详情页另外放维基百科导语和「背景 / 经过 / 结果」一类段落，并列出同地、同时代的其他记述。
- **人物按寿命出现。** 生卒都有的人，在相交的每个时段都会出现。只有生年时，只出现在生年，并写明卒年未收录，不把寿命往后推。
- **出处跟着内容走。** 陈述带有时间、地点和引用。维基数据保持未核验，不写成已核实的定论。配图只收公有领域、CC0、CC BY、CC BY-SA，作者和许可随图标注。
- **手机上就能读完。** 地图、疆域、陈述和已下载的图片打进安装包，不联网也能浏览、检索和收藏。收藏和备注只存在这台手机里。浏览器阅读同一份知识包，收藏单独留在那个浏览器里。

当前离线包约有 9246 条陈述、5130 位人物、3504 个地点。三个页面是「图」「览」「我的」。

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

提交前已核对，下列文件被 `.gitignore` 排除：

- `android/local.properties`：本机 SDK 路径、接口地址、天地图密钥
- `android/keystore.properties` 和 `*.jks`：签名密钥
- `.env`：环境变量
- `backend/db.sqlite3`：本地数据库
- `content/dist/media/`：体积很大的配图文件
- `content/raw/`：维基数据查询缓存

Django 的默认 `SECRET_KEY` 只用于本机开发。对外部署时改用环境变量 `DJANGO_SECRET_KEY`。数据库口令 `longriver-local` 只存在于本机 Postgres 的 `compose.yaml`。

应用不收集姓名、手机号、位置或设备标识，也不接入广告和统计 SDK。

## 构建 Android 应用

需要 JDK 17 和 Android SDK。在 `android/local.properties` 里按需填写（此文件不要提交）：

```properties
sdk.dir=C:\\Android\\Sdk
longriver.apiBaseUrl=http://10.0.2.2:8000
tianditu.key=
```

然后：

```powershell
cd android
.\gradlew.bat :app:assembleDebug
```

调试包在 `android/app/build/outputs/apk/debug/app-debug.apk`。手机已打开 USB 调试时，可以在 `android/` 执行 `.\push-to-phone.ps1`，把包复制到手机下载目录。安装包里的知识、疆域和配图来自 `content/dist/`，由 Gradle 打进 assets，不在 `android/app/src/main/assets/` 里再存一份。

单元测试：

```powershell
cd android
.\gradlew.bat :app:testDebugUnitTest
```

## 知识后台

后台用来审核和发布陈述。要求 Python 3.13。在仓库根目录：

```powershell
docker compose up -d db --wait
cd backend
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
$env:DATABASE_URL = "postgresql://longriver:longriver-local@localhost:5432/longriver"
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py load_reference_data
.\.venv\Scripts\python.exe manage.py runserver
```

- 健康检查：http://127.0.0.1:8000/health/
- 内容后台：http://127.0.0.1:8000/admin/
- 知识包：http://127.0.0.1:8000/api/v1/content/packages/

检查：

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check .
```

发布需要审核者和有效引用。AI 草稿不能直接发布。

## 继续补内容

摘录可以分批下载，中断后重跑会接着写 `content/wiki_briefs.json`：

```powershell
python content/build_briefs.py --limit 400
python content/build_android_package.py
```

配图和维基导语：

```powershell
python content/build_media.py
python content/bundle_media.py
```

人物、事件和地点的维基数据提取：

```powershell
python content/build_wikidata.py
```

这些脚本把阅读包写到 `content/dist/`。手机和浏览器都读这一份。

## 浏览器

需要 Node.js。在 `web/` 目录：

```powershell
npm install
npm run dev
```

开发服务器默认是 http://127.0.0.1:5173 。页面用 Vue 3 写成。收藏和备注存在这个浏览器的 IndexedDB 里，不上传，也不同步到手机。
