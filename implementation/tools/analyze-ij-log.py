#!/usr/bin/env python3
"""
analyze-ij-log.py — IronJacamar (データソース) 系の警告 ⑧⑩⑪⑫⑬ をログから解析する

  (A) ⑧ IJ030040 / ⑫ IJ030042 … 閉じ忘れた Statement / ResultSet を「作った場所」のランキング
  (B) ⑪ IJ000621             … 死んでいた接続の放置時間 (= ログ時刻 - lastReturned) と idle-timeout の推奨値
  (C) ⑩ IJ030027             … 直後の Caused by から根本原因を分類 (wait_timeout / RST / 読み取りタイムアウト 等)
  (D) ⑬ IJ000615             … 停止処理中に出たのか (SIGTERM 等)、それ以外 (アンデプロイ・リロード等) か

使い方:
  python analyze-ij-log.py server.log [--pkg com.example] [--tz +09:00] [--date 2026-09-08]
    --pkg  : アプリのパッケージ接頭辞 (A の「作った場所」を探すのに使う。省略時はフレームワーク以外の最初の行)
    --tz   : ログ時刻のタイムゾーン (lastReturned 等のエポックミリ秒は UTC。既定 +00:00)
    --date : ログ行に日付が無い (HH:mm:ss,SSS だけの) 場合の日付。省略時は lastReturned から推定
"""
import argparse
import datetime as dt
import re
import statistics
import sys
from collections import Counter

TS_PATTERNS = [
    (re.compile(r'^(\d{4}-\d{2}-\d{2})[ T](\d{2}:\d{2}:\d{2})[,.](\d{3})'), 'datetime'),
    (re.compile(r'^(\d{2}:\d{2}:\d{2}),(\d{3})'), 'time'),
]
FRAMEWORK_PREFIXES = ('java.', 'javax.', 'jakarta.', 'jdk.', 'sun.', 'com.sun.', 'org.jboss.', 'org.wildfly.',
                      'io.undertow.', 'com.mysql.', 'org.springframework.', 'org.apache.', 'org.hibernate.',
                      'org.mybatis.', 'org.eclipse.')
SHUTDOWN_MARKERS = ('WFLYSRV0220', 'WFLYSRV0272', 'WFLYSRV0211', 'WFLYSRV0236', 'WFLYSRV0050')


def parse_ts(line, tz, default_date):
    for pat, kind in TS_PATTERNS:
        m = pat.match(line)
        if not m:
            continue
        if kind == 'datetime':
            t = dt.datetime.strptime(f"{m.group(1)} {m.group(2)}.{m.group(3)}", "%Y-%m-%d %H:%M:%S.%f")
        else:
            if default_date is None:
                return ('time', m.group(1), m.group(2))
            t = dt.datetime.strptime(f"{default_date} {m.group(1)}.{m.group(2)}", "%Y-%m-%d %H:%M:%S.%f")
        return t.replace(tzinfo=tz)
    return None


def resolve_time_only(raw, ref_utc, tz):
    """日付の無い時刻を、基準 (lastReturned) の日付で補う。基準より前なら翌日とみなす。"""
    _, hms, ms = raw
    ref_local = ref_utc.astimezone(tz)
    t = dt.datetime.strptime(f"{ref_local:%Y-%m-%d} {hms}.{ms}", "%Y-%m-%d %H:%M:%S.%f").replace(tzinfo=tz)
    if t < ref_local - dt.timedelta(minutes=1):
        t += dt.timedelta(days=1)
    return t


def epoch_ms(value):
    return dt.datetime.fromtimestamp(int(value) / 1000, tz=dt.timezone.utc)


