@file:OptIn(ExperimentalMaterial3Api::class)

package app.changhe

import android.graphics.Paint
import android.graphics.RectF
import androidx.compose.animation.Crossfade
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.runtime.mutableLongStateOf
import androidx.compose.runtime.withFrameMillis
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Menu
import androidx.compose.material.icons.filled.Star
import androidx.compose.material3.AssistChip
import androidx.compose.material3.BottomSheetScaffold
import androidx.compose.material3.Card
import androidx.compose.material3.Checkbox
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilledTonalIconButton
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.rememberBottomSheetScaffoldState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.nativeCanvas
import androidx.compose.ui.graphics.toArgb
import androidx.compose.ui.layout.layout
import androidx.compose.ui.layout.onSizeChanged
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.platform.LocalUriHandler
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.IntSize
import androidx.compose.ui.unit.dp
import app.changhe.data.BookmarkKind
import app.changhe.data.ClaimEntity
import app.changhe.data.EventEntity
import app.changhe.data.PersonEntity
import app.changhe.data.RegionEntity
import app.changhe.data.politiesAt
import app.changhe.data.regionIdList
import kotlin.math.cos
import kotlin.math.pow
import kotlin.math.roundToInt
import kotlin.math.sqrt

private const val HOME_LON = 60.0
private const val HOME_LAT = 32.0
private const val HOME_ZOOM = 0.5
private const val MAX_POLITY_LABELS = 40
private val SHEET_PEEK = 284.dp

private enum class BubbleKind { Event, Person, Work }

private data class SheetList(val start: Int, val end: Int, val inView: List<ClaimEntity>, val all: List<ClaimEntity>)

private data class MapBubble(
    val kind: BubbleKind,
    val place: RegionEntity,
    val label: String,
    val count: Int = 0,
    val person: PersonEntity? = null,
)

