"""Fill missing Chinese names for Cliopatria polities.

Looks up English Wikipedia titles on Wikidata, converts to simplified Chinese,
then patches polity_names_zh.json and content/dist/polities.json. Does not rebuild
border geometry.

    python content/fill_polity_zh.py
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from opencc import OpenCC

T2S = OpenCC("t2s")
ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / "content"
ASSETS = CONTENT / "dist"
TABLE = CONTENT / "polity_names_zh.json"
POLITIES = ASSETS / "polities.json"
CACHE = CONTENT / "raw" / "wikidata"
USER_AGENT = "LongriverContentBuild/0.3 (historical atlas; Chinese labels)"
HAN = re.compile(r"[\u4e00-\u9fff]")

# Extra names Wikidata often misses or labels poorly.
MANUAL = json.loads((ROOT / "content" / "polity_names_extra_zh.json").read_text(encoding="utf-8"))
MANUAL.update({
    "Aztec Empire": "阿兹特克帝国",
    "Aztec": "阿兹特克",
    "Inca Empire": "印加帝国",
    "Maya": "玛雅",
    "Mississippian culture": "密西西比文化",
    "Pueblo": "普韦布洛",
    "Five Dynasties": "五代",
    "Sixteen Kingdoms": "十六国",
    "Ten Kingdoms": "十国",
    "Spring and Autumn": "春秋",
    "Warring States": "战国",
    "Northern and Southern dynasties": "南北朝",
    "Three Kingdoms": "三国",
    "Later Zhao": "后赵",
    "Former Qin": "前秦",
    "Later Qin": "后秦",
    "Western Qin": "西秦",
    "Former Yan": "前燕",
    "Later Yan": "后燕",
    "Southern Yan": "南燕",
    "Northern Yan": "北燕",
    "Former Liang": "前凉",
    "Later Liang (Five Dynasties)": "后梁",
    "Western Liang": "西凉",
    "Northern Liang": "北凉",
    "Southern Liang": "南凉",
    "Cheng Han": "成汉",
    "Dai": "代",
    "Xia (Sixteen Kingdoms)": "夏",
    "Northern Wei": "北魏",
    "Eastern Wei": "东魏",
    "Western Wei": "西魏",
    "Northern Qi": "北齐",
    "Northern Zhou": "北周",
    "Liu Song": "刘宋",
    "Southern Qi": "南齐",
    "Liang Dynasty": "梁",
    "Chen Dynasty": "陈",
    "Wu Zhou": "武周",
    "Dali Kingdom": "大理",
    "Nanzhao": "南诏",
    "Bohai": "渤海",
    "Balhae": "渤海",
    "Gojoseon": "古朝鲜",
    "Goguryeo": "高句丽",
    "Baekje": "百济",
    "Silla": "新罗",
    "Goryeo": "高丽",
    "Joseon": "朝鲜",
    "Yamato": "大和",
    "Ashikaga shogunate": "室町幕府",
    "Tokugawa shogunate": "江户幕府",
    "Kamakura shogunate": "镰仓幕府",
    "Sultanate of Delhi": "德里苏丹国",
    "Delhi Sultanate": "德里苏丹国",
    "Chola Empire": "注辇",
    "Maurya Empire": "孔雀帝国",
    "Gupta Empire": "笈多王朝",
    "Kushan Empire": "贵霜帝国",
    "Satavahana": "萨塔瓦哈那",
    "Pala Empire": "波罗王朝",
    "Vijayanagara Empire": "毗奢耶那伽罗",
    "Maratha Empire": "马拉塔帝国",
    "Ayyubid dynasty": "阿尤布王朝",
    "Fatimid Caliphate": "法蒂玛王朝",
    "Mamluk Sultanate": "马穆鲁克苏丹国",
    "Seljuk Empire": "塞尔柱帝国",
    "Khwarazmian Empire": "花剌子模帝国",
    "Timurid Empire": "帖木儿帝国",
    "Ilkhanate": "伊利汗国",
    "Chagatai Khanate": "察合台汗国",
    "Yuan": "元",
    "Northern Yuan": "北元",
    "Dzungar Khanate": "准噶尔汗国",
    "Kara-Khanid Khanate": "喀喇汗国",
    "Qara Khitai": "西辽",
    "Western Liao": "西辽",
    "Jin dynasty (1115–1234)": "金",
    "Jurchen Jin": "金",
    "Western Xia": "西夏",
    "Liao dynasty": "辽",
    "Khitan": "契丹",
    "Holy Roman Empire": "神圣罗马帝国",
    "Papal States": "教皇国",
    "Republic of Venice": "威尼斯共和国",
    "Republic of Genoa": "热那亚共和国",
    "Crown of Aragon": "阿拉贡联合王国",
    "Crown of Castile": "卡斯蒂利亚王国",
    "Kingdom of León": "莱昂王国",
    "Caliphate of Córdoba": "科尔多瓦哈里发国",
    "Almoravid dynasty": "穆拉比特王朝",
    "Almohad Caliphate": "穆瓦希德王朝",
    "Emirate of Granada": "格拉纳达酋长国",
    "Kingdom of the Franks": "法兰克王国",
    "Carolingian Empire": "加洛林帝国",
    "Merovingian dynasty": "墨洛温王朝",
    "West Francia": "西法兰克",
    "East Francia": "东法兰克",
    "Middle Francia": "中法兰克",
    "Byzantine Empire": "拜占庭帝国",
    "Latin Empire": "拉丁帝国",
    "Bulgarian Empire": "保加利亚帝国",
    "Serbian Empire": "塞尔维亚帝国",
    "Kievan Rus'": "基辅罗斯",
    "Novgorod Republic": "诺夫哥罗德共和国",
    "Grand Duchy of Lithuania": "立陶宛大公国",
    "Polish–Lithuanian Commonwealth": "波兰立陶宛联邦",
    "Habsburg monarchy": "哈布斯堡君主国",
    "Austrian Empire": "奥地利帝国",
    "Austria-Hungary": "奥匈帝国",
    "German Empire": "德意志帝国",
    "German Confederation": "德意志邦联",
    "Kingdom of Italy": "意大利王国",
    "Kingdom of Sardinia": "撒丁王国",
    "Kingdom of the Two Sicilies": "两西西里王国",
    "Duchy of Savoy": "萨伏依公国",
    "Grand Duchy of Tuscany": "托斯卡纳大公国",
    "Republic of the Seven United Netherlands": "荷兰共和国",
    "Spanish Netherlands": "西属尼德兰",
    "Kalmar Union": "卡尔马联盟",
    "Kingdom of Denmark–Norway": "丹麦—挪威",
    "Swedish Empire": "瑞典帝国",
    "Tsardom of Russia": "俄国沙皇国",
    "Grand Duchy of Moscow": "莫斯科大公国",
    "Crimean Khanate": "克里米亚汗国",
    "Khanate of Kazan": "喀山汗国",
    "Khanate of Astrakhan": "阿斯特拉罕汗国",
    "Nogai Horde": "诺盖汗国",
    "White Horde": "白帐汗国",
    "Blue Horde": "青帐汗国",
    "Chichimeca": "奇奇梅卡",
    "Tarascan": "塔拉斯科",
    "Purepecha": "普雷佩查",
    "Mapuche": "马普切",
    "Zulu Kingdom": "祖鲁王国",
    "Mali Empire": "马里帝国",
    "Songhai Empire": "桑海帝国",
    "Ghana Empire": "加纳帝国",
    "Kanem–Bornu": "卡奈姆—博尔努",
    "Kanem-Bornu Empire": "卡奈姆—博尔努帝国",
    "Benin Empire": "贝宁王国",
    "Oyo Empire": "奥约帝国",
    "Ashanti Empire": "阿散蒂帝国",
    "Kingdom of Aksum": "阿克苏姆王国",
    "Ethiopian Empire": "埃塞俄比亚帝国",
    "Sultanate of Kilwa": "基尔瓦苏丹国",
    "Ajuran Sultanate": "阿朱兰苏丹国",
    "Sokoto Caliphate": "索科托哈里发国",
    "Wassoulou Empire": "瓦苏卢帝国",
    "Kongo": "刚果王国",
    "Kingdom of Kongo": "刚果王国",
    "Luba Empire": "卢巴帝国",
    "Lunda Empire": "隆达帝国",
    "Rozvi Empire": "罗兹维帝国",
    "Mutapa Empire": "穆塔帕帝国",
    "Great Zimbabwe": "大津巴布韦",
    "Hunnic Empire": "匈人帝国",
    "Avars": "阿瓦尔",
    "Khazar Khaganate": "可萨汗国",
    "Volga Bulgaria": "伏尔加保加利亚",
    "Pechenegs": "佩切涅格",
    "Cuman-Kipchak confederation": "钦察联盟",
    "Scythians": "斯基泰",
    "Sarmatians": "萨尔马提亚人",
    "Parthia": "帕提亚",
    "Seleucid Empire": "塞琉古帝国",
    "Ptolemaic Kingdom": "托勒密王国",
    "Antigonid dynasty": "安提柯王朝",
    "Macedonian Empire": "马其顿帝国",
    "Kingdom of Macedon": "马其顿王国",
    "Delian League": "提洛同盟",
    "Sparta": "斯巴达",
    "Athens": "雅典",
    "Thebes": "底比斯",
    "Carthage": "迦太基",
    "Phoenicia": "腓尼基",
    "Israel": "以色列",
    "Judah": "犹大王国",
    "Neo-Assyrian Empire": "新亚述帝国",
    "Neo-Babylonian Empire": "新巴比伦帝国",
    "Old Babylonian Empire": "古巴比伦",
    "Akkadian Empire": "阿卡德帝国",
    "Sumer": "苏美尔",
    "Elam": "埃兰",
    "Urartu": "乌拉尔图",
    "Median Empire": "米底王国",
    "Lydia": "吕底亚",
    "Phrygia": "弗里吉亚",
    "Hittite Empire": "赫梯帝国",
    "Mitanni": "米坦尼",
    "New Kingdom of Egypt": "埃及新王国",
    "Middle Kingdom of Egypt": "埃及中王国",
    "Old Kingdom of Egypt": "埃及古王国",
    "Ptolemaic Egypt": "托勒密埃及",
    "Nubia": "努比亚",
    "Kingdom of Axum": "阿克苏姆王国",
    "Saba": "萨巴",
    "Himyar": "希木叶尔",
    "Nabataean Kingdom": "纳巴泰王国",
    "Palmyrene Empire": "巴尔米拉帝国",
    "Gallic Empire": "高卢帝国",
    "Western Roman Empire": "西罗马帝国",
    "Ostrogothic Kingdom": "东哥特王国",
    "Visigothic Kingdom": "西哥特王国",
    "Vandal Kingdom": "汪达尔王国",
    "Frankish Empire": "法兰克帝国",
    "Lombard Kingdom": "伦巴第王国",
    "Avar Khaganate": "阿瓦尔汗国",
    "First Bulgarian Empire": "第一保加利亚帝国",
    "Second Bulgarian Empire": "第二保加利亚帝国",
    "Umayyad Caliphate of Córdoba": "后倭马亚王朝",
    "Rashidun Caliphate": "正统哈里发国",
    "Abbasid": "阿拔斯王朝",
    "Buyid dynasty": "白益王朝",
    "Samanid Empire": "萨曼王朝",
    "Ghaznavid Empire": "伽色尼王朝",
    "Ghurid dynasty": "古尔王朝",
    "Ayyubids": "阿尤布王朝",
    "Ottoman": "奥斯曼帝国",
    "Safavid": "萨法维王朝",
    "Afsharid": "阿夫沙尔王朝",
    "Zand dynasty": "赞德王朝",
    "Qajar": "卡扎尔王朝",
    "Hotak dynasty": "霍塔克王朝",
    "Durrani Empire": "杜兰尼帝国",
    "Sikh Empire": "锡克帝国",
    "Confederate States of America": "美利坚联盟国",
    "Thirteen Colonies": "十三殖民地",
    "New Spain": "新西班牙",
    "Viceroyalty of Peru": "秘鲁总督辖区",
    "Viceroyalty of New Granada": "新格拉纳达总督辖区",
    "Viceroyalty of the Río de la Plata": "拉普拉塔总督辖区",
    "Portuguese Brazil": "葡属巴西",
    "Dutch Brazil": "荷属巴西",
    "Gran Colombia": "大哥伦比亚",
    "United Kingdom of Great Britain and Ireland": "大不列颠及爱尔兰联合王国",
    "Kingdom of Great Britain": "大不列颠王国",
    "Kingdom of England": "英格兰王国",
    "Kingdom of Scotland": "苏格兰王国",
    "Kingdom of France": "法兰西王国",
    "French Republic": "法兰西共和国",
    "First French Empire": "法兰西第一帝国",
    "July Monarchy": "七月王朝",
    "Second French Empire": "法兰西第二帝国",
    "Napoleonic France": "拿破仑法国",
    "Kingdom of Poland": "波兰王国",
    "Duchy of Warsaw": "华沙公国",
    "Congress Poland": "会议波兰",
    "Electorate of Saxony": "萨克森选侯国",
    "Electorate of Bavaria": "巴伐利亚选侯国",
    "Electorate of Brandenburg": "勃兰登堡选侯国",
    "Electorate of Hanover": "汉诺威选侯国",
    "Kingdom of Bavaria": "巴伐利亚王国",
    "Kingdom of Saxony": "萨克森王国",
    "Kingdom of Württemberg": "符腾堡王国",
    "Kingdom of Hanover": "汉诺威王国",
    "Grand Duchy of Baden": "巴登大公国",
    "Grand Duchy of Hesse": "黑森大公国",
    "Swiss Confederation": "瑞士联邦",
    "Old Swiss Confederacy": "旧瑞士邦联",
    "Papal State": "教皇国",
    "Knights Hospitaller": "医院骑士团",
    "Teutonic Order": "条顿骑士团",
    "Livonian Order": "利沃尼亚骑士团",
    "Golden Horde remnant": "金帐汗国残部",
})

PREFIX_MAP = [
    (r"^Kingdom of (.+)$", "{}王国"),
    (r"^Empire of (.+)$", "{}帝国"),
    (r"^Duchy of (.+)$", "{}公国"),
    (r"^Grand Duchy of (.+)$", "{}大公国"),
    (r"^County of (.+)$", "{}伯国"),
    (r"^Principality of (.+)$", "{}公国"),
    (r"^Emirate of (.+)$", "{}酋长国"),
    (r"^Sultanate of (.+)$", "{}苏丹国"),
    (r"^Khanate of (.+)$", "{}汗国"),
    (r"^Republic of (.+)$", "{}共和国"),
    (r"^Caliphate of (.+)$", "{}哈里发国"),
    (r"^Electorate of (.+)$", "{}选侯国"),
    (r"^Margraviate of (.+)$", "{}藩侯国"),
    (r"^Archduchy of (.+)$", "{}大公国"),
    (r"^Viceroyalty of (.+)$", "{}总督辖区"),
    (r"^(.+) Empire$", "{}帝国"),
    (r"^(.+) Kingdom$", "{}王国"),
    (r"^(.+) Dynasty$", "{}"),
    (r"^(.+) Khanate$", "{}汗国"),
    (r"^(.+) Sultanate$", "{}苏丹国"),
    (r"^(.+) Caliphate$", "{}哈里发国"),
    (r"^(.+) Republic$", "{}共和国"),
    (r"^(.+) Confederacy$", "{}邦联"),
    (r"^(.+) Confederation$", "{}联盟"),
]


def has_han(text: str) -> bool:
    return bool(HAN.search(text or ""))


def simplify(text: str) -> str:
    return T2S.convert(text).strip()


def chunks(items: list, size: int):
    for i in range(0, len(items), size):
        yield items[i : i + size]


ENDPOINT = "https://qlever.dev/api/wikidata"
PREFIX = """PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX schema: <http://schema.org/>
"""


def sparql(query: str) -> list[dict]:
    body = urllib.parse.urlencode({"query": PREFIX + query}).encode()
    request = urllib.request.Request(
        ENDPOINT,
        data=body,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/sparql-results+json",
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )
    with urllib.request.urlopen(request, timeout=180) as response:
        return json.load(response)["results"]["bindings"]


def cache_path(title: str) -> Path:
    key = hashlib.sha1(title.encode()).hexdigest()[:12]
    return CACHE / f"zhlabel-{key}.json"


def cached_entities(titles: list[str], refresh: bool) -> dict[str, str]:
    CACHE.mkdir(parents=True, exist_ok=True)
    found: dict[str, str] = {}
    pending = []
    for title in titles:
        path = cache_path(title)
        if path.exists() and not refresh:
            zh = json.loads(path.read_text(encoding="utf-8")).get("zh") or ""
            if zh:
                found[title] = zh
        else:
            pending.append(title)
    print(f"lookup {len(pending)} titles via QLever, {len(found)} already cached")
    for i, batch in enumerate(chunks(pending, 60)):
        values = " ".join('"' + title.replace('"', '\\"') + '"' for title in batch)
        query = f"""
