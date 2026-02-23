#!/bin/bash
# Скрипт для установки зависимостей buildozer в WSL

# Установка системных пакетов
sudo apt update
sudo apt install -y python3-pip python3-venv python3-full git openjdk-17-jdk

# Установка buildozer
pip3 install --break-system-packages buildozer cython

# Создание символических ссылок для Java
mkdir -p ~/.jdk
ln -sf '/mnt/c/Program Files/Eclipse Adoptium/jdk-17.0.18.8-hotspot' ~/.jdk/java-17

# Создание оберток для Java
echo '#!/bin/bash' > ~/.local/bin/javac
echo '"$HOME/.jdk/java-17/bin/javac" "$@"' >> ~/.local/bin/javac
chmod +x ~/.local/bin/javac

echo '#!/bin/bash' > ~/.local/bin/keytool
echo '"$HOME/.jdk/java-17/bin/keytool" "$@"' >> ~/.local/bin/keytool  
chmod +x ~/.local/bin/keytool

echo "Setup complete! Run: cd /mnt/c/Users/Sklad2/Downloads/simple_browser/android && buildozer android debug"