@Composable
fun AtlasScreen(
    model: ChangheViewModel,
    openClaim: (Long) -> Unit,
    openPerson: (Long) -> Unit,
    openPiece: (String) -> Unit,
) {
    val context = LocalContext.current
    val index = remember { AtlasAssets.polities(context) }
    val rangeStart by model.rangeStart.collectAsState()
    val rangeEnd by model.rangeEnd.collectAsState()
    val claims by model.claims.collectAsState()
    val allClaims by model.allClaims.collectAsState()
    val regions by model.regions.collectAsState()
    val events by model.allEvents.collectAsState()
    val people by model.allPeople.collectAsState()
    val playing by model.playing.collectAsState()
    val step by model.playStep.collectAsState()

    var showBorders by rememberSaveable { mutableStateOf(true) }
    var showEvents by rememberSaveable { mutableStateOf(true) }
    var showPeople by rememberSaveable { mutableStateOf(false) }
    var showWorks by rememberSaveable { mutableStateOf(false) }
    var showStars by rememberSaveable { mutableStateOf(true) }
    var layersOpen by remember { mutableStateOf(false) }
    var polityCard by rememberSaveable { mutableStateOf<Long?>(null) }
    var placeCard by rememberSaveable { mutableStateOf<Long?>(null) }
    var mapSize by remember { mutableStateOf(IntSize.Zero) }

    val state = rememberAtlasMapState()
    val mapYear = rangeStart
    val byId = remember(regions) { regions.associateBy { it.id } }
    val marks = remember(allClaims) { allClaims.map { it.startYear } }
    val labels = remember(mapYear, index) {
        when {
            isModernYear(mapYear) && hasModernBase -> emptyList()
            isModernYear(mapYear) -> AtlasAssets.countryLabels(context)
            else -> index.labelsAt(mapYear)
        }
    }

    val tick = state.cameraTick
    val zoom = state.zoom
    val startCamera = remember { model.atlasCamera ?: MapCamera(HOME_LON, HOME_LAT, HOME_ZOOM) }
    LaunchedEffect(tick) {
        state.map?.cameraPosition?.let { position ->
            val target = position.target ?: return@let
            model.atlasCamera = MapCamera(target.longitude, target.latitude, position.zoom)
        }
    }
    val rank = zoomRank(zoom)
    val bubbles = remember(claims, regions, events, people, rank, rangeStart, rangeEnd, showEvents, showPeople, showWorks) {
        buildBubbles(claims, regions, byId, people, rank, rangeStart, rangeEnd, showEvents, showPeople, showWorks)
    }
    val bookmarks by model.bookmarks.collectAsState()
    val starred = remember(bookmarks, byId) {
        bookmarks.filter { it.kind == BookmarkKind.PLACE }.mapNotNull { byId[it.targetId] }
    }
    val focus by model.atlasFocus.collectAsState()
    LaunchedEffect(focus) {
        when (val target = focus) {
            is AtlasFocus.Place -> placeCard = target.id
            is AtlasFocus.Polity -> polityCard = target.id
            null -> return@LaunchedEffect
        }
        model.atlasFocus.value = null
    }
    val inView = remember(claims, regions, tick) {
        claims.filter { claim ->
            claim.regionIdList().firstOrNull()?.let { byId[it] }?.let { state.isVisible(it.longitude, it.latitude) } ?: false
        }.sortedBy { it.startYear }
    }

    val scaffold = rememberBottomSheetScaffoldState()
    BottomSheetScaffold(
        scaffoldState = scaffold,
        sheetPeekHeight = SHEET_PEEK,
        sheetContainerColor = MaterialTheme.colorScheme.surface,
        sheetContent = {
            Column(Modifier.padding(horizontal = 16.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                Row(Modifier.fillMaxWidth().height(30.dp), verticalAlignment = Alignment.Bottom) {
                    Text(formatSpan(rangeStart, rangeEnd), style = MaterialTheme.typography.titleLarge, maxLines = 1)
                    Spacer(Modifier.width(8.dp))
                    Text(
                        if (claims.isEmpty()) "暂无收录" else "视野内 ${inView.size} 件 · 共 ${claims.size} 件",
                        style = MaterialTheme.typography.labelLarge,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                        modifier = Modifier.weight(1f).padding(bottom = 3.dp),
                    )
                    Text(
                        "角标为事件数",
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        maxLines = 1,
                        modifier = Modifier.padding(bottom = 4.dp),
                    )
                }
                TimeScrubber(
                    selectionStart = rangeStart,
                    selectionEnd = rangeEnd,
                    marks = marks,
                    playing = playing,
                    step = step,
                    onSelect = { start, end ->
                        model.stopPlay()
                        model.selectSpan(start, end)
                    },
                    onTogglePlay = model::togglePlay,
                    onStepChange = { model.playStep.value = it },
                )
                Crossfade(
                    targetState = SheetList(rangeStart, rangeEnd, inView, claims),
                    animationSpec = tween(220),
                    modifier = Modifier.fillMaxWidth().height(440.dp),
                    label = "sheet-list",
                ) { sheet ->
                    val listed = sheet.inView.ifEmpty { sheet.all }
                    LazyColumn(
                        Modifier.fillMaxSize(),
                        verticalArrangement = Arrangement.spacedBy(8.dp),
                        contentPadding = PaddingValues(top = 8.dp, bottom = 24.dp),
                    ) {
                        if (listed.isEmpty()) {
                            item {
                                Text(
                                    "这一年还没有收录。拖动时间轴，靠近下方的密度条就能找到有记录的年份。",
                                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                                )
                            }
                        } else if (sheet.inView.isEmpty()) {
                            item {
                                Text("视野里没有事件，下面是这一时段的全部记录。", color = MaterialTheme.colorScheme.onSurfaceVariant)
                            }
                        }
                        items(listed, key = ClaimEntity::id) { claim ->
                            EventRow(claim, byId, events, openClaim)
                        }
                    }
                }
            }
        },
    ) {
        Box(Modifier.fillMaxSize().onSizeChanged { mapSize = it }) {
            AtlasMap(
                year = mapYear,
                showBorders = showBorders,
                state = state,
                modifier = Modifier.fillMaxSize(),
                initialLon = startCamera.lon,
                initialLat = startCamera.lat,
                initialZoom = startCamera.zoom,
                onPolityTap = { polityCard = it },
                onCountryTap = { name ->
                    regions.firstOrNull { it.level == "country" && it.name == name }?.let { placeCard = it.id }
                },
            )
            if (showBorders) PolityLabels(labels, state, tick, mapSize)
            if (state.loadingBorders) {
                Surface(
                    shape = RoundedCornerShape(16.dp),
                    color = MaterialTheme.colorScheme.surface.copy(alpha = 0.92f),
                    modifier = Modifier.align(Alignment.Center).padding(top = 48.dp),
                ) {
                    Text("正在载入这一年的疆域", modifier = Modifier.padding(horizontal = 14.dp, vertical = 8.dp))
                }
            }
            val density = LocalDensity.current.density
            if (showStars) {
                starred.forEach { place ->
                    val point = state.project(place.longitude, place.latitude) ?: return@forEach
                    if (point.x < 0 || point.y < 0 || point.x > mapSize.width || point.y > mapSize.height) return@forEach
                    Icon(
                        Icons.Filled.Star,
                        contentDescription = place.name,
                        tint = BookmarkGold,
                        modifier = Modifier.centerAt(point.copy(y = point.y - 22 * density)).size(18.dp),
                    )
                }
            }
            bubbles.forEach { bubble ->
                val point = state.project(bubble.place.longitude, bubble.place.latitude) ?: return@forEach
                if (point.x < 0 || point.y < 0 || point.x > mapSize.width || point.y > mapSize.height) return@forEach
                val shift = when (bubble.kind) {
                    BubbleKind.Event -> 0f
                    BubbleKind.Person -> 26f
                    BubbleKind.Work -> -26f
                } * density
                PlaceBubble(bubble, Modifier.centerAt(point.copy(y = point.y + shift))) { placeCard = bubble.place.id }
            }
            Row(
                Modifier.fillMaxWidth().statusBarsPadding().padding(horizontal = 12.dp, vertical = 8.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                AssistChip(onClick = { state.flyTo(HOME_LON, HOME_LAT, HOME_ZOOM) }, label = { Text("全球") })
                Spacer(Modifier.weight(1f))
                Surface(
                    shape = RoundedCornerShape(20.dp),
                    color = MaterialTheme.colorScheme.surface.copy(alpha = 0.92f),
                    modifier = Modifier.shadow(3.dp, RoundedCornerShape(20.dp)),
                ) {
                    Text(
                        formatSpan(rangeStart, rangeEnd),
                        style = MaterialTheme.typography.titleLarge,
                        modifier = Modifier.padding(horizontal = 18.dp, vertical = 6.dp),
                    )
                }
                Spacer(Modifier.weight(1f))
                Box {
                    FilledTonalIconButton(onClick = { layersOpen = true }) {
                        Icon(Icons.Filled.Menu, contentDescription = "图层")
                    }
                    DropdownMenu(expanded = layersOpen, onDismissRequest = { layersOpen = false }) {
                        LayerItem("疆域", showBorders) { showBorders = it }
                        LayerItem("事件", showEvents) { showEvents = it }
                        LayerItem("人物", showPeople) { showPeople = it }
                        LayerItem("诗文著作", showWorks) { showWorks = it }
                        LayerItem("我的收藏", showStars) { showStars = it }
                    }
                }
            }
            Column(
                Modifier.align(Alignment.BottomStart).padding(start = 10.dp, bottom = SHEET_PEEK + 6.dp),
            ) {
                LegalInfo.mapLines(mapYear).forEachIndexed { i, line ->
                    Text(
                        line,
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.onBackground.copy(alpha = if (i == 0) 0.75f else 0.55f),
                    )
                }
            }
        }
    }

    polityCard?.let { pid ->
        val polity = index.polity(pid)
        if (polity == null) {
            polityCard = null
        } else {
            ModalBottomSheet(onDismissRequest = { polityCard = null }) {
                PolityCard(polity, claims, byId, events, rangeStart, rangeEnd) {
                    polityCard = null
                    openClaim(it)
                }
            }
        }
    }
    placeCard?.let { id ->
        val place = byId[id]
        if (place == null) {
            placeCard = null
        } else {
            ModalBottomSheet(onDismissRequest = { placeCard = null }) {
                PlaceCard(
                    place = place,
                    regions = regions,
                    claims = claims,
                    events = events,
                    people = people,
                    rangeStart = rangeStart,
                    rangeEnd = rangeEnd,
                    onLocate = { state.flyTo(place.longitude, place.latitude, frameZoom(place.level)) },
                    openClaim = { placeCard = null; openClaim(it) },
                    openPerson = { placeCard = null; openPerson(it) },
                    openPiece = { placeCard = null; openPiece(it) },
                )
            }
        }
    }
}

@Composable
private fun LayerItem(label: String, checked: Boolean, onChange: (Boolean) -> Unit) {
    DropdownMenuItem(
        text = { Text(label) },
        leadingIcon = { Checkbox(checked = checked, onCheckedChange = null) },
        onClick = { onChange(!checked) },
    )
}

private fun buildBubbles(
    claims: List<ClaimEntity>,
    regions: List<RegionEntity>,
    byId: Map<Long, RegionEntity>,
    people: List<PersonEntity>,
    rank: Int,
    rangeStart: Int,
    rangeEnd: Int,
    showEvents: Boolean,
    showPeople: Boolean,
    showWorks: Boolean,
): List<MapBubble> {
    val result = mutableListOf<MapBubble>()
    if (showEvents) {
        val anchors = claims.mapNotNull { claim ->
            claim.regionIdList().firstOrNull()?.let { byId[it] }?.let { rollupPlace(it, rank, byId) }
        }.distinctBy { it.id }
        anchors.forEach { place ->
            val count = eventCount(claimsInPlace(claims, place, regions))
            if (count > 0) result += MapBubble(BubbleKind.Event, place, place.name, count)
        }
    }
    if (showPeople) {
        people.asSequence()
            .filter { it.visibleDuring(rangeStart, rangeEnd) && it.regionId != null }
            .mapNotNull { person -> byId[person.regionId]?.let { rollupPlace(it, rank, byId) to person } }
            .groupBy({ it.first.id }, { it.second })
            .forEach { (id, who) ->
                val place = byId[id] ?: return@forEach
                val lead = who.firstOrNull { it.image.isNotBlank() } ?: who.first()
                result += MapBubble(BubbleKind.Person, place, lead.name, if (who.size > 1) who.size else 0, lead)
            }
    }
    if (showWorks) {
        val bySlug = byId.values.associateBy { it.slug }
        readingPieces.groupBy { it.regionSlug }.forEach { (slug, pieces) ->
            val place = bySlug[slug]?.let { rollupPlace(it, rank, byId) } ?: return@forEach
            result += MapBubble(BubbleKind.Work, place, "诗文", pieces.size)
        }
    }
    return result
}

internal fun EventEntity.personIdList(): List<Long> = personIds.split(",").mapNotNull { it.trim().toLongOrNull() }

private fun Modifier.centerAt(point: Offset) = layout { measurable, constraints ->
    val placeable = measurable.measure(constraints.copy(minWidth = 0, minHeight = 0))
    layout(placeable.width, placeable.height) {
        placeable.place(point.x.roundToInt() - placeable.width / 2, point.y.roundToInt() - placeable.height / 2)
    }
}

@Composable
private fun PlaceBubble(bubble: MapBubble, modifier: Modifier, onClick: () -> Unit) {
    val colors = MaterialTheme.colorScheme
    val (container, content) = when (bubble.kind) {
        BubbleKind.Event -> colors.primary to colors.onPrimary
        BubbleKind.Person -> colors.secondary to colors.onSecondary
        BubbleKind.Work -> colors.tertiary to colors.onTertiary
    }
    Surface(
        onClick = onClick,
        shape = RoundedCornerShape(50),
        color = container,
        contentColor = content,
        shadowElevation = 3.dp,
        modifier = modifier,
    ) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            modifier = Modifier.padding(
                start = if (bubble.person != null) 3.dp else 10.dp,
                end = if (bubble.count > 0) 4.dp else 10.dp,
                top = 3.dp,
                bottom = 3.dp,
            ),
        ) {
            bubble.person?.let {
                Avatar(it.name, it.image, 22.dp)
                Spacer(Modifier.width(5.dp))
            }
            Text(bubble.label, style = MaterialTheme.typography.labelMedium, maxLines = 1)
            if (bubble.count > 0) {
                val badge = (16 + (bubble.count.coerceAtMost(20) - 1) * 0.5f).dp
                Spacer(Modifier.width(5.dp))
                Box(
                    Modifier.size(badge).background(content, CircleShape),
                    contentAlignment = Alignment.Center,
                ) {
                    Text(
                        if (bubble.count > 99) "99+" else bubble.count.toString(),
                        style = MaterialTheme.typography.labelSmall,
                        color = container,
                        maxLines = 1,
                    )
                }
            }
        }
    }
}

