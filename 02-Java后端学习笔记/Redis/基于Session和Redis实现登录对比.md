## 一、基于Session的登陆实现

Session是什么?
>Session 是服务端保存会话状态的机制。客户端通过 `JSESSIONID` 标识自己的 Session，服务器根据 `JSESSIONID` 找到对应 Session，从而获取验证码和当前登录用户

1. 实现流程
```
客户端
   ↓
发送手机号
   ↓
服务器生成验证码
   ↓
验证码保存到 Session
   ↓
响应 JSESSIONID

客户端再次请求
   ↓
携带 JSESSIONID + 验证码
   ↓
服务器根据 JSESSIONID 找到 Session
   ↓
取出验证码校验
   ↓
登录成功
   ↓
用户信息保存到 Session

后续请求
   ↓
携带 JSESSIONID
   ↓
服务器找到 Session
   ↓
获取当前登录用户
```
1. 短信验证码-发送

```java
if (RegexUtils.isPhoneInvalid(phone)) {
    return Result.fail("手机号格式错误");
}
String code = RandomUtil.randomNumbers(6);
session.setAttribute("code", code);
}
```
>① 手机号校验属于公共逻辑，因此封装到 `RegexUtils`。  
   ② 验证码属于临时会话数据，因此可以暂存在 Session。  
   ③ `/user/code` 使用 POST，因为它是在触发“生成并发送验证码”这一业务操作，而不是查询资源。

2. 验证码校验 + 自动注册

LoginFromDTO：
>登录接口只需要 `phone`、`code` 等登录参数，而数据库实体 `User` 代表完整用户数据，因此使用 `LoginFormDTO` 接收登录参数，避免接口层直接依赖数据库实体。

3. JSESSIONID 到底干什么？
用户登录时，服务器生成code保存到Session中，返回JSESSIONID给客户端，后续请求携带 JSESSIONID，服务器通过 JSESSIONID 找到该浏览器对应的 Session；如果 Session 中保存了登录用户信息，就可以确定当前请求对应哪个已登录用户

JSESSIONID用来索引查询每个Session

和JWT的区别：
```
Session：
客户端保存 JSESSIONID
用户信息主要保存在服务器

JWT：
客户端保存 Token
用户身份信息编码在 Token 中
服务器解析 Token 获取身份
```

4. 登陆成功后保存带Session
```java
// 从Session获取验证码进行校验
Object cacheCode = session.getAttribute("code");

if (cacheCode == null || !cacheCode.toString().equals(loginForm.getCode())) {
    return Result.fail("验证码错误");
}

// 登录成功，将精简后的用户信息保存到Session
session.setAttribute(
        "user",
        BeanUtil.copyProperties(user, UserDTO.class)
);
```

4. 拦截器实现登录校验

```java
@Override
public boolean preHandle(
        HttpServletRequest request,
        HttpServletResponse response,
        Object handler) {

    // 从Session获取当前登录用户
    UserDTO user = (UserDTO) request.getSession()
                                   .getAttribute("user");

    // 未登录
    if (user == null) {
        response.setStatus(401);
        return false;
    }

    // 保存到ThreadLocal，供后续业务使用
    UserHolder.saveUser(user);

    return true;
}

@Override
public void afterCompletion(...) {
    UserHolder.removeUser();
}
```

用ThreadLocal实现用户信息的保存，方便Controller和Service层获取用户信息，afterCompletion要将用户信息从ThreadLocal中去除，使用ThreadLocal要定义一个Holder工具类：
```java
public class UserHolder {  
    private static final ThreadLocal<UserDTO> tl = new ThreadLocal<>();  
  
    public static void saveUser(UserDTO user){  
        tl.set(user);  
    }  
  
    public static UserDTO getUser(){  
        return tl.get();  
    }  
  
    public static void removeUser(){  
        tl.remove();  
    }  
}
```

使用拦截器，要用mvc配置类实现拦截器的配置：
```java
@Configuration  
public class MvcConfig implements WebMvcConfigurer {  
    @Override  
    public void addInterceptors(InterceptorRegistry registry) {  
        registry.addInterceptor(new LoginIntercepter())  
                .excludePathPatterns(  
                        "/shop/**",  
                        "/voucher/**",  
                        "/shop-type/**",  
                        "/upload/**",  
                        "/blog/hot",  
                        "/user/code",  
                        "/user/login"  
                );  
    }  
}
```
排除路径中添加可以直接放行的请求路径

User中有很密码敏感信息和无关信息，是不需要返回给前端的，所以在往Session中保存用户信息是保存UserDTO，使用BeadUtil.copyProperties实现复制属性
```java
session.setAttribute("user", BeanUtil.copyProperties(user, UserDTO.class));
```

