import { ref } from 'vue'
import type { Bookmark, BookmarkKind } from './types'

const DB_NAME = 'longriver'
const STORE = 'bookmarks'

export const bookmarks = ref<Bookmark[]>([])

function bookmarkId(kind: BookmarkKind, targetId: number): string {
  return `${kind}:${targetId}`
}

function openDb(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, 1)
    request.onupgradeneeded = () => {
      const db = request.result
      if (!db.objectStoreNames.contains(STORE)) db.createObjectStore(STORE, { keyPath: 'id' })
    }
    request.onsuccess = () => resolve(request.result)
    request.onerror = () => reject(request.error)
  })
}

function requestToPromise<T>(request: IDBRequest<T>): Promise<T> {
  return new Promise((resolve, reject) => {
    request.onsuccess = () => resolve(request.result)
    request.onerror = () => reject(request.error)
  })
}

async function readAll(): Promise<Bookmark[]> {
  const db = await openDb()
  const rows = await requestToPromise(db.transaction(STORE).objectStore(STORE).getAll())
  db.close()
  return (rows as Bookmark[]).sort((left, right) => right.updatedAt - left.updatedAt)
}

export async function refreshBookmarks(): Promise<void> {
  bookmarks.value = await readAll()
}

export async function saveBookmark(kind: BookmarkKind, targetId: number, note: string): Promise<void> {
  const db = await openDb()
  const row: Bookmark = {
    id: bookmarkId(kind, targetId),
    kind,
    targetId,
    note: note.trim(),
    updatedAt: Date.now(),
  }
  await requestToPromise(db.transaction(STORE, 'readwrite').objectStore(STORE).put(row))
  db.close()
  await refreshBookmarks()
}

export async function removeBookmark(kind: BookmarkKind, targetId: number): Promise<void> {
  const db = await openDb()
  await requestToPromise(db.transaction(STORE, 'readwrite').objectStore(STORE).delete(bookmarkId(kind, targetId)))
  db.close()
  await refreshBookmarks()
}

export function findBookmark(kind: BookmarkKind, targetId: number): Bookmark | undefined {
  return bookmarks.value.find((row) => row.kind === kind && row.targetId === targetId)
}
