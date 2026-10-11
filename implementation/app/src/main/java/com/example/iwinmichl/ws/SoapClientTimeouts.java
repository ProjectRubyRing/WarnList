package com.example.iwinmichl.ws;

import java.util.Map;

import jakarta.xml.ws.BindingProvider;

/**
 * ③ WFLYSRV0018 対処: SOAP クライアントのタイムアウトを「標準 API」だけで設定する。
 *
 * よくある private モジュール (org.apache.cxf.impl) 依存の理由は、次のような CXF 実装クラスの直接利用:
 *   HTTPConduit conduit = (HTTPConduit) ClientProxy.getClient(port).getConduit();
 *   HTTPClientPolicy policy = new HTTPClientPolicy();
 *   policy.setConnectionTimeout(5000); policy.setReceiveTimeout(30000);
 *   conduit.setClient(policy);
 * HTTPConduit / HTTPClientPolicy は cxf-rt-transports-http に入っており、EAP では private な
 * org.apache.cxf.impl モジュールに属する。
 *
 * Apache CXF 4.x (EAP 8.x 同梱) は BindingProvider のリクエストコンテキストに置いた
 *   jakarta.xml.ws.client.connectionTimeout / jakarta.xml.ws.client.receiveTimeout (ミリ秒)
 * を HTTPConduit が読む (org.apache.cxf.message.Message#CONNECTION_TIMEOUT / RECEIVE_TIMEOUT)。
 * これなら jakarta.xml.ws.* (標準 API) だけで書け、jboss-deployment-structure.xml の
 * org.apache.cxf.impl 依存を削除できる。
 */
public final class SoapClientTimeouts {

    public static final String CONNECTION_TIMEOUT = "jakarta.xml.ws.client.connectionTimeout";
    public static final String RECEIVE_TIMEOUT = "jakarta.xml.ws.client.receiveTimeout";

    private SoapClientTimeouts() {
    }

    /**
     * ポート (サービスエンドポイントインタフェースのプロキシ) または Dispatch にタイムアウトを設定する。
     *
     * @param portOrDispatch Service#getPort / Service#createDispatch で得たオブジェクト
     * @param connectMillis  接続確立までの上限 (ミリ秒)
     * @param receiveMillis  応答待ちの上限 (ミリ秒)
     */
    public static void apply(Object portOrDispatch, int connectMillis, int receiveMillis) {
        Map<String, Object> ctx = ((BindingProvider) portOrDispatch).getRequestContext();
        ctx.put(CONNECTION_TIMEOUT, connectMillis);
        ctx.put(RECEIVE_TIMEOUT, receiveMillis);
    }
}
