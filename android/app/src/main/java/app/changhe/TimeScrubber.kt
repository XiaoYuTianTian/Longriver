@file:OptIn(ExperimentalMaterial3Api::class)

package app.changhe

import android.graphics.Paint
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.gestures.awaitEachGesture
import androidx.compose.foundation.gestures.awaitFirstDown
import androidx.compose.foundation.gestures.calculateCentroid
import androidx.compose.foundation.gestures.calculatePan
import androidx.compose.foundation.gestures.calculateZoom
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material3.AssistChip
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilledIconButton
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.SegmentedButton
import androidx.compose.material3.SegmentedButtonDefaults
import androidx.compose.material3.SingleChoiceSegmentedButtonRow
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.MutableState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberUpdatedState
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.nativeCanvas
import androidx.compose.ui.graphics.toArgb
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.unit.dp
import kotlin.math.abs
import kotlin.math.ceil

internal const val TIMELINE_START = -3000
internal const val TIMELINE_END = 2026

/** 历史疆域数据截止年份，此后改用现行标准地图。 */
internal const val HISTORICAL_BORDERS_END = 1911

internal data class Era(val name: String, val start: Int, val end: Int)

internal val chinaEras = listOf(
    Era("夏", -2070, -1600), Era("商", -1600, -1046), Era("西周", -1046, -771),
    Era("春秋", -770, -476), Era("战国", -475, -221), Era("秦", -221, -207),
    Era("西汉", -202, 8), Era("新", 9, 23), Era("东汉", 25, 220), Era("三国", 220, 280),
    Era("西晋", 266, 316), Era("东晋", 317, 420), Era("南北朝", 420, 589), Era("隋", 581, 618),
    Era("唐", 618, 907), Era("五代", 907, 979), Era("北宋", 960, 1127), Era("南宋", 1127, 1279),
    Era("元", 1271, 1368), Era("明", 1368, 1644), Era("清", 1644, 1911),
    Era("中华民国", 1912, 1949), Era("中华人民共和国", 1949, TIMELINE_END),
)

internal val worldEras = listOf(
    Era("青铜时代", -3000, -1200), Era("铁器时代", -1200, -500), Era("古典时代", -500, 500),
    Era("中世纪", 500, 1450), Era("近代早期", 1450, 1800), Era("近代", 1800, 1900),
    Era("现代", 1900, TIMELINE_END),
)

private val bandColors = listOf(Color(0xFFE3CDB5), Color(0xFFD2DCCB), Color(0xFFE6D7A8), Color(0xFFCFDBE2))

enum class PlayStep(val years: Int, val label: String) {
    Marks(0, "逐条"), One(1, "每年"), Ten(10, "每10年"), Hundred(100, "每百年");

    fun next() = entries[(ordinal + 1) % entries.size]
}

private enum class DragTarget { None, Start, End, Pan }

private val BAND_HEIGHT = 16.dp
private val BAND_GAP = 2.dp