集群Session共享问题
>多台Tomcat并不共享session存储空间，去切换到不同tomcat服务时导致数据丢失

## 二、基于Redis实现登录

0. 为什么改用Session为Redis？
>Redis 可以作为多个服务实例共享的登录状态存储，解决Session不能在服务器共享的问题

1. 生成的验证码保存在Redis中
- key是phone
- value是code（使用String类型
- 设置存储有效期为 2min
```java
// 3.保存验证码到 redis中,设置 key-value,保存时间为2min
stringRedisTemplate.opsForValue()
	.set(LOGIN_CODE_KEY + phone,code,LOGIN_CODE_TTL, TimeUnit.MINUTES);
```

2. 登陆时如何验证Redis的验证码

cacheCode：Redis中服务器保存的正确验证码
code：用户提交的验证码
判断两者是否一致？
```java
String cacheCode =
        stringRedisTemplate.opsForValue()
                .get(LOGIN_CODE_KEY + phone);

String code = loginForm.getCode();

if(cacheCode == null || !cacheCode.equals(code)){
    return Result.fail("验证码错误");
}
```

验证码通过后，利用MyBatis-Plus查询用户
```java
User user = query()
        .eq("phone", phone)
        .one();
```
用户不存在就创建新用户，将属性传入，然后保存到数据库中（自动注册）
```java
save(newUser);
```


3. Redis登录状态保存

拿到用户信息后，不能直接整个 User 存进Redis
因为User中包含敏感信息（密码）或无关字段
所以需要UserDTO（安全的用户信息）
>DTO的意义：只保存/传递当前场景真正需要的数据，同时减少存储占用

