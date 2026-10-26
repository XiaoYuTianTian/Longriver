[English](README.md) · [中文](docs/README.zh-CN.md)

<p align="center">
  <img src="docs/images/logo.png" width="128" alt="Longriver">
</p>

# Longriver

Stop on a year. The territories of that year spread across the map, and the people and events of the year wait at the side.

![The year holds, then a record opens and the timeline steps aside](docs/images/atlas.gif)

![1521, the map and the timeline together](docs/images/atlas-year.jpg)

The index has two shelves: events, and people. A tag shows only what that year actually holds — a war, a treaty, a scientist, a poet. Choosing a line moves the map to the place and draws the territory around it. The essay stays shut until you ask to read.

![The Diet of Worms, drawn as a record, while the timeline steps aside](docs/images/atlas-reading.jpg)

A record opens as a picture: the year, the place, the title, one sentence. The longer extract and the citations stay folded under 原文. If an illustration can be made, it is requested only for that one record, after the picture is already on the page, and kept for the next visit. The map does not wait for it.

The same package runs in the browser and, without a network, on the phone. Bookmarks stay on the device that made them.

There are about 9,737 records, 5,130 people and 3,617 places, from 3000 BCE through 2026. Borders through 1911 come from Cliopatria. Land and countries from 1912 come from Natural Earth; Taiwan, Hong Kong and Macau are part of China. A person with only a birth year appears in that year alone. A person with a death year stays for the span of the life. Pictures already in the package are public domain, CC0, CC BY or CC BY-SA, and the credit travels with them.

## Where it comes from

| What | Source | Licence |
| --- | --- | --- |
| Borders through 1911 | [Cliopatria](https://doi.org/10.5281/zenodo.13363121) | CC BY 4.0, simplified and cut by year |
| Land and countries from 1912 | [Natural Earth](https://www.naturalearthdata.com/) | Public domain |
| People, places, events | [Wikidata](https://www.wikidata.org/) | CC0 |
| Extracts | Chinese Wikipedia | CC BY-SA 4.0, named on the page |
| Portraits and place pictures | [Wikimedia Commons](https://commons.wikimedia.org/) | PD / CC0 / CC BY / CC BY-SA only |

Wikidata entries in China after 1949 stay in the held batch `china-1949-plus` and are not shipped. Copyrighted books keep a citation, not the text. A Tianditu key can replace the modern basemap; the key is not in the repository. The map has no official review number and is marked as a test build. Historical borders are a sketch of public data, not a claim about present boundaries.

The app does not collect a name, a phone number, a location or a device id, and it does not include ads or analytics.

## In the browser

Node.js, then from `web/`:

```powershell
npm install
npm run dev
```

Open http://127.0.0.1:5173 . To generate a missing illustration the first time a record is opened, set `LONGRIVER_IMAGE_KEY` before starting the dev server. Without the key, the drawn record remains, and nothing else is fetched for the picture.

## On the phone

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

The debug package is `android/app/build/outputs/apk/debug/app-debug.apk`. The knowledge, borders and pictures come from `content/dist/` and are packed by Gradle.

## What is not in the repository

`android/local.properties`, keystores, `.env`, `backend/db.sqlite3`, `content/dist/media/`, `content/dist/detail-art/`, and the Wikidata cache in `content/raw/`. Django's default `SECRET_KEY` is for this machine. The database password `longriver-local` lives only in the local Postgres compose file.
