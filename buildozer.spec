[app]

title = Simple Browser
package.name = simplebrowser
package.domain = org.simplebrowser

source.dir = .
source.include_exts = py,png,jpg,kv,atlas

version = 1.1

orientation = portrait

osx.python_version = 3
osx.kivy_version = 2.1.0

fullscreen = 0

android.permissions = INTERNET,ACCESS_NETWORK_STATE,ACCESS_WIFI_STATE,READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE
android.api = 33
android.minapi = 21
android.archs = arm64-v8a

android.accept_sdk_license = True

android.allow_backup = True

android.meta_data = com.google.android.gms.version=@integer/google_play_services_version

android.presplash_color = #FFFFFF

android.launcher_color = #FFFFFF

requirements = python3,kivy,android,urllib3,certifi,chardet,idna,cryptography

android.allow_debug = 1

[buildozer]

log_level = 2

warn_on_root = 1

build_dir = ./.buildozer

bin_dir = ./bin