3.1 先生成Token
```java
String token = UUID.randomUUID().toString();
```
作为客户端访问 Redis 登录信息的凭证/**索引**，本身不携带用户

SESSIONID、随机 Token、JWT的区别：
>SESSIONID、随机 Token、JWT 都用于让服务器识别请求所属用户，但实现机制不同。JSESSIONID 和 Redis Token 本身主要是身份索引，需要到服务端 Session/Redis 中查询登录状态；JWT 本身携带用户声明，服务器通过验签和解析 JWT 获取用户信息。Redis Token 属于有状态认证，便于服务端主动失效和管理登录状态；JWT 通常属于无状态认证，减少服务端会话存储，但主动注销和失效控制更复杂。

3.2 将用户信息 UserDTO 转为 Map
Redis中使用Map存储用户信息

实现：
```java
Map<String,Object> userMap =
        BeanUtil.beanToMap(
                userDTO,
                new HashMap<>(),
                CopyOptions.create()
                        .setIgnoreNullValue(true)
                        .setFieldValueEditor(
                                (fieldName, fieldValue)
                                        -> fieldValue.toString()
                        )
        );
```

在 StringRedisTemplate中，Key、Value、HashKey、HashValue 都主要按照字符串方式处理，需要将所有 Java对象的属性都转为String（Redis可保存的形式），所以需要fieldValue.toString()

3.3 把整个 Java Map 写入一个 Redis Hash
```java
stringRedisTemplate.opsForHash()
        .putAll(tokenKey, userMap);
```

3.4 设置登录状态有效期 TTL
```java
stringRedisTemplate.expire(
        tokenKey,
        LOGIN_USER_TTL,
        TimeUnit.MINUTES
);
```

3.5 将Token返回客户端
```java
return Result.ok(token);
```
下次用户请求时携带 Token
```json
authorization: token
```

3.6 数据链的转换
```
MySQL
 ↓
User实体
 ↓
BeanUtil.copyProperties()
 ↓
UserDTO
 ↓
BeanUtil.beanToMap()
 ↓
Map<String,Object>
 ↓
字段统一转String
 ↓
Redis Hash
```

在拦截器中
```
Redis Hash
 ↓
Map<Object,Object>
 ↓
BeanUtil.fillBeanWithMap()
 ↓
UserDTO
 ↓
ThreadLocal
```

形成了一个闭环
```
登录：
UserDTO → Map → Redis

请求：
Redis → Map → UserDTO
```

4. Redis登陆状态设计总结

登录成功后，服务器随机生成 Token，并将数据库中的 `User` 转换为只包含必要登录信息的 `UserDTO`。为了使用 Redis Hash 保存用户信息，再将 `UserDTO` 转换成 Map，同时过滤 null 字段，并将字段值统一转换成 String，以适配 `StringRedisTemplate`。

使用 `LOGIN_USER_KEY + token` 作为 Redis Key，以 Hash 结构保存用户的 id、昵称、头像等登录信息，并设置 TTL。Token 返回客户端，客户端后续请求通过请求头携带 Token；服务器利用 Token 从 Redis 中找到当前用户。

因此，**Token 是访问登录状态的凭证，Redis 是登录状态真正的存储位置；UserDTO 用于控制保存的数据范围，Hash 用于保存结构化用户信息，TTL 用于控制登录有效期。**

5. 拦截器的设计

5.1 拦截器设计的核心思想
>把所有请求都会遇到的公共逻辑，从 Controller 中抽离出来，在请求真正进入 Controller 之前统一处理

拦截器用于抽取多个接口共有的前置/后置处理逻辑，并根据不同 URL 配置不同的处理规则。Redis 登录中采用两个拦截器进行职责分离：
- `RefreshTokenInterceptor` 拦截所有请求，只负责尝试解析 Token、恢复当前用户和刷新 TTL，没有 Token 时也应该放行；
-  `LoginInterceptor` 只拦截需要登录的接口，负责根据 ThreadLocal 判断用户是否登录，未登录时才真正返回 401。


5.1 链路

```
客户端请求
   ↓
携带 authorization: token
   ↓
RefreshTokenInterceptor       order(1)
   ↓
根据Token去Redis查询用户
   ↓
查询到用户
→ 保存到ThreadLocal
→ 刷新Token有效期
   ↓
LoginInterceptor              order(2)
   ↓
判断ThreadLocal是否存在用户
   ↓
有用户 → 放行
无用户 → 401
   ↓
Controller → Service
   ↓
请求结束
   ↓
清理ThreadLocal
```

5.2 `RefreshTokenInterceptor`：负责“解析身份 + 刷新登录状态”

先拿 Token
```java
String token = request.getHeader("authorization");
```
从Redis中取出用户信息
```java
Map<Object,Object> userMap =
        stringRedisTemplate.opsForHash()
                .entries(LOGIN_USER_KEY + token);
```
如果 Redis 有用户，转为UserDTO，再保存带ThreadLocal中
```java
UserDTO userDTO =
        BeanUtil.fillBeanWithMap(
                userMap,
                new UserDTO(),
                false
        );
        
UserHolder.saveUser(userDTO);
```

```
Controller
Service
AOP
```
都可以直接
```
UserHolder.getUser();
```
不需要再次访问 Redis。

还要刷新 TTL
```
stringRedisTemplate.expire(
        LOGIN_USER_KEY + token,
        LOGIN_USER_TTL,
        TimeUnit.MINUTES
);
```

5.2 `LoginInterceptor`：负责真正的登录校验

```java
if(UserHolder.getUser() == null){
    response.setStatus(401);
    return false;
}
return true;
```

6. 其他

6.1 Spring原则：
>只有交给 Spring IOC 容器管理的对象，Spring 才能帮它完成 `@Autowired`、`@Resource` 等依赖注入。自己手动 `new` 出来的对象，不属于 Spring Bean，Spring 不会自动给它注入依赖，因此需要由一个 Spring Bean 先获取所需依赖，再通过构造器将依赖传递给手动创建的对象

举例：
```java
@Resouce
private StringRedisTemplate stringRedisTemplate;
...
...(new LoginInterceptor(stringRedisTemplate))
```

6.2 BeanUtil常用API

|转换方向|常用方法|典型场景|
|---|---|---|
|Bean → Bean|`copyProperties()`|Entity → DTO / VO|
|Bean → Map|`beanToMap()`|Redis Hash、动态数据|
|Map → Bean|`fillBeanWithMap()`|Redis Hash → DTO|
|Map → 新 Bean|`toBean()`|Map 转实体|
|List<Bean> → List<Bean>|`copyToList()`|Entity 列表 → DTO 列表|
 6.3 Mybatis-plus
```java
User user = query()
        .eq("phone", phone)
        .one();
```

查询 `tb_user` 表中 phone 等于当前手机号的一条用户数据，并封装成 User

| API                | 作用                 | 类似 MyBatis             |
| ------------------ | ------------------ | ---------------------- |
| `BaseMapper<T>`    | Mapper 通用 CRUD     | 自己写 Mapper SQL         |
| `IService<T>`      | Service 通用 CRUD 接口 | 自己定义 Service 方法        |
| `ServiceImpl<M,T>` | 通用 Service 实现      | 自己实现 Service CRUD      |
| `query()`          | 开始构建查询             | `SELECT ... WHERE ...` |
| `eq()`             | 等值条件               | `WHERE xxx = ?`        |
| `one()`            | 查询一条               | 返回一个实体                 |
| `list()`           | 查询多条               | `List<T>`              |
| `save()`           | 新增                 | `INSERT`               |

