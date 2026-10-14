package app.changhe

import app.changhe.data.PackageParser
import org.junit.Assert.assertEquals
import org.junit.Test

class PackageParserTest {
    @Test
    fun parseSeedPackageKeepsYearRangeAndCitation() {
        val raw = """
            {"version":0,"full":true,"claims":[{"id":4,"text":"明世宗即位","certainty":"inferred","time_label":"1521–1522","start_year":1521,"end_year":1522,"region_ids":[1],"topic_slugs":["politics"],"citations":[{"id":4,"source_title":"维基百科","edition_label":"明世宗","locator":"条目正文","stable_url":"https://zh.wikipedia.org/wiki/明世宗"}]}],"removed_claim_ids":[],"regions":[{"id":1,"slug":"east-asia","name":"东亚","sort_order":10}]}
        """.trim()

        val parsed = PackageParser.parse(raw)

        assertEquals(1521, parsed.claims.single().start_year)
        assertEquals("条目正文", parsed.claims.single().citations.single().locator)
        assertEquals("东亚", parsed.regions.single().name)
    }
}
