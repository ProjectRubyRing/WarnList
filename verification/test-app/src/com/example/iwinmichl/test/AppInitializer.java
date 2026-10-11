package com.example.iwinmichl.test;

import jakarta.servlet.ServletContext;
import jakarta.servlet.ServletRegistration;

import org.springframework.web.WebApplicationInitializer;
import org.springframework.web.context.support.AnnotationConfigWebApplicationContext;
import org.springframework.web.servlet.DispatcherServlet;

/**
 * 検証用 iwinmichl.war の起動クラス (web.xml を使わない Spring MVC 構成)。
 * SpringServletContainerInitializer (spring-web の ServletContainerInitializer) から呼ばれる。
 */
public class AppInitializer implements WebApplicationInitializer {

    @Override
    public void onStartup(ServletContext servletContext) {
        AnnotationConfigWebApplicationContext ctx = new AnnotationConfigWebApplicationContext();
        ctx.register(WebConfig.class);

        ServletRegistration.Dynamic reg = servletContext.addServlet("dispatcher", new DispatcherServlet(ctx));
        reg.setLoadOnStartup(1);
        // ④ の検証: Spring の非同期処理 (Callable) が WFLYEE0007 の影響を受けないことを確かめる
        reg.setAsyncSupported(true);
        reg.addMapping("/api/*");
    }
}
