#!/usr/bin/env python3
"""
scan-war.py — WAR を静的に検査して、警告 ②③④⑤⑥⑦ の「原因になっている中身」を特定する

  ② jboss-deployment-structure.xml の <resource-root> が WAR 内に実在するか
  ③ jboss-deployment-structure.xml / MANIFEST.MF の Dependencies にある private モジュール
     (WAR 本体だけでなく WEB-INF/lib の各 jar の MANIFEST も見る。例: spring-core → org.jboss.vfs)
  ④ jakarta.servlet.AsyncListener 実装クラスのうち「引数なしコンストラクタが無い」もの
     (Weld 無効の WAR では WFLYEE0048 → WFLYEE0007 になる)
  ⑤ WildFly が「CDI アノテーション」と判定する 20 種のアノテーションの使用箇所 (どの jar か)
     と beans.xml の有無、WEB-INF/lib に同梱された Jakarta EE API jar
  ⑥ <exclusions> に書かれたモジュールのうち、デプロイの依存に直接入らないもの (空振りになる)
  ⑦ javax.* (Java EE 時代の名前空間) のクラスや TLD を含む jar

使い方:
  python scan-war.py iwinmichl.war [--jboss-home /opt/jboss-eap]
    --jboss-home を渡すと、実サーバの module.xml の jboss.api を読んで ③ を正確に判定する
外部ライブラリ不要 (Python 3.8+ 標準ライブラリのみ)。
"""
import argparse
import io
import os
import re
import struct
import sys
import xml.etree.ElementTree as ET
import zipfile
from collections import defaultdict

# WildFly (weld/subsystem CdiAnnotations) が「CDI アノテーションあり」と判定する 20 種
CDI_ANNOTATIONS = [
    'jakarta/decorator/Decorator', 'jakarta/decorator/Delegate',
    'jakarta/enterprise/context/ApplicationScoped', 'jakarta/enterprise/context/ConversationScoped',
    'jakarta/enterprise/context/RequestScoped', 'jakarta/enterprise/context/SessionScoped',
    'jakarta/enterprise/context/NormalScope', 'jakarta/enterprise/context/Dependent',
    'jakarta/inject/Singleton', 'jakarta/enterprise/event/Observes',
    'jakarta/enterprise/inject/Alternative', 'jakarta/enterprise/inject/Any', 'jakarta/enterprise/inject/Default',
    'jakarta/enterprise/inject/Disposes', 'jakarta/enterprise/inject/Model', 'jakarta/enterprise/inject/New',
    'jakarta/enterprise/inject/Produces', 'jakarta/enterprise/inject/Specializes',
    'jakarta/enterprise/inject/Stereotype', 'jakarta/enterprise/inject/Typed',
]
CDI_DESC = {'L' + a + ';' for a in CDI_ANNOTATIONS}
ASYNC_LISTENER = 'jakarta/servlet/AsyncListener'

# --jboss-home 無しで使う既知の private モジュール (Red Hat「JBoss EAP 8 Included Modules」より抜粋)
KNOWN_PRIVATE = {'org.apache.cxf.impl', 'org.jboss.vfs', 'org.jboss.logmanager.log4j2', 'org.jboss.ws.spi',
                 'org.jboss.as.server', 'org.jboss.as.controller', 'org.jboss.as.ee', 'org.jboss.as.web-common',
                 'org.jboss.jandex', 'org.jboss.modules', 'org.wildfly.security.elytron-private'}
# logging サブシステムが暗黙に追加するモジュール (add-logging-api-dependencies=true のとき)
LOGGING_IMPLICIT = {'org.apache.commons.logging', 'org.apache.logging.log4j.api', 'org.jboss.logging',
                    'org.jboss.logging.jul-to-slf4j-stub', 'org.jboss.logmanager', 'org.slf4j', 'org.slf4j.impl'}
EE_API_JAR = re.compile(r'(jakarta|javax)\.[a-z.]+-api|(^|/)jakarta\.(inject|annotation|transaction|persistence|'
                        r'validation|enterprise|interceptor|servlet|ws\.rs|xml\.bind|xml\.ws|faces|ejb|jms|mail|json)',
                        re.I)


