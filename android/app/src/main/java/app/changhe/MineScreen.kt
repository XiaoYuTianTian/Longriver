package app.changhe

import android.content.Context
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Card
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.FilledTonalButton
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalUriHandler
import androidx.compose.ui.unit.dp
import androidx.compose.ui.window.DialogProperties

private const val PREFS = "legal"
private const val KEY_CONSENT = "consent_version"
private const val KEY_ONBOARD = "onboarded"

fun hasConsent(context: Context): Boolean =
    context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).getInt(KEY_CONSENT, 0) >= LegalInfo.CONSENT_VERSION

fun saveConsent(context: Context) {
    context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit()
        .putInt(KEY_CONSENT, LegalInfo.CONSENT_VERSION)
        .apply()
}

fun hasOnboarded(context: Context): Boolean =
    context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).getBoolean(KEY_ONBOARD, false)

fun saveOnboarded(context: Context) {
    context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit()
        .putBoolean(KEY_ONBOARD, true)
        .apply()
}

@Composable
fun MineScreen(
    bookmarks: @Composable () -> Unit,
    syncing: Boolean,
    onSync: () -> Unit,
    openAbout: () -> Unit,
    openPrivacy: () -> Unit,
    openTerms: () -> Unit,
) {
    val uri = LocalUriHandler.current
    LazyColumn(
        Modifier.fillMaxSize(),
        contentPadding = PaddingValues(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        item {
            Column(Modifier.padding(vertical = 8.dp)) {
                Text("长河", style = MaterialTheme.typography.headlineMedium)
                Text(
                    "版本 ${BuildConfig.VERSION_NAME} · 世界史地图集",
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
        }
        item { bookmarks() }
        item {
            Card(Modifier.fillMaxWidth()) {
                Row(Modifier.padding(16.dp), verticalAlignment = Alignment.CenterVertically) {
                    Column(Modifier.weight(1f)) {
                        Text("知识库", style = MaterialTheme.typography.titleMedium)
                        Text("内容随安装包提供，离线可读。联网可获取审核后的新条目。", color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                    if (syncing) {
                        CircularProgressIndicator(Modifier.size(22.dp), strokeWidth = 2.dp)
                    } else {
                        FilledTonalButton(onClick = onSync) { Text("更新") }
                    }
                }
            }
        }
        item {
            Card(Modifier.fillMaxWidth()) {
                Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                    Text("地图", style = MaterialTheme.typography.titleMedium)
                    Text(LegalInfo.mapApprovalLabel, color = MaterialTheme.colorScheme.secondary)
                    Text(
                        "历史疆域为近似示意，依据公开学术数据绘制，不代表对任何现实边界的认定。",
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
            }
        }
        item { Text("数据来源与许可", style = MaterialTheme.typography.titleMedium, modifier = Modifier.padding(top = 8.dp)) }
        LegalInfo.sources.forEach { source ->
            item {
                Card(onClick = { uri.openUri(source.url) }, modifier = Modifier.fillMaxWidth()) {
                    Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                        Text(source.title, style = MaterialTheme.typography.titleSmall)
                        Text(source.detail, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                }
            }
        }
        item { HorizontalDivider(Modifier.padding(vertical = 8.dp)) }
        item { TextButton(onClick = openAbout) { Text("关于长河") } }
        item { TextButton(onClick = openPrivacy) { Text("隐私政策") } }
        item { TextButton(onClick = openTerms) { Text("用户协议") } }
        item {
            Column(Modifier.padding(horizontal = 12.dp), verticalArrangement = Arrangement.spacedBy(2.dp)) {
                Text(LegalInfo.operatorName, style = MaterialTheme.typography.labelMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
                Text("联系：${LegalInfo.contactEmail}", style = MaterialTheme.typography.labelMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
                if (LegalInfo.appFilingNumber.isNotBlank()) {
                    Text("备案号：${LegalInfo.appFilingNumber}", style = MaterialTheme.typography.labelMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
            }
        }
    }
}

@Composable
fun AboutScreen(model: ChangheViewModel) {
    val claims by model.allClaims.collectAsState()
    val people by model.allPeople.collectAsState()
    val regions by model.regions.collectAsState()
    val events by model.allEvents.collectAsState()
    LazyColumn(
        Modifier.fillMaxSize(),
        contentPadding = PaddingValues(20.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        item { Text("长河是一张会随年代变化的世界史地图。先选定年份，再在地图上读当时的疆域、事件和人物。", style = MaterialTheme.typography.bodyLarge) }
        item {
            Text("收录范围", style = MaterialTheme.typography.titleMedium)
        }
        item {
            Text(
                "时间从公元前 3000 年到 ${TIMELINE_END} 年。1911 年及以前的疆域来自 Cliopatria；1912 年以后的国界来自 Natural Earth 公开数据。",
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
        item {
            Text(
                "目前本地有 ${events.size} 个事件、${claims.size} 条记述、${people.size} 位人物、${regions.size} 个地点。",
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
        item { Text("语言", style = MaterialTheme.typography.titleMedium) }
        item {
            Text(
                "界面默认简体中文。政权、人物、地点优先显示中文名；拉丁名只在详情页作副标题，方便对照来源，不在地图上混排。以后若要做多语言，会按系统语言切换界面，但仍以中文为默认。",
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
        item { Text("内容怎么来", style = MaterialTheme.typography.titleMedium) }
        item {
            Text(
                "开放数据加结构化抽取，每条记述带出处和可信度。人工智能只起草候选，发布前由人核对。受版权保护的书籍只收录书目，不提供全文。",
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
    }
}

@Composable
fun LegalTextScreen(text: String) {
    Text(
        text,
        style = MaterialTheme.typography.bodyMedium,
        modifier = Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(20.dp),
    )
}

@Composable
fun ConsentDialog(
    onAgree: () -> Unit,
    onDecline: () -> Unit,
    openPrivacy: () -> Unit,
    openTerms: () -> Unit,
) {
    AlertDialog(
        onDismissRequest = {},
        properties = DialogProperties(dismissOnBackPress = false, dismissOnClickOutside = false),
        title = { Text("欢迎使用长河") },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text("使用前请阅读《隐私政策》和《用户协议》。长河不收集你的个人信息，收藏只保存在本机；只有更新知识库时才会联网。")
                Row {
                    TextButton(onClick = openPrivacy) { Text("《隐私政策》") }
                    TextButton(onClick = openTerms) { Text("《用户协议》") }
                }
            }
        },
        confirmButton = { TextButton(onClick = onAgree) { Text("同意并继续") } },
        dismissButton = { TextButton(onClick = onDecline) { Text("不同意") } },
    )
}

private val onboardPages = listOf(
    "长河是什么" to "一张会随年代变化的世界史地图。选定一年，就能看到当时的疆域、事件和人物。",
    "怎么用" to "拖动底部时间轴换年份，点色带可选整个朝代。点疆域看政权，点地名看当地收录。「览」里按时代、人物、事件、地点翻已收录的内容。界面为简体中文。",
    "内容怎么来" to "开放数据加人工审核。每条记述有出处和可信度。受版权保护的书只列书目，不提供全文。",
)

@Composable
fun Onboarding(onDone: () -> Unit) {
    var page by remember { mutableIntStateOf(0) }
    val (title, body) = onboardPages[page]
    AlertDialog(
        onDismissRequest = {},
        properties = DialogProperties(dismissOnBackPress = false, dismissOnClickOutside = false),
        title = { Text(title) },
        text = { Text(body) },
        confirmButton = {
            TextButton(onClick = {
                if (page < onboardPages.lastIndex) page++ else onDone()
            }) { Text(if (page < onboardPages.lastIndex) "下一步" else "开始阅读") }
        },
    )
}
