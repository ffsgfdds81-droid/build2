#!/bin/bash

echo "Building iOS app..."

if ! command -v buildozer &> /dev/null; then
    pip install buildozer
fi

cd "$(dirname "$0")"

buildozer ios debug

echo "Build complete! APK/IPA should be in bin/"