# ---------------------------------------------------------------- class file parser (最小限)
class ClassInfo:
    __slots__ = ('name', 'super', 'interfaces', 'flags', 'ctors', 'annotations', 'refs_javax_servlet')


def parse_class(data):
    if data[:4] != b'\xca\xfe\xba\xbe':
        return None
    pos = 8
    (count,) = struct.unpack_from('>H', data, pos); pos += 2
    utf8, classes = {}, {}
    i = 1
    while i < count:
        tag = data[pos]; pos += 1
        if tag == 1:
            (ln,) = struct.unpack_from('>H', data, pos); pos += 2
            utf8[i] = data[pos:pos + ln].decode('utf-8', 'replace'); pos += ln
        elif tag == 7:
            (idx,) = struct.unpack_from('>H', data, pos); pos += 2; classes[i] = idx
        elif tag in (8, 16, 19, 20):
            pos += 2
        elif tag == 15:
            pos += 3
        elif tag in (3, 4, 9, 10, 11, 12, 17, 18):
            pos += 4
        elif tag in (5, 6):
            pos += 8; i += 1
        else:
            return None
        i += 1
    cname = lambda ci: utf8.get(classes.get(ci, 0), '')
    flags, this_c, super_c, icount = struct.unpack_from('>HHHH', data, pos); pos += 8
    ifaces = [cname(struct.unpack_from('>H', data, pos + 2 * k)[0]) for k in range(icount)]
    pos += 2 * icount
    annots = set()

    def read_ev(p):
        tag = chr(data[p]); p += 1
        if tag in 'BCDFIJSZsc':
            return p + 2
        if tag == 'e':
            return p + 4
        if tag == '@':
            return read_annotation(p)
        if tag == '[':
            (n,) = struct.unpack_from('>H', data, p); p += 2
            for _ in range(n):
                p = read_ev(p)
            return p
        raise ValueError(tag)

    def read_annotation(p):
        tidx, npairs = struct.unpack_from('>HH', data, p); p += 4
        annots.add(utf8.get(tidx, ''))
        for _ in range(npairs):
            p = read_ev(p + 2)
        return p

    def read_attrs(p, ctor_holder=None):
        (n,) = struct.unpack_from('>H', data, p); p += 2
        for _ in range(n):
            nidx, ln = struct.unpack_from('>HI', data, p); p += 6
            an = utf8.get(nidx, '')
            if an in ('RuntimeVisibleAnnotations', 'RuntimeInvisibleAnnotations'):
                (k,) = struct.unpack_from('>H', data, p); q = p + 2
                for _ in range(k):
                    q = read_annotation(q)
            elif an in ('RuntimeVisibleParameterAnnotations', 'RuntimeInvisibleParameterAnnotations'):
                q = p + 1
                for _ in range(data[p]):
                    (k,) = struct.unpack_from('>H', data, q); q += 2
                    for _ in range(k):
                        q = read_annotation(q)
            p += ln
        return p

    ctors = []
    for member in ('fields', 'methods'):
        (n,) = struct.unpack_from('>H', data, pos); pos += 2
        for _ in range(n):
            _, nidx, didx = struct.unpack_from('>HHH', data, pos); pos += 6
            if member == 'methods' and utf8.get(nidx) == '<init>':
                ctors.append(utf8.get(didx, ''))
            pos = read_attrs(pos)
    read_attrs(pos)
    ci = ClassInfo()
    ci.name, ci.super, ci.interfaces, ci.flags = cname(this_c), cname(super_c), ifaces, flags
    ci.ctors, ci.annotations = ctors, annots
    ci.refs_javax_servlet = any(v.startswith(('javax/servlet/', 'Ljavax/servlet/')) or 'Ljavax/servlet/' in v
                                for v in utf8.values())
    return ci