@Composable
private fun PolityLabels(labels: List<PolityLabel>, state: AtlasMapState, tick: Int, size: IntSize) {
    val density = LocalDensity.current.density
    val ink = MaterialTheme.colorScheme.onBackground.copy(alpha = 0.78f).toArgb()
    val zoom = state.zoom
    val previous = remember { mutableMapOf<Long, LabelDraw>() }
    val appeared = remember { mutableMapOf<Long, Long>() }
    val leaving = remember { mutableMapOf<Long, Pair<LabelDraw, Long>>() }
    var frame by remember { mutableLongStateOf(nowMs()) }
    val placed = remember(labels, tick, size) {
        val worldPx = 512.0 * 2.0.pow(zoom) * density
        val showPx = 32 * density
        val keepPx = 24 * density
        val boxes = mutableListOf<RectF>()
        val ordered = labels.sortedWith(
            compareByDescending<PolityLabel> { it.polity.id in previous }.thenByDescending { it.areaKm2 },
        )
        val result = ordered.mapNotNull { label ->
            if (boxes.size >= MAX_POLITY_LABELS) return@mapNotNull null
            val kmPerPx = 40075.0 * cos(Math.toRadians(label.lat)) / worldPx
            val spanPx = sqrt(label.areaKm2) / kmPerPx.coerceAtLeast(1e-6)
            if (spanPx < if (label.polity.id in previous) keepPx else showPx) return@mapNotNull null
            val point = state.project(label.lon, label.lat) ?: return@mapNotNull null
            if (point.x < 0 || point.y < 0 || point.x > size.width || point.y > size.height) return@mapNotNull null
            val text = label.polity.displayName
            if (text.none { Character.UnicodeScript.of(it.code) == Character.UnicodeScript.HAN }) return@mapNotNull null
            val textSize = ((11 + (spanPx / (40 * density)).coerceAtMost(6.0)) * density).toFloat()
            val half = text.length * textSize * 0.55f
            val box = RectF(point.x - half, point.y - textSize, point.x + half, point.y + textSize * 0.4f)
            if (boxes.any { RectF.intersects(it, box) }) return@mapNotNull null
            boxes += box
            LabelDraw(label.polity.id, text, label.lon, label.lat, textSize)
        }
        val now = nowMs()
        val ids = result.map { it.id }.toSet()
        previous.values.filter { it.id !in ids }.forEach { leaving[it.id] = it to now }
        result.filter { it.id !in previous }.forEach {
            appeared[it.id] = now
            leaving.remove(it.id)
        }
        appeared.keys.retainAll(ids)
        previous.clear()
        result.forEach { previous[it.id] = it }
        result
    }
    LaunchedEffect(placed) {
        val until = nowMs() + LABEL_FADE_MS + 20
        while (nowMs() < until) withFrameMillis { frame = nowMs() }
    }
    Canvas(Modifier.fillMaxSize()) {
        val halo = Paint().apply {
            isAntiAlias = true
            textAlign = Paint.Align.CENTER
            style = Paint.Style.STROKE
            strokeWidth = 3f * density
            color = Color.White.copy(alpha = 0.85f).toArgb()
        }
        val fill = Paint().apply {
            isAntiAlias = true
            textAlign = Paint.Align.CENTER
            color = ink
            isFakeBoldText = true
        }
        fun draw(label: LabelDraw, alpha: Float) {
            if (alpha <= 0f) return
            val point = state.project(label.lon, label.lat) ?: return
            halo.textSize = label.textSize
            fill.textSize = label.textSize
            halo.alpha = (alpha * 217).toInt()
            fill.alpha = (alpha * 255 * 0.78f).toInt()
            drawContext.canvas.nativeCanvas.drawText(label.text, point.x, point.y, halo)
            drawContext.canvas.nativeCanvas.drawText(label.text, point.x, point.y, fill)
        }
        val now = frame
        leaving.entries.removeAll { now - it.value.second > LABEL_FADE_MS }
        leaving.values.forEach { (label, since) -> draw(label, 1f - (now - since).toFloat() / LABEL_FADE_MS) }
        placed.forEach { label ->
            val since = appeared[label.id] ?: 0L
            draw(label, ((now - since).toFloat() / LABEL_FADE_MS).coerceIn(0f, 1f))
        }
    }
}

