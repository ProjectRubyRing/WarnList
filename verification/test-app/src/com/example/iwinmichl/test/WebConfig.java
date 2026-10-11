package com.example.iwinmichl.test;

import org.springframework.context.annotation.ComponentScan;
import org.springframework.context.annotation.Configuration;
import org.springframework.core.task.SimpleAsyncTaskExecutor;
import org.springframework.web.servlet.config.annotation.AsyncSupportConfigurer;
import org.springframework.web.servlet.config.annotation.EnableWebMvc;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

/**
 * Spring MVC 設定。
 * com.example.iwinmichl.web は「修正後」WAR にだけ入る (⑨ の MethodNotAllowedAdvice)。
 */
@Configuration
@EnableWebMvc
@ComponentScan(basePackages = {"com.example.iwinmichl.test", "com.example.iwinmichl.web"})
public class WebConfig implements WebMvcConfigurer {

    @Override
    public void configureAsyncSupport(AsyncSupportConfigurer configurer) {
        configurer.setDefaultTimeout(30_000);
        configurer.setTaskExecutor(new SimpleAsyncTaskExecutor("MvcAsync"));
    }
}
