#!/usr/bin/env python3
"""Guarded source/API migration for the pinned CustomModels 1.2.1 source on BS 1.45.3."""
from pathlib import Path

ROOT = Path.cwd()

def read(rel):
    path = ROOT / rel
    if not path.is_file():
        raise SystemExit(f"Required source file is missing: {rel}")
    return path, path.read_text()

def replace_count(rel, old, new, expected):
    path, data = read(rel)
    count = data.count(old)
    if count != expected:
        raise SystemExit(f"{rel}: expected {expected} source matches, found {count}: {old[:100]!r}")
    path.write_text(data.replace(old, new))

def replace_once(rel, old, new):
    replace_count(rel, old, new, 1)

def add_include(rel, anchor, include):
    path, data = read(rel)
    if include in data:
        return
    if data.count(anchor) != 1:
        raise SystemExit(f"{rel}: expected exactly one include anchor {anchor!r}")
    path.write_text(data.replace(anchor, anchor + "\n" + include, 1))

# ConfigUtils 3.x serializes configuration with reflect-cpp. Its config values
# must be ordinary reflected structs, not RapidJSON-Macros Parent subclasses.
config_path, old_config = read("include/config.hpp")
if old_config.count("MAP_DEFAULT(CustomModels::Profile, Profiles") != 1:
    raise SystemExit("config.hpp is not the expected upstream 1.2.1 layout")
if old_config.count("DECLARE_JSON_STRUCT(Profile)") != 1:
    raise SystemExit("config.hpp Profile declaration changed; refusing an unreviewed rewrite")

new_config = r'''#pragma once

#include "config-utils/shared/config-utils.hpp"

#include <string>
#include <vector>

namespace CustomModels {
    struct SaberSettings {
        float length = 1;
        bool overrideLength = false;
        float width = 1;
        bool overrideWidth = false;

        float Length() {
            return overrideLength ? length : 1;
        }
        float Width() {
            return overrideWidth ? width : 1;
        }
    };

    struct TrailSettings {
        bool whiteStep = false;
        float length = 1;
        bool overrideLength = false;
        float width = 1;
        bool overrideWidth = false;
        float widthOffset = 0;

        float Length() {
            return overrideLength ? length : 1;
        }
        float Width() {
            return overrideWidth ? width : 1;
        }
    };

    struct NoteSettings {
        float size = 1;
        bool overrideSize = false;
        bool defaultBombs = false;
        bool defaultDebris = false;

        float Size() {
            return overrideSize ? size : 1;
        }
    };

    struct WallSettings {
        bool disableFrame = false;
        bool disableCore = false;
    };

    struct Profile {
        // empty string is default model
        std::string SaberModel = "";
        std::string TrailModel = "";
        std::string MenuSaberModel = "";
        std::string MenuTrailModel = "";
        std::string NoteModel = "";
        std::string WallModel = "";

        bool MenuSaber = false;
        // copy, none, custom
        int TrailMode = 0;
        int MenuTrailMode = 0;

        CustomModels::SaberSettings SaberSettings = {};
        CustomModels::TrailSettings TrailSettings = {};
        CustomModels::SaberSettings MenuSaberSettings = {};
        CustomModels::TrailSettings MenuTrailSettings = {};
        CustomModels::NoteSettings NotesSettings = {};
        CustomModels::WallSettings WallsSettings = {};
    };
}

#define PROFILE_GETTER(name) \
    auto& name() { return CurrentProfile().name; }

DECLARE_CONFIG(Config) {
    CONFIG_VALUE(Enabled, bool, "ModEnabled", true);

    CONFIG_VALUE(Profile, std::string, "Profile", "Default");

    CONFIG_VALUE(Profiles, ConfigUtils::Map<CustomModels::Profile>, "Profiles", {});

    CustomModels::Profile& CurrentProfile() {
        auto& profiles = Profiles.GetValue();
        if (!profiles.contains(Profile.GetValue()))
            Profile.SetValue(Profile.GetDefaultValue());
        return profiles[Profile.GetValue()];
    }

    PROFILE_GETTER(SaberModel);
    PROFILE_GETTER(TrailModel);
    PROFILE_GETTER(MenuSaberModel);
    PROFILE_GETTER(MenuTrailModel);
    PROFILE_GETTER(NoteModel);
    PROFILE_GETTER(WallModel);

    PROFILE_GETTER(MenuSaber);
    PROFILE_GETTER(TrailMode);
    PROFILE_GETTER(MenuTrailMode);

    PROFILE_GETTER(SaberSettings);
    PROFILE_GETTER(TrailSettings);
    PROFILE_GETTER(MenuSaberSettings);
    PROFILE_GETTER(MenuTrailSettings);
    PROFILE_GETTER(NotesSettings);
    PROFILE_GETTER(WallsSettings);

    CONFIG_VALUE(LoadingGuard, std::string, "LoadingGuard", "");
    CONFIG_VALUE(LoadingFailures, std::vector<std::string>, "LoadingFailures", {});
    CONFIG_VALUE(ModVersion, std::string, "ModVersion", VERSION);

    bool LoadFailed(std::string const& file) {
        auto fails = LoadingFailures.GetValue();
        for (auto& fail : fails) {
            if (fail == file)
                return true;
        }
        return false;
    }
};

#undef PROFILE_GETTER
'''
config_path.write_text(new_config)

