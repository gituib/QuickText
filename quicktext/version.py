"""版本号的唯一来源。

发布约定：
    发版只需修改这里的 __version__ 并推送到 main。
    CI 读取本值构建 exe 与安装包；若远端还没有对应的 vX.Y.Z tag，
    会自动打 tag 并发布 GitHub Release，已发布过的版本则只构建不重复发布。

    QuickText.spec 读取此处生成 exe 的版本资源；
    QuickText.iss 通过 /DMyAppVersion 接收同一版本，不在脚本内二次硬编码。
"""
__version__ = "0.1.1"
