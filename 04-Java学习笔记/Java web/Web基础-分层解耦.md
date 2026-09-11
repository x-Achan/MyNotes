
1. 三层架构

- ControllerL：控制层
接受请求，响应数据

- service：业务逻辑层
业务逻辑处理

- Dao：数据访问层
数据访问操作，增删改查

2. 分层解耦的思路

- 控制反转 Inversion Of Control，简称 IOC
对象的创建控制权由程序自身转移到外部容器
- 依赖注入 Dependency Injection，简称 DI
容器为应用程序提供运行时，所依赖的资源，称之为依赖注入
- Bean对象
IOC容器中创建、管理的对象，称之为 Bean

3. IOC & DI 入门
- 将 Dao 及 Service 层的实现类，交给IOC容器管理
@Component ：将类产生的对象交给容器

- 为Controller 及 Service注入运行时所依赖的对象
@Autowired：应用程序运行时，会自动的查询该类型的bean对象，并赋值给该成员变量

4. IOC详解
要把某个对象交给IOC容器管理，需要在对应的类上加上如下注解之一
- @Component
声明 bean 的基础注解，不属于一下三类时，用此注解
- @Controller
@Component的衍生注解，标注在控制层上
- @Service
@Component的衍生注解，标注在业务层上
- @Repository
@Component的衍生注解，标注在数据访问层上（由于与myabtis整合，用的少）

- 注意事项
声明bean的注解要想生效，需要被扫描到，启动类默认扫描当前包及其子包

5. DI详解
基于@Autowired进行依赖注入的常见方式有如下三种
- 属性注入
- 构造函数注入
- setter注入（不多）

@Autowired注解，默认是按照类型注入的
如果存在多个相同类型的bean，将会报错
解决方案：
- @Primary 提高bean的优先级
- @Autowired + @Qualifier
- @Resource