package app.longriver.data

import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json

@Serializable
data class KnowledgePackage(
    val version: Int,
    val full: Boolean = true,
    val claims: List<ClaimPayload> = emptyList(),
    val removed_claim_ids: List<Long> = emptyList(),
    val regions: List<RegionPayload> = emptyList(),
    val topics: List<TopicPayload> = emptyList(),
    val events: List<EventPayload> = emptyList(),
    val snapshots: List<SnapshotPayload> = emptyList(),
    val people: List<PersonPayload> = emptyList(),
    val polities: List<PolityPayload> = emptyList(),
)

@Serializable
data class ClaimPayload(
    val id: Long,
    val text: String,
    val certainty: String,
    val time_label: String,
    val start_year: Int,
    val end_year: Int,
    val region_ids: List<Long> = emptyList(),
    val topic_slugs: List<String> = emptyList(),
    val event_id: Long? = null,
    val snapshot_id: Long? = null,
    val citations: List<CitationPayload> = emptyList(),
    val brief: String = "",
)

@Serializable
data class CitationPayload(
    val id: Long,
    val source_title: String,
    val edition_label: String,
    val locator: String = "",
    val quotation: String = "",
    val stable_url: String = "",
)

@Serializable
data class RegionPayload(
    val id: Long,
    val slug: String,
    val name: String,
    val sort_order: Int = 0,
    val parent_id: Long? = null,
    val latitude: Double = 0.0,
    val longitude: Double = 0.0,
    val level: String = "region",
    val polity_spans: List<List<Int>> = emptyList(),
    val description: String = "",
    val image: String = "",
    val image_credit: String = "",
)

@Serializable
data class TopicPayload(val slug: String, val name: String)

@Serializable
data class EventPayload(
    val id: Long,
    val title: String,
    val time_label: String,
    val person_ids: List<Long> = emptyList(),
)

@Serializable
data class SnapshotPayload(val id: Long, val label: String, val time_label: String)

@Serializable
data class PersonPayload(
    val id: Long,
    val name: String,
    val birth_year: Int? = null,
    val death_year: Int? = null,
    val description: String = "",
    val region_id: Long? = null,
    val image: String = "",
    val image_credit: String = "",
    val wikidata: String = "",
)

@Serializable
data class PolityPayload(val id: Long, val name: String, val slug: String)

@Serializable
data class VersionResponse(val version: Int)

object PackageParser {
    private val json = Json { ignoreUnknownKeys = true }

    fun parse(raw: String): KnowledgePackage = json.decodeFromString(raw)

    fun parseVersion(raw: String): Int = json.decodeFromString<VersionResponse>(raw).version
}
