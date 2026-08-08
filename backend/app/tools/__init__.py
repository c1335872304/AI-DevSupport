# tools 包初始化文件
# 本文件标识 app/tools/ 为 Python 包，使其可被 import。
# 各工具模块（apikey、billing_tools、logs、ticket_tools）和工具注册中心（registry）
# 均位于此包下。应用启动时应调用 registry.load_tools() 以触发所有工具的注册。
