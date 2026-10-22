AOP：面向切面编程（面向特定方法编程）
优点：
- 减少重复代码
- 维护方便
- 对原始业务方法是零侵入的

>AOP是一种思想，在Spring框架中对这种思想进行的实现，Spring AOP

## 1.AOP基础

1.1导入依赖
```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-aspectj</artifactId>
</dependency>
```

1.2定义一个AOP类（切面类）
- @Component：Spring容器
- @Aspect：标识当前是一个AOP类 
- @Around指定特定的方法

需求：统计所有业务方法的执行耗时
获取方法开始的开始时间和结束时间，计算执行耗时

- 切入点的表达式：指定方法对那些业务生效 
```java
@Around("execution(* com.ccy.service.impl.EmpServiceImpl.getById())")
```

- 执行业务方法
```java
// 执行业务方法，业务方法可能有返回值，统一用Object来封装  
Object result = pjp.proceed();
```
- 完整代码
```java
@Slf4j  
@Aspect  
@Component  
public class RecordTimeAspect {  
    @Around("execution(* com.ccy.service.impl.EmpServiceImpl.getById())")  
    public Object recordTime(ProceedingJoinPoint pjp) throws Throwable {  
        long begin = System.currentTimeMillis();  
  
        // 执行业务方法，业务方法可能有返回值，统一用Object来封装  
        Object result = pjp.proceed();  
  
        long end = System.currentTimeMillis();  
        log.info("{}业务耗时了{}ms",pjp.getSignature(),end - begin);  
        return result;  
    }  
}
```

1.3应用场景
- 记录系统的操作日志
- 事务管理（底层就是用AOP实现的）
- 权限控制

## 2.AOP进阶

2.1 核心概念
- 连接点：JoinPoint，可以被AOP控制的方法
- 通知：Advice，重复的逻辑，也就是共性功能
- 切入点：PointCut，匹配连接点的条件，通知仅会在切入点方法执行时被应用（实际被AOP控制的方法），通过切入点表达式描述切入点，切入点一定是连接点，连接点不一定是切入点
- 切面：Aspect，描述通知与切入点的对应关系（通知+切入点）
- 目标对象：Target，通知所应用的对象

2.2 AOP执行流程

底层：动态代理技术
为目标生成一个代理对象，对代理对象中的方法进行增强（通知方法中的方法）， 最后运行的时候，调用的是代理对象的的方法

2.3 通知类型
- @Around(重要)：环绕通知，通知方法再目标方法前、后都会执行
- @Before：前置通知，只在目标方法之前运行
- @After：后置通知，目标方法后被执行，无论是否有异常都只执行
- @AfterReturning：返回后通知，目标方法执行后被执行，有异常不会执行
- @AfterThrowing：异常后通知，方法发生异常后执行

>@Around环绕通知需要自己调用ProceedingJoinPoint.proceed()来让原始方法执行，其他通知不需要考虑目标方法执行
>@Around环绕通知方法的返回值，必须指定为Object，来接受原始方法的返回值

2.4 注解@PointCut
>讲公共的切入点表达式抽取出来，需要用到时引用切入点表达式即可

```java
@Pointcut("execution(* com.ccy.service.impl.EmpServiceImpl.getById())")  
private void pt() {}  
  
@Around("pt()")  
public Object recordTime(ProceedingJoinPoint pjp) throws Throwable
```
2.5 通知顺序
当有多个切面的切入点都匹配了目标方法，目标方法运行时，多个通知方法都会被执行

不同切面类中，默认按照切面类的类名字母排序（像拦截器链Filter的顺序）

在切面类上用@Order(数字)，控制顺序，数字越小越先执行

2.6 切入点表达式
用来决定项目中哪些方法需要加入通知

常见形式：
- execution（优先）：根据方法的签名匹配
```java
execution(访问修饰符？ 返回值 包名.类名.？方法名（参数） throws 异常？)  //带问号可省略
```
>星号 \*：通配任意返回值
   点点 .. :多个连续的任意符号，可以荣配任意层级的包
   idea提供左边的图标，直接定位到切入点
- @annotation:根据注解匹配

2.7 连接点

Spring中用KJoinPoint抽象了连接点，用它可以获得方法执行时的相关信息，如目标类名、方法名、方法参数等
- 对于@Around通知，获取连接点信息只能使用 ProceedingJoinPoint
- 对于其他四种通知，获取连接带点信息只能使用JoinPoint，他是ProceedingJoinPoint的父类型

```java
// 获取目标对象
Object target = joinPoint.getTarget();
// 获取目标类
String className = joinPoint.getTarget.getClas().getName();
// 获取目标方法
String methodName = JoinPoint.getSignature().getName();
// 获取目标方法参数
Object[] args = joinPoint.getArgs();
```

## 3. AOP案例

案例：将案例中的增、删、改相关接口的操作日志记录到数据库表中
采用@Around环绕通知
切入点表达式：匹配Controller层增删改的方法，选择基于注解的方式

