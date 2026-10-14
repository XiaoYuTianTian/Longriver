package app.longriver

import android.graphics.Color as AndroidColor
import android.graphics.PointF
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberUpdatedState
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.viewinterop.AndroidView
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import androidx.lifecycle.compose.LocalLifecycleOwner
import java.net.URI
import kotlinx.coroutines.delay
import org.maplibre.android.MapLibre
import org.maplibre.android.camera.CameraPosition
import org.maplibre.android.camera.CameraUpdateFactory
import org.maplibre.android.geometry.LatLng
import org.maplibre.android.maps.MapLibreMap
import org.maplibre.android.maps.MapLibreMapOptions
import org.maplibre.android.maps.MapView
import org.maplibre.android.maps.Style
import org.maplibre.android.style.expressions.Expression
import org.maplibre.android.style.layers.FillLayer
import org.maplibre.android.style.layers.LineLayer
import org.maplibre.android.style.layers.PropertyFactory
import org.maplibre.android.style.layers.RasterLayer
import org.maplibre.android.style.sources.RasterSource
import org.maplibre.android.style.sources.TileSet
import org.maplibre.android.style.layers.TransitionOptions
import org.maplibre.android.style.sources.GeoJsonSource

private const val FILL_OPACITY = 0.74f
private const val LINE_OPACITY = 0.95f

private val BORDER_PALETTE = listOf(
    "#C45A32", "#3E8A58", "#C49A1C", "#2F6F9A", "#A24E7A", "#6B7C28", "#B86A3A", "#4A5F9A",
)

class AtlasMapState {
    var map by mutableStateOf<MapLibreMap?>(null)
        internal set
    var cameraTick by mutableIntStateOf(0)
        internal set
    var loadingBorders by mutableStateOf(false)
        internal set

    val zoom: Double get() = map?.cameraPosition?.zoom ?: 0.0

    fun project(lon: Double, lat: Double): Offset? {
        val point = map?.projection?.toScreenLocation(LatLng(lat, lon)) ?: return null
        return Offset(point.x, point.y)
    }

    fun isVisible(lon: Double, lat: Double): Boolean =
        map?.projection?.visibleRegion?.latLngBounds?.contains(LatLng(lat, lon)) ?: false

    fun flyTo(lon: Double, lat: Double, zoom: Double) {
        map?.animateCamera(CameraUpdateFactory.newLatLngZoom(LatLng(lat, lon), zoom), 600)
    }
}

@Composable
fun rememberAtlasMapState() = remember { AtlasMapState() }