def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')  # Windows のコンソールでも UTF-8 で出す
    ap = argparse.ArgumentParser()
    ap.add_argument('log')
    ap.add_argument('--pkg', default=None)
    ap.add_argument('--tz', default='+00:00')
    ap.add_argument('--date', default=None)
    a = ap.parse_args()
    sign = 1 if a.tz[0] != '-' else -1
    hh, mm = a.tz.lstrip('+-').split(':')
    tz = dt.timezone(sign * dt.timedelta(hours=int(hh), minutes=int(mm)))

    with open(a.log, encoding='utf-8', errors='replace') as f:
        lines = [l.rstrip('\n') for l in f]

    def stack_after(i):
        out = []
        for l in lines[i + 1:i + 200]:
            s = l.strip()
            if s.startswith('at ') or s.startswith('Caused by:') or s.startswith('...') or s.startswith('Suppressed:'):
                out.append(s)
            elif out:
                break
        return out

    # ---------- (A) ----------
    leak = Counter()
    for i, l in enumerate(lines):
        kind = 'IJ030040 Statement' if 'IJ030040' in l else ('IJ030042 ResultSet' if 'IJ030042' in l else None)
        if not kind:
            continue
        site = '(アプリのフレームが見つからない)'
        for s in stack_after(i):
            if not s.startswith('at '):
                continue
            frame = s[3:]
            if '//' in frame:  # JBoss Modules 形式: 'deployment.iwinmichl.war//com.example.Foo.bar(...)'
                frame = frame.split('//', 1)[1]
            if (a.pkg and frame.startswith(a.pkg)) or (not a.pkg and not frame.startswith(FRAMEWORK_PREFIXES)):
                site = frame
                break
        leak[(kind, site)] += 1
    print('=' * 70)
    print(' (A) ⑧ IJ030040 / ⑫ IJ030042 閉じ忘れの「作った場所」ランキング')
    print('=' * 70)
    if not leak:
        print('  (該当なし)')
    for (kind, site), n in leak.most_common(30):
        print(f'  {n:5d}  {kind:20s} {site}')

    # ---------- (B) ----------
    print('\n' + '=' * 70)
    print(' (B) ⑪ IJ000621 死んでいた接続の放置時間 (ログ時刻 - lastReturned)')
    print('=' * 70)
    idles = []
    pat = re.compile(r'lastReturned=(\d+) lastValidated=(\d+) lastCheckedOut=(\d+)')
    for l in lines:
        if 'IJ000621' not in l:
            continue
        m = pat.search(l)
        if not m:
            continue
        ret, val, out = (epoch_ms(x) for x in m.groups())
        ts = parse_ts(l, tz, a.date)
        if isinstance(ts, tuple):
            ts = resolve_time_only(ts, ret, tz)
        if ts is None:
            print(f'  (ログ時刻が読めない行) lastReturned={ret:%Y-%m-%dT%H:%M:%SZ}')
            continue
        idle = (ts - ret).total_seconds()
        idles.append(idle)
        print(f'  log={ts:%Y-%m-%d %H:%M:%S%z} lastReturned={ret:%Y-%m-%dT%H:%M:%SZ} '
              f'idle={idle:7.0f}s lastValidated={val:%H:%M:%SZ} (作成 or 最後の背景検証)')
    if idles:
        lo = min(idles)
        print(f'  件数={len(idles)}  最小={lo:.0f}s  中央値={statistics.median(idles):.0f}s  最大={max(idles):.0f}s')
        rec = max(1, int(lo / 1.5 // 60))
        print(f'  -> 最も短い放置 {lo:.0f}s で既に死んでいた。idle-timeout-minutes は {rec} 以下を推奨')
        print('     (IdleRemover は idle-timeout の半分間隔で動くため、接続は最長で約 1.5 倍まで残る)')
        print('     あわせて MySQL の wait_timeout、経路のアイドル切断 (NAT Gateway/NLB 350 秒 等) を確認すること')
    else:
        print('  (該当なし)')

    # ---------- (C) ----------
    print('\n' + '=' * 70)
    print(' (C) ⑩ IJ030027 の根本原因 (直後の Caused by から分類)')
    print('=' * 70)
    causes = Counter()
    for i, l in enumerate(lines):
        if 'IJ030027' not in l:
            continue
        text = ' '.join(stack_after(i)) + ' ' + l
        if '4031' in text or 'because of inactivity' in text:
            c = 'DB 側の wait_timeout / interactive_timeout による切断 (MySQL 8.0.24+ はエラー 4031 を返す)'
        elif 'Connection reset' in text:
            c = 'TCP RST (経路のアイドル切断 / DB 再起動・フェイルオーバー 等)'
        elif 'Read timed out' in text or 'SocketTimeoutException' in text:
            c = '読み取りタイムアウト (半開き TCP。socketTimeout で打ち切られた)'
        elif 'No operations allowed after connection closed' in text:
            c = 'ドライバ側で既に閉じられていた接続'
        elif 'Communications link failure' in text:
            c = '通信断 (Communications link failure。詳細は Caused by の下位を確認)'
        else:
            c = 'その他 (スタックトレースを個別に確認)'
        causes[c] += 1
    print(f'  IJ030027 件数={sum(causes.values())}')
    for c, n in causes.most_common():
        print(f'  {n:5d}  {c}')

    # ---------- (D) ----------
    print('\n' + '=' * 70)
    print(' (D) ⑬ IJ000615 (使用中の接続をプール停止で破棄) の発生状況')
    print('=' * 70)
    during, other = 0, 0
    for i, l in enumerate(lines):
        if 'IJ000615' not in l:
            continue
        window = lines[max(0, i - 400):i]
        if any(mk in w for w in window for mk in SHUTDOWN_MARKERS):
            during += 1
        else:
            other += 1
    print(f'  停止処理中={during}  それ以外 (アンデプロイ / リロード / データソース停止 等)={other}')
    if during:
        print('  停止処理中 -> org.wildfly.sigterm.suspend.timeout / ECS stopTimeout / ALB 登録解除遅延 / '
              'LAUNCH_JBOSS_IN_BACKGROUND を確認')
    if other:
        print('  それ以外   -> 直前の管理操作 (deploy/undeploy/:reload/データソース無効化) を確認。'
              '接続リーク疑いなら CCM debug (IJ000100)')


if __name__ == '__main__':
    sys.exit(main())
