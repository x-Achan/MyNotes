
## 1. 配置优先级

主流： 推荐yml格式的配置
SpringBoot 除了支持配置文件属性配置， 还支持Java系统属性和命令行参数的方式进行属性配置

 优先级：命令行参数>java系统属性>yml文件

执行maven打包指令package
执行java指令，运行jar包可以配置Java系统属性和命令行参数 
```powershell
java -jar app.jar --server.port=8081
```

## 2.bean的管理

==Bean本质：==
>由Spring IOC容器负责创建、管理和维护的Java对象

### 2.1bean的作用域

作用域：
  - **singleton**：容器内同名称的bean只有一个单例（默认）
  - **prototype**：每次使用该bean时都会创建新的实例（多例）
  - request/session/application（了解）

设置bean为多例
```java
@Scope("prototype")
```

ApplicationContext类：IOC容器
- getBean：“获取bean对象

Bean什么时候创建？
**Bean对象默认是在项目启动的时候创建的**
**创建完毕后，会讲bean放入IOC容器**
@Lazy：延迟初始化，延迟到第一次使用的时候，再来创建这个Bean

不同的作用域有不同的作用场景：
单例的bean，适用于无状态的Bean：不保存数据
多例的bean，适用于有状态的Bean：保存数据

>项目开发当中，绝大部分的Bean是单例的，绝大部分Bean不需要配置scope

Spring容器的bean是线程安全的吗？
>无状态的bean是线程安全的，因为不存在数据共享的问题
>有状态的bean，多个线程操作bean时，有可能出现线程安全问题

### 2.2第三方Bean

对于自己实现的类，可以通过注解@Component声明这是一个bean对象

对于第三方库的类，不能去源码中添加注解
通过@Bean注解声明一个方法
- **Bean方法通常写在配置类Config中，通常写在 @Configuration 配置类中**
- 返回值 = bean类型
- 方法名默认就是 Bean 名称
- 方法返回的对象 = IOC 容器管理的对象
- 默认是单例 Bean

模板：
```java
@Configuration
public class XxxConfig {

    @Bean
    public Xxx xxx() {
        return new Xxx();
    }
}
```

## 3.SpringBoot自动配置原理

起步依赖的原理就是Maven的依赖

自动配置：SpirngBoot的自动配置就是当spring详谬启动后，一些配置类、bean对象就自动存入了IOC容器中，不需要我们手动声明，从而简化开发，省区繁琐的配置操作

### 3.1自动配置实现方案

@SpringBootApplication：具备组件扫描的功能，但是扫描的时启动类所在的包及其子包

方案一：@ComponentScan：在启动类上添加，设置扫描范围，适用于第三方提供的依赖
```java
@ComponentScan(baseOackages = {"包名1","包名2"...})
```

方案二：@Import导入
>可以把 Spring 默认扫描不到的类主动导入 IOC 容器体系
>相当于告诉Spring，这个类你也给我加载

导入形式：
- 普通类
- 配置类
- **ImportSelector接口实现类，批量导入**（需要自己手动实现ImportSelector接口）
```java
//普通类 & 配置类
@Import(类名.class) 

//ImportSelector接口实现类
@Import(MyImportSelector.class)
```

```
@ComponentScan
→ 自己去包里找

@Import
→ 我直接把类告诉Spring
```

方案三：第三方类的开发者会讲@Import注解进行封装，提供注解@EnableXxxx直接导入 

### 3.2 源码跟踪

启动类注解@SpringBootApplication源码有三个核心组成
- **@SpringBootConfiguration注解**：这个注解里面有@Configuration，所以启动类本质是一个配置类（所以可以在启动类中声明第三方的Bean）
- **@ComponentScan**：组件扫描，默认扫描当前引导类所在包及其子包
- **==@EnableAutoConfiguration==**：SpringBoot实现自动化配置的核心注解，**通过自动配置导入机制获取候选“自动配置类”的全类名，并将这些自动配置类导入 Spring**。Spring 随后解析这些配置类，根据 `@Conditional` 系列注解判断配置是否满足条件；**满足条件后执行其中的 `@Bean` 方法，将创建出来的 Bean 注册到 IOC 容器中**

