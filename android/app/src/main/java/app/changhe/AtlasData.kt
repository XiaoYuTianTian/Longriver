package app.changhe

import android.content.Context
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json

@Serializable
data class PolityInfo(
    val id: Long,
    val name: String,
    val zh: String,
    val capital: String = "",
    val wikipedia: String = "",
    val from: Int,
    val to: Int,
    val labels: List<List<Double>> = emptyList(),
) {
    /** 界面默认中文；没有汉字译名时才退回数据集里的拉丁名。 */
    val displayName: String get() = if (zh.any { it.isHan() }) zh else name

    /** 与中文不同的拉丁名，只在详情里作副标题。 */
    val latinName: String? get() = name.takeIf { it.isNotBlank() && it != displayName }
}

private fun Char.isHan(): Boolean = Character.UnicodeScript.of(code) == Character.UnicodeScript.HAN

@Serializable
data class PolityIndex(
    val attribution: String,
    val start: Int,
    val bucket_years: Int,
    val polities: List<PolityInfo>,
) {
    private val byId by lazy { polities.associateBy { it.id } }

    fun polity(id: Long): PolityInfo? = byId[id]

    fun bucketFor(year: Int): Int = (year - start).coerceAtLeast(0) / bucket_years

    fun labelsAt(year: Int): List<PolityLabel> = polities.mapNotNull { polity ->
        polity.labels.firstOrNull { it[0] <= year && year <= it[1] }?.let {
            PolityLabel(polity, it[2], it[3], it[4])
        }
    }
}

data class PolityLabel(val polity: PolityInfo, val lon: Double, val lat: Double, val areaKm2: Double)

object AtlasAssets {
    private val json = Json { ignoreUnknownKeys = true }
    @Volatile private var cached: PolityIndex? = null
    @Volatile private var countryLabelCache: List<PolityLabel>? = null

    fun polities(context: Context): PolityIndex = cached ?: synchronized(this) {
        cached ?: context.assets.open("polities.json").bufferedReader().use { reader ->
            json.decodeFromString<PolityIndex>(reader.readText())
        }.also { cached = it }
    }

    fun countryLabels(context: Context): List<PolityLabel> = countryLabelCache ?: synchronized(this) {
        countryLabelCache ?: context.assets.open("country-labels.json").bufferedReader().use { reader ->
            json.decodeFromString<List<CountryLabelRow>>(reader.readText()).mapIndexed { index, row ->
                PolityLabel(
                    PolityInfo(
                        id = -(index + 1).toLong(),
                        name = "",
                        zh = row.n,
                        from = HISTORICAL_BORDERS_END + 1,
                        to = TIMELINE_END,
                    ),
                    row.lon,
                    row.lat,
                    row.a.toDouble(),
                )
            }
        }.also { countryLabelCache = it }
    }
}

@Serializable
private data class CountryLabelRow(val n: String, val lon: Double, val lat: Double, val a: Int)
