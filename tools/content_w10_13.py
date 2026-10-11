# -*- coding: utf-8 -*-
"""警告 ⑩〜⑬ の原稿"""
from doclib import B, C, DIA, KID, NOTE, P, S, T

FIELDS_TABLE = T(["フィールド (⑪のログ)", "意味", "この環境の値の読み方"], [
    ["state=NORMAL", "接続リスナの状態 (NORMAL / DESTROY / DESTROYED)", "破棄の直前なので NORMAL"],
    ["connection handles=0", "アプリに渡している接続ハンドルの数", "0 = 誰も使っていない (プールで待機していた)"],
    ["lastReturned=1788828592947", "最後にプールへ戻された時刻 (エポックミリ秒, UTC)", "2026-09-08 09:49:52.947 JST"],
    ["lastValidated=1788827437514", "作成時刻、または最後の背景検証の時刻 (貸出時検証では更新されない)", "2026-09-08 09:30:37.514 JST (約 19 分前 = 背景検証は動いていない可能性が高い)"],
    ["lastCheckedOut=1788828592692", "最後に貸し出された時刻", "09:49:52.692 JST → 255 ms 使って返却"],
    ["trackByTx=false", "トランザクションに接続を固定するか", "false (通常)"],
    ["mcp=SemaphoreConcurrentLinkedDequeManagedConnectionPool", "プールの実装クラス", "EAP 8 の既定"],
    ["xaResource=XAResourceWrapperImpl[... pad=false overrideRmValue=false productName=MySQL productVersion=8.4.7]",
     "XA リソースの情報 (pad-xid、same-rm-override、DB の製品名と版)", "Aurora MySQL 8.4.7 (2026-05 GA の最初のマイナー版と一致)"],
], widths=[3, 3, 3])

