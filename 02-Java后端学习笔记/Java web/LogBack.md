#### 记录日志的步骤
- 引入logback依赖、配置文件logback.xml
- 定义日志对象Logger，调用方法（debug/info/...）记录日志
```java
// 固定的
private static final Logger log = LoggerFactory.getLogger(LogTest.class); 
```
在类上 @Slf4j注解，就不用上面的代码了，程序在编译的时候会自动生成一个日志记录器 log

#### logback.xml文件解析

```xml
<?xml version="1.0" encoding="UTF-8"?>  
  
<configuration>  
  
    <!-- 控制台输出 -->  
    <appender name="STDOUT" class="ch.qos.logback.core.ConsoleAppender">  
        <encoder class="ch.qos.logback.classic.encoder.PatternLayoutEncoder">  
  
            <!--格式化输出：%d 表示日期，%thread 表示线程名，%-5level表示级别从左显示5个字符宽度，%logger显示日志记录器的名称，%msg表示日志消息，%n表示换行符-->  
            <pattern>%d{yyyy-MM-dd HH:mm:ss.SSS} [%thread] %-5level %logger{50}-%msg%n</pattern>  
  
        </encoder>  
    </appender>  
  
  
    <!-- 系统文件输出 -->  
    <appender name="FILE" class="ch.qos.logback.core.rolling.RollingFileAppender">  
  
        <rollingPolicy class="ch.qos.logback.core.rolling.SizeAndTimeBasedRollingPolicy">  
  
            <!-- 日志文件输出的文件名，%i表示序号 -->  
            <FileNamePattern>D:/tlias-%d{yyyy-MM-dd}-%i.log</FileNamePattern>  
  
            <!-- 最多保留的历史日志文件数量 -->  
            <MaxHistory>30</MaxHistory>  
  
            <!-- 最大文件大小，超过这个大小会触发滚动到新文件，默认为10MB -->  
            <maxFileSize>10MB</maxFileSize>  
  
        </rollingPolicy>  
  
        <encoder class="ch.qos.logback.classic.encoder.PatternLayoutEncoder">  
  
            <!--格式化输出：%d 表示日期，%thread 表示线程名，%-5level表示级别从左显示5个字符宽度，%msg表示日志消息，%n表示换行符-->  
            <pattern>%d{yyyy-MM-dd HH:mm:ss.SSS} [%thread] %-5level %logger{50}-%msg%n</pattern>  
  
        </encoder>  
  
    </appender>  
  
  
    <!-- 日志输出级别 -->  
    <root level="ALL">  
  
        <!-- 输出到控制台 -->  
        <appender-ref ref="STDOUT" />  
  
        <!-- 输出到文件 -->  
        <appender-ref ref="FILE" />  
  
    </root>  
  
  
</configuration>
```

##### configuration 根标签
Logback 的整个配置文件入口
##### appender（日志输出目的地）
定义日志输出到哪里
上面的xml文件中有两个
- STDOUT
- FILE
##### 控制台输出 STDOUT

- pattern
##### 文件输出 FILE


##### 日志级别（级别由低到高）
- trace 追踪
- debug 调试
- info 一般信息
- warn 警告
- error 错误信息

- ALL 开启所有日志
- OFF 关闭所有日志
配置文件中，灵活的控制输出哪些类型的日志（大于等于配置的日志级别的日志才会输出）
```xml
<!-- 日志输出级别 -->  
<root level="info">  

    <!-- 输出到控制台 -->  
    <appender-ref ref="STDOUT" />  
  
    <!-- 输出到文件 -->  
    <appender-ref ref="FILE" />  
  
</root>
```