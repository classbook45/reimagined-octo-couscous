#!/usr/bin/env python3
"""Deliberate, assertion-checked CustomModels port for Beat Saber 1.45.3."""

from pathlib import Path
import re

ROOTS = (Path("include"), Path("src"))

def edit(path, old, new, expected=1):
    source = path.read_text()
    count = source.count(old)
    if count != expected:
        raise SystemExit(f"{path}: expected {expected} occurrence(s), found {count}: {old!r}")
    path.write_text(source.replace(old, new))

# Hook 9 moved the public hook header and folded the old il2cpp utility namespaces
# into i2c. These are explicit API renames, applied only to C++ source/header files.
for root in ROOTS:
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix not in {".h", ".hpp", ".cpp"}:
            continue
        source = path.read_text()
        updated = source.replace(
            '"beatsaber-hook/shared/utils/hooking.hpp"',
            '"beatsaber-hook/shared/hooking.hpp"'
        )
        updated = updated.replace(
            '"beatsaber-hook/shared/utils/logging.hpp"',
            '"beatsaber-hook/shared/utils.hpp"'
        )
        updated = updated.replace(
            '"beatsaber-hook/shared/config/config-utils.hpp"',
            '"beatsaber-hook/shared/utils.hpp"'
        )
        updated = updated.replace("il2cpp_functions::", "i2c::functions::")
        updated = updated.replace("il2cpp_utils::", "i2c::")
        updated = re.sub(r"\bSafePtr\b", "safe_ptr", updated)
        updated = updated.replace('"metacore/shared/game.hpp"', '"metacore-bs/shared/game.hpp"')
        updated = updated.replace('"metacore/shared/internals.hpp"', '"metacore-bs/shared/internals.hpp"')
        updated = updated.replace('"metacore/shared/ui.hpp"', '"metacore-bs/shared/ui.hpp"')
        if updated != source:
            path.write_text(updated)

# The 1.45.3 generated CORDL headers no longer expose this old transition type.
# Gameplay color state is already supplied by MetaCoreBS; keep the tutorial path
# functional without installing a hook against a nonexistent generated class.
hooks_cpp = Path("src/hooks.cpp")
source = hooks_cpp.read_text()
source = source.replace('#include "GlobalNamespace/TutorialScenesTransitionSetupDataSO.hpp"\n', "")
pattern = re.compile(
    r"// not sure why hooking TutorialSceneSetupData_ctor doesn't work, maybe too small somehow\?\s*"
    r"MAKE_AUTO_HOOK_MATCH\(\s*TutorialScenesTransitionSetupDataSO_Init,.*?\n\}\n\n",
    re.S
)
source, count = pattern.subn(
    "// Tutorial scene color state is provided by MetaCoreBS on 1.45.3; the old transition hook type is not generated.\n\n",
    source
)
if count != 1:
    raise SystemExit(f"src/hooks.cpp: expected to remove exactly one obsolete tutorial transition hook, found {count}")
hooks_cpp.write_text(source)

# Hook 9 no longer has the legacy MAKE_AUTO_HOOK_MATCH helper. Preserve the
# project's deferred-install lifecycle while using Hook 9's typed hook structs.
hooks_hpp = Path("include/hooks.hpp")
hooks_hpp.write_text(r'''#pragma once

#include "beatsaber-hook/shared/hooking.hpp"
#include "main.hpp"

class Hooks {
   private:
    static inline std::vector<void (*)()> installFuncs;

   public:
    static inline void AddInstallFunc(void (*installFunc)()) { installFuncs.push_back(installFunc); }

    static inline void Install() {
        logger.info("Installing hooks...");
        for (auto& func : installFuncs)
            func();
        logger.info("Installed all hooks!");
    }
};

#define MAKE_AUTO_HOOK_MATCH(name_, method_, ret_type, ...)                                                        \
    struct BS_HOOK_HIDDEN hook_##name_ {                                                                            \
        static constexpr auto cast_test = []<typename T>() { return requires { static_cast<T>(method_); }; };      \
        using func_t = ret_type (*)(__VA_ARGS__);                                                                   \
        using cast_t = ::i2c::detail::method_check<cast_test, func_t>::type;                                         \
        static_assert(cast_test.operator()<cast_t>(), "Hook method signature does not match!");                    \
        static_assert(::i2c::detail::match_hookable<static_cast<cast_t>(method_)>, "Method cannot be hooked!");     \
        __INTERNAL_HOOK_STRUCT(name_, ::i2c::metadata_getter<static_cast<cast_t>(method_)>::method_info(), ret_type, __VA_ARGS__) \
    };                                                                                                              \
    struct Auto_Install_##name_ {                                                                                   \
        static void Install() { ::i2c::install_hook<hook_##name_>(logger); }                                         \
        Auto_Install_##name_() { Hooks::AddInstallFunc(Install); }                                                   \
    };                                                                                                              \
    static Auto_Install_##name_ Auto_Install_Instance_##name_;                                                      \
    ret_type hook_##name_::hook_m_##name_(__VA_ARGS__)
''')