# =====================================================================
# ⑩ IJ030027
# =====================================================================
W10 = {
    "key": "W10", "no": "⑩", "sheet": "⑩IJ030027", "id": "IJ030027", "severity": "B",
    "title": "⑩ IJ030027: 有効でない接続を破棄する (Ping failed: java.lang.reflect.InvocationTargetException)",
    "user_log": "org.jboss.jca.adapters.jdbc.xa.XAManagedConnectionFactory default task-7 IJ030027: Destroying connection that is not valid, due to the following exception: com.mysql.cj.jdbc.ConnectionWrapper@752a69a6: java.sql.SQLException: Ping failed: java.lang.reflect.InvocationTargetException",
    "verify_labels": ["IJ030027 destroying connection not valid", "IJ000621 destroying conn. not validated"],
    "sections": [
        S("ひとことで (小学生向け)",
          KID("タクシー会社 (接続プール) は、お客さん (リクエスト) に車 (DB 接続) を貸す前に、エンジンがかかるか確かめます (ping)。\n"
              "長く駐車していた車は、知らないうちにバッテリーが上がっていました (DB 側に回線を切られていた)。\n"
              "点検係は「この車は動かないので廃車にします。理由は…」と日記に書き (⑩)、配車係も「点検に通らなかった車を廃車にしました」と書いて (⑪)、"
              "別の車を出しました。お客さんは何も気づかずに目的地に着きます。"),
          T(["たとえ", "本当の仕組み"], [
              ["車", "DB への物理接続 (XA 接続。Connector/J の ConnectionWrapper)"],
              ["エンジンの点検", "valid-connection-checker = MySQLValidConnectionChecker (接続の ping メソッドをリフレクションで呼ぶ)"],
              ["バッテリー上がり", "DB の wait_timeout や、経路 (NAT / NLB 等) のアイドル切断で TCP がもう切れている"],
              ["点検係の日記", "⑩ IJ030027 (理由 = 例外の連鎖付き)"],
              ["配車係の日記", "⑪ IJ000621 (貸出時検証で破棄した記録)"],
          ], widths=[1, 3])),
        S("メッセージの正体",
          T(["項目", "内容"], [
              ["英語原文", "IJ030027: Destroying connection that is not valid, due to the following exception: %s"],
              ["ID / レベル", "IJ030027 / WARN (例外の連鎖 = Caused by が続けて出力される)"],
              ["ロガー", "org.jboss.jca.adapters.jdbc.xa.XAManagedConnectionFactory"],
              ["出す場所", "BaseWrapperManagedConnectionFactory#getInvalidConnections (貸出時検証・背景検証のどちらからも呼ばれる)"],
              ["\"Ping failed: ...InvocationTargetException\"", "MySQLValidConnectionChecker が ping をリフレクションで呼び、包まれた例外を SQLException(\"Ping failed: \" + e, e) にしたもの"],
              ["本当の理由の見方", "直後の Caused by を読む (検証: CommunicationsException: The client was disconnected by the server because of inactivity. See wait_timeout ...)"],
          ], widths=[1, 4])),
        S("動作原理",
          B("データソースは validate-on-match=true (貸出時検証) と MySQLValidConnectionChecker で構成されている (⑪ がリクエスト処理スレッドで出ていること、"
            "Ping failed の文言から推定)。",
            "貸出時、プールは待機中の接続を 1 本取り出し、getInvalidConnections → isValidConnection → MySQLValidConnectionChecker#isValidConnection を呼ぶ。",
            "チェッカは接続クラスの ping メソッドを探し (Connector/J の ConnectionWrapper にある)、Method#invoke で呼ぶ。"
            "TCP がもう切れていると ping の中で CommunicationsException が起き、InvocationTargetException に包まれて返る。"
            "チェッカはそれを SQLException(\"Ping failed: \" + e.toString(), e) にして返す。",
            "ファクトリは IJ030027 を例外の連鎖付きで出し、その接続を「無効」と答える → プールが IJ000621 を出して破棄 → 次の接続を試す / 新しく作る。",
            "アプリには正常な接続が渡るので、この 2 行は「プールが自分で直した」記録。検証でも放置後の要求は HTTP 200 だった。")),
        S("動作イメージ",
          DIA("""[待機] 接続はプールで待機 …… その間に
          ├ MySQL/Aurora: wait_timeout を超えた無操作の接続を切断 (8.0.24 以降はエラー 4031 を送ってから切る)
          └ 経路: NAT Gateway / NLB などが 350 秒の無通信で状態を捨てる (以後のパケットに RST)
[貸出 (default task-N)]
 プール: 待機中の接続を取り出す → validate-on-match → MySQLValidConnectionChecker
   → ConnectionWrapper.ping() (リフレクション) → 例外 → InvocationTargetException
   → SQLException("Ping failed: ...") → IJ030027 (WARN, Caused by 付き) ★⑩
 プール: その接続を破棄 → IJ000621 (WARN) ★⑪ → 別の接続 / 新規接続を渡す
 アプリ: 正常な接続で処理を続ける (エラーにならない)""")),
        S("歴史・背景・必要になった経緯",
          B("JDBC 2.0 (1999) で接続プールが標準化され、使い回す接続が「いつの間にか死んでいる」問題が生まれた。",
            "JBoss の JCA 実装 (JBossJCA → 2011 年以降 IronJacamar) は、DB ごとの検証クラス (valid-connection-checker) と、"
            "致命的エラーを判定する exception-sorter を用意し、貸出時 (validate-on-match) または定期 (background-validation) の検証を選べるようにした。",
            "2021 MySQL 8.0.24: wait_timeout で切断するとき、理由 (ER_CLIENT_INTERACTION_TIMEOUT = 4031) をクライアントに送るようになった (WL#12999)。"
            "以前は「Communications link failure」としか分からなかった。",
            "クラウドでは、NAT Gateway や NLB の 350 秒のアイドル切断が新たな原因として加わった (NLB は 2024-09 から変更可能)。")),
        S("この環境での原因と切り分け",
          P("「プールで待機している間に、接続が外から切られていた」ことは確実です。誰が切ったかは、IJ030027 の Caused by と、"
            "⑪ の「ログ時刻 - lastReturned (放置時間)」で判別します。"),
          T(["Caused by の文言", "切った者", "放置時間の目安"], [
              ["The client was disconnected by the server because of inactivity (4031)", "DB の wait_timeout / interactive_timeout", "≧ wait_timeout (Aurora の既定は 28800 秒)"],
              ["Connection reset / Communications link failure", "経路のアイドル切断 (NAT Gateway・NLB 350 秒等)、DB の再起動・フェイルオーバー", "≧ 350 秒なら経路を疑う"],
              ["Read timed out", "半開き TCP (相手が消えた)。socketTimeout で打ち切った", "-"],
          ], widths=[3, 3, 2]),
          C("""python analyze-ij-log.py server.log --tz +09:00
 (B) ⑪ IJ000621 死んでいた接続の放置時間 (ログ時刻 - lastReturned)
  log=2026-10-11 05:33:53+0000 lastReturned=2026-10-11T05:31:03Z idle=    170s
  -> 最も短い放置 170s で既に死んでいた。idle-timeout-minutes は 1 以下を推奨
 (C) ⑩ IJ030027 の根本原因 (直後の Caused by から分類)
      1  DB 側の wait_timeout / interactive_timeout による切断 (MySQL 8.0.24+ はエラー 4031 を返す)""",
            "text", "検証ログ (MySQL wait_timeout=150 秒、170 秒放置) での実行結果"),
          NOTE("ユーザー環境の ⑪ は lastValidated が lastReturned の約 19 分前でした。lastValidated は「作成時刻か、最後の背景検証の時刻」で、"
               "貸出時検証では更新されません。背景検証 (background-validation) は動いていないと読めます (Red Hat の推奨どおり、貸出時検証のみの構成)。")),
        S("影響度と放置した場合のリスク",
          P("危険度 B。アプリへのエラーにはなっていませんが、(1) 貸出のたびに死んだ接続を引くと検証と再接続のぶん遅くなる、"
            "(2) 半開き TCP では ping が socketTimeout まで固まる、(3) exception-sorter が無いと、使用中に死んだ接続がプールに戻されて別の要求が失敗する、"
            "といった形で悪化しえます。頻発するなら設定と経路の不一致です。")),
        S("対処方針の比較",
          T(["対処", "内容", "効く原因"], [
              ["idle-timeout-minutes を短く ★", "切られる前にプール側で捨てる。IdleRemover は idle-timeout の半分間隔なので最長 1.5 倍残る点を考慮", "wait_timeout / 経路のアイドル切断"],
              ["exception-sorter を追加 ★", "MySQLExceptionSorter。使用中に致命的エラーが出た接続をプールに戻さない", "フェイルオーバー・再起動"],
              ["貸出時検証は維持 ★", "validate-on-match=true + MySQLValidConnectionChecker。背景検証とは併用しない (Red Hat 推奨)", "すべて (最後の砦)"],
              ["TCP keepalive", "Connector/J の tcpKeepAlive=true (既定) + ECS の systemControls で net.ipv4.tcp_keepalive_time=60 等", "経路のアイドル切断 (wait_timeout には効かない)"],
              ["socketTimeout", "半開き TCP で ping が固まらないよう上限を付ける (最長クエリより長く)", "半開き"],
              ["DB / 経路側の設定", "wait_timeout、NLB の tcp.idle_timeout.seconds、経路から NAT を外す 等", "原因に応じて"],
          ], widths=[2, 5, 2])),
        S("実装 (jboss-cli + ECS)",
          C("""# 30-datasource-mysql-xa.cli (抜粋)
/subsystem=datasources/xa-data-source=MIF02JA_JDS:add( ... \\
    idle-timeout-minutes="${env.DB_IDLE_TIMEOUT_MIN:5}", \\
    validate-on-match=true, background-validation=false, \\
    valid-connection-checker-class-name=org.jboss.jca.adapters.jdbc.extensions.mysql.MySQLValidConnectionChecker, \\
    exception-sorter-class-name=org.jboss.jca.adapters.jdbc.extensions.mysql.MySQLExceptionSorter, ...)
/subsystem=datasources/xa-data-source=MIF02JA_JDS/xa-datasource-properties=TcpKeepAlive:add(value=true)
/subsystem=datasources/xa-data-source=MIF02JA_JDS/xa-datasource-properties=SocketTimeout:add(value="${env.DB_SOCKET_TIMEOUT_MS:120000}")""",
            "text"),
          C("""// ECS タスク定義 (抜粋): awsvpc / Fargate ではタスク内の全コンテナに効くので 1 コンテナにだけ書く
"systemControls": [
  { "namespace": "net.ipv4.tcp_keepalive_time",   "value": "60" },
  { "namespace": "net.ipv4.tcp_keepalive_intvl",  "value": "10" },
  { "namespace": "net.ipv4.tcp_keepalive_probes", "value": "6" }
]""", "json")),
        S("確認方法",
          C("""# 待機中の接続が切られる時間より長く放置してから要求し、
grep -c -E 'IJ030027|IJ000621' server.log   # → 0
/opt/jboss-eap/bin/jboss-cli.sh -c '/subsystem=datasources/xa-data-source=MIF02JA_JDS/statistics=pool:read-resource(include-runtime=true)'
# DestroyedCount / InvalidCount などの増え方を見る (statistics-enabled=true)""", "bash")),
    ],
    "refs": ["src-ij-adapters", "src-ij-mysqlvcc", "kb-ds", "mysql-4031", "aws-natgw", "aws-nlb", "aws-fargate-sysctl", "aws-cfn-sysctl", "aws-aurora84"],
}

