[English](README.md) · [中文](docs/README.zh-CN.md)

<p align="center">
  <img src="docs/images/logo.png" width="128" alt="Longriver">
</p>

<h1 align="center">Longriver</h1>

<p align="center">Stop on a year. The territories of that year spread across the map,<br>and the people and events of the year wait at the side.</p>

<p align="center">
  <a href="LICENSE"><img alt="Source code is MIT" src="https://img.shields.io/badge/code-MIT-1f4e5f"></a>
  <img alt="Wikipedia extracts remain CC BY-SA 4.0" src="https://img.shields.io/badge/extracts-CC%20BY--SA%204.0-2f6f9a">
  <img alt="Years from 3000 BCE to 2026" src="https://img.shields.io/badge/years-3000%20BCE%E2%80%932026-8a6232">
</p>

An offline atlas of world history. The same knowledge package runs in the browser and, without a network, on the phone. There are about 9,737 records, 5,130 people and 3,617 places, from 3000 BCE through 2026.

<p align="center">
  <img src="docs/images/atlas.gif" alt="The year holds, then a record opens and the timeline steps aside">
</p>

## What you can do

- Stop on a year and let the territories take that year's color.
- Read events and people on two shelves. A tag shows only what that year actually holds.
- Choose a line to move the map and draw the territory. The essay stays shut until you ask to read.
- Open a record as a drawn page: the year, the place, the title, one sentence. The longer extract and the citations stay folded under 原文.
- Request an illustration only after that page is open. It is kept for the next visit. With no key, the drawn page stands on its own.
- Keep bookmarks on the device that made them.

<p align="center">
  <img src="docs/images/atlas-year.jpg" width="49%" alt="1521, the map and the timeline together">
  <img src="docs/images/atlas-reading.jpg" width="49%" alt="A record open, while the timeline steps aside">
</p>

A person with only a birth year appears in that year alone. A person with a death year stays for the span of the life. Pictures already in the package are public domain, CC0, CC BY or CC BY-SA, and the credit travels with them.

## Get started

### Browser

Node.js, then from `web/`:

```powershell
npm install
npm run dev
```

Open http://127.0.0.1:5173 . The page is Vue 3. Bookmarks and notes stay in this browser's IndexedDB.

To make a missing illustration the first time a record opens, set `LONGRIVER_IMAGE_KEY` before starting the dev server. Without the key, the drawn record remains, and nothing else is fetched for the picture.

### Phone

JDK 17 and the Android SDK. `android/local.properties` stays off the repository:

```properties
sdk.dir=C:\\Android\\Sdk
longriver.apiBaseUrl=http://10.0.2.2:8000
tianditu.key=
```

```powershell
cd android
.\gradlew.bat :app:assembleDebug
```

The debug package is `android/app/build/outputs/apk/debug/app-debug.apk`. Knowledge, borders and pictures come from `content/dist/` and are packed by Gradle.

## Sources

| What | Source | Licence |
| --- | --- | --- |
| Borders through 1911 | [Cliopatria](https://doi.org/10.5281/zenodo.13363121) | CC BY 4.0, simplified and cut by year |
| Land and countries from 1912 | [Natural Earth](https://www.naturalearthdata.com/) | Public domain |
| People, places, events | [Wikidata](https://www.wikidata.org/) | CC0 |
| Extracts | Chinese Wikipedia | CC BY-SA 4.0, named on the page |
| Portraits and place pictures | [Wikimedia Commons](https://commons.wikimedia.org/) | PD / CC0 / CC BY / CC BY-SA only |

Wikidata entries in China after 1949 stay in the held batch `china-1949-plus` and are not shipped. Copyrighted books keep a citation, not the text. A Tianditu key can replace the modern basemap; the key is not in the repository. The map has no official review number and is marked as a test build. Historical borders are a sketch of public data, not a claim about present boundaries. Taiwan, Hong Kong and Macau are drawn as part of China.

## Layout

| Path | What it holds |
| --- | --- |
| [`web/`](web/) | Browser client |
| [`android/`](android/) | Phone app |
| [`content/`](content/) | Scripts that build the shared knowledge package |
| [`docs/`](docs/) | Chinese homepage and the pictures on this page |
| [`backend/`](backend/) | Local services used while preparing data |

Rebuild the package with:

```powershell
python content/build_wikidata.py
python content/build_android_package.py
```

The browser and the phone both read `content/dist/`.

## Help

Questions and corrections go in [issues](https://github.com/XiaoYuTianTian/Longriver/issues). How to send a change is written in [CONTRIBUTING.md](CONTRIBUTING.md). The repository is maintained by [XiaoYuTianTian](https://github.com/XiaoYuTianTian).

The app does not collect a name, a phone number, a location or a device id, and it does not include ads or analytics.

## License

Original source code is under the [MIT License](LICENSE).

That licence stops at the code. Wikipedia extracts remain CC BY-SA 4.0. Cliopatria borders remain CC BY 4.0. Natural Earth remains public domain. Wikidata facts remain CC0. Each picture keeps the licence stored with it.

## Not in this repository

- `android/local.properties`, `android/keystore.properties`, and `*.jks`
- `.env`, including `LONGRIVER_IMAGE_KEY`
- `backend/db.sqlite3`
- `content/dist/media/` and `content/dist/detail-art/`
- `content/raw/`, the Wikidata query cache

Django's default `SECRET_KEY` is for this machine. The database password `longriver-local` lives only in the local Postgres compose file.