@Composable
fun TimeScrubber(
    selectionStart: Int,
    selectionEnd: Int,
    marks: List<Int>,
    playing: Boolean,
    step: PlayStep,
    onSelect: (Int, Int) -> Unit,
    onTogglePlay: () -> Unit,
    onStepChange: (PlayStep) -> Unit,
    modifier: Modifier = Modifier,
) {
    val window = remember { mutableStateOf(-600f to TIMELINE_END.toFloat()) }
    var spanMode by remember { mutableStateOf(selectionStart != selectionEnd) }
    if (selectionStart != selectionEnd && !spanMode) spanMode = true
    if (playing && spanMode) spanMode = false
    val marksState = rememberUpdatedState(marks)
    val selection = rememberUpdatedState(selectionStart to selectionEnd)
    val select = rememberUpdatedState(onSelect)
    val spanState = rememberUpdatedState(spanMode)
    val ink = MaterialTheme.colorScheme.onBackground
    val accent = MaterialTheme.colorScheme.secondary
    val primary = MaterialTheme.colorScheme.primary
    val labelArgb = MaterialTheme.colorScheme.onSurfaceVariant.toArgb()
    val inkArgb = ink.toArgb()
    val (visibleStart, visibleEnd) = window.value

    Column(modifier, verticalArrangement = Arrangement.spacedBy(4.dp)) {
        Canvas(
            Modifier
                .fillMaxWidth()
                .height(104.dp)
                .pointerInput(Unit) {
                    awaitEachGesture {
                        val down = awaitFirstDown(requireUnconsumed = false)
                        val width = size.width.toFloat().coerceAtLeast(1f)
                        val bandBottom = (BAND_HEIGHT * 2 + BAND_GAP).toPx()
                        val grab = 24.dp.toPx()
                        fun xOf(year: Int): Float {
                            val (a, b) = window.value
                            return (year - a) / (b - a) * width
                        }
                        val (selStart, selEnd) = selection.value
                        val span = spanState.value
                        val target = when {
                            down.position.y < bandBottom -> DragTarget.Pan
                            span && abs(down.position.x - xOf(selEnd)) < grab &&
                                abs(down.position.x - xOf(selEnd)) <= abs(down.position.x - xOf(selStart)) -> DragTarget.End
                            span && abs(down.position.x - xOf(selStart)) < grab -> DragTarget.Start
                            !span && abs(down.position.x - xOf(selStart)) < grab -> DragTarget.Start
                            else -> DragTarget.Pan
                        }
                        var dragging = false
                        var abandoned = false
                        var multi = false
                        var dx = 0f
                        var dy = 0f
                        while (true) {
                            val event = awaitPointerEvent()
                            val pressed = event.changes.filter { it.pressed }
                            if (pressed.isEmpty()) break
                            if (pressed.size >= 2) {
                                multi = true
                                dragging = true
                                panAndZoom(window, event.calculateCentroid().x, event.calculatePan().x, event.calculateZoom(), width)
                                event.changes.forEach { it.consume() }
                                continue
                            }
                            if (abandoned || multi) continue
                            val change = pressed.first()
                            val stepX = change.position.x - change.previousPosition.x
                            dx += stepX
                            dy += change.position.y - change.previousPosition.y
                            if (!dragging) {
                                if (abs(dx) < viewConfiguration.touchSlop && abs(dy) < viewConfiguration.touchSlop) continue
                                if (target == DragTarget.Pan && abs(dy) > abs(dx)) {
                                    abandoned = true
                                    continue
                                }
                                dragging = true
                            }
                            val year = yearAt(change.position.x, width, window.value)
                            val (curStart, curEnd) = selection.value
                            when (target) {
                                DragTarget.Start ->
                                    if (spanState.value) select.value(minOf(year, curEnd), curEnd) else select.value(year, year)
                                DragTarget.End -> select.value(curStart, maxOf(year, curStart))
                                else -> panAndZoom(window, change.position.x, stepX, 1f, width)
                            }
                            change.consume()
                        }
                        if (!dragging && !abandoned) {
                            val tapX = down.position.x
                            if (down.position.y < bandBottom) {
                                val row = if (down.position.y < BAND_HEIGHT.toPx()) chinaEras else worldEras
                                val year = yearAt(tapX, width, window.value)
                                row.firstOrNull { year in it.start..it.end }?.let { era ->
                                    spanMode = true
                                    select.value(era.start, era.end)
                                    focusWindow(window, era.start, era.end)
                                }
                            } else {
                                val year = snapYear(tapX, width, window.value, marksState.value, 18.dp.toPx())
                                if (spanState.value) {
                                    val (curStart, curEnd) = selection.value
                                    if (abs(year - curStart) <= abs(year - curEnd)) {
                                        select.value(minOf(year, curEnd), curEnd)
                                    } else {
                                        select.value(curStart, maxOf(year, curStart))
                                    }
                                } else {
                                    select.value(year, year)
                                }
                            }
                        }
                    }
                },
        ) {
            val width = size.width
            val visible = (visibleEnd - visibleStart).coerceAtLeast(1f)
            fun xOf(year: Float) = (year - visibleStart) / visible * width
            val bandHeight = BAND_HEIGHT.toPx()
            val bandPaint = Paint().apply {
                isAntiAlias = true
                color = inkArgb
                textAlign = Paint.Align.CENTER
                textSize = 10.dp.toPx()
            }
            listOf(chinaEras to 0f, worldEras to bandHeight + BAND_GAP.toPx()).forEach { (eras, top) ->
                eras.forEachIndexed { i, era ->
                    val left = xOf(era.start.toFloat()).coerceAtLeast(0f)
                    val right = xOf(era.end.toFloat()).coerceAtMost(width)
                    if (right <= left) return@forEachIndexed
                    val chosen = selectionStart == era.start && selectionEnd == era.end
                    drawRoundRect(
                        if (chosen) accent.copy(alpha = 0.45f) else bandColors[i % bandColors.size],
                        topLeft = Offset(left, top),
                        size = Size(right - left - 1f, bandHeight),
                        cornerRadius = CornerRadius(4.dp.toPx()),
                    )
                    if (bandPaint.measureText(era.name) + 6.dp.toPx() < right - left) {
                        drawContext.canvas.nativeCanvas.drawText(era.name, (left + right) / 2f, top + bandHeight * 0.72f, bandPaint)
                    }
                }
            }

            val axisTop = bandHeight * 2 + 4.dp.toPx()
            val axisY = bandHeight * 2 + 22.dp.toPx()
            val leftYear = selectionStart.toFloat()
            val rightYear = selectionEnd.toFloat()
            if (spanMode) {
                val left = xOf(leftYear).coerceIn(0f, width)
                val right = xOf(rightYear).coerceIn(0f, width)
                drawRoundRect(
                    accent.copy(alpha = 0.18f),
                    topLeft = Offset(left, axisTop),
                    size = Size((right - left).coerceAtLeast(2f), size.height - axisTop),
                    cornerRadius = CornerRadius(6.dp.toPx()),
                )
            }
            drawLine(ink.copy(alpha = 0.75f), Offset(0f, axisY), Offset(width, axisY), strokeWidth = 2.dp.toPx())

            val tick = tickStep(visible)
            val tickPaint = Paint().apply {
                isAntiAlias = true
                color = labelArgb
                textAlign = Paint.Align.CENTER
                textSize = 11.dp.toPx()
            }
            var year = ceil(visibleStart / tick) * tick
            while (year <= visibleEnd) {
                val x = xOf(year)
                val major = year % (tick * 2f) == 0f
                drawLine(
                    ink.copy(alpha = if (major) 0.6f else 0.25f),
                    Offset(x, axisY - if (major) 7.dp.toPx() else 4.dp.toPx()),
                    Offset(x, axisY),
                    strokeWidth = 1.2.dp.toPx(),
                )
                if (major) {
                    val label = tickLabel(year.toInt())
                    val half = tickPaint.measureText(label) / 2f
                    drawContext.canvas.nativeCanvas.drawText(label, x.coerceIn(half, width - half), axisY - 10.dp.toPx(), tickPaint)
                }
                year += tick
            }

            val binCount = 60
            val bins = IntArray(binCount)
            marks.forEach { mark ->
                val fraction = (mark - visibleStart) / visible
                if (fraction in 0f..1f) bins[(fraction * (binCount - 1)).toInt()]++
            }
            val maxBin = (bins.maxOrNull() ?: 0).coerceAtLeast(1)
            val binWidth = width / binCount
            val densityTop = axisY + 6.dp.toPx()
            val densityHeight = size.height - densityTop - 2.dp.toPx()
            bins.forEachIndexed { i, count ->
                if (count == 0) return@forEachIndexed
                val h = densityHeight * (0.25f + 0.75f * count / maxBin)
                drawRoundRect(
                    primary.copy(alpha = 0.55f),
                    topLeft = Offset(i * binWidth + 1f, densityTop),
                    size = Size(binWidth - 2f, h),
                    cornerRadius = CornerRadius(2.dp.toPx()),
                )
            }

            val handles = if (spanMode) listOf(leftYear, rightYear) else listOf(leftYear)
            handles.forEach { handleYear ->
                val x = xOf(handleYear)
                if (x !in 0f..width) return@forEach
                drawLine(accent, Offset(x, axisTop), Offset(x, size.height), strokeWidth = 2.dp.toPx())
                if (spanMode) {
                    val w = 12.dp.toPx()
                    val h = 22.dp.toPx()
                    drawRoundRect(Color.White, Offset(x - w / 2 - 1.5f, axisY - h / 2 - 1.5f), Size(w + 3f, h + 3f), CornerRadius(5.dp.toPx()))
                    drawRoundRect(accent, Offset(x - w / 2, axisY - h / 2), Size(w, h), CornerRadius(4.dp.toPx()))
                    for (k in -1..1) {
                        val gy = axisY + k * 4.dp.toPx()
                        drawLine(Color.White, Offset(x - 3.dp.toPx(), gy), Offset(x + 3.dp.toPx(), gy), strokeWidth = 1.dp.toPx())
                    }
                } else {
                    drawCircle(Color.White, 10.dp.toPx(), Offset(x, axisY))
                    drawCircle(accent, 7.dp.toPx(), Offset(x, axisY))
                }
            }
        }
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            SingleChoiceSegmentedButtonRow(Modifier.width(144.dp)) {
                SegmentedButton(
                    selected = !spanMode,
                    onClick = {
                        spanMode = false
                        onSelect(selectionStart, selectionStart)
                    },
                    shape = SegmentedButtonDefaults.itemShape(0, 2),
                    icon = {},
                ) { Text("单年") }
                SegmentedButton(
                    selected = spanMode,
                    onClick = {
                        if (!spanMode) {
                            spanMode = true
                            val width = ((visibleEnd - visibleStart) / 6f).toInt().coerceAtLeast(10)
                            onSelect(selectionStart, (selectionStart + width).coerceAtMost(TIMELINE_END))
                        }
                    },
                    shape = SegmentedButtonDefaults.itemShape(1, 2),
                    icon = {},
                ) { Text("时段") }
            }
            FilledIconButton(onClick = onTogglePlay, modifier = Modifier.size(40.dp)) {
                if (playing) PauseGlyph() else Icon(Icons.Filled.PlayArrow, contentDescription = "播放")
            }
            AssistChip(onClick = { onStepChange(step.next()) }, label = { Text(step.label) })
            Spacer(Modifier.weight(1f))
            AssistChip(
                onClick = { window.value = TIMELINE_START.toFloat() to TIMELINE_END.toFloat() },
                label = { Text("全览") },
            )
        }
        Text(
            if (spanMode) "拖动两端把手调整时段，点上方色带直接选中一个朝代" else "拖动圆点换年份，点上方色带选中整个朝代",
            style = MaterialTheme.typography.labelSmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
    }
}