Enable开头的注解底层一般都会封装@Import注解
```java
@Import(AutoConfigurationImportSelector.class)
```
AutoConfigurationImportSelector中实现了selectImports
**返回值String[]数组：封装了需要导入到IOC中的类的自动配置类的类名
```java
public String[] selectImports(AnnotationMetadata annotationMetadata)
```

String[]数组中的类名来源于该文件
```bash
META-INF/spring/
org.springframework.boot.autoconfigure.AutoConfiguration.imports
```
文件中保存了很多自动配置类名，**这些都是配置类中都声明了一个一个的Bean对象**
**这些Bean对象不会全部加载到IOC容器上，会根据@Condiitional条件判断是否满足** 

自己自定义自动配置类也是将自动配置类配置在这个文件中

完整的自动配置流程：
```
SpringBoot启动
        ↓
@SpringBootApplication
        ↓
@EnableAutoConfiguration
        ↓
@Import(...)
        ↓
找到 AutoConfiguration.imports
        ↓
得到一批“自动配置类”
        ↓
把这些自动配置类导入 Spring
        ↓
Spring解析这些配置类
        ↓
检查 @Conditional 条件
        ↓
条件满足
        ↓
执行里面的 @Bean 方法
        ↓
创建Bean
        ↓
放入IOC容器
```

### 3.3@Conditional

作用：
>根据指定条件判断，满足条件后才注册 Bean

位置：方法、类
@Conditional本身是一个父注解，派生出大量的子注解
 - @ConditionalOnClass：classpath 中存在这个类时，配置才生效，才注册bean到IOC容器
 - @ConditionOnMissingBean：IOC 中没有这个 Bean，我才创建
 - @ConditionalOnProperty：判断yml配置文件中有对应的属性和值，才会注册到IOC容器中

```java
@ConditionalOnClass(name = "Xxx.class")

@ConditionalOnMissingBean  

//判断yml配置文件中： name值是否为ccy
@ConditionalOnProperty(name="myname",havingValue="ccy")
```

## 3.4自定义starter

```
starter = 依赖管理
autoconfigure = Bean自动配置
```

 在实际开发中，经常会自定义一些公共组件，提供给各个项目团队使用。而在SpringBoot的项目中，一般会将这些公共组件封装为SpringBoot的starter（博阿寒起步依赖和自动配置的功能）

案例：自定义aliyun-oss-spring-boot-starter，完成阿里云OSS操作工具类 AliyunOSSOperator的自动配置
目标：引入起步依赖之后，要想使用阿里云OSS，注入AliyunOSSOperator 直接使用即可
步骤：
- 创建aliyun-oss-spring-boot-starter模块
- 创建aliyun-oss-spring-boot-autoconfigure模块，在starter中引入该模块
- 在aliyun-oss-spring-bootautoconfigure模块中的定义自动配置功能，并定义自动配置文件 META-INF/spring/xxxxx.imports

## 4.常见问题


### Q1： IOC & DI
答：
>IOC：对象创建和管理的控制权交给Spring
>DI：Spring创建Bean之后，把Bean所依赖的其他Bean注入进去
>IOC 是思想，DI 是 IOC 的主要实现方式

---

### Q2：@Component 和 @Bean的核心区别 
>`@Component` 和 `@Bean` 都可以把对象交给 Spring IOC 容器管理。
>
>`@Component` 是类级别注解，通常通过组件扫描发现，由 Spring 负责创建该类的对象，适合自己编写的业务类；
>`@Bean` 是方法级别注解，**Spring 会执行被 `@Bean` 标注的方法，并把方法返回值注册到 IOC 容器中**，因此更适合第三方类或者需要自定义对象创建、初始化过程的场景。
>`@Component` 更偏向“声明这个类由 Spring 管理”
>`@Bean` 更偏向“我负责创建对象，Spring 负责管理对象”。
>`@Controller`、`@Service`、`@Repository` 本质上都是基于 `@Component` 的语义化注解