# Hook 9 / MetaCore 2 split the Beat Saber-specific API into MetaCoreBS.
# RapidjsonMacros 3 retains the model manifest serialization macros; config-utils
# 3 is now used only for persisted mod settings.
Path("include/json.hpp").write_text(r'''#pragma once

#include "rapidjson-macros/shared/macros.hpp"
#include "rapidjson-macros/shared/serialization.hpp"
#include "UnityEngine/Color.hpp"

namespace ConfigUtils {
    DECLARE_JSON_STRUCT(Color) {
        VALUE(float, r);
        VALUE(float, g);
        VALUE(float, b);
        VALUE(float, a);

        Color() = default;
        Color(UnityEngine::Color const& value) : r(value.r), g(value.g), b(value.b), a(value.a) {}
        Color& operator=(UnityEngine::Color const& value) {
            r = value.r; g = value.g; b = value.b; a = value.a;
            return *this;
        }
        operator UnityEngine::Color() const { return {r, g, b, a}; }
    };
    inline UnityEngine::Color operator*(UnityEngine::Color const& lhs, Color const& rhs) {
        auto value = static_cast<UnityEngine::Color>(rhs);
        return {lhs.r * value.r, lhs.g * value.g, lhs.b * value.b, lhs.a * value.a};
    }
}

namespace CustomModels {
    DECLARE_JSON_STRUCT(TrailObject) {
        VALUE(int, trailId);
        VALUE(bool, isTop);
    };

    DECLARE_JSON_STRUCT(TrailInfo) {
        VALUE(int, trailId);
        VALUE(int, colorType);
        VALUE(ConfigUtils::Color, trailColor);
        VALUE(ConfigUtils::Color, multiplierColor);
        VALUE(int, length);
        VALUE(float, whiteStep);
    };

    DECLARE_JSON_STRUCT(SaberInfo) {
        VALUE_DEFAULT(bool, hasTrail, false);
        VALUE_DEFAULT(bool, keepFakeGlow, false);
        VALUE_DEFAULT(bool, isLegacy, false);
    };

    DECLARE_JSON_STRUCT(NoteInfo) {
        VALUE_DEFAULT(bool, hasDebris, false);
        VALUE_DEFAULT(bool, hasChainHeadDebris, false);
        VALUE_DEFAULT(bool, hasChainLinkDebris, false);
        VALUE_DEFAULT(bool, hasSlider, false);
        VALUE_DEFAULT(bool, hasBomb, false);
        VALUE_DEFAULT(bool, showArrows, false);
        VALUE_DEFAULT(bool, isMirrorable, false);
        VALUE_DEFAULT(bool, isLegacy, false);
    };

    DECLARE_JSON_STRUCT(WallInfo) {
        VALUE_DEFAULT(bool, replaceCoreMaterial, false);
        VALUE_DEFAULT(bool, replaceFrameMaterial, false);
        VALUE_DEFAULT(bool, replaceCoreMesh, false);
        VALUE_DEFAULT(bool, replaceFrameMesh, false);
        VALUE_DEFAULT(bool, disableCore, false);
        VALUE_DEFAULT(bool, disableFrame, false);
        VALUE_DEFAULT(bool, disableFakeGlow, false);
        VALUE_DEFAULT(bool, isMirrorable, false);
        VALUE_DEFAULT(bool, isLegacy, false);
    };

    DECLARE_JSON_STRUCT(Descriptor) {
        VALUE(std::string, author);
        VALUE(std::string, objectName);
        VALUE(std::string, description);
        VALUE_DEFAULT(std::string, coverImage, "");
    };

    DECLARE_JSON_STRUCT(Manifest) {
        VALUE(std::string, androidFileName);
        VALUE(Descriptor, descriptor);
        VALUE(UnparsedJSON, config);
    };

    DECLARE_JSON_STRUCT(LegacyDescriptor) {
        VALUE(std::string, authorName);
        VALUE(std::string, objectName);
        VALUE(std::string, description);
    };

    DECLARE_JSON_STRUCT(LegacyTrail) {
        VALUE(std::string, name);
        VALUE(int, colorType);
        VALUE(ConfigUtils::Color, trailColor);
        VALUE(ConfigUtils::Color, multiplierColor);
        VALUE(int, length);
        VALUE(float, whiteStep);
    };

    DECLARE_JSON_STRUCT(LegacySaberConfig) {
        VALUE_DEFAULT(bool, enableFakeGlow, false);
        VALUE_DEFAULT(bool, hasCustomTrails, false);
        VECTOR_DEFAULT(LegacyTrail, leftTrails, {});
        VECTOR_DEFAULT(LegacyTrail, rightTrails, {});
    };

    DECLARE_JSON_STRUCT(LegacyNoteConfig) {
        VALUE_DEFAULT(bool, disableBaseGameArrows, true);
        VALUE_DEFAULT(bool, hasBomb, false);
        VALUE_DEFAULT(bool, hasDebris, false);
    };

    DECLARE_JSON_STRUCT(LegacyWallConfig) {
        VALUE_DEFAULT(bool, replaceCoreMaterial, false);
        VALUE_DEFAULT(bool, replaceCoreMesh, false);
        VALUE_DEFAULT(bool, disableFrame, false);
        VALUE_DEFAULT(bool, disableFakeGlow, false);
        VALUE_DEFAULT(bool, replaceFrameMaterial, false);
        VALUE_DEFAULT(bool, replaceFrameMesh, false);
        VALUE_DEFAULT(bool, scoreSubmissionDisabled, false);
        VALUE_DEFAULT(bool, moreThan1Core, false);
        VALUE_DEFAULT(bool, moreThan1Frame, false);
    };
}
''')