@Composable
private fun PauseGlyph() {
    val tint = MaterialTheme.colorScheme.onPrimary
    Canvas(Modifier.size(16.dp)) {
        val bar = size.width * 0.3f
        drawRect(tint, topLeft = Offset(size.width * 0.12f, 0f), size = Size(bar, size.height))
        drawRect(tint, topLeft = Offset(size.width * 0.58f, 0f), size = Size(bar, size.height))
    }
}

internal fun formatYear(year: Int): String = when {
    year > 0 -> "${year}年"
    year == 0 -> "公元前1年"
    else -> "公元前${-year}年"
}

internal fun formatSpan(start: Int, end: Int): String =
    if (start == end) formatYear(start) else "${formatYear(start)} – ${formatYear(end)}"

private fun tickLabel(year: Int): String = when {
    year > 0 -> year.toString()
    year == 0 -> "前1"
    else -> "前${-year}"
}

private fun tickStep(visibleYears: Float): Float = when {
    visibleYears > 3000f -> 250f
    visibleYears > 1500f -> 100f
    visibleYears > 600f -> 50f
    visibleYears > 240f -> 25f
    visibleYears > 80f -> 10f
    visibleYears > 30f -> 5f
    else -> 1f
}

private fun yearAt(x: Float, width: Float, window: Pair<Float, Float>): Int {
    val (start, end) = window
    return (start + (x / width).coerceIn(0f, 1f) * (end - start)).toInt().coerceIn(TIMELINE_START, TIMELINE_END)
}

