package app.longriver

object LegalInfo {
    const val CONSENT_VERSION = 1

    /** 拿到自然资源部审图号后填入，例如 "GS（2027）1234号"。 */
    const val mapApprovalNumber = ""

    /** 完成 APP 备案后填入。 */
    const val appFilingNumber = ""

    const val operatorName = "Longriver（运营主体待填写）"
    const val contactEmail = "待填写联系邮箱"
    const val effectiveDate = "2026年9月29日"

    /** 天地图底图的审图号，以天地图官网公布的当前编号为准。 */
    const val tiandituApprovalNumber = ""

    val mapApprovalLabel: String
        get() = if (mapApprovalNumber.isBlank()) "内测版，地图未审核" else "审图号：$mapApprovalNumber"

    const val mapAttribution = "疆域 Cliopatria CC BY 4.0 · 陆地 Natural Earth"

    fun mapLines(year: Int): List<String> = if (year > HISTORICAL_BORDERS_END) {
        listOf(
            mapApprovalLabel,
            if (hasModernBase) {
                "底图：天地图" + if (tiandituApprovalNumber.isBlank()) "" else " · 审图号：$tiandituApprovalNumber"
            } else {
                "国界 Natural Earth · 陆地 Natural Earth"
            },
        )
    } else {
        listOf(mapApprovalLabel, mapAttribution)
    }

    val sources = listOf(
        Source(
            "Cliopatria 历史疆域数据集",
            "Seshat Global History Databank，2024，Zenodo 记录 13363121。以 CC BY 4.0 协议发布，本应用对轮廓做了简化和按年份切分。",
            "https://doi.org/10.5281/zenodo.13363121",
        ),
        Source(
            "Natural Earth 陆地与国界",
            "1:5000 万比例尺陆地和当代国界，属公共领域。1912 年以后的离线国界用这份数据，台湾、香港、澳门轮廓并入中国。",
            "https://www.naturalearthdata.com/",
        ),
        Source(
            "维基百科与维基数据",
            "部分事件的出处与政权条目链接指向维基百科，条目文字按 CC BY-SA 4.0 协议授权，版权归原作者。",
            "https://www.wikipedia.org/",
        ),
        Source(
            "天地图（国家地理信息公共服务平台）",
            "配置密钥后，1912 年以后可改用天地图底图、国界与注记，按天地图服务条款在线调用。",
            "https://www.tianditu.gov.cn/",
        ),
        Source(
            "维基共享资源图片",
            "人物与地点配图来自维基共享资源，仅收录公有领域、CC0、CC BY 与 CC BY-SA 授权的图片，作者与许可随图标注。",
            "https://commons.wikimedia.org/",
        ),
        Source(
            "MapLibre Native",
            "地图渲染引擎，BSD 协议开源。",
            "https://maplibre.org/",
        ),
    )

    data class Source(val title: String, val detail: String, val url: String)

    val privacyPolicy = """
        生效日期：$effectiveDate

        $operatorName（以下称“我们”）重视你的个人信息保护。本政策说明 Longriver 如何处理信息。

        一、我们处理的信息
        1. 收藏与备注只保存在你的手机本地，我们不上传，也无法查看。
        2. 点击“更新知识库”时，应用会向知识库服务器请求最新版本。服务器会记录请求时间和网络地址，用于保障服务安全，保存不超过 30 天。
        3. 应用不收集姓名、手机号、位置、通讯录、设备标识等个人信息，不接入广告或统计分析类第三方 SDK。

        二、权限
        应用只使用网络权限，用于更新知识库。地图与疆域数据随安装包提供，离线可用。

        三、第三方服务
        点击维基百科等外部链接时会离开本应用，由浏览器打开对应网站，其信息处理适用该网站的政策。

        四、你的权利
        你可以随时在收藏页删除收藏，卸载应用会清除全部本地数据。如需查询、更正或删除服务器日志，请联系我们。

        五、未成年人
        本应用内容为历史资料阅读，不针对未成年人收集信息。未成年人应在监护人指导下使用。

        六、政策更新
        政策变更时，我们会在应用内提示并重新征得你的同意。

        七、联系我们
        $contactEmail
    """.trimIndent()

    val userAgreement = """
        生效日期：$effectiveDate

        欢迎使用 Longriver。使用本应用即表示你同意本协议。

        一、服务内容
        Longriver 提供按时间和地图浏览的世界史资料。每条记述附有出处、时间精度与可信度标注，内容经人工审核，但不保证完全无误。学术引用请核对原始出处。

        二、地图说明
        历史疆域为依据公开学术数据绘制的近似示意，不代表对任何现实边界的认定。未取得审图号的版本仅供内部测试，不得对外传播截图。

        三、知识产权
        应用界面、编排与原创文字归运营方所有。第三方数据按其协议使用，详见“我的 · 数据来源与许可”。受版权保护的书籍只收录书目信息。

        四、使用规范
        你不得利用本应用从事违法活动，不得批量抓取或转售内容。

        五、免责
        因网络、设备或不可抗力导致的服务中断，我们会尽力恢复，但不承担由此产生的间接损失。

        六、协议变更与终止
        协议变更时会在应用内提示。你可以随时停止使用并卸载应用。

        七、法律适用
        本协议适用中华人民共和国法律。

        联系方式：$contactEmail
    """.trimIndent()
}
