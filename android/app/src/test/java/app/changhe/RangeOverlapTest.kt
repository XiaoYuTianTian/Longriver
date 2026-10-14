package app.changhe

import app.changhe.data.ClaimEntity
import app.changhe.data.RegionEntity
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class RangeOverlapTest {
    @Test
    fun claimOverlapsSelectedSpan() {
        val claim = claim(1912, 1949, 2)
        assertTrue(claim.overlaps(1912, 1949))
        assertTrue(claim.overlaps(1900, 1912))
        assertFalse(claim.overlaps(1950, 1960))
    }

    @Test
    fun placeCardKeepsDescendantsInsideTheSpan() {
        val china = RegionEntity(id = 1, slug = "china", name = "中国", sortOrder = 1, level = "country")
        val nanjing = RegionEntity(id = 2, slug = "nanjing", name = "南京", sortOrder = 2, parentId = 1, level = "city")
        val paris = RegionEntity(id = 3, slug = "paris", name = "巴黎", sortOrder = 3, level = "city")
        val regions = listOf(china, nanjing, paris)
        val claims = listOf(
            claim(1912, 1912, 2),
            claim(1368, 1644, 2),
            claim(1920, 1920, 3),
        )
        val shown = claimsInPlace(claims.filter { it.overlaps(1912, 1949) }, china, regions)
        assertEquals(listOf(1912), shown.map { it.startYear })
    }

    @Test
    fun personWithBothYearsAppearsInEachOverlappingSpan() {
        val person = app.changhe.data.PersonEntity(id = 1, name = "跨代", birthYear = 850, deathYear = 960)
        assertTrue(person.visibleDuring(618, 907))
        assertTrue(person.visibleDuring(960, 1279))
        assertFalse(person.visibleDuring(1368, 1644))
    }

    @Test
    fun personWithoutDeathYearStaysOnTheBirthYear() {
        val person = app.changhe.data.PersonEntity(id = 2, name = "只知生年", birthYear = 701, deathYear = null)
        assertTrue(person.visibleDuring(701, 701))
        assertTrue(person.visibleDuring(618, 907))
        assertFalse(person.visibleDuring(800, 800))
        assertFalse(person.visibleDuring(960, 1279))
    }

    @Test
    fun samePlaceKeepsClaimsWithinThirtyYears() {
        val here = claim(100, 100, 1, id = 1, text = "甲出生于某地。")
        val near = claim(120, 120, 1, id = 2, text = "乙出生于某地。")
        val far = claim(200, 200, 1, id = 3, text = "丙。")
        val other = claim(100, 100, 2, id = 4, text = "战争。", topics = "politics")
        val rows = samePlaceClaims(here, listOf(here, near, far, other))
        assertEquals(listOf(2L), rows.map { it.id })
    }

    @Test
    fun contemporaryPrefersWarOverBirth() {
        val here = claim(100, 120, 1, id = 1, text = "甲出生于某地。")
        val birth = claim(110, 110, 2, id = 2, text = "乙出生于他处。")
        val war = claim(115, 116, 3, id = 3, text = "某战。", topics = "politics")
        val rows = contemporaryClaims(here, listOf(here, birth, war), limit = 1)
        assertEquals(listOf(3L), rows.map { it.id })
    }

    @Test
    fun briefKeepsHeadingAndPlainLead() {
        val blocks = parseBrief("早年从政。\n\n§背景\n两国交兵。")
        assertEquals("", blocks[0].heading)
        assertEquals("早年从政。", blocks[0].text)
        assertEquals("背景", blocks[1].heading)
        assertEquals("两国交兵。", blocks[1].text)
    }

    private fun claim(
        start: Int,
        end: Int,
        regionId: Long,
        id: Long = start.toLong(),
        text: String = "",
        topics: String = "",
    ) = ClaimEntity(
        id = id,
        text = text,
        certainty = "unverified",
        timeLabel = "$start",
        startYear = start,
        endYear = end,
        regionIds = regionId.toString(),
        topicSlugs = topics,
        eventId = id,
        snapshotId = null,
        citationsJson = "",
        searchText = "",
    )
}