Path("include/config.hpp").write_text(r'''#pragma once

#include "config-utils/shared/config-utils.hpp"

namespace CustomModels {
    // config-utils 3 uses reflect-cpp, which needs plain aggregate structs.
    // RapidJSON-generated structs inherit a data-bearing base and are not valid
    // reflect-cpp models; keep manifest serialization separate in json.hpp.
    struct SaberSettings {
        float length = 1;
        bool overrideLength = false;
        float width = 1;
        bool overrideWidth = false;
        float Length() const { return overrideLength ? length : 1; }
        float Width() const { return overrideWidth ? width : 1; }
    };
    struct TrailSettings {
        bool whiteStep = false;
        float length = 1;
        bool overrideLength = false;
        float width = 1;
        bool overrideWidth = false;
        float widthOffset = 0;
        float Length() const { return overrideLength ? length : 1; }
        float Width() const { return overrideWidth ? width : 1; }
    };
    struct NoteSettings {
        float size = 1;
        bool overrideSize = false;
        bool defaultBombs = false;
        bool defaultDebris = false;
        float Size() const { return overrideSize ? size : 1; }
    };
    struct WallSettings {
        bool disableFrame = false;
        bool disableCore = false;
    };
    struct Profile {
        std::string SaberModel = "";
        std::string TrailModel = "";
        std::string MenuSaberModel = "";
        std::string MenuTrailModel = "";
        std::string NoteModel = "";
        std::string WallModel = "";
        bool MenuSaber = false;
        int TrailMode = 0;
        int MenuTrailMode = 0;
        SaberSettings SaberSettings{};
        TrailSettings TrailSettings{};
        SaberSettings MenuSaberSettings{};
        TrailSettings MenuTrailSettings{};
        NoteSettings NotesSettings{};
        WallSettings WallsSettings{};
    };
}

#define PROFILE_GETTER(name) auto& name() { return CurrentProfile().name; }

DECLARE_CONFIG(Config) {
    CONFIG_VALUE(Enabled, bool, "ModEnabled", true);
    CONFIG_VALUE(Profile, std::string, "Profile", "Default");
    CONFIG_VALUE(
        Profiles,
        ConfigUtils::Map<CustomModels::Profile>,
        "Profiles",
        ConfigUtils::Map<CustomModels::Profile>({{"Default", CustomModels::Profile{}}})
    );

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
        for (auto& fail : fails)
            if (fail == file)
                return true;
        return false;
    }
};

#undef PROFILE_GETTER
''')