# Hook 9 moved the persistent Mods root to PERSISTENT_DIR and removed the old
# getDataDir helper. Preserve the Quest folder layout used by CustomModels.
main_path, main_header = read("include/main.hpp")
if "getDataDir(std::string const& modId)" not in main_header:
    anchor = '#include "beatsaber-hook/shared/utils.hpp"'
    if main_header.count(anchor) != 1:
        raise SystemExit("main.hpp no longer matches the pinned upstream include layout")
    helper = r'''
#include <filesystem>
#include <stdexcept>
#include <string>
#include "beatsaber-hook/shared/config.hpp"

inline std::filesystem::path getDataDir(std::string const& modId) {
    std::string path = PERSISTENT_DIR;
    const auto marker = path.find("{}");
    if (marker == std::string::npos)
        throw std::runtime_error("Hook PERSISTENT_DIR has no game-id placeholder");
    path.replace(marker, 2, "com.beatgames.beatsaber");
    return std::filesystem::path(path) / modId;
}
'''
    main_path.write_text(main_header.replace(anchor, anchor + "\n" + helper, 1))

# The 1.45.3 MetaCore split keeps Beat Saber game-state APIs in MetaCoreBS.
replace_once("src/colors.cpp", '"metacore/shared/game.hpp"', '"metacore-bs/shared/game.hpp"')
replace_once("src/colors.cpp", '"metacore/shared/internals.hpp"', '"metacore-bs/shared/internals.hpp"')
replace_once("src/wall.cpp", '"metacore/shared/game.hpp"', '"metacore-bs/shared/game.hpp"')

# Hook 9 moved ConfigUtils out of beatsaber-hook; use the standalone package.
replace_once(
    "src/legacy.cpp",
    '"beatsaber-hook/shared/config/config-utils.hpp"',
    '"config-utils/shared/config-utils.hpp"',
)
replace_once(
    "src/main.cpp",
    '"beatsaber-hook/shared/config/config-utils.hpp"',
    '"config-utils/shared/config-utils.hpp"',
)

# RapidJSON macros are no longer re-exported by ConfigUtils 3.x.
# Keep the mod's package/legacy JSON format while restoring the Color bridge.
json_path, json_data = read("include/json.hpp")
if json_data.count('#include "config-utils/shared/config-utils.hpp"') != 1:
    raise SystemExit("json.hpp config-utils include changed; refusing migration")
if '#include "rapidjson-macros/shared/macros.hpp"' not in json_data:
    json_data = json_data.replace(
        '#include "config-utils/shared/config-utils.hpp"',
        '#include "config-utils/shared/config-utils.hpp"\\n#include "rapidjson-macros/shared/macros.hpp"\\n#include "UnityEngine/Color.hpp"',
        1,
    )