@Composable
fun AtlasMap(
    year: Int,
    showBorders: Boolean,
    state: AtlasMapState,
    modifier: Modifier = Modifier,
    interactive: Boolean = true,
    initialLon: Double = 70.0,
    initialLat: Double = 30.0,
    initialZoom: Double = 0.6,
    texture: Boolean = false,
    onPolityTap: (Long) -> Unit = {},
    onCountryTap: (String) -> Unit = {},
) {
    val context = LocalContext.current
    val lifecycle = LocalLifecycleOwner.current.lifecycle
    val index = remember { AtlasAssets.polities(context) }
    val tap by rememberUpdatedState(onPolityTap)
    val countryTap by rememberUpdatedState(onCountryTap)
    val bordersOn by rememberUpdatedState(showBorders && !isModernYear(year))
    val countriesOn by rememberUpdatedState(showBorders && isModernYear(year) && !hasModernBase)
    val borders = remember { BorderLayers(index) }
    val mapView = remember {
        MapLibre.getInstance(context)
        val options = MapLibreMapOptions.createFromAttributes(context)
            .camera(CameraPosition.Builder().target(LatLng(initialLat, initialLon)).zoom(initialZoom).build())
            .logoEnabled(false)
            .attributionEnabled(false)
            .compassEnabled(false)
            .rotateGesturesEnabled(false)
            .tiltGesturesEnabled(false)
            .scrollGesturesEnabled(interactive)
            .zoomGesturesEnabled(interactive)
            .doubleTapGesturesEnabled(interactive)
            .textureMode(texture)
        MapView(context, options).apply { onCreate(null) }
    }

    DisposableEffect(lifecycle, mapView) {
        val observer = LifecycleEventObserver { _, event ->
            when (event) {
                Lifecycle.Event.ON_START -> mapView.onStart()
                Lifecycle.Event.ON_RESUME -> mapView.onResume()
                Lifecycle.Event.ON_PAUSE -> mapView.onPause()
                Lifecycle.Event.ON_STOP -> mapView.onStop()
                else -> Unit
            }
        }
        lifecycle.addObserver(observer)
        if (lifecycle.currentState.isAtLeast(Lifecycle.State.STARTED)) mapView.onStart()
        if (lifecycle.currentState.isAtLeast(Lifecycle.State.RESUMED)) mapView.onResume()
        onDispose {
            lifecycle.removeObserver(observer)
            state.map = null
            mapView.onPause()
            mapView.onStop()
            mapView.onDestroy()
        }
    }

    LaunchedEffect(mapView) {
        mapView.getMapAsync { map ->
            map.setMinZoomPreference(0.3)
            map.setMaxZoomPreference(9.0)
            map.setStyle(Style.Builder().fromJson(ATLAS_STYLE)) { style ->
                style.addSource(GeoJsonSource("land", URI("asset://land.geojson")))
                style.addLayer(
                    FillLayer("land-fill", "land").withProperties(
                        PropertyFactory.fillColor(AndroidColor.parseColor("#E8DFD0")),
                    ),
                )
                installCountries(style)
                installModernBase(style)
                borders.install(style)
                applyYear(style, borders, year, showBorders)
                map.addOnCameraMoveListener { state.cameraTick++ }
                map.addOnCameraIdleListener { state.cameraTick++ }
                map.addOnMapClickListener { latLng ->
                    val point = map.projection.toScreenLocation(latLng)
                    if (bordersOn) {
                        val pid = borders.polityAt(map, point)
                        if (pid != null) {
                            tap(pid)
                            return@addOnMapClickListener true
                        }
                    }
                    if (countriesOn) {
                        val name = map.queryRenderedFeatures(point, "countries-fill")
                            .firstNotNullOfOrNull { it.getStringProperty("n")?.takeIf { text -> text.isNotBlank() } }
                        if (name != null) {
                            countryTap(name)
                            return@addOnMapClickListener true
                        }
                    }
                    false
                }
                state.map = map
                state.cameraTick++
            }
        }
    }

    LaunchedEffect(year, showBorders, state.map) {
        val style = state.map?.style ?: return@LaunchedEffect
        val historical = showBorders && !isModernYear(year)
        state.loadingBorders = historical
        applyYear(style, borders, year, showBorders)
        if (historical) {
            delay(400)
            state.loadingBorders = false
        } else {
            state.loadingBorders = false
        }
    }

    AndroidView(factory = { mapView }, modifier = modifier)
}

internal fun isModernYear(year: Int) = year > HISTORICAL_BORDERS_END

internal val hasModernBase: Boolean get() = BuildConfig.TIANDITU_KEY.isNotBlank()

private val MODERN_LAYERS = listOf("vec", "cva")

private fun installCountries(style: Style) {
    style.addSource(GeoJsonSource("countries", URI("asset://countries.geojson")))
    val colors = Expression.match(
        Expression.get("c"),
        Expression.color(AndroidColor.parseColor(BORDER_PALETTE[0])),
        *BORDER_PALETTE.mapIndexed { i, hex ->
            Expression.stop(i, Expression.color(AndroidColor.parseColor(hex)))
        }.toTypedArray(),
    )
    style.addLayer(
        FillLayer("countries-fill", "countries").withProperties(
            PropertyFactory.fillColor(colors),
            PropertyFactory.fillOpacity(0f),
        ),
    )
    style.addLayer(
        LineLayer("countries-line", "countries").withProperties(
            PropertyFactory.lineColor(AndroidColor.parseColor("#3F3428")),
            PropertyFactory.lineWidth(2.2f),
            PropertyFactory.lineOpacity(0f),
        ),
    )
}

private fun installModernBase(style: Style) {
    if (!hasModernBase) return
    MODERN_LAYERS.forEach { layer ->
        val urls = (0..7).map { n ->
            "https://t$n.tianditu.gov.cn/${layer}_w/wmts?SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0" +
                "&LAYER=$layer&STYLE=default&TILEMATRIXSET=w&FORMAT=tiles" +
                "&TILEMATRIX={z}&TILEROW={y}&TILECOL={x}&tk=${BuildConfig.TIANDITU_KEY}"
        }
        style.addSource(RasterSource("tdt-$layer", TileSet("2.1.0", *urls.toTypedArray()), 256))
        val raster = RasterLayer("tdt-$layer", "tdt-$layer").withProperties(PropertyFactory.rasterOpacity(0f))
        raster.rasterOpacityTransition = TransitionOptions(300, 0)
        style.addLayer(raster)
    }
}

