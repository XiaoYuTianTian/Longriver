# Contributing

Issues and pull requests are welcome, in English or in Chinese.

## What to send

A useful issue names the year, the record, and what looked wrong. A useful change stays close to the file it edits, and leaves secrets out of the diff.

Do not commit:

- `android/local.properties`, keystores, `.env`, or `LONGRIVER_IMAGE_KEY`
- `content/dist/media/`, `content/dist/detail-art/`, or the Wikidata cache in `content/raw/`
- `backend/db.sqlite3`

Wikidata entries in China after 1949 stay in the held batch `china-1949-plus` and are not written into the package.

## Regenerating the package

When the knowledge itself changes:

```powershell
python content/build_wikidata.py
python content/build_android_package.py
```

Include the regenerated `content/dist/knowledge-package.json` in the same change. The browser and the phone both read that file.

## Checks

From `web/`:

```powershell
npx vue-tsc --noEmit
```

When the phone app or the shared package changes, from `android/`:

```powershell
.\gradlew.bat :app:assembleDebug
```
