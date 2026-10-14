package app.changhe.data

import androidx.room.Dao
import androidx.room.Database
import androidx.room.Entity
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.PrimaryKey
import androidx.room.Query
import androidx.room.RoomDatabase
import androidx.room.migration.Migration
import androidx.sqlite.db.SupportSQLiteDatabase
import kotlinx.coroutines.flow.Flow

@Entity(tableName = "claims")
data class ClaimEntity(
    @PrimaryKey val id: Long,
    val text: String,
    val certainty: String,
    val timeLabel: String,
    val startYear: Int,
    val endYear: Int,
    val regionIds: String,
    val topicSlugs: String,
    val eventId: Long?,
    val snapshotId: Long?,
    val citationsJson: String,
    val searchText: String,
    val brief: String = "",
)

@Entity(tableName = "regions")
data class RegionEntity(
    @PrimaryKey val id: Long,
    val slug: String,
    val name: String,
    val sortOrder: Int,
    val parentId: Long? = null,
    val latitude: Double = 0.0,
    val longitude: Double = 0.0,
    val level: String = "region",
    val politySpans: String = "",
    val description: String = "",
    val image: String = "",
    val imageCredit: String = "",
)

@Entity(tableName = "topics")
data class TopicEntity(
    @PrimaryKey val slug: String,
    val name: String,
)

@Entity(tableName = "events")
data class EventEntity(
    @PrimaryKey val id: Long,
    val title: String,
    val timeLabel: String,
    val personIds: String,
)

@Entity(tableName = "people")
data class PersonEntity(
    @PrimaryKey val id: Long,
    val name: String,
    val birthYear: Int? = null,
    val deathYear: Int? = null,
    val description: String = "",
    val regionId: Long? = null,
    val image: String = "",
    val imageCredit: String = "",
    val wikidataId: String = "",
)

@Entity(tableName = "snapshots")
data class SnapshotEntity(
    @PrimaryKey val id: Long,
    val label: String,
    val timeLabel: String,
)

object BookmarkKind {
    const val CLAIM = "claim"
    const val PERSON = "person"
    const val PLACE = "place"
    const val POLITY = "polity"
}

@Entity(tableName = "bookmarks", primaryKeys = ["kind", "targetId"])
data class BookmarkEntity(
    val kind: String,
    val targetId: Long,
    val note: String,
    val updatedAt: Long,
)

@Entity(tableName = "sync_meta")
data class SyncMetaEntity(
    @PrimaryKey val id: Int = 1,
    val version: Int,
)

@Dao
interface KnowledgeDao {
    @Query("SELECT * FROM claims ORDER BY startYear, id")
    fun observeClaims(): Flow<List<ClaimEntity>>

    @Query("SELECT * FROM events")
    fun observeEvents(): Flow<List<EventEntity>>

    @Query("SELECT * FROM people ORDER BY name")
    fun observePeople(): Flow<List<PersonEntity>>

    @Query("SELECT * FROM claims WHERE startYear <= :year AND endYear >= :year ORDER BY id")
    fun observeForYear(year: Int): Flow<List<ClaimEntity>>

    @Query("SELECT * FROM claims WHERE searchText LIKE '%' || :query || '%' ORDER BY id")
    fun search(query: String): Flow<List<ClaimEntity>>

    @Query("SELECT * FROM claims WHERE id = :id")
    fun observeClaim(id: Long): Flow<ClaimEntity?>

    @Query("SELECT * FROM regions ORDER BY sortOrder, name")
    fun observeRegions(): Flow<List<RegionEntity>>

    @Query("SELECT * FROM topics ORDER BY name")
    fun observeTopics(): Flow<List<TopicEntity>>

    @Query("SELECT * FROM events WHERE id = :id")
    suspend fun event(id: Long): EventEntity?

    @Query("SELECT * FROM people WHERE id = :id")
    suspend fun person(id: Long): PersonEntity?

    @Query("SELECT * FROM snapshots")
    fun observeSnapshots(): Flow<List<SnapshotEntity>>

    @Query("SELECT * FROM snapshots WHERE id = :id")
    suspend fun snapshot(id: Long): SnapshotEntity?

    @Query("SELECT * FROM bookmarks ORDER BY updatedAt DESC")
    fun observeBookmarks(): Flow<List<BookmarkEntity>>

    @Query("SELECT * FROM bookmarks WHERE kind = :kind AND targetId = :targetId")
    fun observeBookmark(kind: String, targetId: Long): Flow<BookmarkEntity?>

    @Query("SELECT version FROM sync_meta WHERE id = 1")
    suspend fun version(): Int?

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertClaims(rows: List<ClaimEntity>)

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertRegions(rows: List<RegionEntity>)

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertTopics(rows: List<TopicEntity>)

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertEvents(rows: List<EventEntity>)

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertPeople(rows: List<PersonEntity>)

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertSnapshots(rows: List<SnapshotEntity>)

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertBookmark(row: BookmarkEntity)

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertMeta(row: SyncMetaEntity)

