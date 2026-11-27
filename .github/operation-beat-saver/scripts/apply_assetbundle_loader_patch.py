#!/usr/bin/env python3
"""Apply the narrow Unity AssetBundle loader compatibility patch during the native build."""
from pathlib import Path

path = Path("src/loading.cpp")
if not path.is_file():
    raise SystemExit("src/loading.cpp is missing; run the CustomModels source port first")
source = path.read_text()

old_includes = '#include "loading.hpp"'
required = [
    '#include "System/IntPtr.hpp"',
    '#include "UnityEngine/Bindings/ManagedSpanWrapper.hpp"',
]
if source.count(old_includes) != 1:
    raise SystemExit("loading.cpp include anchor changed; refusing an unreviewed patch")
for include in required:
    if include not in source:
        source = source.replace(old_includes, old_includes + "\n" + include, 1)
        old_includes = include

old_resolver = '''static auto LoadFromMemoryAsync = i2c::resolve_icall<UnityEngine::AssetBundleCreateRequest*, ArrayW<uint8_t>, uint32_t>(
        "UnityEngine.AssetBundle::LoadFromMemoryAsync_Internal"
    );
    if (!LoadFromMemoryAsync)
        throw std::runtime_error("Could not resolve Unity AssetBundle::LoadFromMemoryAsync_Internal");'''
new_resolver = '''using UnityEngine::Bindings::ManagedSpanWrapper;
    static auto LoadFromMemoryAsync = i2c::resolve_icall<UnityEngine::AssetBundleCreateRequest*, ArrayW<uint8_t>, uint32_t>(
        "UnityEngine.AssetBundle::LoadFromMemoryAsync_Internal"
    );
    static auto LoadFromMemoryAsyncInjected = i2c::resolve_icall<System::IntPtr, ManagedSpanWrapper*, uint32_t>(
        "UnityEngine.AssetBundle::LoadFromMemoryAsync_Internal_Injected"
    );
    if (!LoadFromMemoryAsync && !LoadFromMemoryAsyncInjected)
        throw std::runtime_error("Could not resolve Unity AssetBundle LoadFromMemoryAsync (standard or injected)");'''

if new_resolver not in source:
    if source.count(old_resolver) != 1:
        raise SystemExit("Expected exactly one original AssetBundle resolver; refusing patch")
    source = source.replace(old_resolver, new_resolver, 1)

old_call = "auto request = (*LoadFromMemoryAsync)(array, 0);"
new_call = '''UnityEngine::AssetBundleCreateRequest* request = nullptr;
    if (LoadFromMemoryAsync) {
        request = (*LoadFromMemoryAsync)(array, 0);
    } else {
        ManagedSpanWrapper span{const_cast<char*>(bytes.data()), static_cast<int32_t>(bytes.size())};
        auto nativeRequest = (*LoadFromMemoryAsyncInjected)(&span, 0);
        if (nativeRequest.m_value)
            request = UnityEngine::AssetBundleCreateRequest::BindingsMarshaller::ConvertToManaged(nativeRequest);
    }'''

if new_call not in source:
    if source.count(old_call) != 1:
        raise SystemExit("Expected exactly one AssetBundle loader call; refusing patch")
    source = source.replace(old_call, new_call, 1)

if "if (!request) {" not in source:
    raise SystemExit("Null-request failure guard is missing after loader migration")
path.write_text(source)
print("Applied AssetBundle standard/injected loader compatibility patch before compilation.")