# ---------------------------------------------------------------- WAR walking
def walk_archive(zf, origin, out_classes, out_meta):
    for info in zf.infolist():
        n = info.filename
        if n.endswith('.class'):
            try:
                ci = parse_class(zf.read(n))
            except Exception:
                ci = None
            if ci:
                out_classes.append((origin, ci))
        elif n.upper() == 'META-INF/MANIFEST.MF':
            out_meta[origin]['manifest'] = zf.read(n).decode('utf-8', 'replace')
        elif n.lower().endswith('.tld'):
            out_meta[origin].setdefault('tlds', []).append((n, zf.read(n).decode('utf-8', 'replace')))
        elif n.endswith('beans.xml'):
            out_meta[origin].setdefault('beans', []).append(n)


def manifest_deps(text):
    if not text:
        return []
    joined = re.sub(r'\r?\n ', '', text)
    for line in joined.splitlines():
        if line.lower().startswith('dependencies:'):
            return [d.strip().split()[0] for d in line.split(':', 1)[1].split(',') if d.strip()]
    return []


def module_api(jboss_home, name):
    if not jboss_home:
        return 'private' if name in KNOWN_PRIVATE else '?'
    rel = name.replace('.', os.sep)
    for base in (os.path.join(jboss_home, 'modules', 'system', 'layers', 'base'), os.path.join(jboss_home, 'modules')):
        p = os.path.join(base, rel, 'main', 'module.xml')
        if os.path.exists(p):
            m = re.search(r'name="jboss\.api"\s+value="([^"]+)"', open(p, encoding='utf-8').read())
            return m.group(1) if m else 'public'
    return 'not-found'


