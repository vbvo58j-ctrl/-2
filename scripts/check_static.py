"""Static checks that run without a Flutter SDK: bracket balance, imports,
symbol/import consistency and the contracts of the v27 design."""
import re
import sys
from pathlib import Path

R = Path(__file__).resolve().parents[1]
problems = []


def strip(src):
    out, i, n = [], 0, len(src)
    while i < n:
        c = src[i]
        if src.startswith('//', i):
            j = src.find('\n', i); i = n if j < 0 else j; continue
        if src.startswith('/*', i):
            j = src.find('*/', i + 2); i = n if j < 0 else j + 2; continue
        if c in '\'"':
            raw = i > 0 and src[i - 1] == 'r'
            if src.startswith(c * 3, i):
                j = src.find(c * 3, i + 3); i = n if j < 0 else j + 3; continue
            i += 1
            while i < n and src[i] != c:
                if src[i] == '\\' and not raw: i += 1
                elif src[i] == '$' and i + 1 < n and src[i + 1] == '{':
                    depth, i = 1, i + 2
                    while i < n and depth:
                        depth += (src[i] == '{') - (src[i] == '}'); i += 1
                    continue
                i += 1
            i += 1; continue
        out.append(c); i += 1
    return ''.join(out)


def balanced(text):
    pairs, st = {')': '(', ']': '[', '}': '{'}, []
    for ch in text:
        if ch in '([{': st.append(ch)
        elif ch in ')]}':
            if not st or st.pop() != pairs[ch]: return False
    return not st


SYMBOLS = {
    r'\bMeshHub\b|\bMeshPeer\b|\bMeshStatus\b': 'mesh_hub.dart',
    r'\bPacketCodec\b|\bStorageCodec\b': 'packet_codec.dart',
    r'\bBlousab(GlowFrame|GlowTitle|IconBox|BellButton|ActionButton|SectionHeader|Group|Tile|ProfileAvatar|StoryAvatar|BottomBar|NavItem|PageBackground|NeonPanel|ChatWallpaper)\b|\bBlousabVisuals\b': 'blousab_visuals.dart',
    r'\bLocalNetworkService\b': 'local_network_service.dart',
    r'\bWifiAwareService\b': 'wifi_aware_service.dart',
    r'\bBluetoothClassicService\b|\bBlousabEvent\b|\bBlousabDevice\b': 'bluetooth_classic_service.dart',
    r'\bSystemRadios\b|\bRadioReadiness\b': 'system_radios.dart',
    r'\bTimer\b|\bStreamSubscription\b|\bunawaited\b|\bCompleter\b': 'dart:async',
    r'\bjsonEncode\b|\bjsonDecode\b|\bbase64Encode\b|\bbase64Decode\b': 'dart:convert',
    r'\bSharedPreferences\b': 'shared_preferences',
}

for f in sorted(list((R / 'lib').rglob('*.dart')) + list((R / 'test').rglob('*.dart'))):
    src = f.read_text(encoding='utf-8')
    rel = f.relative_to(R)
    if not balanced(strip(src)):
        problems.append(f'unbalanced brackets: {rel}')
    imports = re.findall(r"^import '([^']+)'", src, re.M)
    for imp in imports:
        if imp.startswith(('package:', 'dart:')): continue
        if not (f.parent / imp).resolve().exists():
            problems.append(f'missing import target: {rel} -> {imp}')
    body = re.sub(r'^import .*$', '', src, flags=re.M)
    if f.parts[-3:-1] == ('lib', 'models'): continue
    for pattern, lib in SYMBOLS.items():
        if f.name == lib: continue
        if re.search(pattern, strip(body)) and not any(lib in i for i in imports):
            problems.append(f'{rel}: uses a symbol of {lib} without importing it')

# --- v27 contracts -----------------------------------------------------------
def read(p): return (R / p).read_text(encoding='utf-8')

main = read('lib/main.dart')
if 'RadioGate(child: BlousabShell())' not in main: problems.append('main.dart must start with RadioGate')
if 'BluetoothGate' in main: problems.append('the old optional BluetoothGate still exists')
for leftover in ['_connectionMode', 'connection_mode', 'LocalNetworkService.instance.start']:
    for f in (R / 'lib').rglob('*.dart'):
        if leftover in f.read_text(encoding='utf-8') and f.name not in ('mesh_hub.dart',):
            problems.append(f'{f.relative_to(R)} still references {leftover}')

# the retired app name may survive only inside the one-time migration
for f in list((R / 'lib').rglob('*.dart')) + list((R / 'android').rglob('*.kt')) + list((R / 'scripts').glob('*')):
    if f.name in ('legacy_migration.dart', 'check_static.py'): continue
    if re.search(r'wasl', f.read_text(encoding='utf-8', errors='ignore'), re.I):
        problems.append(f'legacy app name left in {f.relative_to(R)}')

for name in ['public_feed_screen', 'stories_strip', 'chat_screen', 'communities_screen', 'games_screen']:
    text = read(f'lib/screens/{name}.dart')
    for banned in ['LocalNetworkService.instance.broadcastMessage', '_bluetooth.sendMessage', '_bluetooth.broadcastMessage']:
        if banned in text: problems.append(f'{name}.dart bypasses MeshHub with {banned}')

manifest = read('android/app/src/main/AndroidManifest.xml')
for needle in ['MeshForegroundService', 'FOREGROUND_SERVICE_CONNECTED_DEVICE']:
    if needle not in manifest: problems.append(f'manifest lacks {needle}')
if 'SYSTEM_ALERT_WINDOW' in manifest: problems.append('manifest still requests SYSTEM_ALERT_WINDOW')
for needle in ['isWifiEnabled', 'startKeepAlive', 'isDiscoverable', 'extraSockets']:
    if needle not in read('android/app/src/main/kotlin/com/plosap/myapp/MainActivity.kt'):
        problems.append(f'MainActivity.kt lacks {needle}')

for p in problems: print('FAIL:', p)
if problems: sys.exit(1)
print('PASS: static source checks (no Flutter SDK needed)')
