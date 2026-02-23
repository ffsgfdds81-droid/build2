#!/bin/bash
# Скрипт сборки APK для Simple Browser

echo "=== Настройка окружения ==="

# Java
export JAVA_HOME=$(dirname $(dirname $(readlink -f $(which java))))
export PATH=$JAVA_HOME/bin:$PATH

# Android SDK
export ANDROID_SDK_ROOT=/mnt/c/Users/Sklad2/AppData/Local/Android/Sdk
export ANDROID_HOME=$ANDROID_SDK_ROOT
export PATH=$ANDROID_SDK_ROOT/cmdline-tools/latest/bin:$ANDROID_SDK_ROOT/platform-tools:$PATH

echo "JAVA_HOME: $JAVA_HOME"
echo "ANDROID_SDK_ROOT: $ANDROID_SDK_ROOT"

# Проверка SDK
if [ ! -d "$ANDROID_SDK_ROOT" ]; then
    echo "ОШИБКА: Android SDK не найден!"
    exit 1
fi

echo ""
echo "=== Установка buildozer ==="
pip install --user buildozer cython 2>/dev/null
pip install --user python-for-android 2>/dev/null

echo ""
echo "=== Сборка APK ==="
cd /mnt/c/Users/Sklad2/Downloads/simple_browser/android

# Очистка
rm -rf .buildozer bin 2>/dev/null

# Сборка
python -m buildozer android debug

echo ""
echo "=== Готово! ==="
ls -la bin/