SELECT ?title ?zh WHERE {{
  VALUES ?title {{ {values} }}
  {{
    ?article schema:about ?item ; schema:isPartOf <https://en.wikipedia.org/> ; schema:name ?title .
  }} UNION {{
    ?item rdfs:label ?en .
    FILTER(LANG(?en) = "en" && STR(?en) = ?title)
  }}
  OPTIONAL {{ ?item rdfs:label ?a . FILTER(LANG(?a) = "zh-cn") }}
  OPTIONAL {{ ?item rdfs:label ?b . FILTER(LANG(?b) = "zh-hans") }}
  OPTIONAL {{ ?item rdfs:label ?c . FILTER(LANG(?c) = "zh") }}
  OPTIONAL {{ ?item rdfs:label ?d . FILTER(LANG(?d) = "zh-hant") }}
  BIND(COALESCE(?a, ?b, ?c, ?d) AS ?zh)
  FILTER(BOUND(?zh))
}}
"""
        mapped: dict[str, str] = {}
        try:
            for row in sparql(query):
                title = row.get("title", {}).get("value") or ""
                zh = simplify(row.get("zh", {}).get("value") or "")
                if title and has_han(zh):
                    mapped[title] = zh
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
            print(f"qlever batch {i} failed: {error}", file=sys.stderr)
            time.sleep(3)
            continue
        for title in batch:
            zh = mapped.get(title) or mapped.get(title.replace("_", " ")) or ""
            cache_path(title).write_text(
                json.dumps({"title": title, "zh": zh}, ensure_ascii=False),
                encoding="utf-8",
            )
            if zh:
                found[title] = zh
        print(f"  batch {i + 1}: {len(mapped)} hits")
        time.sleep(1)
    return found


def pattern_zh(english: str, known: dict[str, str]) -> str | None:
    for pattern, template in PREFIX_MAP:
        match = re.match(pattern, english, re.IGNORECASE)
        if not match:
            continue
        inner = match.group(1).strip()
        inner_zh = known.get(inner) or MANUAL.get(inner)
        if inner_zh and has_han(inner_zh):
            return template.format(inner_zh)
    return None


def wikipedia_title(polity: dict) -> str:
    wiki = (polity.get("wikipedia") or "").replace("_", " ").strip()
    return wiki or polity["name"]


def needs_zh(polity: dict) -> bool:
    return not has_han(polity.get("zh") or "")


def main() -> None:
    refresh = "--refresh" in sys.argv
    table = json.loads(TABLE.read_text(encoding="utf-8"))
    names: dict[str, list] = table.setdefault("names", {})
    index = json.loads(POLITIES.read_text(encoding="utf-8"))
    polities = index["polities"]

    missing = [item for item in polities if needs_zh(item)]
    already = {english: values[0] for english, values in names.items() if has_han(values[0])}
    already.update(MANUAL)
    titles = set()
    for item in missing:
        if item["name"] in already:
            continue
        for key in (item["name"], wikipedia_title(item)):
            if key not in already:
                titles.add(key)
    titles = sorted(titles)
    print(f"untranslated: {len(missing)} / {len(polities)} polities, {len(titles)} lookup keys")

    fetched = cached_entities(titles, refresh)
    known = {english: values[0] for english, values in names.items() if has_han(values[0])}
    known.update(MANUAL)
    known.update(fetched)

    filled = 0
    still = []
    for item in polities:
        english = item["name"]
        zh = item.get("zh") or ""
        if has_han(zh) and zh != english:
            names.setdefault(english, [zh, item.get("capital") or ""])
            continue
        capital = (names.get(english) or ["", item.get("capital") or ""])[1] if english in names else item.get("capital") or ""
        wiki = wikipedia_title(item)
        resolved = MANUAL.get(english) or fetched.get(wiki) or fetched.get(english) or pattern_zh(english, known)
        if resolved and has_han(resolved):
            item["zh"] = resolved
            names[english] = [resolved, capital]
            filled += 1
        else:
            still.append(english)

    TABLE.write_text(json.dumps(table, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    POLITIES.write_text(json.dumps(index, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"filled {filled}; still English {len(still)}")
    for name in still[:40]:
        print(f"  {name}")
    if len(still) > 40:
        print(f"  ... {len(still) - 40} more")


if __name__ == "__main__":
    main()
