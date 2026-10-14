package app.longriver

import app.longriver.data.ClaimEntity
import app.longriver.data.PersonEntity
import app.longriver.data.RegionEntity
import app.longriver.data.regionIdList
import app.longriver.data.topicSlugList
import kotlin.math.abs

private val levelRank = mapOf("region" to 0, "country" to 1, "province" to 2, "city" to 3)

private var indexedList: List<RegionEntity>? = null
private var indexedById: Map<Long, RegionEntity> = emptyMap()

/** The region list is replaced wholesale on sync, so caching by identity stays correct. */
internal fun regionIndex(regions: List<RegionEntity>): Map<Long, RegionEntity> = synchronized(levelRank) {
    if (indexedList !== regions) {
        indexedById = regions.associateBy { it.id }
        indexedList = regions
    }
    indexedById
}

internal fun RegionEntity.ancestors(regions: List<RegionEntity>): List<RegionEntity> {
    val byId = regionIndex(regions)
    val chain = ArrayDeque<RegionEntity>()
    var current: RegionEntity? = this
    while (current != null) {
        chain.addFirst(current)
        current = current.parentId?.let { byId[it] }
    }
    return chain.toList()
}

internal fun RegionEntity.root(regions: List<RegionEntity>): RegionEntity = ancestors(regions).first()

internal fun RegionEntity.containsPlace(placeId: Long, regions: List<RegionEntity>): Boolean {
    val byId = regionIndex(regions)
    var current = byId[placeId]
    while (current != null) {
        if (current.id == id) return true
        current = current.parentId?.let { byId[it] }
    }
    return false
}

internal fun rollupPlace(place: RegionEntity, targetRank: Int, byId: Map<Long, RegionEntity>): RegionEntity {
    var current = place
    while ((levelRank[current.level] ?: 0) > targetRank) {
        val parent = current.parentId?.let { byId[it] } ?: break
        if ((levelRank[parent.level] ?: 0) < 1) break
        current = parent
    }
    return current
}

internal fun zoomRank(zoom: Double): Int = when {
    zoom < 2.6 -> 1
    zoom < 4.4 -> 2
    else -> 3
}

/** A claim belongs to a selected span when the two intervals overlap. */
internal fun ClaimEntity.overlaps(start: Int, end: Int): Boolean = startYear <= end && endYear >= start

internal fun PersonEntity.visibleDuring(start: Int, end: Int): Boolean {
    val birth = birthYear ?: return false
    val death = deathYear ?: return birth in start..end
    return birth <= end && death >= start
}

/** Claims whose place is this region or one of its descendants. */
internal fun claimsInPlace(
    claims: List<ClaimEntity>,
    place: RegionEntity,
    regions: List<RegionEntity>,
): List<ClaimEntity> = claims.filter { claim -> claim.regionIdList().any { place.containsPlace(it, regions) } }

internal fun eventCount(claims: List<ClaimEntity>): Int = claims.mapNotNull { it.eventId }.distinct().size

internal fun frameZoom(level: String): Double = when (level) {
    "region" -> 2.0
    "country" -> 3.2
    "province" -> 5.0
    else -> 6.5
}

/** Wider than the atlas close-up, so a detail map shows the place inside its region. */
internal fun detailZoom(level: String): Double = when (level) {
    "region" -> 1.35
    "country" -> 2.3
    "province" -> 3.4
    else -> 4.2
}

/** Other recorded places in the same country, nearest first, for the detail map. */
internal fun contextPlaces(place: RegionEntity, regions: List<RegionEntity>, limit: Int = 16): List<RegionEntity> {
    val rootId = place.root(regions).id
    return regions.asSequence()
        .filter { it.id != place.id && it.latitude != 0.0 && it.longitude != 0.0 }
        .filter { it.root(regions).id == rootId }
        .sortedBy { squaredDistance(it, place) }
        .take(limit)
        .toList()
}

internal data class BriefBlock(val heading: String, val text: String)

/** Detail copy is either a plain paragraph or a §heading followed by its paragraph. */
internal fun parseBrief(brief: String): List<BriefBlock> {
    if (brief.isBlank()) return emptyList()
    return brief.split("\n\n").mapNotNull { raw ->
        val block = raw.trim()
        if (block.isEmpty()) return@mapNotNull null
        val lines = block.lines()
        if (lines.first().startsWith("§")) {
            val body = lines.drop(1).joinToString("\n").trim()
            if (body.isEmpty()) null else BriefBlock(lines.first().removePrefix("§").trim(), body)
        } else {
            BriefBlock("", block)
        }
    }
}

/** Birth sentences rank after wars, treaties, and works when several events share a year. */
internal fun ClaimEntity.archiveRank(): Int = when {
    "出生" in text -> 2
    topicSlugList().any { it == "politics" || it == "culture" || it == "technology" } -> 0
    else -> 1
}

internal fun yearGap(left: ClaimEntity, right: ClaimEntity): Int {
    if (left.endYear >= right.startYear && right.endYear >= left.startYear) return 0
    return if (left.endYear < right.startYear) right.startYear - left.endYear else left.startYear - right.endYear
}

/** Other claims at the same place whose years fall within 30 years. */
internal fun samePlaceClaims(current: ClaimEntity, claims: List<ClaimEntity>, limit: Int = 6): List<ClaimEntity> {
    val regions = current.regionIdList()
    if (regions.isEmpty()) return emptyList()
    return claims.asSequence()
        .filter { it.id != current.id && it.regionIdList().intersect(regions).isNotEmpty() }
        .filter { yearGap(current, it) <= 30 }
        .sortedWith(compareBy({ yearGap(current, it) }, { it.endYear - it.startYear }, { it.archiveRank() }, { it.startYear }, { it.id }))
        .take(limit)
        .toList()
}

/** Overlapping claims at a different place. Wars, treaties, and works come before births. */
internal fun contemporaryClaims(current: ClaimEntity, claims: List<ClaimEntity>, limit: Int = 4): List<ClaimEntity> {
    val regions = current.regionIdList()
    return claims.asSequence()
        .filter { it.id != current.id && it.overlaps(current.startYear, current.endYear) }
        .filter { it.regionIdList().intersect(regions).isEmpty() }
        .sortedWith(
            compareBy(
                { it.archiveRank() },
                { abs(it.startYear - current.startYear) },
                { it.endYear - it.startYear },
                { it.id },
            ),
        )
        .take(limit)
        .toList()
}

private fun squaredDistance(a: RegionEntity, b: RegionEntity): Double {
    val dx = a.longitude - b.longitude
    val dy = a.latitude - b.latitude
    return dx * dx + dy * dy
}