private fun applyYear(style: Style, borders: BorderLayers, year: Int, showBorders: Boolean) {
    val modern = isModernYear(year)
    val showCountries = showBorders && modern && !hasModernBase
    val showTianditu = showBorders && modern && hasModernBase
    style.getLayerAs<FillLayer>("countries-fill")?.setProperties(
        PropertyFactory.fillOpacity(if (showCountries) FILL_OPACITY else 0f),
    )
    style.getLayerAs<LineLayer>("countries-line")?.setProperties(
        PropertyFactory.lineOpacity(if (showCountries) LINE_OPACITY else 0f),
    )
    MODERN_LAYERS.forEach { layer ->
        style.getLayerAs<RasterLayer>("tdt-$layer")?.setProperties(
            PropertyFactory.rasterOpacity(if (showTianditu) 1f else 0f),
        )
    }
    borders.show(style, year.coerceAtMost(HISTORICAL_BORDERS_END), showBorders && !modern)
}

private class BorderLayers(private val index: PolityIndex) {
    private var active = 0
    private val buckets = intArrayOf(-1, -1)
    private var shownYear: Int? = null

    fun install(style: Style) {
        for (slot in 0..1) {
            style.addSource(GeoJsonSource("borders-$slot"))
            val colors = Expression.match(
                Expression.get("c"),
                Expression.color(AndroidColor.parseColor(BORDER_PALETTE[0])),
                *BORDER_PALETTE.mapIndexed { i, hex ->
                    Expression.stop(i, Expression.color(AndroidColor.parseColor(hex)))
                }.toTypedArray(),
            )
            val fill = FillLayer("borders-fill-$slot", "borders-$slot").withProperties(
                PropertyFactory.fillColor(colors),
                PropertyFactory.fillOpacity(0f),
            )
            fill.fillOpacityTransition = TransitionOptions(260, 0)
            val line = LineLayer("borders-line-$slot", "borders-$slot").withProperties(
                PropertyFactory.lineColor(AndroidColor.parseColor("#3F3428")),
                PropertyFactory.lineWidth(2.4f),
                PropertyFactory.lineOpacity(0f),
            )
            line.lineOpacityTransition = TransitionOptions(260, 0)
            style.addLayer(fill)
            style.addLayer(line)
        }
    }

    fun show(style: Style, year: Int, visible: Boolean) {
        if (shownYear == year) {
            applyOpacity(style, if (visible) active else -1)
            return
        }
        val target = if (shownYear == null) active else 1 - active
        val bucket = index.bucketFor(year)
        if (buckets[target] != bucket) {
            style.getSourceAs<GeoJsonSource>("borders-$target")?.setUri(URI("asset://borders/$bucket.geojson"))
            buckets[target] = bucket
        }
        val filter = Expression.all(
            Expression.lte(Expression.get("f"), Expression.literal(year)),
            Expression.gte(Expression.get("t"), Expression.literal(year)),
        )
        style.getLayerAs<FillLayer>("borders-fill-$target")?.setFilter(filter)
        style.getLayerAs<LineLayer>("borders-line-$target")?.setFilter(filter)
        active = target
        shownYear = year
        applyOpacity(style, if (visible) active else -1)
    }

    private fun applyOpacity(style: Style, visibleSlot: Int) {
        for (slot in 0..1) {
            val on = slot == visibleSlot
            style.getLayerAs<FillLayer>("borders-fill-$slot")?.setProperties(
                PropertyFactory.fillOpacity(if (on) FILL_OPACITY else 0f),
            )
            style.getLayerAs<LineLayer>("borders-line-$slot")?.setProperties(
                PropertyFactory.lineOpacity(if (on) LINE_OPACITY else 0f),
            )
        }
    }

    fun polityAt(map: MapLibreMap, point: PointF): Long? =
        map.queryRenderedFeatures(point, "borders-fill-$active")
            .mapNotNull { it.getNumberProperty("p")?.toLong() }
            .firstOrNull()
}

private const val ATLAS_STYLE = """
{
  "version": 8,
  "sources": {},
  "layers": [
    {"id": "ocean", "type": "background", "paint": {"background-color": "#D5E3E3"}}
  ]
}
"""
