@file:OptIn(ExperimentalMaterial3Api::class)

package app.changhe

import android.app.Activity
import android.app.Application
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.core.tween
import androidx.compose.animation.slideInHorizontally
import androidx.compose.animation.slideOutHorizontally
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyListScope
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.DateRange
import androidx.compose.material.icons.filled.Person
import androidx.compose.material.icons.filled.Place
import androidx.compose.material3.Card
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.produceState
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.layout.layout
import androidx.compose.ui.layout.onSizeChanged
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.IntSize
import androidx.compose.ui.unit.dp
import kotlin.math.roundToInt
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.NavGraph.Companion.findStartDestination
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import androidx.navigation.navArgument
import app.changhe.data.BookmarkKind
import app.changhe.data.ClaimEntity
import app.changhe.data.EventEntity
import app.changhe.data.KnowledgeRepository
import app.changhe.data.PersonEntity
import app.changhe.data.RegionEntity
import app.changhe.data.regionIdList
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        enableEdgeToEdge()
        super.onCreate(savedInstanceState)
        setContent { ChangheTheme { ChangheApp() } }
    }
}

data class MapCamera(val lon: Double, val lat: Double, val zoom: Double)

sealed interface AtlasFocus {
    data class Place(val id: Long) : AtlasFocus
    data class Polity(val id: Long) : AtlasFocus
}

class ChangheViewModel(app: Application) : AndroidViewModel(app) {
    private val repository = KnowledgeRepository(app, BuildConfig.API_BASE_URL)
    val rangeStart = MutableStateFlow(1521)
    val rangeEnd = MutableStateFlow(1521)
    val message = MutableStateFlow<String?>(null)
    val syncing = MutableStateFlow(false)
    val playing = MutableStateFlow(false)
    val playStep = MutableStateFlow(PlayStep.Marks)
    var atlasCamera: MapCamera? = null
    private var playJob: Job? = null
    val regions = repository.regions().stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), emptyList())
    val bookmarks = repository.bookmarks().stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), emptyList())
    val snapshots = repository.snapshots().stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), emptyList())
    val allClaims = repository.claims().stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), emptyList())
    val allEvents = repository.events().stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), emptyList())
    val allPeople = repository.people().stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), emptyList())

    val claims = combine(rangeStart, rangeEnd, allClaims) { start, end, rows ->
        rows.filter { it.overlaps(start, end) }
    }.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), emptyList())

    /** Card the atlas should open after a jump from elsewhere (bookmarks, person page). */
    val atlasFocus = MutableStateFlow<AtlasFocus?>(null)
    val seeding = MutableStateFlow(true)

    init {
        viewModelScope.launch {
            try {
                repository.ensureSeeded(BuildConfig.SEED_REVISION) {
                    app.assets.open("knowledge-package.json").bufferedReader().use { it.readText() }
                }
            } finally {
                seeding.value = false
            }
        }
    }

    fun showOnMap(year: Int, lon: Double, lat: Double, zoom: Double, focus: AtlasFocus? = null, endYear: Int? = null) {
        stopPlay()
        selectSpan(year, endYear ?: year)
        atlasCamera = MapCamera(lon, lat, zoom)
        atlasFocus.value = focus
    }

    fun selectSpan(start: Int, end: Int) {
        rangeStart.value = minOf(start, end).coerceIn(TIMELINE_START, TIMELINE_END)
        rangeEnd.value = maxOf(start, end).coerceIn(TIMELINE_START, TIMELINE_END)
    }

    fun togglePlay() {
        if (playing.value) {
            stopPlay()
            return
        }
        playing.value = true
        playJob = viewModelScope.launch {
            try {
                while (true) {
                    val step = playStep.value
                    val current = rangeStart.value
                    val next = if (step == PlayStep.Marks) {
                        allClaims.value.asSequence().map { it.startYear }.filter { it > current }.minOrNull()
                    } else {
                        (current + step.years).takeIf { it <= TIMELINE_END }
                    } ?: break
                    selectSpan(next, next)
                    delay(
                        when (step) {
                            PlayStep.Marks -> 1200
                            PlayStep.One -> 260
                            else -> 520
                        },
                    )
                }
            } finally {
                playing.value = false
            }
        }
    }

    fun stopPlay() {
        playJob?.cancel()
        playJob = null
        playing.value = false
    }

    fun sync() {
        viewModelScope.launch {
            if (syncing.value) return@launch
            syncing.value = true
            try {
                repository.sync()
                message.value = "知识库已是最新"
            } catch (error: Exception) {
                message.value = readableSyncError(error)
            } finally {
                syncing.value = false
            }
        }
    }

    fun toggleBookmark(kind: String, targetId: Long, bookmarked: Boolean) {
        viewModelScope.launch {
            if (bookmarked) {
                repository.removeBookmark(kind, targetId)
            } else {
                repository.saveBookmark(kind, targetId, "")
                message.value = "已收藏，可在“我的”里查看"
            }
        }
    }

    fun claim(id: Long) = repository.claim(id)
    fun bookmark(kind: String, id: Long) = repository.bookmark(kind, id)
    suspend fun eventTitle(id: Long?) = id?.let { repository.event(it)?.title }
    suspend fun snapshotLabel(id: Long?) = id?.let { repository.snapshot(it)?.label }
    suspend fun people(eventId: Long?) = repository.peopleForEvent(eventId)
}

