#!/bin/bash
# Настройка Java для buildozer

# Найти Java
export JAVA_HOME=$(dirname $(dirname $(readlink -f $(which java))))
echo "JAVA_HOME: $JAVA_HOME"

# Добавить в PATH
export PATH=$JAVA_HOME/bin:$PATH

# Проверить
java -version
javac -version

# Запустить сборку
cd /mnt/c/Users/Sklad2/Downloads/simple_browser/android
buildozer android debug