# Hook 9 / CORDL 4503 API changes verified against the published Hook 9.4.3,
# CORDL 4503 and BSML 0.6.7 headers.
for root in ROOTS:
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix not in {".h", ".hpp", ".cpp"}:
            continue
        source = path.read_text()
        updated = re.sub(r"\bgetDataDir\(", "get_data_dir(", source)
        updated = updated.replace("il2cpp_utils::exceptions::StackTraceException", "i2c::trace_exception")
        updated = updated.replace("i2c::functions::Init()", "i2c::functions::initialize()")
        if updated != source:
            path.write_text(updated)

loading_cpp = Path("src/loading.cpp")
source = loading_cpp.read_text()
source = source.replace('#include "loading.hpp"\n', '#include "loading.hpp"\n\n#include <algorithm>\n#include <set>\n#include "beatsaber-hook/shared/safeptr.hpp"\n')
source = source.replace(
    'auto array = ArrayW<uint8_t>({(uint8_t*) bytes.data(), bytes.size()});',
    'auto array = ArrayW<uint8_t>(bytes.size());\n    std::copy(bytes.begin(), bytes.end(), array.begin());'
)
source = source.replace('return request->isDone;', 'return request->get_isDone();')
source = source.replace('asset = object->ptr();', 'asset = object;')
loading_cpp.write_text(source)

hooks_cpp = Path("src/hooks.cpp")
source = hooks_cpp.read_text()
source = source.replace('#include "hooks.hpp"\n', '#include "hooks.hpp"\n\n#include "beatsaber-hook/shared/safeptr.hpp"\n')
source = source.replace('ByRef<NoteSpawnData>', 'by_ref<NoteSpawnData const>')
source = source.replace('ByRef<NoteDebris*>', 'by_ref<NoteDebris*>')
source = source.replace('ByRef<BeatmapKey>', 'by_ref<BeatmapKey const>')
source = source.replace('NoteData::GameplayType noteGameplayType', 'NoteData_GameplayType noteGameplayType')
source, removed = re.subn(
    r"// don't run the base class Awake on our saber trail\s*MAKE_AUTO_HOOK_MATCH\(SaberTrail_Awake,.*?\n\}\n\n",
    "",
    source,
    flags=re.S
)
if removed != 1:
    raise SystemExit(f"Expected to remove one obsolete SaberTrail::Awake hook, removed {removed}")
source = source.replace(
    'if (auto custom = i2c::try_cast<CustomModels::CustomSaberTrail>(self)) {',
    'if (auto custom = safe_ptr<SaberTrail*>(self).try_cast<CustomModels::CustomSaberTrail*>()) {'
)
source = source.replace(
    'if (auto note = i2c::try_cast<GameNoteController>(self).value_or(nullptr)) {',
    'if (auto note = safe_ptr<NoteController*>(self).try_cast<GameNoteController*>()) {'
)
source = source.replace(
    '} else if (auto bomb = i2c::try_cast<BombNoteController>(self).value_or(nullptr))',
    '} else if (auto bomb = safe_ptr<NoteController*>(self).try_cast<BombNoteController*>())'
)
hooks_cpp.write_text(source)

# Fail closed if any known incompatible API references remain.
all_cpp = "\n".join(p.read_text() for root in ROOTS for p in root.rglob("*") if p.is_file() and p.suffix in {".h", ".hpp", ".cpp"})
for stale in (
    "beatsaber-hook/shared/config/config-utils.hpp",
    "beatsaber-hook/shared/utils/hooking.hpp",
    "metacore/shared/game.hpp",
    "metacore/shared/internals.hpp",
    "metacore/shared/ui.hpp",
    "TutorialScenesTransitionSetupDataSO",
    "il2cpp_utils::",
    "il2cpp_functions::",
    "SafePtr",
    "getDataDir(",
    "ByRef<",
    "SaberTrail_Awake",
):
    if stale in all_cpp:
        raise SystemExit(f"Unmigrated 1.45.3 API reference remains: {stale}")

print("Ported CustomModels source: Hook 9 API, MetaCoreBS split, RapidjsonMacros 3, config-utils 3.")