# =====================================================================
# ⑪ IJ000621
# =====================================================================
W11 = {
    "key": "W11", "no": "⑪", "sheet": "⑪IJ000621", "id": "IJ000621", "severity": "B",
    "title": "⑪ IJ000621: 検証できなかった接続を破棄する (プール側の記録)",
    "user_log": "org.jboss.jca.core.connectionmanager.pool.strategy.OnePool default-task-7 IJ000621: Destroying connection that could not be validated: org.jboss.jca.core.connectionmanager.listener.TxConnectionListener@384d5be6[state=NORMAL managed connection=org.jboss.jca.adapters.jdbc.xa.XAManagedConnection@c24620c connection handles=0 lastReturned=1788828592947 lastValidated=1788827437514 lastCheckedOut=1788828592692 trackByTx=false pool=...OnePool@4a8f027f mcp=SemaphoreConcurrentLinkedDequeManagedConnectionPool@4a9fc932[pool=MIF02JA_JDS] xaResource=XAResourceWrapperImpl@5ece3ccd[... productName=MySQL productVersion=8.4.7 jndiName=java:/jdbc/MIF02JA_JDS] txSync=null]",
    "verify_labels": ["IJ000621 destroying conn. not validated", "IJ030027 destroying connection not valid"],
    "sections": [
        S("ひとことで (小学生向け)",
          KID("⑩ で「この車は動かない」と分かった車を、配車係 (プール) が実際に廃車にしたときの日記です。\n"
              "日記には車の記録 (いつ最後に返ってきたか、いつ点検したか、いつ貸したか) も書いてあるので、"
              "「どれくらい駐車していたら動かなくなったか」を計算できます。"),
          T(["たとえ", "本当の仕組み"], [
              ["配車係", "OnePool (プール戦略) / SemaphoreConcurrentLinkedDequeManagedConnectionPool"],
              ["車の記録", "TxConnectionListener の lastReturned / lastValidated / lastCheckedOut など"],
              ["駐車していた時間", "ログの時刻 - lastReturned"],
          ], widths=[1, 3])),
        S("メッセージの正体",
          T(["項目", "内容"], [
              ["英語原文", "IJ000621: Destroying connection that could not be validated: %s"],
              ["ID / レベル", "IJ000621 / WARN"],
              ["ロガー", "org.jboss.jca.core.connectionmanager.pool.strategy.OnePool"],
              ["出す場所", "SemaphoreConcurrentLinkedDequeManagedConnectionPool#getConnection の validate-on-match 分岐だけ"],
              ["スレッドから分かること", "default task-7 = HTTP 要求の処理スレッド → 貸出時検証で見つけた (背景検証は別スレッドで、IJ000621 は出さない)"],
          ], widths=[1, 4]),
          FIELDS_TABLE),
        S("動作原理",
          B("getConnection で待機中の接続を取り出し、matchManagedConnections のあと validate-on-match が true なら getInvalidConnections で検証する (⑩)。",
            "無効と判定されたら IJ000621 を出し、プールから外して destroy する。続けて次の待機接続を試すか、新しい接続を作る。",
            "背景検証 (background-validation) で無効を見つけた場合は IJ030027 だけで、IJ000621 は出ない (ソースで確認)。",
            "lastValidated は作成時と背景検証のときにだけ更新され、貸出時検証では更新されない。")),
        S("動作イメージ",
          DIA("""[時刻の読み方 (ユーザー環境の値)]
 09:30:37.514  lastValidated  … 接続の作成 (または最後の背景検証)
 09:49:52.692  lastCheckedOut … 貸出
 09:49:52.947  lastReturned   … 返却 (255 ms 使用)
      ↓  ここから待機 (時間 = IJ000621 のログ時刻 - 09:49:52.947)
 ??:??:??      IJ000621       … 次の貸出時の検証で失敗 → 破棄""")),
        S("歴史・背景・必要になった経緯",
          P("⑩ と同じです。IronJacamar は「点検 (ファクトリ側の IJ030027)」と「廃車 (プール側の IJ000621)」を別々に記録するため、2 行がペアで出ます。")),
        S("この環境での原因と切り分け",
          P("⑩ と同じ原因です。⑪ のログ時刻と lastReturned の差 (放置時間) を、DB の wait_timeout や経路のアイドル切断 (350 秒等) と比べます。"
            "ユーザー環境のログには行の時刻が含まれていないため、CloudWatch Logs で同じ行の時刻を確認してください。"),
          C("python analyze-ij-log.py server.log --tz +09:00   # (B) に放置時間と idle-timeout の推奨値が出る", "bash")),
        S("影響度と放置した場合のリスク",
          P("危険度 B。⑩ と同じ。件数と時間帯 (夜間・休日明けの最初の要求に集中するか等) を CloudWatch Logs のメトリクスフィルタで監視すると、"
            "設定の妥当性を継続的に確かめられます。")),
        S("対処方針の比較",
          P("⑩ と同じ (idle-timeout-minutes の短縮、exception-sorter、貸出時検証の維持、TCP keepalive)。"
            "放置時間の実測値から idle-timeout-minutes を決めます: idle-timeout × 1.5 < 最短の放置時間 (切られる時間)。")),
        S("実装",
          C("""# ECS タスク定義の環境変数で調整 (30-datasource-mysql-xa.cli が参照)
{ "name": "DB_IDLE_TIMEOUT_MIN", "value": "5" }""", "json")),
        S("確認方法",
          C("""grep -c IJ000621 server.log   # → 0
# CloudWatch Logs Insights
fields @timestamp, @message | filter @message like /IJ000621/ | stats count() by bin(1h)""", "text")),
    ],
    "refs": ["src-ij-pool", "kb-ds", "aws-aurora84"],
}