color_marker = "namespace CustomModels {"
color_bridge = r'''namespace ConfigUtils {
    DECLARE_JSON_STRUCT(Color) {
        VALUE(float, r);
        VALUE(float, g);
        VALUE(float, b);
        VALUE(float, a);

        Color() = default;
        Color(float r, float g, float b, float a) : r(r), g(g), b(b), a(a) {}
        Color(UnityEngine::Color const& other) : r(other.r), g(other.g), b(other.b), a(other.a) {}

        Color& operator=(UnityEngine::Color const& other) {
            r = other.r;
            g = other.g;
            b = other.b;
            a = other.a;
            return *this;
        }

        operator UnityEngine::Color() const { return UnityEngine::Color(r, g, b, a); }
    };
}

'''
if "namespace ConfigUtils {\\n    DECLARE_JSON_STRUCT(Color)" not in json_data:
    if json_data.count(color_marker) != 1:
        raise SystemExit("json.hpp namespace marker changed; refusing Color bridge insertion")
    json_data = json_data.replace(color_marker, color_bridge + color_marker, 1)
json_path.write_text(json_data)

# The 1.45.3 generated class was renamed and Init gained its gameplay-info argument.
add_include(
    "src/hooks.cpp",
    '#include "GlobalNamespace/GameplayCoreSceneSetupData.hpp"',
    '#include "GlobalNamespace/GameplayAdditionalInformation.hpp"',
)
replace_once(
    "src/hooks.cpp",
    '#include "GlobalNamespace/TutorialScenesTransitionSetupDataSO.hpp"',
    '#include "GlobalNamespace/TutorialScenesTransitionSetupData.hpp"',
)
replace_once(
    "src/hooks.cpp",
    '''MAKE_AUTO_HOOK_MATCH(
    TutorialScenesTransitionSetupDataSO_Init,
    &TutorialScenesTransitionSetupDataSO::Init,
    void,
    TutorialScenesTransitionSetupDataSO* self,
    PlayerSpecificSettings* settings
) {
    TutorialScenesTransitionSetupDataSO_Init(self, settings);''',
    '''MAKE_AUTO_HOOK_MATCH(
    TutorialScenesTransitionSetupData_Init,
    &TutorialScenesTransitionSetupData::Init,
    void,
    TutorialScenesTransitionSetupData* self,
    PlayerSpecificSettings* settings,
    GameplayAdditionalInformation* gameplayAdditionalInformation
) {
    TutorialScenesTransitionSetupData_Init(self, settings, gameplayAdditionalInformation);''',
)

# Include current Hook 9 APIs explicitly where the migrated symbols are used.
add_include("src/legacy.cpp", '#include "legacy.hpp"', '#include <exception>')
add_include("src/main.cpp", '#include "main.hpp"', '#include "beatsaber-hook/shared/api.hpp"')
add_include("src/loading.cpp", '#include "loading.hpp"', '#include "beatsaber-hook/shared/safeptr.hpp"')
add_include("src/loading.cpp", '#include "loading.hpp"', '#include <set>')
add_include("src/loading.cpp", '#include "loading.hpp"', '#include <vector>')
add_include("src/hooks.cpp", '#include "hooks.hpp"', '#include "beatsaber-hook/shared/byref.hpp"')
add_include("src/hooks.cpp", '#include "hooks.hpp"', '#include "beatsaber-hook/shared/safeptr.hpp"')

replace_once(
    "src/legacy.cpp",
    "il2cpp_utils::exceptions::StackTraceException",
    "std::exception",
)
replace_once(
    "src/main.cpp",
    "il2cpp_functions::Init();",
    "i2c::functions::initialize();",
)
replace_once(
    "src/loading.cpp",
    "auto array = ArrayW<uint8_t>({(uint8_t*) bytes.data(), bytes.size()});",
    "auto array = ArrayW<uint8_t>(std::vector<uint8_t>(bytes.begin(), bytes.end()));",
)
replace_once(
    "src/loading.cpp",
    "[request = SafePtr(request), file]()",
    "[request = safe_ptr<UnityEngine::AssetBundleCreateRequest>(*request), file]()",
)
replace_once(
    "src/loading.cpp",
    "[this, bundle, request = SafePtr(request), assetName, file, onDone]()",
    "[this, bundle, request = safe_ptr<UnityEngine::AssetBundleRequest>(*request), assetName, file, onDone]()",
)
replace_once("src/loading.cpp", "asset = object->ptr();", "asset = object.ptr();")

