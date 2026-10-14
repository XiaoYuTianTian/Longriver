package app.longriver.data

import android.content.Context
import androidx.room.Room
import androidx.room.withTransaction
import java.net.HttpURLConnection
import java.net.URL
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

class KnowledgeRepository(context: Context, private val baseUrl: String) {
    private val database = Room.databaseBuilder(
        context.applicationContext,
        KnowledgeDatabase::class.java,
        "longriver.db",
    ).addMigrations(MIGRATION_1_2, MIGRATION_2_3, MIGRATION_3_4, MIGRATION_4_5).build()
    private val dao = database.dao()
    private val prefs = context.applicationContext.getSharedPreferences("seed", Context.MODE_PRIVATE)

    fun claims() = dao.observeClaims()
    fun events() = dao.observeEvents()
    fun people() = dao.observePeople()
    fun claimsForYear(year: Int) = dao.observeForYear(year)
    fun search(query: String) = dao.search(query)
    fun claim(id: Long) = dao.observeClaim(id)
    fun regions() = dao.observeRegions()
    fun topics() = dao.observeTopics()
    fun bookmarks() = dao.observeBookmarks()
    fun snapshots() = dao.observeSnapshots()
    fun bookmark(kind: String, targetId: Long) = dao.observeBookmark(kind, targetId)
    suspend fun event(id: Long) = dao.event(id)
    suspend fun snapshot(id: Long) = dao.snapshot(id)

    suspend fun peopleForEvent(eventId: Long?): List<PersonEntity> {
        val ids = eventId?.let { dao.event(it)?.personIds }.orEmpty()
        return ids.split(",").mapNotNull { it.trim().toLongOrNull() }.mapNotNull { dao.person(it) }
    }

    /** Imports the bundled package once per app build unless a synced package already replaced it. */
    suspend fun ensureSeeded(seedKey: Int, readSeed: () -> String) = withContext(Dispatchers.IO) {
        val localVersion = dao.version()
        val seeded = prefs.getInt("seed_key", -1) == seedKey
        if (localVersion == null || (localVersion == 0 && !seeded)) {
            apply(PackageParser.parse(readSeed()), replaceAll = true)
            prefs.edit().putInt("seed_key", seedKey).apply()
        }
    }

    suspend fun saveBookmark(kind: String, targetId: Long, note: String) {
        dao.insertBookmark(BookmarkEntity(kind, targetId, note.trim(), System.currentTimeMillis()))
    }

    suspend fun removeBookmark(kind: String, targetId: Long) {
        dao.deleteBookmark(kind, targetId)
    }

    suspend fun sync() = withContext(Dispatchers.IO) {
        val remoteVersion = PackageParser.parseVersion(get("/api/v1/content/version/"))
        val localVersion = dao.version() ?: 0
        if (remoteVersion == 0 || remoteVersion <= localVersion) {
            return@withContext
        }
        val raw = get("/api/v1/content/packages/?since=$localVersion")
        val parsed = PackageParser.parse(raw)
        apply(parsed, replaceAll = parsed.full)
    }

    private suspend fun apply(parsed: KnowledgePackage, replaceAll: Boolean) {
        database.withTransaction {
            if (replaceAll) {
                dao.clearClaims()
                dao.clearRegions()
                dao.clearTopics()
                dao.clearEvents()
                dao.clearPeople()
                dao.clearSnapshots()
            }
            if (parsed.removed_claim_ids.isNotEmpty()) {
                dao.deleteClaims(parsed.removed_claim_ids)
            }
            val regionsById = parsed.regions.associateBy { it.id }
            val topicsBySlug = parsed.topics.associateBy { it.slug }
            val eventsById = parsed.events.associateBy { it.id }
            val snapshotsById = parsed.snapshots.associateBy { it.id }
            val peopleById = parsed.people.associateBy { it.id }
            dao.insertRegions(
                parsed.regions.map {
                    RegionEntity(
                        it.id,
                        it.slug,
                        it.name,
                        it.sort_order,
                        it.parent_id,
                        it.latitude,
                        it.longitude,
                        it.level,
                        it.polity_spans.joinToString(";") { span -> span.joinToString(":") },
                        it.description,
                        it.image,
                        it.image_credit,
                    )
                },
            )
            dao.insertTopics(parsed.topics.map { TopicEntity(it.slug, it.name) })
            dao.insertPeople(
                parsed.people.map {
                    PersonEntity(
                        it.id,
                        it.name,
                        it.birth_year,
                        it.death_year,
                        it.description,
                        it.region_id,
                        it.image,
                        it.image_credit,
                        it.wikidata,
                    )
                },
            )
            dao.insertEvents(
                parsed.events.map {
                    EventEntity(it.id, it.title, it.time_label, it.person_ids.joinToString(","))
                },
            )
            dao.insertSnapshots(parsed.snapshots.map { SnapshotEntity(it.id, it.label, it.time_label) })
            dao.insertClaims(
                parsed.claims.map { claim ->
                    claim.toEntity(
                        searchText(
                            claim,
                            regionsById,
                            topicsBySlug,
                            eventsById,
                            snapshotsById,
                            peopleById,
                        ),
                    )
                },
            )
            dao.insertMeta(SyncMetaEntity(version = parsed.version))
        }
    }

    suspend fun sendFeedback(claimId: Long?, message: String) = withContext(Dispatchers.IO) {
        val body = buildString {
            append("{\"message\":")
            append(jsonString(message))
            if (claimId != null) {
                append(",\"claim_id\":")
                append(claimId)
            }
            append("}")
        }
        post("/api/v1/feedback/", body)
    }

    private fun get(path: String): String = request(path, "GET", null)

    private fun post(path: String, body: String): String = request(path, "POST", body)

    private fun request(path: String, method: String, body: String?): String {
        val connection = URL(baseUrl.trimEnd('/') + path).openConnection() as HttpURLConnection
        connection.requestMethod = method
        connection.connectTimeout = 8000
        connection.readTimeout = 8000
        connection.setRequestProperty("Accept", "application/json")
        if (body != null) {
            connection.doOutput = true
            connection.setRequestProperty("Content-Type", "application/json")
            connection.outputStream.use { it.write(body.toByteArray()) }
        }
        val stream = if (connection.responseCode in 200..299) {
            connection.inputStream
        } else {
            error("服务器返回 ${connection.responseCode}")
        }
        return stream.bufferedReader().use { it.readText() }
    }

    private fun jsonString(value: String): String =
        "\"" + value.replace("\\", "\\\\").replace("\"", "\\\"") + "\""

    private fun searchText(
        claim: ClaimPayload,
        regionsById: Map<Long, RegionPayload>,
        topicsBySlug: Map<String, TopicPayload>,
        eventsById: Map<Long, EventPayload>,
        snapshotsById: Map<Long, SnapshotPayload>,
        peopleById: Map<Long, PersonPayload>,
    ): String {
        val event = claim.event_id?.let { eventsById[it] }
        val snapshot = claim.snapshot_id?.let { snapshotsById[it] }
        val people = event?.person_ids.orEmpty().mapNotNull { peopleById[it]?.name }
        val regions = claim.region_ids.mapNotNull { regionsById[it]?.name }
        val topics = claim.topic_slugs.mapNotNull { topicsBySlug[it]?.name }
        return listOf(claim.text, claim.brief, event?.title, snapshot?.label)
            .filterNotNull()
            .plus(people)
            .plus(regions)
            .plus(topics)
            .joinToString(" ")
    }
}
