[app]
title = Vazao Sovereign Trader
package.name = vazaosovereigntrader
package.domain = pt.andrevazao
source.dir = .
source.include_exts = py,json,png,jpg,jpeg
version = 0.4.0
requirements = python3,kivy
icon.filename = %(source.dir)s/vst-launcher-icon.png
orientation = portrait
fullscreen = 0
android.permissions = INTERNET,ACCESS_NETWORK_STATE,RECORD_AUDIO
android.api = 35
android.python_version = 3.11
p4a.python_version = 3.11
android.minapi = 24
android.archs = arm64-v8a
p4a.branch = v2024.01.21

[buildozer]
log_level = 2
warn_on_root = 1