# Beat Saber 1.45.3's generated SaberTrail exposes Init/LateUpdate, not Awake.
replace_once(
    "src/hooks.cpp",
    '''// don't run the base class Awake on our saber trail
MAKE_AUTO_HOOK_MATCH(SaberTrail_Awake, &SaberTrail::Awake, void, SaberTrail* self) {
    if (!il2cpp_utils::try_cast<CustomModels::CustomSaberTrail>(self).has_value())
        SaberTrail_Awake(self);
}''',
    '''// Skip the base SaberTrail initializer for our custom subclass.
MAKE_AUTO_HOOK_MATCH(SaberTrail_Init, &SaberTrail::Init, void, SaberTrail* self) {
    if (!safe_ptr<SaberTrail>(*self).try_cast<CustomModels::CustomSaberTrail>())
        SaberTrail_Init(self);
}''',
)
replace_once(
    "src/hooks.cpp",
    '''    if (auto custom = il2cpp_utils::try_cast<CustomModels::CustomSaberTrail>(self)) {
        if (!(*custom)->PreLateUpdate())
            return;
    }''',
    '''    if (auto custom = safe_ptr<SaberTrail>(*self).try_cast<CustomModels::CustomSaberTrail>()) {
        if (!custom->PreLateUpdate())
            return;
    }''',
)
replace_once(
    "src/hooks.cpp",
    "ByRef<NoteSpawnData>",
    "by_ref<NoteSpawnData const>",
)
replace_count(
    "src/hooks.cpp",
    "ByRef<NoteDebris*>",
    "by_ref<NoteDebris*>",
    2,
)
replace_once(
    "src/hooks.cpp",
    "ByRef<BeatmapKey>",
    "by_ref<BeatmapKey const>",
)
replace_once(
    "src/hooks.cpp",
    '''    if (auto note = il2cpp_utils::try_cast<GameNoteController>(self).value_or(nullptr)) {
        for (auto hitbox : note->_bigCuttableBySaberList)
            Scale(hitbox, inverse);
        for (auto hitbox : note->_smallCuttableBySaberList)
            Scale(hitbox, inverse);
    } else if (auto bomb = il2cpp_utils::try_cast<BombNoteController>(self).value_or(nullptr))
        Scale(bomb->_cuttableBySaber, inverse);''',
    '''    if (auto note = safe_ptr<NoteController>(*self).try_cast<GameNoteController>()) {
        for (auto hitbox : note->_bigCuttableBySaberList)
            Scale(hitbox, inverse);
        for (auto hitbox : note->_smallCuttableBySaberList)
            Scale(hitbox, inverse);
    } else if (auto bomb = safe_ptr<NoteController>(*self).try_cast<BombNoteController>()) {
        Scale(bomb->_cuttableBySaber, inverse);
    }''',
)

# Fail loudly if known obsolete APIs remain in the source after migration.
for rel in ("src/legacy.cpp", "src/loading.cpp", "src/hooks.cpp", "src/main.cpp", "include/config.hpp"):
    _, data = read(rel)
    for obsolete in ("il2cpp_utils::exceptions::StackTraceException", "i2c::exceptions::StackTraceException", "il2cpp_functions::Init()", "ByRef<", "il2cpp_utils::try_cast", "SafePtr("):
        if obsolete in data:
            raise SystemExit(f"{rel}: obsolete API remains after migration: {obsolete}")

print("Applied guarded CustomModels -> Beat Saber 1.45.3 / Hook 9.3 source migrations.")
