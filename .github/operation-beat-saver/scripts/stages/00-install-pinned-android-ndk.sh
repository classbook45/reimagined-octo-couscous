set -euo pipefail
sdkmanager --install "platform-tools" "ndk;29.0.14206865"
NDK_PATH="$ANDROID_SDK_ROOT/ndk/29.0.14206865"
test -f "$NDK_PATH/source.properties"
{
  echo "ANDROID_NDK_HOME=$NDK_PATH"
  echo "ANDROID_NDK_ROOT=$NDK_PATH"
  echo "ANDROID_NDK_LATEST_HOME=$NDK_PATH"
} >> "$GITHUB_ENV"
grep "Pkg.Revision" "$NDK_PATH/source.properties"
