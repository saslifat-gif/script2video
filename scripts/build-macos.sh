#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

VERSION="1.0.7"
APP_PATH="$PROJECT_ROOT/dist/Script2Video Studio.app"
STAGING="$PROJECT_ROOT/build/macos-dmg"
DMG="$PROJECT_ROOT/release/Script2Video-Studio-$VERSION-macOS-arm64.dmg"

python packaging/macos/generate_icon.py
python -m PyInstaller --noconfirm --clean packaging/macos/script2video.spec

if [[ ! -d "$APP_PATH" ]]; then
  echo "Expected application was not created: $APP_PATH" >&2
  exit 1
fi
if ! find "$APP_PATH" -path "*/language_tags/data/json/index.json" -print -quit | grep -q .; then
  echo "Packaged language-tags registry is missing." >&2
  exit 1
fi

rm -rf "$STAGING"
mkdir -p "$STAGING" "$PROJECT_ROOT/release"
cp -R "$APP_PATH" "$STAGING/"
ln -s /Applications "$STAGING/Applications"
rm -f "$DMG"
hdiutil create \
  -volname "Script2Video Studio $VERSION" \
  -srcfolder "$STAGING" \
  -ov \
  -format UDZO \
  "$DMG"
echo "Built $DMG"
