package app.longriver

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Star
import androidx.compose.material3.Card
import androidx.compose.material3.FilledTonalButton
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.SolidColor
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.graphics.vector.addPathNodes
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import app.longriver.data.BookmarkKind
import app.longriver.data.regionIdList

internal val BookmarkGold = Color(0xFFC9962B)

private val StarBorder: ImageVector = ImageVector.Builder("StarBorder", 24.dp, 24.dp, 24f, 24f).addPath(
    pathData = addPathNodes(
        "M22,9.24l-7.19,-0.62L12,2 9.19,8.63 2,9.24l5.46,4.73L5.82,21 12,17.27 18.18,21l-1.63,-7.03L22,9.24z" +
            "M12,15.4l-3.76,2.27 1,-4.28 -3.32,-2.88 4.38,-0.38L12,6.1l1.71,4.04 4.38,0.38 -3.32,2.88 1,4.28L12,15.4z",
    ),
    fill = SolidColor(Color.Black),
).build()

@Composable
internal fun BookmarkButton(bookmarked: Boolean, onToggle: () -> Unit) {
    if (bookmarked) {
        FilledTonalButton(onClick = onToggle) {
            Icon(Icons.Filled.Star, contentDescription = null, tint = BookmarkGold)
            Spacer(Modifier.width(6.dp))
            Text("已收藏")
        }
    } else {
        OutlinedButton(onClick = onToggle) {
            Icon(StarBorder, contentDescription = null)
            Spacer(Modifier.width(6.dp))
            Text("收藏")
        }
    }
}

@Composable
internal fun BookmarkIcon(bookmarked: Boolean, onToggle: () -> Unit) {
    IconButton(onClick = onToggle) {
        if (bookmarked) {
            Icon(Icons.Filled.Star, contentDescription = "取消收藏", tint = BookmarkGold)
        } else {
            Icon(StarBorder, contentDescription = "收藏")
        }
    }
}

private data class BookmarkRow(
    val kind: String,
    val targetId: Long,
    val title: String,
    val subtitle: String,
    val year: Int?,
    val open: () -> Unit,
    val showOnMap: (() -> Unit)?,
)

private val kindLabels = listOf(
    BookmarkKind.CLAIM to "事件",
    BookmarkKind.PERSON to "人物",
    BookmarkKind.PLACE to "地点",
    BookmarkKind.POLITY to "政权",
)