# =====================================================================
# ⑫ IJ030042
# =====================================================================
W12 = {
    "key": "W12", "no": "⑫", "sheet": "⑫IJ030042", "id": "IJ030042", "severity": "B",
    "title": "⑫ IJ030042: 開いたままの ResultSet を閉じた (自分で後片付けしてください)",
    "user_log": "org.jboss.jca.adapters.jdbc.WrappedConnection default-task-7 IJ030042: Closing a result set you left open please do your own housekeeping for: com.mysql.cj.jdbc.result.ResultSetImpl@46f61974:java.lang.Throwable: STACKTRACE",
    "verify_labels": ["IJ030042 result set left open", "IJ030040 statement left open"],
    "sections": [
        S("ひとことで (小学生向け)",
          KID("⑧ の続きです。メモ用紙 (Statement) だけでなく、そこに書いた答えのプリント (ResultSet) も出しっぱなしでした。\n"
              "司書がメモ用紙を片付けるときに、一緒にプリントも片付けて「これも自分で片付けてね」と書きました。"),
          T(["たとえ", "本当の仕組み"], [
              ["答えのプリント", "ResultSet (SELECT の結果)"],
              ["メモ用紙と一緒に片付ける", "Statement を閉じるとき、その Statement の ResultSet も閉じる (WrappedStatement)"],
          ], widths=[1, 3])),
        S("メッセージの正体",
          T(["項目", "内容"], [
              ["英語原文", "IJ030042: Closing a result set you left open, please do your own housekeeping for: %s"],
              ["ID / レベル", "IJ030042 / WARN (%s は ResultSet の toString。com.mysql.cj.jdbc.result.ResultSetImpl@...)"],
              ["ロガー", "org.jboss.jca.adapters.jdbc.WrappedConnection (WrappedStatement が接続のロガーで出す)"],
              ["出す場所", "WrappedStatement の closeResultSets (track-statements=TRUE のとき)"],
              ["付いてくるスタック", "ResultSet を作った呼び出し元 (検証: DbServlet.leak(DbServlet.java:71))"],
          ], widths=[1, 4])),
        S("動作原理",
          B("track-statements=TRUE のとき、WrappedStatement は自分が作った ResultSet とその作成箇所を記録する。",
            "Statement が閉じられる (アプリが閉じる / ⑧ のように接続返却時に IronJacamar が閉じる) とき、開いたままの ResultSet があれば "
            "IJ030042 とスタックを出して閉じる。",
            "⑧ と同じリクエストで、Statement も ResultSet も閉じていない場合は、⑧ → ⑫ の順にペアで出る (検証でも同じ)。")),
        S("動作イメージ",
          DIA("""c.close()  (Statement も ResultSet も閉じていない)
  → IronJacamar: Statement を閉じる → IJ030040 (⑧)
       → その Statement の ResultSet を閉じる → IJ030042 (⑫) ★今回""")),
        S("歴史・背景・必要になった経緯",
          P("⑧ と同じ (JBossJCA から IronJacamar に引き継がれた track-statements の機能)。")),
        S("この環境での原因と切り分け",
          P("アプリのコードが ResultSet を閉じていません。⑧ と同じ箇所のことが多いので、analyze-ij-log.py のランキングで両方を一緒に直します。")),
        S("影響度と放置した場合のリスク",
          P("危険度 B。MySQL Connector/J は既定で結果を全件クライアントに読み込むため、大きな結果を閉じずに持ち続けるとメモリを圧迫します。"
            "ストリーミング (fetchSize=Integer.MIN_VALUE) を使っている場合は、閉じるまで同じ接続で次の SQL を実行できません。")),
        S("対処方針の比較",
          P("⑧ と同じ。ResultSet も try-with-resources で閉じる (Statement を閉じれば ResultSet も閉じるが、明示的に閉じる方が分かりやすい)。"
            "Spring JdbcTemplate の queryForStream など Stream を返す API は、呼び出し側で Stream を閉じないと同じ警告になる。")),
        S("実装",
          C("""try (Connection c = ds.getConnection();
     PreparedStatement ps = c.prepareStatement(sql);
     ResultSet rs = ps.executeQuery()) {
    ...
}
// Spring: try (Stream<Emp> s = jdbcTemplate.queryForStream(sql, mapper)) { ... }""", "java")),
        S("確認方法",
          C("grep -c IJ030042 server.log   # → 0 (DB_TRACK_STATEMENTS=TRUE の検証環境で)", "bash")),
    ],
    "refs": ["src-ij-adapters", "src-ij-defaults"],
}

