package com.example.iwinmichl.test;

import java.io.IOException;
import java.io.InputStream;
import java.io.PrintWriter;
import java.net.URI;
import java.net.URL;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.security.cert.Certificate;
import java.security.cert.X509Certificate;
import java.time.Duration;
import java.util.concurrent.Callable;

import javax.net.ssl.HttpsURLConnection;
import javax.net.ssl.SSLContext;
import javax.net.ssl.SSLSocketFactory;

import jakarta.servlet.annotation.WebServlet;
import jakarta.servlet.http.HttpServlet;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;

/**
 * ① の検証用: アウトバウンド HTTPS が「どの信頼設定」を使うかを、クライアントの種類ごとに確かめる。
 *
 *   A … HttpsURLConnection (既定の SSLSocketFactory = SSLContext.getDefault() 由来)
 *   B … java.net.http.HttpClient (既定 = SSLContext.getDefault())
 *   C … SSLContext.getInstance("TLS").init(null, null, null)
 *       = 自前で SSLContext を作るライブラリの典型 (JSSE 既定の TrustManagerFactory
 *         → javax.net.ssl.trustStore があればそれ、無ければ JDK の cacerts)
 *
 * 使い方: /tls?url=https://extraslb-test/
 */
@WebServlet("/tls")
public class TlsProbeServlet extends HttpServlet {

    private static final long serialVersionUID = 1L;

    @Override
    protected void doGet(HttpServletRequest req, HttpServletResponse resp) throws IOException {
        resp.setContentType("text/plain;charset=UTF-8");
        PrintWriter out = resp.getWriter();
        String url = req.getParameter("url");
        try {
            SSLContext def = SSLContext.getDefault();
            out.println("SSLContext.getDefault() = " + def.getClass().getName() + " (provider=" + def.getProvider().getName() + ")");
        } catch (Exception e) {
            out.println("SSLContext.getDefault() = ERROR " + e);
        }
        out.println("javax.net.ssl.trustStore = " + System.getProperty("javax.net.ssl.trustStore"));
        out.println(probe("A HttpsURLConnection(default)        ", () -> viaUrlConnection(url, null)));
        out.println(probe("B java.net.http.HttpClient(default)  ", () -> viaHttpClient(url)));
        out.println(probe("C new SSLContext(TLS).init(null,...) ", () -> {
            SSLContext ctx = SSLContext.getInstance("TLS");
            ctx.init(null, null, null);
            return viaUrlConnection(url, ctx.getSocketFactory());
        }));
    }

    private static String probe(String label, Callable<String> c) {
        try {
            return label + " -> OK  " + c.call();
        } catch (Exception e) {
            Throwable t = e;
            while (t.getCause() != null && t.getCause() != t) {
                t = t.getCause();
            }
            return label + " -> NG  " + t.getClass().getSimpleName() + ": " + String.valueOf(t.getMessage()).replaceAll("\\s+", " ");
        }
    }

    private static String viaUrlConnection(String url, SSLSocketFactory factory) throws Exception {
        HttpsURLConnection con = (HttpsURLConnection) new URL(url).openConnection();
        if (factory != null) {
            con.setSSLSocketFactory(factory);
        }
        con.setConnectTimeout(5000);
        con.setReadTimeout(5000);
        int code = con.getResponseCode();
        // 本文を読み切ると接続がキープアライブに戻され getServerCertificates() が使えなくなるので先に取る
        Certificate[] chain = con.getServerCertificates();
        String issuer = chain.length > 0 && chain[0] instanceof X509Certificate x
                ? x.getIssuerX500Principal().getName() : "?";
        try (InputStream in = code < 400 ? con.getInputStream() : con.getErrorStream()) {
            if (in != null) {
                in.readAllBytes();
            }
        }
        con.disconnect();
        return "HTTP " + code + " issuer=" + issuer;
    }

    private static String viaHttpClient(String url) throws Exception {
        HttpClient client = HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(5)).build();
        HttpResponse<String> r = client.send(
                HttpRequest.newBuilder(URI.create(url)).timeout(Duration.ofSeconds(5)).GET().build(),
                HttpResponse.BodyHandlers.ofString());
        return "HTTP " + r.statusCode();
    }
}
