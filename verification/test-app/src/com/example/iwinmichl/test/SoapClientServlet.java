package com.example.iwinmichl.test;

import java.io.IOException;
import java.io.PrintWriter;

import javax.xml.namespace.QName;

import jakarta.servlet.annotation.WebServlet;
import jakarta.servlet.http.HttpServlet;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import jakarta.xml.soap.MessageFactory;
import jakarta.xml.soap.SOAPElement;
import jakarta.xml.soap.SOAPMessage;
import jakarta.xml.ws.Dispatch;
import jakarta.xml.ws.Service;
import jakarta.xml.ws.WebServiceException;
import jakarta.xml.ws.soap.SOAPBinding;

/**
 * ③ の検証用: org.apache.cxf.impl (private モジュール) に依存せず、
 * Jakarta XML Web Services の標準 API だけで SOAP クライアントのタイムアウトを設定できることを確かめる。
 *
 *   接続タイムアウト: jakarta.xml.ws.client.connectionTimeout (ms)
 *   応答タイムアウト: jakarta.xml.ws.client.receiveTimeout    (ms)
 *   (Apache CXF 4.x の org.apache.cxf.message.Message#CONNECTION_TIMEOUT / RECEIVE_TIMEOUT と同じキー)
 *
 * 使い方: /soap?sleepMs=3000&timeoutMs=1000  … 応答が 1 秒で打ち切られることを確認
 */
@WebServlet("/soap")
public class SoapClientServlet extends HttpServlet {

    private static final long serialVersionUID = 1L;
    private static final String NS = "http://wsbackend.example.com/";

    @Override
    protected void doGet(HttpServletRequest req, HttpServletResponse resp) throws IOException {
        resp.setContentType("text/plain;charset=UTF-8");
        PrintWriter out = resp.getWriter();
        int sleepMs = intParam(req, "sleepMs", 3000);
        int timeoutMs = intParam(req, "timeoutMs", 1000);
        String endpoint = req.getParameter("endpoint") != null
                ? req.getParameter("endpoint") : "http://localhost:8080/ws-backend/SlowService";
        long t0 = System.currentTimeMillis();
        try {
            QName serviceName = new QName(NS, "SlowService");
            QName portName = new QName(NS, "SlowServicePort");
            Service service = Service.create(serviceName);
            service.addPort(portName, SOAPBinding.SOAP11HTTP_BINDING, endpoint);
            Dispatch<SOAPMessage> dispatch = service.createDispatch(portName, SOAPMessage.class, Service.Mode.MESSAGE);
            dispatch.getRequestContext().put("jakarta.xml.ws.client.connectionTimeout", 2000);
            dispatch.getRequestContext().put("jakarta.xml.ws.client.receiveTimeout", timeoutMs);

            SOAPMessage request = MessageFactory.newInstance().createMessage();
            SOAPElement op = request.getSOAPBody().addChildElement("sleep", "ns", NS);
            op.addChildElement("arg0").addTextNode(String.valueOf(sleepMs));
            request.saveChanges();

            SOAPMessage response = dispatch.invoke(request);
            out.println("OK in " + (System.currentTimeMillis() - t0) + " ms: "
                    + response.getSOAPBody().getTextContent().trim()
                    + " (client=" + dispatch.getClass().getName() + ")");
        } catch (WebServiceException e) {
            Throwable t = e;
            while (t.getCause() != null && t.getCause() != t) {
                t = t.getCause();
            }
            out.println("TIMEOUT/ERROR after " + (System.currentTimeMillis() - t0) + " ms: "
                    + t.getClass().getName() + ": " + t.getMessage());
        } catch (Exception e) {
            out.println("ERROR: " + e);
        }
    }

    private static int intParam(HttpServletRequest req, String name, int def) {
        String v = req.getParameter(name);
        return v == null ? def : Integer.parseInt(v);
    }
}
