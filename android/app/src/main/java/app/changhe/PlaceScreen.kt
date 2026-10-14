@file:OptIn(ExperimentalMaterial3Api::class)

package app.changhe

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Card
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import app.changhe.data.BookmarkKind
import app.changhe.data.ClaimEntity
import app.changhe.data.EventEntity
import app.changhe.data.PersonEntity
import app.changhe.data.RegionEntity
import app.changhe.data.regionIdList

@Composable
internal fun PlaceResults(
    section: String,
    region: RegionEntity,
    regions: List<RegionEntity>,
    claims: List<ClaimEntity>,
    events: List<EventEntity>,
    people: List<PersonEntity>,
    rangeStart: Int,
    rangeEnd: Int,
    openClaim: (Long) -> Unit,
    openPerson: (Long) -> Unit,
    openPiece: (String) -> Unit,
    modifier: Modifier,
) {
    val inside = remember(region, regions) { regions.filter { region.containsPlace(it.id, regions) }.map { it.id }.toSet() }
    val regionClaims = remember(claims, inside, rangeStart, rangeEnd) {
        claims.filter { claim -> claim.overlaps(rangeStart, rangeEnd) && claim.regionIdList().any { it in inside } }
            .sortedBy { it.startYear }
    }
    val firstClaimByEvent = remember(regionClaims) {
        regionClaims.filter { it.eventId != null }.groupBy { it.eventId!! }.mapValues { it.value.first() }
    }
    val regionEvents = remember(events, firstClaimByEvent) {
        events.filter { it.id in firstClaimByEvent }.sortedBy { firstClaimByEvent[it.id]?.startYear ?: 0 }
    }
    val regionPeople = remember(people, regionEvents, inside, rangeStart, rangeEnd) {
        val personIds = regionEvents.flatMap { it.personIdList() }.toSet()
        people.filter { person ->
            person.id in personIds || (person.regionId in inside && person.visibleDuring(rangeStart, rangeEnd))
        }.sortedBy { it.birthYear ?: Int.MAX_VALUE }
    }
    val ancestorSlugs = region.ancestors(regions).map { it.slug }.toSet()
    val descendantSlugs = regions.filter { it.id in inside }.map { it.slug }.toSet()
    val pieces = readingPieces.filter { (it.regionSlug in ancestorSlugs || it.regionSlug in descendantSlugs) && it.kind == section }
    LazyColumn(modifier, verticalArrangement = Arrangement.spacedBy(8.dp), contentPadding = PaddingValues(bottom = 24.dp)) {
        when (section) {
            "event" -> {
                if (regionEvents.isEmpty()) item { EmptyLine("这一地区还没有收录事件。") }
                items(regionEvents, key = { it.id }) { event ->
                    val claim = firstClaimByEvent[event.id]
                    ReadOnlyCard(event.title, event.timeLabel) { claim?.let { openClaim(it.id) } }
                }
            }
            "person" -> {
                if (regionPeople.isEmpty()) item { EmptyLine("这一地区还没有收录人物。") }
                items(regionPeople, key = { it.id }) { person ->
                    PersonRow(person, openPerson)
                }
            }
            else -> {
                if (pieces.isEmpty()) item { EmptyLine(if (section == "verse") "这一地区还没有收录诗句。" else "这一地区还没有收录著作。") }
                items(pieces, key = { it.id }) { piece ->
                    ReadOnlyCard(piece.title, "${piece.author} · ${piece.yearLabel}") { openPiece(piece.id) }
                }
            }
        }
    }
}

@Composable
private fun ReadOnlyCard(title: String, subtitle: String, onClick: () -> Unit) {
    Card(onClick = onClick, modifier = Modifier.fillMaxWidth()) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
            Text(title, style = MaterialTheme.typography.titleMedium)
            Text(subtitle, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
    }
}