---
### Q3：Spring Boot 自动配置原理是什么？
答：
>Spring Boot 启动类上的 `@SpringBootApplication` 中包含 `@EnableAutoConfiguration`，用于开启自动配置。  
>
`@EnableAutoConfiguration` 会通过 `@Import` 机制加载自动配置相关组件，并读取 `AutoConfiguration.imports` 中声明的候选自动配置类。 
Spring 会解析这些自动配置类，并根据 `@ConditionalOnClass`、`@ConditionalOnMissingBean`、`@ConditionalOnProperty` 等条件注解判断当前环境是否满足配置条件。  
如果条件满足，就会执行自动配置类中相应的 `@Bean` 方法，创建 Bean 并注册到 IOC 容器，从而实现自动配置。


流程：
```
@SpringBootApplication
        ↓
@EnableAutoConfiguration
        ↓
通过 @Import 导入自动配置相关组件
        ↓
读取 AutoConfiguration.imports
        ↓
获得候选自动配置类
        ↓
Spring 解析这些自动配置类
        ↓
@Conditional 判断是否满足条件
        ↓
满足条件后执行其中的 @Bean 方法
        ↓
创建 Bean 并注册到 IOC 容器
```

---
### Q4：`@SpringBootApplication` 有什么作用？

答：

> 它是 Spring Boot 的核心组合注解，主要包含配置类、组件扫描和开启自动配置三个功能。启动类本身是一个配置类，默认扫描启动类所在包及其子包，同时开启 Spring Boot 自动配置。

### Q5：为什么启动类一般放在项目最外层包？

答：

> 因为 `@SpringBootApplication` 默认会扫描启动类所在包及其子包。放在最外层包可以确保 Controller、Service、Mapper、Component 等组件都能够被扫描到。

---

### Q6：什么是 IOC？

> IOC 是控制反转，本来对象由程序员自己 `new`，Spring 中把对象的创建和管理交给 IOC 容器。

---

### Q7：什么是 DI？

> DI 是依赖注入。当一个 Bean 依赖另外一个 Bean 时，Spring 从 IOC 容器中找到对应对象并注入进去。

---

### Q9：Spring Bean 默认是单例吗？

> 是。默认作用域是 singleton，在同一个 IOC 容器中，同名称 Bean 通常只有一个实例。

---

### Q10：单例 Bean 一定线程安全吗？

这题很容易挖坑。

不要答：

```
Spring单例Bean是线程安全的。
```

应该答：

> 不一定。如果 Bean 是无状态的，没有可变共享成员变量，一般不会产生共享数据竞争；如果 Bean 保存了可变状态，多线程同时操作时就可能产生线程安全问题。

---

### Q11：`@ConditionalOnMissingBean` 有什么作用？

> 当 IOC 容器中不存在指定 Bean 时才注册当前 Bean，因此 Spring Boot 可以提供默认配置，同时允许开发者自定义 Bean 覆盖默认配置。

---

### Q12：Starter 是什么？

> Starter 本质上是一组依赖的封装。开发者只需要引入一个 Starter，就可以一次性获得某项功能需要的一组依赖；配合自动配置机制，还可以自动创建相关 Bean。

---

### Q13：Starter 和自动配置有什么区别？

这题你最好会。

```
Starter
→ 解决“需要引入哪些依赖”

自动配置
→ 解决“这些组件应该怎么配置成Bean”
```

---

### Q14：`@Import` 有什么作用？

> 用来将类主动导入 Spring 容器体系，可以导入普通类、配置类以及 ImportSelector 等。Spring Boot 的自动配置机制中也大量利用了 Import 思想。