private const val LABEL_FADE_MS = 200L

private data class LabelDraw(val id: Long, val text: String, val lon: Double, val lat: Double, val textSize: Float)

private fun nowMs() = System.nanoTime() / 1_000_000

@Composable
private fun EventRow(claim: ClaimEntity, byId: Map<Long, RegionEntity>, events: List<EventEntity>, openClaim: (Long) -> Unit) {
    val place = claim.regionIdList().firstOrNull()?.let { byId[it] }
    val title = events.firstOrNull { it.id == claim.eventId }?.title
    Card(onClick = { openClaim(claim.id) }, modifier = Modifier.fillMaxWidth()) {
        Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
            Text(
                listOfNotNull(claim.timeLabel, place?.name).joinToString(" · "),
                style = MaterialTheme.typography.labelLarge,
                color = MaterialTheme.colorScheme.primary,
            )
            if (!title.isNullOrBlank()) Text(title, style = MaterialTheme.typography.titleMedium)
            Text(claim.text, style = MaterialTheme.typography.bodyMedium, maxLines = 3, overflow = TextOverflow.Ellipsis)
        }
    }
}

@Composable
private fun PolityCard(
    polity: PolityInfo,
    claims: List<ClaimEntity>,
    byId: Map<Long, RegionEntity>,
    events: List<EventEntity>,
    rangeStart: Int,
    rangeEnd: Int,
    openClaim: (Long) -> Unit,
) {
    val uri = LocalUriHandler.current
    val inside = claims.filter { claim ->
        claim.overlaps(rangeStart, rangeEnd) &&
            claim.regionIdList().any { id ->
                val year = claim.startYear.coerceIn(rangeStart, rangeEnd)
                byId[id]?.politiesAt(year)?.contains(polity.id) == true
            }
    }
    LazyColumn(
        contentPadding = PaddingValues(start = 20.dp, end = 20.dp, bottom = 32.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        item { Text(polity.displayName, style = MaterialTheme.typography.headlineSmall) }
        polity.latinName?.let { latin ->
            item { Text(latin, color = MaterialTheme.colorScheme.onSurfaceVariant) }
        }
        item {
            Text(
                "存续 ${formatSpan(polity.from, polity.to)}" + if (polity.capital.isNotBlank()) " · 都城 ${polity.capital}" else "",
                style = MaterialTheme.typography.bodyLarge,
            )
        }
        if (polity.wikipedia.isNotBlank()) {
            item {
                TextButton(onClick = {
                    val query = java.net.URLEncoder.encode(polity.displayName, "UTF-8")
                    uri.openUri("https://zh.wikipedia.org/w/index.php?search=$query")
                }) {
                    Text("查看中文维基百科")
                }
            }
        }
        item {
            Text(
                "${formatSpan(rangeStart, rangeEnd)}境内的记录",
                style = MaterialTheme.typography.titleMedium,
                modifier = Modifier.padding(top = 8.dp),
            )
        }
        if (inside.isEmpty()) {
            item { Text("这一时段境内还没有收录事件。", color = MaterialTheme.colorScheme.onSurfaceVariant) }
        }
        items(inside, key = ClaimEntity::id) { claim -> EventRow(claim, byId, events, openClaim) }
        item {
            Text(
                "疆域数据：Cliopatria（CC BY 4.0），轮廓为近似示意。",
                style = MaterialTheme.typography.labelSmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.padding(top = 12.dp),
            )
        }
    }
}

@Composable
private fun PlaceCard(
    place: RegionEntity,
    regions: List<RegionEntity>,
    claims: List<ClaimEntity>,
    events: List<EventEntity>,
    people: List<PersonEntity>,
    rangeStart: Int,
    rangeEnd: Int,
    onLocate: () -> Unit,
    openClaim: (Long) -> Unit,
    openPerson: (Long) -> Unit,
    openPiece: (String) -> Unit,
) {
    var section by rememberSaveable { mutableStateOf("event") }
    Column(Modifier.padding(horizontal = 20.dp).height(if (place.image.isNotBlank()) 640.dp else 520.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
        Text(
            place.ancestors(regions).dropLast(1).joinToString(" / ") { it.name }.ifBlank { "世界" },
            style = MaterialTheme.typography.labelLarge,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        Row(verticalAlignment = Alignment.CenterVertically) {
            Text(place.name, style = MaterialTheme.typography.headlineSmall, modifier = Modifier.weight(1f))
            TextButton(onClick = onLocate) { Text("在地图上定位") }
        }
        Text(formatSpan(rangeStart, rangeEnd), style = MaterialTheme.typography.labelMedium, color = MaterialTheme.colorScheme.secondary)
        if (place.image.isNotBlank()) {
            HeaderImage(place.image, place.imageCredit, place.name, height = 120.dp)
        }
        PlaceSections(section, { section = it })
        PlaceResults(
            section, place, regions, claims, events, people,
            rangeStart, rangeEnd, openClaim, openPerson, openPiece, Modifier.weight(1f),
        )
    }
}

@Composable
private fun PlaceSections(section: String, onSelect: (String) -> Unit) {
    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        listOf("event" to "事件", "person" to "人物", "verse" to "诗句", "book" to "著作").forEach { (id, label) ->
            androidx.compose.material3.FilterChip(
                selected = section == id,
                onClick = { onSelect(id) },
                label = { Text(label) },
            )
        }
    }
}