需要将记录保存到数据库
- 建表语句
```sql
create table operate_log(  
                            id int unsigned primary key auto_increment comment 'ID',  
                            operate_emp_id int unsigned comment '操作人ID',  
                            operate_time datetime comment '操作时间',  
                            class_name varchar(100) comment '操作的类名',  
                            method_name varchar(100) comment '操作的方法名',  
                            method_params varchar(2000) comment '方法参数',  
                            return_value varchar(2000) comment '返回值',  
                            cost_time bigint unsigned comment '方法执行耗时，单位:ms'  
) comment '操作日志表';
```
- 对应实体类（对应数据库中的表结构）
```java
@Data  
public class OperateLog {  
    private Integer id; //ID  
    private Integer operateEmpId; //操作人ID  
    private LocalDateTime operateTime; //操作时间  
    private String className; //操作类名  
    private String methodName; //操作方法名  
    private String methodParams; //操作方法参数  
    private String returnValue; //操作方法返回值  
    private Long costTime; //操作耗时  
}
```
- mapper接口
```java
@Mapper  
public interface OperateLogMapper {  
  
    // 插入日志数据  
    @Insert("insert into operate_log (operate_emp_id, operate_time, class_name, method_name, method_params, return_value, cost_time) " +  
            "values (#{operateEmpId}, #{operateTime}, #{className}, #{methodName}, #{methodParams}, #{returnValue}, #{costTime})")  
    public void insert(OperateLog log);  
}
```
实现AOP，切入点表达式采用@annotion注解方式
- 新建一个注解类
```java
@Target(ElementType.METHOD)  
@Retention(RetentionPolicy.RUNTIME)  
public @interface Log {  
}
```

@Target：规定注解可以写在哪里
@Target(ElementType.METHOD) → @Log只能标注在方法上

@Retention：规定注解保留到什么时候 @Retention(RetentionPolicy.RUNTIME) → @Log保留到程序运行阶段 → 运行时可以通过反射/AOP获取这个注解

- AI生成AOP实现
propmt：
```markdown
假如你是一名java开发工程师，请帮我基于Spring AOP实现记录系统所有增、删、改功能接口的操作日志。具体信息如下：

1. 日志信息包含：操作人、操作时间、目标类的全类名、目标方法的方法名、方法运行时参数、返回值、方法执行时长

2. 功能接口所在包为 com.itheima.controller

3. 日志表为 operate_log 表，对应的实体类为 OperateLog。
具体表结构如下：

create table operate_log(
    id int unsigned primary key auto_increment comment 'ID',
    operate_emp_id int unsigned comment '操作人ID',
    operate_time datetime comment '操作时间',
    class_name varchar(100) comment '操作的类名',
    method_name varchar(100) comment '操作的方法名',
    method_params varchar(2000) comment '方法参数',
    return_value varchar(2000) comment '返回值',
    cost_time bigint unsigned comment '方法执行耗时，单位:ms'
) comment '操作日志表';

实体类如下：

@Data
public class OperateLog {
    private Integer id; //ID
    private Integer operateEmpId; //操作人ID
    private LocalDateTime operateTime; //操作时间
    private String className; //操作类名
    private String methodName; //操作方法名
    private String methodParams; //操作方法参数
    private String returnValue; //操作方法返回值
    private Long costTime; //操作耗时
}

4. 并且已经提供了 OperateLogMapper 接口来操作 operate_log，并在其中已经定义好了 insert 方法用来保存日志数据。
```

AI生成的代码
```java
@Slf4j
@Aspect
@Component
public class OperateLogAspect {

    @Autowired
    private OperateLogMapper operateLogMapper;

    @Around("@annotation(com.itheima.anno.Log)")
    public Object recordLog(ProceedingJoinPoint joinPoint) throws Throwable {

        // 1. 记录开始时间
        long begin = System.currentTimeMillis();

        // 2. 执行目标方法
        Object result = joinPoint.proceed();

        // 3. 计算方法执行耗时
        long end = System.currentTimeMillis();
        long costTime = end - begin;

        // 4. 获取目标类的全类名
        String className = joinPoint.getTarget()
                .getClass()
                .getName();

        // 5. 获取目标方法名
        String methodName = joinPoint.getSignature().getName();

        // 6. 获取方法参数
        Object[] args = joinPoint.getArgs();
        String methodParams = Arrays.toString(args);

        // 7. 获取方法返回值
        String returnValue = result == null ? null : result.toString();

        // 8. 封装日志对象
        OperateLog operateLog = new OperateLog();

        operateLog.setOperateEmpId(/* 当前登录员工ID */);
        operateLog.setOperateTime(LocalDateTime.now());
        operateLog.setClassName(className);
        operateLog.setMethodName(methodName);
        operateLog.setMethodParams(methodParams);
        operateLog.setReturnValue(returnValue);
        operateLog.setCostTime(costTime);

        // 9. 保存日志
        operateLogMapper.insert(operateLog);

        log.info("记录操作日志：{}", operateLog);

        return result;
    }
} 
```

给想要方法添加@Log注解，实现该方法的日志记录

ThreadLocal
- ThreadLocal并不是一个Thread，而是Thread的局部变量

ThreadLocal为每个线程提供一份单独的存储空间，具有线程隔离效果，不同线程之间不会相互干扰
ThreadLocal常用方法：
```java
// 设置当前线程的线程局部变量的值
public void set(T value)

//返回当前线程所对应的线程局部变量的值
public T get()

// 移除当前线程的线程局部变量
public void remove()
```

>保存在ThreadLocal中的值，在用完之后要及时的删除掉

浏览器每一次请求对应一个Tomcat的线程

使用ThreadLocal来获得员工信息的过程：
>员工 ID 被存入 JWT。之后每次请求都会携带 JWT，TokenFilter 在请求进入 Controller 之前获取并校验 JWT，从中解析出当前登录员工 ID，并将其保存到 ThreadLocal。由于同一次请求通常由同一个线程处理，因此后续的 AOP、Controller、Service 等都可以通过 ThreadLocal 获取当前登录员工 ID。AOP 在记录操作日志时，从 ThreadLocal 中获取操作人 ID。请求结束后需要调用 `remove()` 清除 ThreadLocal，避免线程复用导致数据残留。


经过 Filter 之后，后面的业务代码通常就**不需要再解析 token 了**，所以AOP只能从Filter中拿到当前登录用户的ID用户信息