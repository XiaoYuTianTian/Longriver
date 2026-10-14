@file:OptIn(ExperimentalMaterial3Api::class)

package app.longriver

import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Card
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilterChip
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import app.longriver.data.ClaimEntity
import app.longriver.data.EventEntity
import app.longriver.data.PersonEntity
import app.longriver.data.RegionEntity
import app.longriver.data.regionIdList

@Composable
fun BrowseScreen(
    model: LongriverViewModel,
    openClaim: (Long) -> Unit,
    openPerson: (Long) -> Unit,
    goAtlas: () -> Unit,
) {
    val claims by model.allClaims.collectAsState()
    val people by model.allPeople.collectAsState()
    val events by model.allEvents.collectAsState()
    val regions by model.regions.collectAsState()
    val byId = regionIndex(regions)
    var section by rememberSaveable { mutableStateOf("era") }
    var query by rememberSaveable { mutableStateOf("") }
    var limitToEra by rememberSaveable { mutableStateOf(false) }
    var eraStart by rememberSaveable { mutableStateOf(0) }
    var eraEnd by rememberSaveable { mutableStateOf(0) }
    var eraLabel by rememberSaveable { mutableStateOf("") }
    val needle = query.trim()
    Column(Modifier.fillMaxSize().padding(horizontal = 16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
        Text("浏览已收录的内容，不跟地图上的当前年份。", color = MaterialTheme.colorScheme.onSurfaceVariant)
        OutlinedTextField(
            value = query,
            onValueChange = { query = it },
            modifier = Modifier.fillMaxWidth(),
            singleLine = true,
            label = { Text("筛选") },
            placeholder = { Text("人名、事件、地点或时代") },
        )
        Row(
            Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()),
            horizontalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            listOf("era" to "时代", "person" to "人物", "event" to "事件", "place" to "地点").forEach { (id, label) ->
                FilterChip(selected = section == id, onClick = { section = id }, label = { Text(label) })
            }
        }
        LazyColumn(
            Modifier.weight(1f),
            verticalArrangement = Arrangement.spacedBy(8.dp),
            contentPadding = PaddingValues(bottom = 24.dp),
        ) {
            when (section) {
                "era" -> {
                    val eras = chinaEras
                    val matched = eras.filter { needle.isEmpty() || it.name.contains(needle) }
                    items(matched, key = { "${it.name}-${it.start}" }) { era ->
                        val count = claims.count { it.overlaps(era.start, era.end) }
                        val peopleCount = people.count { it.visibleDuring(era.start, era.end) }
                        Card(onClick = {
                            model.showOnMap(
                                era.start.coerceIn(TIMELINE_START, TIMELINE_END),
                                HOME_BROWSE_LON,
                                HOME_BROWSE_LAT,
                                1.2,
                                endYear = era.end.coerceIn(TIMELINE_START, TIMELINE_END),
                            )
                            goAtlas()
                        }, modifier = Modifier.fillMaxWidth()) {
                            Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                                Text(era.name, style = MaterialTheme.typography.titleMedium)
                                Text(
                                    "${formatSpan(era.start, era.end)} · ${count} 条记述 · ${peopleCount} 位人物",
                                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                                )
                                Row {
                                    TextButton(onClick = {
                                        model.showOnMap(era.start.coerceIn(TIMELINE_START, TIMELINE_END), HOME_BROWSE_LON, HOME_BROWSE_LAT, 1.2, endYear = era.end.coerceIn(TIMELINE_START, TIMELINE_END))
                                        goAtlas()
                                    }) { Text("在地图上看") }
                                    TextButton(onClick = {
                                        eraStart = era.start
                                        eraEnd = era.end
                                        eraLabel = era.name
                                        limitToEra = true
                                        section = "person"
                                    }) { Text("这个时代的人") }
                                }
                            }
                        }
                    }
                }
                "person" -> {
                    val pool = if (limitToEra) people.filter { it.visibleDuring(eraStart, eraEnd) } else people
                    val rows = pool.filter { needle.isEmpty() || it.name.contains(needle) }
                        .sortedWith(compareBy<PersonEntity> { it.birthYear ?: Int.MAX_VALUE }.thenBy { it.name })
                    if (limitToEra) {
                        item {
                            TextButton(onClick = { limitToEra = false }) { Text("显示全部人物，不限${eraLabel}") }
                        }
                    }
                    if (rows.isEmpty()) item { Text("没有匹配的人物。", color = MaterialTheme.colorScheme.onSurfaceVariant) }
                    items(rows, key = PersonEntity::id) { person ->
                        Card(onClick = { openPerson(person.id) }, modifier = Modifier.fillMaxWidth()) {
                            Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                                Text(person.name, style = MaterialTheme.typography.titleMedium)
                                Text(
                                    lifeSpan(person.birthYear, person.deathYear) ?: "人物",
                                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                                )
                            }
                        }
                    }
                }
                "event" -> {
                    val byEvent = events.associateBy { it.id }
                    val rows = claims.asSequence()
                        .filter { claim ->
                            needle.isEmpty() ||
                                claim.text.contains(needle) ||
                                byEvent[claim.eventId]?.title.orEmpty().contains(needle)
                        }
                        .sortedBy { it.startYear }
                        .toList()
                    if (rows.isEmpty()) item { Text("没有匹配的事件。", color = MaterialTheme.colorScheme.onSurfaceVariant) }
                    items(rows, key = ClaimEntity::id) { claim ->
                        EventBrowseRow(claim, byId, byEvent, openClaim, goAtlas, model)
                    }
                }
                else -> {
                    val rows = regions.filter { it.level != "region" && (needle.isEmpty() || it.name.contains(needle)) }
                        .sortedBy { it.sortOrder }
                    if (rows.isEmpty()) item { Text("没有匹配的地点。", color = MaterialTheme.colorScheme.onSurfaceVariant) }
                    items(rows, key = RegionEntity::id) { place ->
                        val count = claims.count { place.id in it.regionIdList() }
                        Card(
                            onClick = {
                                model.showOnMap(model.rangeStart.value, place.longitude, place.latitude, frameZoom(place.level), AtlasFocus.Place(place.id))
                                goAtlas()
                            },
                            modifier = Modifier.fillMaxWidth(),
                        ) {
                            Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                                Text(place.name, style = MaterialTheme.typography.titleMedium)
                                Text(
                                    "${place.ancestors(regions).dropLast(1).joinToString(" / ") { it.name }.ifBlank { "世界" }} · ${count} 条",
                                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                                    maxLines = 1,
                                    overflow = TextOverflow.Ellipsis,
                                )
                            }
                        }
                    }
                }
            }
        }
    }
}

