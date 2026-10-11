#!/bin/bash
#
# check-warnings.sh <server.log | docker logs の保存ファイル | CloudWatch Logs から落としたファイル>
#
# 警告 ①〜⑬ と関連メッセージの件数を数える (対処の前後比較・定期チェック用)。
# メッセージ ID で数えるので、日本語ロケールのログでも英語ロケールのログでも使える。
set -uo pipefail
LOG="${1:?usage: check-warnings.sh <logfile>}"
[[ -r "${LOG}" ]] || { echo "cannot read ${LOG}" >&2; exit 1; }

count() { grep -a -c -E -- "$1" "${LOG}" 2>/dev/null || true; }
row()   { printf '%-6s %-44s %5s\n' "$1" "$2" "$(count "$3")"; }

printf '%-6s %-44s %5s\n' "No" "Message" "Count"
printf '%-6s %-44s %5s\n' "------" "--------------------------------------------" "-----"
row "①"   "WFLYELY00023 keystore file does not exist"        'WFLYELY00023'
row "  ①+" "WFLYELY01084 self-signed will be generated"       'WFLYELY01084'
row "  ①+" "WFLYELY00022 does not exist and required"         'WFLYELY00022'
row "  ①+" "WFLYELY00024 certificate in keystore not valid"   'WFLYELY00024'
row "②"   "WFLYSRV0058 resource root does not exist"         'WFLYSRV0058'
row "③"   "WFLYSRV0018 private module used"                  'WFLYSRV0018'
row "  ③+" "  of which org.apache.cxf.impl"                  'WFLYSRV0018.*org\.apache\.cxf\.impl'
row "  ③+" "  of which org.jboss.vfs (spring-core)"          'WFLYSRV0018.*org\.jboss\.vfs'
row "④"   "WFLYEE0007 optional component not installed"     'WFLYEE0007'
row "  ④+" "  of which org.springframework.*"                 'WFLYEE0007.*org\.springframework\.'
row "  ④+" "  of which javax.servlet.jsp.jstl.* (=⑦)"         'WFLYEE0007.*javax\.servlet\.jsp\.jstl'
row "⑤"   "WFLYWELD0013 CDI annotations, no bean archive"   'WFLYWELD0013'
row "⑥"   "WFLYSRV0274 excluded dependency does not exist"  'WFLYSRV0274'
row "  ⑥+" "WFLYSRV0273 excluded subsystem does not exist"   'WFLYSRV0273'
row "⑦"   "Failed to define class javax.*"                  'Failed to define class javax\.'
row "⑧"   "IJ030040 statement left open"                    'IJ030040'
row "⑨"   "Resolved [...HttpRequestMethodNotSupported...]"  'Resolved \[.*HttpRequestMethodNotSupportedException'
row "  ⑨+" "HTTP 405 detail line (MethodNotAllowedAdvice)"   'HTTP 405 method='
row "⑩"   "IJ030027 destroying connection not valid"        'IJ030027'
row "⑪"   "IJ000621 destroying conn. not validated"         'IJ000621'
row "⑫"   "IJ030042 result set left open"                   'IJ030042'
row "⑬"   "IJ000615 destroying active connection"           'IJ000615'
row "  ⑬+" "IJ000100 CCM closed a leaked connection"         'IJ000100'
row "  ⑬+" "WFLYSRV0211/0272 suspending server"            'WFLYSRV02(11|72)'
row "  ⑬+" "WFLYSRV0220 shutdown requested via OS signal"   'WFLYSRV0220'
row "  ⑬+" "IJ030022 lock owned during cleanup"             'IJ030022'
row "  他" "WFLYTX0013 node-identifier is default"           'WFLYTX0013'
echo
echo "total (①〜⑬ 本体) = $(( $(count 'WFLYELY00023') + $(count 'WFLYSRV0058') + $(count 'WFLYSRV0018') + $(count 'WFLYEE0007') + $(count 'WFLYWELD0013') + $(count 'WFLYSRV0274') + $(count 'Failed to define class javax\.') + $(count 'IJ030040') + $(count 'Resolved \[.*HttpRequestMethodNotSupportedException') + $(count 'IJ030027') + $(count 'IJ000621') + $(count 'IJ030042') + $(count 'IJ000615') ))"