# =====================================================================
# ⑬ IJ000615
# =====================================================================
W13 = {
    "key": "W13", "no": "⑬", "sheet": "⑬IJ000615", "id": "IJ000615", "severity": "A",
    "title": "⑬ IJ000615: 使用中の接続をプールで破棄した (停止時)",
    "user_log": "org.jboss.jca.core.connectionmanager.pool.strategy.OnePool ServerService Thread Pool -- 80) IJ000615: Destroying active connection in pool: MIF02JA_JDS (org.jboss.jca.adapters.jdbc.xa.XAManagedConnection@6c1a1d2)",
    "verify_labels": ["IJ000615 destroying active connection", "WFLYSRV0211/0272 suspending server",
                      "WFLYSRV0220 shutdown requested via OS signal", "IJ030022 lock owned during cleanup"],
    "sections": [
        S("ひとことで (小学生向け)",
          KID("お店を閉める時間 (タスク停止) になりました。本当は「新しいお客さんはお断りして、いま対応中のお客さんの用事が終わるまで待ってから閉店」"
              "したいのに、待ち時間の設定が 0 秒だったので、レジ (DB 接続) を使っている途中のお客さんがいるのに、レジを片付けてしまいました。\n"
              "係は「使用中のレジを片付けました」と日記に書きました。そのお客さんの用事は失敗しています。"),
          T(["たとえ", "本当の仕組み"], [
              ["閉店の合図", "ECS からの SIGTERM (ローリングデプロイ・スケールイン・タスク停止)"],
              ["新しいお客さんを断って待つ", "EAP のサスペンド (新規要求を 503 で断り、処理中の要求の完了を待つ)"],
              ["待ち時間の設定", "システムプロパティ org.wildfly.sigterm.suspend.timeout (秒)。既定 0 = 待たない"],
              ["レジを片付ける", "データソースのサービス停止 → プールの shutdown → 使用中の接続も破棄 (IJ000615)"],
          ], widths=[1, 3])),
        S("メッセージの正体",
          T(["項目", "内容"], [
              ["英語原文", "IJ000615: Destroying active connection in pool: %s (%s)"],
              ["ID / レベル", "IJ000615 / WARN"],
              ["ロガー", "org.jboss.jca.core.connectionmanager.pool.strategy.OnePool"],
              ["出す場所", "SemaphoreConcurrentLinkedDequeManagedConnectionPool#shutdown (貸出中の接続があるときに出す)"],
              ["スレッド ServerService Thread Pool", "サーバのサービスを非同期で起動・停止する実行スレッド (データソースの停止はここで動く)"],
              ["一緒に出るもの (実測)", "WFLYSRV0272: Suspending server → WFLYSRV0220: Server shutdown has been requested via an OS signal → IJ000615 → "
                                     "IJ030022: Lock owned during cleanup: default task-2 (使っていた要求のスレッド)"],
          ], widths=[1, 4])),
        S("動作原理",
          B("プール (ManagedConnectionPool) の shutdown は、データソースのサービスが止まるとき (サーバ停止・リロード、データソースの無効化・削除、"
            "ドライバのアンデプロイ等) に呼ばれる。貸出中の接続があれば IJ000615 を出し、まとめて破棄する。",
            "SIGTERM を受けた JVM はシャットダウンフックを走らせ、サーバが RUNNING なら先にサスペンドする。"
            "待ち時間は org.wildfly.sigterm.suspend.timeout (秒)。未設定 (既定) は 0 で、ほぼ待たずにサービス停止へ進む (BootstrapImpl で確認)。"
            "EAP 8.1 の構成ガイドにも「OS シグナルで正常にシャットダウンするには org.wildfly.sigterm.suspend.timeout を設定する」とある。",
            "SIGTERM が JVM に届く前提として、standalone.sh は LAUNCH_JBOSS_IN_BACKGROUND が設定されているときだけ、受けた TERM を JVM に中継する。"
            "未設定で standalone.sh が PID 1 だと JVM に届かず、stopTimeout 後の SIGKILL で強制終了になる (この場合 IJ000615 も出ないが、停止処理自体が一切走らない)。",
            "ユーザー環境で IJ000615 が出ている = SIGTERM は JVM に届いているが、待ち時間が足りない (おそらく 0) と読める。")),
        S("動作イメージ",
          DIA("""[修正前: suspend.timeout=0]
 ECS: SIGTERM → standalone.sh (LAUNCH_JBOSS_IN_BACKGROUND=true) → JVM
 JVM: WFLYSRV0272 Suspending server → すぐ (0 秒 + 0.5 秒) 停止へ → WFLYSRV0220
      データソース停止 → 処理中の要求 (SELECT SLEEP(15)) の接続を破棄 → IJ000615 ★ / IJ030022
      → 要求は失敗 (検証: HTTP 000 = 応答なしで切断)
[修正後: suspend.timeout=30]
 JVM: WFLYSRV0211 Suspending server with 30000 ms timeout → 新規要求は 503、処理中の要求を待つ
      → 要求が完了 (検証: HTTP 200 "slept 15") → 停止 → IJ000615 なし
[LAUNCH_JBOSS_IN_BACKGROUND 未設定]
 ECS: SIGTERM → PID 1 のシェルが受けても JVM に届かない → stopTimeout まで待って SIGKILL (検証: 91 秒、終了コード 137)""")),
        S("歴史・背景・必要になった経緯",
          B("2015 WildFly 9: サスペンド / レジューム とグレースフルシャットダウン (request-controller) が導入された。",
            "その後、OS シグナル (SIGTERM) による停止でもサスペンドの待ち時間を指定できる org.wildfly.sigterm.suspend.timeout が加わった "
            "(EAP 8.1 構成ガイドに記載)。",
            "Docker (2013)、ECS (2015)、Kubernetes の普及で「SIGTERM → 猶予 → SIGKILL」がアプリ停止の標準手順になり、"
            "PID 1 とシグナル中継、猶予時間の設計が重要になった。",
            "ECS の stopTimeout は既定 30 秒、Fargate の上限は 120 秒。ALB の deregistration delay (既定 300 秒) の間に新規要求は止まる。")),
        S("この環境での原因と切り分け",
          P("SIGTERM 時のサスペンド待ち時間が既定の 0 秒のままで、停止の瞬間に処理中だった要求の DB 接続がプールごと破棄されています。"
            "停止以外 (デプロイ・:reload・データソースの無効化) でも同じ警告になるので、直前のログで区別します。"),
          T(["直前に出ているもの", "判断"], [
              ["WFLYSRV0272 / WFLYSRV0211 (Suspending server)、WFLYSRV0220 (OS signal)", "SIGTERM による停止中 → 本対処"],
              ["WFLYSRV0028 (Stopped deployment) だけ / 管理操作のログ", "アンデプロイ・再デプロイ・リロード"],
              ["IJ000100 (CCM が閉じ忘れの接続を閉じた)", "接続リーク (要求が終わっても返されない接続) の疑い"],
          ], widths=[3, 3]),
          C("python analyze-ij-log.py server.log   # (D) に「停止処理中=N / それ以外=M」が出る", "bash")),
        S("影響度と放置した場合のリスク",
          P("危険度 A。デプロイやスケールインのたびに、処理中の要求が途中で失敗します (利用者にはエラー画面、XA トランザクションは中断 → ロールバックや"
            "未確定状態の回復処理)。リリース頻度が上がるほど影響が増えます。")),
        S("対処方針の比較",
          T(["対処", "内容", "評価"], [
              ["サスペンド待ち時間 ★", "jboss-cli で /system-property=org.wildfly.sigterm.suspend.timeout (値は環境変数で上書き可)", "◎ 本体"],
              ["シグナル中継 ★", "entrypoint で LAUNCH_JBOSS_IN_BACKGROUND=true を export し、exec standalone.sh", "◎ 前提条件"],
              ["ECS の時間設計 ★", "最長の要求時間 ≦ suspend.timeout < stopTimeout (Fargate は最大 120 秒)。ALB の deregistration delay も最長の要求以上", "◎"],
              ["initProcessEnabled", "tini がゾンビを回収しシグナルを子に渡す。LAUNCH_JBOSS_IN_BACKGROUND の代わりにはならない", "○ 補助"],
              ["ドライバはモジュールで", "ドライバを deployments に置くと、再デプロイで依存データソースが止まる", "○"],
          ], widths=[2, 5, 1])),
        S("実装",
          C("""# 00-system-properties.cli
if (outcome != success) of /system-property=org.wildfly.sigterm.suspend.timeout:read-resource
    /system-property=org.wildfly.sigterm.suspend.timeout:add(value="${env.EAP_SIGTERM_SUSPEND_TIMEOUT:30}")
end-if""", "text", "jboss-cli"),
          C("""# entrypoint.sh (抜粋)
export LAUNCH_JBOSS_IN_BACKGROUND=true
exec "${JBOSS_HOME}/bin/standalone.sh" "${ARGS[@]}" "$@\"""", "bash", "entrypoint"),
          C("""// ECS タスク定義 (抜粋)
"stopTimeout": 60,
"environment": [ { "name": "EAP_SIGTERM_SUSPEND_TIMEOUT", "value": "45" } ],
"linuxParameters": { "initProcessEnabled": true }
// ALB ターゲットグループ: deregistration_delay.timeout_seconds は最長の要求時間以上 (例 60)""", "json", "ECS")),
        S("確認方法",
          C("""# 長い要求の最中にタスクを止める (ECS: aws ecs stop-task / ローカル: docker stop -t 90)
grep -E 'WFLYSRV0211|IJ000615' server.log
# → "Suspending server with 30000 ms timeout." が出て、IJ000615 が出ないこと。要求は正常応答""", "bash")),
    ],
    "refs": ["eap-cfg", "src-bootstrap", "src-standalone", "src-ij-pool", "aws-stoptimeout"],
}