private data class Tab(val route: String, val label: String, val icon: ImageVector)

private val tabs = listOf(
    Tab("atlas", "图", Icons.Filled.Place),
    Tab("browse", "览", Icons.Filled.DateRange),
    Tab("mine", "我的", Icons.Filled.Person),
)

@Composable
fun ChangheApp(model: ChangheViewModel = viewModel()) {
    val context = LocalContext.current
    val nav = rememberNavController()
    val destination = nav.currentBackStackEntryAsState().value?.destination?.route
    val message by model.message.collectAsState()
    val syncing by model.syncing.collectAsState()
    val seeding by model.seeding.collectAsState()
    var consented by remember { mutableStateOf(hasConsent(context)) }
    var onboarded by remember { mutableStateOf(hasOnboarded(context)) }
    val onTab = tabs.any { it.route == destination }
    val goAtlas = {
        nav.navigate("atlas") {
            popUpTo(nav.graph.findStartDestination().id) { saveState = true }
            launchSingleTop = true
            restoreState = true
        }
    }
    val snackbarHostState = remember { SnackbarHostState() }
    LaunchedEffect(message) {
        val text = message ?: return@LaunchedEffect
        snackbarHostState.showSnackbar(text)
        model.message.value = null
    }
    Scaffold(
        containerColor = MaterialTheme.colorScheme.background,
        contentWindowInsets = WindowInsets(0, 0, 0, 0),
        snackbarHost = { SnackbarHost(snackbarHostState) },
        topBar = {
            if (destination != "atlas") {
                TopAppBar(
                    title = {
                        Text(
                            when {
                                destination == "browse" -> "览"
                                destination == "mine" -> "我的"
                                destination == "about" -> "关于长河"
                                destination?.startsWith("piece/") == true -> "查阅"
                                destination?.startsWith("person/") == true -> "人物"
                                destination == "legal/privacy" -> "隐私政策"
                                destination == "legal/terms" -> "用户协议"
                                else -> "史料"
                            },
                        )
                    },
                    navigationIcon = {
                        if (!onTab && destination != null) {
                            IconButton(onClick = { nav.popBackStack() }) {
                                Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "返回")
                            }
                        }
                    },
                    colors = TopAppBarDefaults.topAppBarColors(containerColor = MaterialTheme.colorScheme.background),
                )
            }
        },
        bottomBar = {
            if (onTab) {
                NavigationBar(containerColor = MaterialTheme.colorScheme.background) {
                    tabs.forEach { tab ->
                        NavigationBarItem(
                            selected = destination == tab.route,
                            onClick = {
                                nav.navigate(tab.route) {
                                    popUpTo(nav.graph.findStartDestination().id) { saveState = true }
                                    launchSingleTop = true
                                    restoreState = true
                                }
                            },
                            icon = { Icon(tab.icon, contentDescription = tab.label) },
                            label = { Text(tab.label) },
                        )
                    }
                }
            }
        },
    ) { padding ->
        Box(Modifier.padding(padding).fillMaxSize()) {
            NavHost(
                nav,
                startDestination = "atlas",
                modifier = Modifier.fillMaxSize(),
            ) {
            composable("atlas", enterTransition = { fadeIn(tween(220)) }, exitTransition = { fadeOut(tween(160)) }) {
                AtlasScreen(
                    model,
                    openClaim = { nav.navigate("claim/$it") },
                    openPerson = { nav.navigate("person/$it") },
                    openPiece = { nav.navigate("piece/$it") },
                )
            }
            composable("browse", enterTransition = { fadeIn(tween(220)) }, exitTransition = { fadeOut(tween(160)) }) {
                BrowseScreen(
                    model,
                    openClaim = { nav.navigate("claim/$it") },
                    openPerson = { nav.navigate("person/$it") },
                    goAtlas = goAtlas,
                )
            }
            composable("mine", enterTransition = { fadeIn(tween(220)) }, exitTransition = { fadeOut(tween(160)) }) {
                MineScreen(
                    bookmarks = { BookmarkSection(model, { nav.navigate("claim/$it") }, { nav.navigate("person/$it") }, goAtlas) },
                    syncing = syncing,
                    onSync = model::sync,
                    openAbout = { nav.navigate("about") },
                    openPrivacy = { nav.navigate("legal/privacy") },
                    openTerms = { nav.navigate("legal/terms") },
                )
            }
            composable("about") { AboutScreen(model) }
            composable("legal/privacy") { LegalTextScreen(LegalInfo.privacyPolicy) }
            composable("legal/terms") { LegalTextScreen(LegalInfo.userAgreement) }
            composable(
                "claim/{id}",
                listOf(navArgument("id") { type = NavType.LongType }),
                enterTransition = { slideInHorizontally(tween(280)) { it / 4 } + fadeIn(tween(220)) },
                exitTransition = { fadeOut(tween(140)) },
                popEnterTransition = { fadeIn(tween(180)) },
                popExitTransition = { slideOutHorizontally(tween(240)) { it / 4 } + fadeOut(tween(160)) },
            ) { entry ->
                DetailScreen(
                    model,
                    entry.arguments?.getLong("id") ?: 0L,
                    goAtlas,
                    openPerson = { nav.navigate("person/$it") },
                    openClaim = { nav.navigate("claim/$it") },
                )
            }
            composable(
                "piece/{id}",
                listOf(navArgument("id") { type = NavType.StringType }),
                enterTransition = { slideInHorizontally(tween(280)) { it / 4 } + fadeIn(tween(220)) },
                popExitTransition = { slideOutHorizontally(tween(240)) { it / 4 } + fadeOut(tween(160)) },
            ) { entry ->
                ReadingPieceScreen(entry.arguments?.getString("id").orEmpty())
            }
            composable(
                "person/{id}",
                listOf(navArgument("id") { type = NavType.LongType }),
                enterTransition = { slideInHorizontally(tween(280)) { it / 4 } + fadeIn(tween(220)) },
                popExitTransition = { slideOutHorizontally(tween(240)) { it / 4 } + fadeOut(tween(160)) },
            ) { entry ->
                PersonScreen(
                    model,
                    entry.arguments?.getLong("id") ?: 0L,
                    openClaim = { nav.navigate("claim/$it") },
                    goAtlas = goAtlas,
                )
            }
        }
            if (seeding) {
                Box(
                    Modifier.fillMaxSize().background(MaterialTheme.colorScheme.background.copy(alpha = 0.94f)),
                    contentAlignment = Alignment.Center,
                ) {
                    Column(horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(12.dp)) {
                        CircularProgressIndicator()
                        Text("正在载入知识库", style = MaterialTheme.typography.bodyLarge)
                    }
                }
            }
        }
    }
    if (!consented && destination?.startsWith("legal/") != true) {
        ConsentDialog(
            onAgree = {
                saveConsent(context)
                consented = true
            },
            onDecline = { (context as? Activity)?.finish() },
            openPrivacy = { nav.navigate("legal/privacy") },
            openTerms = { nav.navigate("legal/terms") },
        )
    } else if (consented && !onboarded) {
        Onboarding(onDone = {
            saveOnboarded(context)
            onboarded = true
        })
    }
}

