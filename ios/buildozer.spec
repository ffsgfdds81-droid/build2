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

ios.permissions = INTERNET,ACCESS_NETWORK_STATE,ACCESS_WIFI_STATE

ios.kivy_ios_url = https://github.com/kivy/kivy-ios
ios.kivy_ios_branch = master

requirements = python3,kivy

ios.sdk_version = 15.0
ios.minDeploymentTarget = 12.0

[buildozer]

log_level = 2

warn_on_root = 1

build_dir = ./.buildozer

bin_dir = ./bin
