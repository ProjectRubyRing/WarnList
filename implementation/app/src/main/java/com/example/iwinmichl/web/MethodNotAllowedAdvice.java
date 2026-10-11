package com.example.iwinmichl.web;

import java.util.Set;

import jakarta.servlet.RequestDispatcher;
import jakarta.servlet.http.HttpServletRequest;

import org.apache.commons.logging.Log;
import org.apache.commons.logging.LogFactory;
import org.springframework.core.Ordered;
import org.springframework.core.annotation.Order;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.HttpRequestMethodNotSupportedException;
import org.springframework.web.bind.annotation.ControllerAdvice;
import org.springframework.web.bind.annotation.ExceptionHandler;

/**
 * ⑨ 対処: 405 (HttpRequestMethodNotSupportedException) を「原因が追える 1 行」で記録する。
 *
 * Spring 既定の DefaultHandlerExceptionResolver は
 *   Resolved [org.springframework.web.HttpRequestMethodNotSupportedException: Request method 'POST' is not supported]
 * としか出さず、URL・送信元・エラーページ経由かどうかが分からない。
 * ここで先に処理すると (@ExceptionHandler が優先)、Spring 既定の WARN 行は出なくなり、代わりに
 *   HTTP 405 method=POST uri=/iwinmichl/api/hello remote=10.0.1.23 xff=203.0.113.5 ...
 * が 1 行だけ出る。応答は従来どおり 405 + Allow ヘッダ。
 *
 * ログ出力は commons-logging (spring-jcl) 経由 = EAP の logging サブシステムに乗る
 * (カテゴリ: com.example.iwinmichl.web.MethodNotAllowedAdvice)。
 */
@ControllerAdvice
@Order(Ordered.HIGHEST_PRECEDENCE)
public class MethodNotAllowedAdvice {

    private static final Log LOG = LogFactory.getLog(MethodNotAllowedAdvice.class);
    private static final int MAX_LEN = 200;

    @ExceptionHandler(HttpRequestMethodNotSupportedException.class)
    public ResponseEntity<String> handleMethodNotAllowed(HttpRequestMethodNotSupportedException ex,
                                                         HttpServletRequest req) {
        Set<HttpMethod> supported = ex.getSupportedHttpMethods();
        HttpHeaders headers = new HttpHeaders();
        if (supported != null && !supported.isEmpty()) {
            headers.setAllow(supported);
        }
        if (LOG.isWarnEnabled()) {
            // エラーページへの内部転送 (ERROR ディスパッチ) で POST のまま届いたケースを見分ける
            Object errorOrigin = req.getAttribute(RequestDispatcher.ERROR_REQUEST_URI);
            LOG.warn(String.format(
                    "HTTP 405 method=%s uri=%s query=%s dispatcher=%s errorOrigin=%s remote=%s xff=%s ua=%s referer=%s allowed=%s",
                    req.getMethod(), clean(req.getRequestURI()), clean(req.getQueryString()),
                    req.getDispatcherType(), clean(errorOrigin == null ? null : errorOrigin.toString()),
                    req.getRemoteAddr(), clean(req.getHeader("X-Forwarded-For")),
                    clean(req.getHeader("User-Agent")), clean(req.getHeader("Referer")), supported));
        }
        return new ResponseEntity<>("Method Not Allowed", headers, HttpStatus.METHOD_NOT_ALLOWED);
    }

    /** ログ注入 (改行の混入) を防ぎ、長すぎる値は切り詰める。 */
    private static String clean(String s) {
        if (s == null) {
            return "-";
        }
        String t = s.replaceAll("[\\r\\n\\t]", "_");
        return t.length() > MAX_LEN ? t.substring(0, MAX_LEN) + "..." : t;
    }
}
