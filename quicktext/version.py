"""版本号的唯一来源。

发布约定：
    打 tag（如 v0.1.1）触发 CI，CI 用 tag 覆盖本文件的 __version__，
    再依次构建 exe 与安装包，因此本文件的值就是"上一次发布的版本"。

    QuickText.spec 读取此处生成 exe 的版本资源；
    QuickText.iss 通过 /DMyAppVersion 接收同一版本，不在脚本内二次硬编码。
"""
__version__ = "0.1.0"