def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')  # Windows のコンソールでも UTF-8 で出す
    ap = argparse.ArgumentParser()
    ap.add_argument('war')
    ap.add_argument('--jboss-home')
    a = ap.parse_args()
    war = zipfile.ZipFile(a.war)
    names = set(war.namelist())
    classes, meta = [], defaultdict(dict)
    walk_archive(war, '(WAR)', classes, meta)
    libs = sorted(n for n in names if n.startswith('WEB-INF/lib/') and n.endswith('.jar'))
    for lib in libs:
        try:
            walk_archive(zipfile.ZipFile(io.BytesIO(war.read(lib))), lib.split('/')[-1], classes, meta)
        except zipfile.BadZipFile:
            pass

    jds = None
    for cand in ('WEB-INF/jboss-deployment-structure.xml', 'META-INF/jboss-deployment-structure.xml'):
        if cand in names:
            jds = ET.fromstring(war.read(cand))
    strip = lambda t: t.split('}')[-1]
    findall = lambda el, tag: [e for e in el.iter() if strip(e.tag) == tag] if el is not None else []

    print(f'# scan-war: {a.war}  (classes={len(classes)}, WEB-INF/lib jars={len(libs)})')

    # ② -------------------------------------------------------------
    print('\n## ② resource-root (jboss-deployment-structure.xml)')
    roots = [e.get('path') for e in findall(jds, 'resource-root')]
    if not roots:
        print('  OK: 追加リソースルートの指定なし')
    for r in roots:
        exists = any(n == r or n.startswith(r.rstrip('/') + '/') for n in names)
        print(f'  {"OK " if exists else "NG "} {r}  {"(存在する)" if exists else "← WAR に無い: WFLYSRV0058 の原因。記述を削除する"}')

    # ③ -------------------------------------------------------------
    print('\n## ③ 明示依存 (jboss-deployment-structure.xml / MANIFEST.MF Dependencies)')
    deps = [(e.get('name'), 'jboss-deployment-structure.xml') for e in findall(jds, 'dependencies')
            for e in findall(e, 'module')]
    for origin, m in meta.items():
        for d in manifest_deps(m.get('manifest')):
            deps.append((d, f'{origin} の MANIFEST.MF'))
    if not deps:
        print('  明示依存なし')
    for name, src in deps:
        api = module_api(a.jboss_home, name)
        mark = 'NG ' if api in ('private', 'unsupported', 'deprecated') else 'OK '
        print(f'  {mark}{name:40s} jboss.api={api:11s} 出どころ: {src}')

    # ⑥ -------------------------------------------------------------
    print('\n## ⑥ exclusions (除外指定)')
    excl = [e.get('name') for e in findall(jds, 'exclusions') for e in findall(e, 'module')]
    if not excl:
        print('  除外指定なし')
    for x in excl:
        if x == 'org.jboss.logmanager.log4j2':
            print(f'  NG {x}: デプロイの依存に直接入らない (org.apache.logging.log4j.api の内部依存) → 空振り = WFLYSRV0274。'
                  ' 自前の Log4j 2 を使うなら除外対象は org.apache.logging.log4j.api')
        elif x in LOGGING_IMPLICIT:
            print(f'  OK {x}: logging サブシステムの暗黙依存 (除外は有効)')
        else:
            print(f'  ?  {x}: 暗黙依存に入っていなければ WFLYSRV0274 (空振り)。サーバログで確認')
    subs = [e.get('name') for e in findall(jds, 'exclude-subsystems') for e in findall(e, 'subsystem')]
    print(f'  exclude-subsystems: {subs or "なし"}')

    # ④ -------------------------------------------------------------
    print('\n## ④ jakarta.servlet.AsyncListener 実装 (Weld 無効の WAR では引数なしコンストラクタが必要)')
    by_name = {ci.name: (o, ci) for o, ci in classes}

    def implements(cn, target, seen=None):
        seen = seen or set()
        if cn in seen or cn not in by_name:
            return False
        seen.add(cn)
        _, c = by_name[cn]
        if target in c.interfaces:
            return True
        return any(implements(x, target, seen) for x in c.interfaces + [c.super])

    hits = 0
    for o, ci in classes:
        if ci.flags & 0x0600:  # interface / abstract
            continue
        if implements(ci.name, ASYNC_LISTENER):
            hits += 1
            ok = '()V' in ci.ctors
            print(f'  {"OK " if ok else "NG "}{ci.name.replace("/", ".")}  [{o}]'
                  f'{"" if ok else "  ← 引数なしコンストラクタ無し (WFLYEE0048 → WFLYEE0007)"}')
    if not hits:
        print('  該当なし')

    # ⑤ -------------------------------------------------------------
    print('\n## ⑤ WildFly が「CDI アノテーション」と判定するもの (WFLYWELD0013 の材料)')
    beans = [(o, b) for o, m in meta.items() for b in m.get('beans', [])]
    print(f'  beans.xml: {beans or "なし"}')
    cdi_by_origin = defaultdict(set)
    for o, ci in classes:
        for d in ci.annotations & CDI_DESC:
            cdi_by_origin[o].add(f'{ci.name.replace("/", ".")} @{d[1:-1].split("/")[-1]}')
    if not cdi_by_origin:
        print('  使用なし')
    for o, uses in sorted(cdi_by_origin.items()):
        print(f'  NG {o}: {len(uses)} 件  例: {sorted(uses)[:3]}')
    ee_api = [l.split('/')[-1] for l in libs if EE_API_JAR.search(l.split('/')[-1])]
    print(f'  WEB-INF/lib の Jakarta/Java EE API jar (サーバが提供するので provided にする): {ee_api or "なし"}')

    # ⑦ -------------------------------------------------------------
    print('\n## ⑦ javax.* (Java EE 時代) の痕跡')
    javax_jars = defaultdict(int)
    for o, ci in classes:
        if ci.name.startswith('javax/servlet/') or ci.refs_javax_servlet:
            javax_jars[o] += 1
    for o, m in meta.items():
        for tld, text in m.get('tlds', []):
            for cls in re.findall(r'<(?:validator-class|tag-class|listener-class)>\s*(javax\.[\w.$]+)', text):
                print(f'  NG TLD {o}:{tld} → {cls}')
    for o, n in sorted(javax_jars.items()):
        print(f'  NG {o}: javax.servlet を参照・定義するクラス {n} 個 (EAP 8 は jakarta.* のみ。Jakarta 版へ置換/除去)')
    if not javax_jars:
        print('  javax.servlet の参照なし')
    return 0


if __name__ == '__main__':
    sys.exit(main())
