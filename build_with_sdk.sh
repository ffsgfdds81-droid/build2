#!/bin/bash
# Настройка Android SDK для buildozer

export ANDROID_SDK_ROOT=/mnt/c/Users/Sklad2/AppData/Local/Android/Sdk
export ANDROID_HOME=$ANDROID_SDK_ROOT

# Проверить SDK
if [ -d "$ANDROID_SDK_ROOT" ]; then
    echo "Android SDK найден: $ANDROID_SDK_ROOT"
    ls $ANDROID_SDK_ROOT
else
    echo "Android SDK не найден!"
fi

# Путь к cmdline-tools
export PATH=$ANDROID_SDK_ROOT/cmdline-tools/latest/bin:$ANDROID_SDK_ROOT/platform-tools:$PATH

# Запустить buildozer
cd /mnt/c/Users/Sklad2/Downloads/simple_browser/android
buildozer android debug