    @Query("DELETE FROM claims")
    suspend fun clearClaims()

    @Query("DELETE FROM regions")
    suspend fun clearRegions()

    @Query("DELETE FROM topics")
    suspend fun clearTopics()

    @Query("DELETE FROM events")
    suspend fun clearEvents()

    @Query("DELETE FROM people")
    suspend fun clearPeople()

    @Query("DELETE FROM snapshots")
    suspend fun clearSnapshots()

    @Query("DELETE FROM claims WHERE id IN (:ids)")
    suspend fun deleteClaims(ids: List<Long>)

    @Query("DELETE FROM bookmarks WHERE kind = :kind AND targetId = :targetId")
    suspend fun deleteBookmark(kind: String, targetId: Long)
}

internal fun ClaimPayload.toEntity(searchText: String) = ClaimEntity(
    id = id,
    text = text,
    certainty = certainty,
    timeLabel = time_label,
    startYear = start_year,
    endYear = end_year,
    regionIds = region_ids.joinToString(","),
    topicSlugs = topic_slugs.joinToString(","),
    eventId = event_id,
    snapshotId = snapshot_id,
    searchText = searchText,
    citationsJson = citations.joinToString("\n") { citation ->
        listOf(
            citation.source_title,
            citation.edition_label,
            citation.locator,
            citation.stable_url,
        ).joinToString(" | ")
    },
    brief = brief,
)

fun ClaimEntity.regionIdList(): Set<Long> =
    regionIds.split(",").filter { it.isNotBlank() }.map { it.toLong() }.toSet()

fun ClaimEntity.topicSlugList(): Set<String> =
    topicSlugs.split(",").filter { it.isNotBlank() }.toSet()

@Database(
    entities = [
        ClaimEntity::class,
        RegionEntity::class,
        TopicEntity::class,
        EventEntity::class,
        PersonEntity::class,
        SnapshotEntity::class,
        BookmarkEntity::class,
        SyncMetaEntity::class,
    ],
    version = 5,
    exportSchema = false,
)
abstract class KnowledgeDatabase : RoomDatabase() {
    abstract fun dao(): KnowledgeDao
}

val MIGRATION_1_2 = object : Migration(1, 2) {
    override fun migrate(db: SupportSQLiteDatabase) {
        db.execSQL("ALTER TABLE regions ADD COLUMN parentId INTEGER")
        db.execSQL("ALTER TABLE regions ADD COLUMN latitude REAL NOT NULL DEFAULT 0")
        db.execSQL("ALTER TABLE regions ADD COLUMN longitude REAL NOT NULL DEFAULT 0")
        db.execSQL("ALTER TABLE regions ADD COLUMN level TEXT NOT NULL DEFAULT 'region'")
    }
}

val MIGRATION_2_3 = object : Migration(2, 3) {
    override fun migrate(db: SupportSQLiteDatabase) {
        db.execSQL("ALTER TABLE regions ADD COLUMN politySpans TEXT NOT NULL DEFAULT ''")
    }
}

val MIGRATION_3_4 = object : Migration(3, 4) {
    override fun migrate(db: SupportSQLiteDatabase) {
        listOf("description", "image", "imageCredit").forEach {
            db.execSQL("ALTER TABLE regions ADD COLUMN $it TEXT NOT NULL DEFAULT ''")
        }
        db.execSQL("ALTER TABLE people ADD COLUMN birthYear INTEGER")
        db.execSQL("ALTER TABLE people ADD COLUMN deathYear INTEGER")
        db.execSQL("ALTER TABLE people ADD COLUMN regionId INTEGER")
        listOf("description", "image", "imageCredit", "wikidataId").forEach {
            db.execSQL("ALTER TABLE people ADD COLUMN $it TEXT NOT NULL DEFAULT ''")
        }
        db.execSQL(
            "CREATE TABLE bookmarks_new (kind TEXT NOT NULL, targetId INTEGER NOT NULL, " +
                "note TEXT NOT NULL, updatedAt INTEGER NOT NULL, PRIMARY KEY(kind, targetId))",
        )
        db.execSQL(
            "INSERT INTO bookmarks_new (kind, targetId, note, updatedAt) " +
                "SELECT 'claim', claimId, note, updatedAt FROM bookmarks",
        )
        db.execSQL("DROP TABLE bookmarks")
        db.execSQL("ALTER TABLE bookmarks_new RENAME TO bookmarks")
    }
}

val MIGRATION_4_5 = object : Migration(4, 5) {
    override fun migrate(db: SupportSQLiteDatabase) {
        db.execSQL("ALTER TABLE claims ADD COLUMN brief TEXT NOT NULL DEFAULT ''")
    }
}

fun RegionEntity.politiesAt(year: Int): Set<Long> =
    politySpans.split(";").filter { it.isNotBlank() }.mapNotNull { span ->
        val (from, to, pid) = span.split(":").map { it.toInt() }
        if (year in from..to) pid.toLong() else null
    }.toSet()
