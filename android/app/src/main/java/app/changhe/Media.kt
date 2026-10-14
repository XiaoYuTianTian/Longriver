package app.changhe

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import coil.compose.AsyncImage

internal fun mediaUrl(path: String): String? =
    path.takeIf { it.isNotBlank() }?.let { BuildConfig.MEDIA_BASE_URL.trimEnd('/') + "/" + it.trimStart('/') }

@Composable
internal fun mediaModel(path: String): Any? {
    val context = LocalContext.current
    if (path.isBlank()) return null
    val asset = "media/" + path.trimStart('/')
    val bundled = remember(path) {
        runCatching { context.assets.open(asset).close() }.isSuccess
    }
    return if (bundled) "file:///android_asset/$asset" else mediaUrl(path)
}

@Composable
internal fun Avatar(name: String, image: String, size: Dp, modifier: Modifier = Modifier) {
    var failed by remember(image) { mutableStateOf(false) }
    val model = mediaModel(image)
    Box(
        modifier.size(size).clip(CircleShape).background(MaterialTheme.colorScheme.secondaryContainer),
        contentAlignment = Alignment.Center,
    ) {
        if (model == null || failed) {
            Text(
                name.take(1),
                color = MaterialTheme.colorScheme.onSecondaryContainer,
                fontSize = (size.value * 0.42f).sp,
            )
        } else {
            AsyncImage(
                model = model,
                contentDescription = name,
                contentScale = ContentScale.Crop,
                alignment = Alignment.TopCenter,
                onError = { failed = true },
                modifier = Modifier.size(size),
            )
        }
    }
}

/** Header picture with its licence line; renders nothing when the image is missing or unreachable. */
@Composable
internal fun HeaderImage(image: String, credit: String, description: String, height: Dp = 160.dp) {
    var failed by remember(image) { mutableStateOf(false) }
    val model = mediaModel(image) ?: return
    if (failed) return
    Column {
        AsyncImage(
            model = model,
            contentDescription = description,
            contentScale = ContentScale.Crop,
            onError = { failed = true },
            modifier = Modifier.fillMaxWidth().height(height).clip(RoundedCornerShape(14.dp)),
        )
        if (credit.isNotBlank()) {
            Text(
                "图片：$credit",
                style = MaterialTheme.typography.labelSmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                maxLines = 1,
            )
        }
    }
}