private const val HOME_BROWSE_LON = 105.0
private const val HOME_BROWSE_LAT = 35.0

@Composable
private fun EventBrowseRow(
    claim: ClaimEntity,
    byId: Map<Long, RegionEntity>,
    events: Map<Long, EventEntity>,
    openClaim: (Long) -> Unit,
    goAtlas: () -> Unit,
    model: LongriverViewModel,
) {
    val place = claim.regionIdList().firstOrNull()?.let { byId[it] }
    val title = claim.eventId?.let { events[it]?.title }
    Card(onClick = { openClaim(claim.id) }, modifier = Modifier.fillMaxWidth()) {
        Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
            Text(
                listOfNotNull(claim.timeLabel, place?.name).joinToString(" · "),
                style = MaterialTheme.typography.labelLarge,
                color = MaterialTheme.colorScheme.primary,
            )
            if (!title.isNullOrBlank()) Text(title, style = MaterialTheme.typography.titleMedium)
            Text(claim.text, style = MaterialTheme.typography.bodyMedium, maxLines = 3, overflow = TextOverflow.Ellipsis)
            if (place != null) {
                TextButton(onClick = {
                    model.showOnMap(claim.startYear, place.longitude, place.latitude, frameZoom(place.level))
                    goAtlas()
                }) { Text("在地图上看") }
            }
        }
    }
}