@Composable
private fun DetailScreen(
    model: ChangheViewModel,
    claimId: Long,
    goAtlas: () -> Unit,
    openPerson: (Long) -> Unit,
    openClaim: (Long) -> Unit,
) {
    val claim by model.claim(claimId).collectAsState(initial = null)
    val bookmark by model.bookmark(BookmarkKind.CLAIM, claimId).collectAsState(initial = null)
    val regions by model.regions.collectAsState()
    val current = claim
    if (current == null) {
        Text(
            "这条陈述不在本地知识库中。",
            modifier = Modifier.padding(24.dp),
            style = MaterialTheme.typography.bodyLarge,
        )
        return
    }
    val place = current.regionIdList().firstOrNull()?.let { id -> regions.firstOrNull { it.id == id } }
    val eventTitle by produceState("", current.eventId) { value = model.eventTitle(current.eventId).orEmpty() }
    val snapshotLabel by produceState("", current.snapshotId) {
        value = model.snapshotLabel(current.snapshotId).orEmpty()
    }
    val people by produceState(emptyList<PersonEntity>(), current.eventId) { value = model.people(current.eventId) }
    val claims by model.allClaims.collectAsState()
    val events by model.allEvents.collectAsState()
    val eventById = remember(events) { events.associateBy { it.id } }
    val samePlace = remember(current.id, claims) { samePlaceClaims(current, claims) }
    val contemporary = remember(current.id, claims) { contemporaryClaims(current, claims) }
    val briefBlocks = remember(current.brief) { parseBrief(current.brief) }
    BoxWithConstraints(Modifier.fillMaxSize().navigationBarsPadding()) {
        val mapHeight = minOf(maxHeight * 0.46f, 340.dp)
        Column(Modifier.fillMaxSize()) {
        if (place != null) {
            DetailMap(
                place = place,
                regions = regions,
                year = current.startYear.coerceIn(TIMELINE_START, TIMELINE_END),
                captionYear = current.startYear,
                modifier = Modifier.fillMaxWidth().height(mapHeight),
            )
        } else {
            Text(
                "这条记述没有地点，地图上暂不标点。",
                modifier = Modifier.fillMaxWidth().background(MaterialTheme.colorScheme.surfaceVariant).padding(16.dp),
            )
        }
        LazyColumn(
            Modifier.weight(1f),
            contentPadding = PaddingValues(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            item { Text(current.timeLabel, style = MaterialTheme.typography.labelLarge, color = MaterialTheme.colorScheme.primary) }
            if (eventTitle.isNotBlank()) item { Text(eventTitle, style = MaterialTheme.typography.headlineSmall) }
            if (snapshotLabel.isNotBlank()) item { Text(snapshotLabel, color = MaterialTheme.colorScheme.onSurfaceVariant) }
            item { Text(current.text, style = MaterialTheme.typography.bodyLarge) }
            briefBlocks.forEachIndexed { index, block ->
                item(key = "brief-$index") {
                    Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                        if (block.heading.isNotBlank()) {
                            Text(block.heading, style = MaterialTheme.typography.titleMedium)
                        }
                        Text(block.text, style = MaterialTheme.typography.bodyLarge)
                    }
                }
            }
            if (briefBlocks.isNotEmpty()) {
                item {
                    Text(
                        "正文摘自维基百科，CC BY-SA 4.0",
                        style = MaterialTheme.typography.labelMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
            }
            relatedClaims("同地", samePlace, eventById, openClaim)
            relatedClaims("同时代", contemporary, eventById, openClaim)
            if (people.isNotEmpty()) {
                item { Text("相关人物", style = MaterialTheme.typography.titleMedium) }
                items(people, key = PersonEntity::id) { person ->
                    Card(onClick = { openPerson(person.id) }, modifier = Modifier.fillMaxWidth()) {
                        Row(
                            Modifier.padding(12.dp),
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.spacedBy(12.dp),
                        ) {
                            Avatar(person.name, person.image, 40.dp)
                            Column {
                                Text(person.name, style = MaterialTheme.typography.titleMedium)
                                Text(
                                    lifeSpan(person.birthYear, person.deathYear) ?: "查看人物",
                                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                                )
                                if (person.imageCredit.isNotBlank()) {
                                    Text(
                                        "头像：${person.imageCredit}",
                                        style = MaterialTheme.typography.labelSmall,
                                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                                        maxLines = 2,
                                    )
                                }
                            }
                        }
                    }
                }
            }
            if (current.certainty != "unverified") {
                item { Text(certaintyLabel(current.certainty), color = MaterialTheme.colorScheme.secondary) }
            }
            item { Text("出处", style = MaterialTheme.typography.titleMedium) }
            current.citationsJson.lines().filter { it.isNotBlank() }.forEach { line ->
                item {
                    Text(formatCitation(line), style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
            }
            item {
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    BookmarkButton(bookmark != null) { model.toggleBookmark(BookmarkKind.CLAIM, claimId, bookmark != null) }
                    if (place != null) {
                        TextButton(onClick = {
                            model.showOnMap(
                                current.startYear,
                                place.longitude,
                                place.latitude,
                                detailZoom(place.level),
                                endYear = current.endYear,
                            )
                            goAtlas()
                        }) { Text("在地图上看") }
                    }
                }
            }
        }
        }
    }
}

private fun LazyListScope.relatedClaims(
    title: String,
    rows: List<ClaimEntity>,
    eventById: Map<Long, EventEntity>,
    openClaim: (Long) -> Unit,
) {
    if (rows.isEmpty()) return
    item(key = title) { Text(title, style = MaterialTheme.typography.titleMedium) }
    items(rows, key = { claim -> "$title-${claim.id}" }) { claim ->
        val label = claim.eventId?.let { eventById[it]?.title }?.takeIf { it.isNotBlank() } ?: claim.text
        Card(onClick = { openClaim(claim.id) }, modifier = Modifier.fillMaxWidth()) {
            Column(Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                Text(claim.timeLabel, style = MaterialTheme.typography.labelLarge, color = MaterialTheme.colorScheme.primary)
                Text(label, style = MaterialTheme.typography.bodyLarge, maxLines = 2, overflow = TextOverflow.Ellipsis)
            }
        }
    }
}

@Composable
private fun DetailMap(
    place: RegionEntity,
    regions: List<RegionEntity>,
    year: Int,
    captionYear: Int,
    modifier: Modifier = Modifier,
) {
    val context = LocalContext.current
    val index = remember { AtlasAssets.polities(context) }
    val mapState = rememberAtlasMapState()
    val zoom = detailZoom(place.level)
    val neighbors = remember(place.id, regions) { contextPlaces(place, regions) }
    val polityLabels = remember(year, index) {
        when {
            isModernYear(year) && hasModernBase -> emptyList()
            isModernYear(year) -> AtlasAssets.countryLabels(context)
            else -> index.labelsAt(year)
        }
    }
    var mapSize by remember { mutableStateOf(IntSize.Zero) }
    val tick = mapState.cameraTick
    LaunchedEffect(mapState.map, place.id) {
        mapState.flyTo(place.longitude, place.latitude, zoom)
    }
    val trail = place.ancestors(regions).joinToString(" · ") { it.name }
    Box(
        modifier
            .background(Color(0xFFD5E3E3))
            .onSizeChanged { mapSize = it },
    ) {
        AtlasMap(
            year = year,
            showBorders = true,
            state = mapState,
            modifier = Modifier.fillMaxSize(),
            initialLon = place.longitude,
            initialLat = place.latitude,
            initialZoom = zoom,
            texture = true,
        )
        val placed = remember(tick, mapSize, place.id, neighbors, polityLabels) {
            projectDetailMarks(mapState, mapSize, place, neighbors, polityLabels)
        }
        placed.forEach { mark ->
            if (mark.kind == DetailMarkKind.PlaceName || mark.kind == DetailMarkKind.Polity) {
                Text(
                    mark.text,
                    style = if (mark.kind == DetailMarkKind.Polity) {
                        MaterialTheme.typography.labelMedium
                    } else {
                        MaterialTheme.typography.labelSmall
                    },
                    color = MaterialTheme.colorScheme.onBackground.copy(alpha = if (mark.kind == DetailMarkKind.Polity) 0.72f else 0.88f),
                    maxLines = 1,
                    modifier = Modifier.pinAt(mark.at),
                )
            } else {
                Box(
                    Modifier.pinAt(mark.at).size(8.dp).background(MaterialTheme.colorScheme.secondary, CircleShape),
                )
            }
        }
        mapState.project(place.longitude, place.latitude)?.let { point ->
            Column(Modifier.pinAt(point), horizontalAlignment = Alignment.CenterHorizontally) {
                Box(
                    Modifier.size(18.dp).background(Color.White, CircleShape),
                    contentAlignment = Alignment.Center,
                ) {
                    Box(Modifier.size(10.dp).background(MaterialTheme.colorScheme.primary, CircleShape))
                }
                Text(
                    place.name,
                    style = MaterialTheme.typography.labelLarge,
                    modifier = Modifier
                        .padding(top = 2.dp)
                        .background(MaterialTheme.colorScheme.surface.copy(alpha = 0.92f), RoundedCornerShape(8.dp))
                        .padding(horizontal = 8.dp, vertical = 2.dp),
                )
            }
        }
        Text(
            "$trail · ${formatYear(captionYear)}",
            style = MaterialTheme.typography.labelLarge,
            modifier = Modifier
                .align(Alignment.BottomStart)
                .padding(10.dp)
                .background(MaterialTheme.colorScheme.surface.copy(alpha = 0.92f), RoundedCornerShape(8.dp))
                .padding(horizontal = 8.dp, vertical = 4.dp),
        )
    }
}

private enum class DetailMarkKind { Polity, Neighbor, PlaceName }

private data class DetailMark(val kind: DetailMarkKind, val text: String, val at: Offset)

private fun projectDetailMarks(
    state: AtlasMapState,
    size: IntSize,
    place: RegionEntity,
    neighbors: List<RegionEntity>,
    labels: List<PolityLabel>,
): List<DetailMark> {
    if (size == IntSize.Zero || state.map == null) return emptyList()
    val marks = mutableListOf<DetailMark>()
    val occupied = mutableListOf<Offset>()
    state.project(place.longitude, place.latitude)?.let { occupied += it }
    fun fits(point: Offset): Boolean {
        if (point.x < 8 || point.y < 8 || point.x > size.width - 8 || point.y > size.height - 36) return false
        return occupied.none { kotlin.math.hypot((it.x - point.x).toDouble(), (it.y - point.y).toDouble()) < 88.0 }
    }
    labels.sortedByDescending { it.areaKm2 }.forEach { label ->
        if (marks.count { it.kind == DetailMarkKind.Polity } >= 6) return@forEach
        val text = label.polity.displayName
        if (text.isBlank() || text == place.name) return@forEach
        val point = state.project(label.lon, label.lat) ?: return@forEach
        if (!fits(point)) return@forEach
        occupied += point
        marks += DetailMark(DetailMarkKind.Polity, text, point)
    }
    neighbors.forEach { neighbor ->
        if (marks.count { it.kind == DetailMarkKind.PlaceName } >= 4) return@forEach
        val point = state.project(neighbor.longitude, neighbor.latitude) ?: return@forEach
        if (!fits(point)) return@forEach
        occupied += point
        marks += DetailMark(DetailMarkKind.Neighbor, "", Offset(point.x, point.y - 14f))
        marks += DetailMark(DetailMarkKind.PlaceName, neighbor.name, Offset(point.x, point.y + 10f))
    }
    return marks
}

private fun Modifier.pinAt(point: Offset) = layout { measurable, constraints ->
    val placeable = measurable.measure(constraints.copy(minWidth = 0, minHeight = 0))
    val x = (point.x - placeable.width / 2f).roundToInt()
    val y = (point.y - placeable.height / 2f).roundToInt()
    layout(placeable.width, placeable.height) { placeable.place(x, y) }
}

private fun certaintyLabel(value: String) = when (value) {
    "verified" -> "已证实"
    "inferred" -> "学界推断"
    "disputed" -> "存在争议"
    "unverified" -> "待核查"
    else -> value
}

private fun formatCitation(line: String): String {
    val parts = line.split(" | ")
    if (parts.size < 4) return line
    val title = listOf(parts[0], parts[1], parts[2])
        .filter { it.isNotBlank() && it != "维基百科条目" && it != "条目正文" }
        .joinToString(" · ")
    val url = parts[3]
    return if (url.isBlank()) title else "$title\n$url"
}

private fun readableSyncError(error: Exception): String {
    val raw = error.message.orEmpty()
    return when {
        "failed to connect" in raw || "Unable to resolve" in raw || "timed out" in raw || "Network" in raw ->
            "连不上知识库。离线内容仍可阅读；真机更新需要电脑上的服务地址，模拟器地址在手机上不可用。"
        raw.startsWith("服务器返回") -> raw
        else -> "更新失败"
    }
}