@Composable
internal fun BookmarkSection(
    model: LongriverViewModel,
    openClaim: (Long) -> Unit,
    openPerson: (Long) -> Unit,
    goAtlas: () -> Unit,
) {
    val context = LocalContext.current
    val index = remember { AtlasAssets.polities(context) }
    val bookmarks by model.bookmarks.collectAsState()
    val claims by model.allClaims.collectAsState()
    val people by model.allPeople.collectAsState()
    val regions by model.regions.collectAsState()
    val events by model.allEvents.collectAsState()
    val byId = regionIndex(regions)
    val claimsById = remember(claims) { claims.associateBy { it.id } }
    val peopleById = remember(people) { people.associateBy { it.id } }
    val eventTitles = remember(events) { events.associate { it.id to it.title } }

    fun jump(year: Int, lon: Double, lat: Double, zoom: Double, focus: AtlasFocus? = null) {
        model.showOnMap(year.coerceIn(TIMELINE_START, TIMELINE_END), lon, lat, zoom, focus)
        goAtlas()
    }

    val rows = bookmarks.mapNotNull { bookmark ->
        when (bookmark.kind) {
            BookmarkKind.CLAIM -> claimsById[bookmark.targetId]?.let { claim ->
                val place = claim.regionIdList().firstOrNull()?.let { byId[it] }
                BookmarkRow(
                    bookmark.kind, bookmark.targetId,
                    claim.eventId?.let { eventTitles[it] } ?: claim.text,
                    listOfNotNull(claim.timeLabel, place?.name).joinToString(" · "),
                    claim.startYear,
                    { openClaim(claim.id) },
                    place?.let { { jump(claim.startYear, it.longitude, it.latitude, frameZoom(it.level)) } },
                )
            }
            BookmarkKind.PERSON -> peopleById[bookmark.targetId]?.let { person ->
                val place = person.regionId?.let { byId[it] }
                val year = person.birthYear
                BookmarkRow(
                    bookmark.kind, bookmark.targetId, person.name,
                    listOfNotNull(lifeSpan(person.birthYear, person.deathYear), place?.name).joinToString(" · "),
                    year,
                    { openPerson(person.id) },
                    if (place != null && year != null) {
                        { jump(year, place.longitude, place.latitude, frameZoom(place.level)) }
                    } else {
                        null
                    },
                )
            }
            BookmarkKind.PLACE -> byId[bookmark.targetId]?.let { place ->
                val first = claims.firstOrNull { claim -> place.id in claim.regionIdList() }?.startYear
                BookmarkRow(
                    bookmark.kind, bookmark.targetId, place.name,
                    place.ancestors(regions).dropLast(1).joinToString(" / ") { it.name }.ifBlank { "世界" },
                    first,
                    { jump(model.rangeStart.value, place.longitude, place.latitude, frameZoom(place.level), AtlasFocus.Place(place.id)) },
                    { jump(model.rangeStart.value, place.longitude, place.latitude, frameZoom(place.level)) },
                )
            }
            BookmarkKind.POLITY -> index.polity(bookmark.targetId)?.let { polity ->
                val year = polity.from.coerceAtLeast(TIMELINE_START)
                val label = index.labelsAt(year).firstOrNull { it.polity.id == polity.id }
                BookmarkRow(
                    bookmark.kind, bookmark.targetId, polity.displayName,
                    "存续 ${formatSpan(polity.from, polity.to)}",
                    polity.from,
                    {
                        if (label != null) jump(year, label.lon, label.lat, 3.0, AtlasFocus.Polity(polity.id))
                    },
                    label?.let { { jump(year, it.lon, it.lat, 3.0) } },
                )
            }
            else -> null
        }
    }

    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Text("收藏", style = MaterialTheme.typography.titleMedium)
        if (rows.isEmpty()) {
            Text(
                "在事件、人物、地点或政权的卡片上点星标即可收藏。收藏只保存在本机，这里按类型和年份排好，点“在地图上看”会回到那一年、那个地方。",
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
        kindLabels.forEach { (kind, label) ->
            val group = rows.filter { it.kind == kind }.sortedBy { it.year ?: Int.MAX_VALUE }
            if (group.isEmpty()) return@forEach
            Text(
                "$label · ${group.size}",
                style = MaterialTheme.typography.labelLarge,
                color = MaterialTheme.colorScheme.primary,
                modifier = Modifier.padding(top = 4.dp),
            )
            group.forEach { row ->
                Card(onClick = row.open, modifier = Modifier.fillMaxWidth()) {
                    Row(Modifier.padding(start = 16.dp, end = 4.dp, top = 8.dp, bottom = 8.dp), verticalAlignment = Alignment.CenterVertically) {
                        Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {
                            Text(row.title, style = MaterialTheme.typography.titleSmall, maxLines = 2, overflow = TextOverflow.Ellipsis)
                            Text(row.subtitle, style = MaterialTheme.typography.labelMedium, color = MaterialTheme.colorScheme.onSurfaceVariant, maxLines = 1)
                        }
                        row.showOnMap?.let { TextButton(onClick = it) { Text("在地图上看") } }
                        BookmarkIcon(true) { model.toggleBookmark(row.kind, row.targetId, true) }
                    }
                }
            }
        }
    }
}

internal fun lifeSpan(birth: Int?, death: Int?): String? = when {
    birth == null && death == null -> null
    death == null -> "${formatYear(birth!!)}生 · 卒年未收录"
    birth == null -> "卒于${formatYear(death)}"
    else -> "${formatYear(birth)} – ${formatYear(death)}"
}