@Composable
private fun PersonRow(person: PersonEntity, openPerson: (Long) -> Unit) {
    Card(onClick = { openPerson(person.id) }, modifier = Modifier.fillMaxWidth()) {
        Row(Modifier.padding(12.dp), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            Avatar(person.name, person.image, 44.dp)
            Column(verticalArrangement = Arrangement.spacedBy(2.dp)) {
                Text(person.name, style = MaterialTheme.typography.titleMedium)
                Text(
                    lifeSpan(person.birthYear, person.deathYear) ?: "查看相关记述",
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
        }
    }
}

@Composable
private fun EmptyLine(text: String) {
    Text(text, color = MaterialTheme.colorScheme.onSurfaceVariant, modifier = Modifier.padding(vertical = 8.dp))
}

@Composable
fun ReadingPieceScreen(pieceId: String) {
    val piece = readingPieces.firstOrNull { it.id == pieceId }
    if (piece == null) {
        Text("没有找到这篇。", modifier = Modifier.padding(24.dp))
        return
    }
    Column(
        Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(24.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Text(piece.yearLabel, color = MaterialTheme.colorScheme.primary)
        Text(piece.title, style = MaterialTheme.typography.headlineSmall)
        Text(piece.author, color = MaterialTheme.colorScheme.onSurfaceVariant)
        Text(piece.body, style = MaterialTheme.typography.bodyLarge)
    }
}

@Composable
fun PersonScreen(model: ChangheViewModel, personId: Long, openClaim: (Long) -> Unit, goAtlas: () -> Unit) {
    val people by model.allPeople.collectAsState()
    val events by model.allEvents.collectAsState()
    val claims by model.allClaims.collectAsState()
    val regions by model.regions.collectAsState()
    val bookmark by model.bookmark(BookmarkKind.PERSON, personId).collectAsState(initial = null)
    val person = people.firstOrNull { it.id == personId }
    if (person == null) {
        Text("没有找到这位人物。", modifier = Modifier.padding(24.dp))
        return
    }
    val related = remember(events, claims, personId) {
        val eventIds = events.filter { personId in it.personIdList() }.map { it.id }.toSet()
        claims.filter { it.eventId in eventIds }.sortedBy { it.startYear }
    }
    val place = person.regionId?.let { regionIndex(regions)[it] }
    val mapYear = person.birthYear ?: related.firstOrNull()?.startYear
    LazyColumn(
        Modifier.fillMaxSize(),
        contentPadding = PaddingValues(20.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp),
    ) {
        item {
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(16.dp)) {
                Avatar(person.name, person.image, 88.dp)
                Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {
                    Text(person.name, style = MaterialTheme.typography.headlineSmall)
                    lifeSpan(person.birthYear, person.deathYear)?.let {
                        Text(it, style = MaterialTheme.typography.titleSmall, color = MaterialTheme.colorScheme.primary)
                    }
                    place?.let {
                        Text("生于${it.name}", color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                }
            }
        }
        if (person.imageCredit.isNotBlank()) {
            item {
                Text(
                    "头像：${person.imageCredit}",
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
        }
        item {
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                BookmarkButton(bookmark != null) { model.toggleBookmark(BookmarkKind.PERSON, personId, bookmark != null) }
                if (place != null && mapYear != null) {
                    TextButton(onClick = {
                        model.showOnMap(
                            mapYear.coerceIn(TIMELINE_START, TIMELINE_END),
                            place.longitude,
                            place.latitude,
                            frameZoom(place.level),
                            AtlasFocus.Place(place.id),
                        )
                        goAtlas()
                    }) { Text("在地图上看 ${formatYear(mapYear)}") }
                }
            }
        }
        if (person.description.isNotBlank()) {
            item { Text(person.description, style = MaterialTheme.typography.bodyLarge) }
            item {
                Text(
                    "简介摘自维基百科（CC BY-SA 4.0）及维基数据（CC0）。",
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
        }
        item { Text("生平记录", style = MaterialTheme.typography.titleMedium, modifier = Modifier.padding(top = 8.dp)) }
        if (related.isEmpty()) {
            item { EmptyLine("还没有与这位人物相连的记述。") }
        }
        items(related, key = { it.id }) { claim ->
            Card(onClick = { openClaim(claim.id) }, modifier = Modifier.fillMaxWidth()) {
                Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                    Text(claim.timeLabel, style = MaterialTheme.typography.labelLarge, color = MaterialTheme.colorScheme.primary)
                    Text(claim.text, style = MaterialTheme.typography.bodyMedium)
                }
            }
        }
    }
}