private fun snapYear(x: Float, width: Float, window: Pair<Float, Float>, marks: List<Int>, snapPx: Float): Int {
    val (start, end) = window
    val tapped = yearAt(x, width, window)
    val nearest = marks.minByOrNull { abs(it - tapped) } ?: return tapped
    val pixels = abs(nearest - tapped) / ((end - start) / width).coerceAtLeast(0.001f)
    return if (pixels <= snapPx) nearest else tapped
}

private fun focusWindow(window: MutableState<Pair<Float, Float>>, start: Int, end: Int) {
    val pad = ((end - start) * 0.25f).coerceAtLeast(8f)
    val from = (start - pad).coerceAtLeast(TIMELINE_START.toFloat())
    val to = (end + pad).coerceAtMost(TIMELINE_END.toFloat())
    window.value = from to maxOf(to, from + 12f)
}

private fun panAndZoom(window: MutableState<Pair<Float, Float>>, focalX: Float, panX: Float, zoom: Float, width: Float) {
    val (visibleStart, visibleEnd) = window.value
    val visible = (visibleEnd - visibleStart).coerceAtLeast(8f)
    val focal = visibleStart + focalX / width * visible
    val next = (visible / zoom).coerceIn(12f, (TIMELINE_END - TIMELINE_START).toFloat())
    val left = (focal - visibleStart) / visible
    var start = focal - left * next - panX / width * next
    var end = start + next
    if (start < TIMELINE_START) {
        end += TIMELINE_START - start
        start = TIMELINE_START.toFloat()
    }
    if (end > TIMELINE_END) {
        start -= end - TIMELINE_END
        end = TIMELINE_END.toFloat()
    }
    window.value = start to end
}
