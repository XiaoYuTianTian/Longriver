package app.changhe

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Shapes
import androidx.compose.material3.Typography
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

private val Ink = Color(0xFF1C1915)
private val Paper = Color(0xFFF4EFE6)
private val PaperRaised = Color(0xFFFFFBF5)
private val River = Color(0xFF1F4E5F)
private val Clay = Color(0xFF8C4A32)
private val Night = Color(0xFF141210)
private val NightRaised = Color(0xFF221F1B)
private val Mist = Color(0xFFE8E0D4)

private val LightColors = lightColorScheme(
    primary = River,
    onPrimary = Paper,
    secondary = Clay,
    onSecondary = Paper,
    tertiary = Color(0xFF6B5A2E),
    onTertiary = Paper,
    background = Paper,
    onBackground = Ink,
    surface = PaperRaised,
    onSurface = Ink,
    surfaceVariant = Color(0xFFE7DFD2),
    onSurfaceVariant = Color(0xFF5C564E),
    outline = Color(0xFFC8BEB0),
)

private val DarkColors = darkColorScheme(
    primary = Color(0xFF8FCBD6),
    onPrimary = Color(0xFF00363E),
    secondary = Color(0xFFE2B08A),
    onSecondary = Color(0xFF3D2416),
    tertiary = Color(0xFFD4BF84),
    onTertiary = Color(0xFF2E2508),
    background = Night,
    onBackground = Mist,
    surface = NightRaised,
    onSurface = Mist,
    surfaceVariant = Color(0xFF2C2823),
    onSurfaceVariant = Color(0xFFC8BEB0),
)

private val ChangheTypography = Typography(
    displaySmall = TextStyle(
        fontFamily = FontFamily.Serif,
        fontWeight = FontWeight.Medium,
        fontSize = 40.sp,
        lineHeight = 48.sp,
    ),
    headlineSmall = TextStyle(
        fontFamily = FontFamily.Serif,
        fontWeight = FontWeight.Medium,
        fontSize = 26.sp,
        lineHeight = 34.sp,
    ),
    titleMedium = TextStyle(
        fontFamily = FontFamily.Serif,
        fontWeight = FontWeight.Medium,
        fontSize = 18.sp,
        lineHeight = 26.sp,
    ),
    bodyLarge = TextStyle(
        fontFamily = FontFamily.Serif,
        fontSize = 16.sp,
        lineHeight = 26.sp,
    ),
    bodyMedium = TextStyle(
        fontFamily = FontFamily.Serif,
        fontSize = 15.sp,
        lineHeight = 24.sp,
    ),
    labelLarge = TextStyle(fontFamily = FontFamily.SansSerif, fontSize = 14.sp),
    labelMedium = TextStyle(fontFamily = FontFamily.SansSerif, fontSize = 12.sp),
)

private val ChangheShapes = Shapes(
    extraSmall = RoundedCornerShape(8.dp),
    small = RoundedCornerShape(12.dp),
    medium = RoundedCornerShape(16.dp),
    large = RoundedCornerShape(20.dp),
)

fun regionAccent(slug: String): Color = when (slug) {
    "east-asia" -> Color(0xFF8C3A2F)
    "west-asia-north-africa" -> Color(0xFFB0893E)
    "europe" -> Color(0xFF1F4E5F)
    "americas" -> Color(0xFF3E6B4F)
    "south-asia" -> Color(0xFFA0522D)
    "southeast-asia" -> Color(0xFF4F7F6A)
    "central-asia" -> Color(0xFF7A6A9B)
    "africa" -> Color(0xFF9A6B2F)
    "oceania" -> Color(0xFF3F6E8C)
    else -> Color(0xFF6B645B)
}

@Composable
fun ChangheTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = if (isSystemInDarkTheme()) DarkColors else LightColors,
        typography = ChangheTypography,
        shapes = ChangheShapes,
        content = content,
    )
}
