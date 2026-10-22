# 一、认证基础

传统Sesssion：
```
用户登录：
- 服务器创建Session,保存:sessionId -> user
- 浏览器保存 JSESSIONID
- 以后请求携带JSESSIONID，服务器查Session
```
JWT：
```
用户登录
- 服务器生成JWT
- 返回给客户端,客户端保存JWT
- 以后请求携带：Authorization:Bearer eyJxxxx
- 服务器验证JWT签名,解析用户信息
```

# 二、JWT

## 2.1 JWT结构

结构：
```
JWT = Header.Payload.Signatur
```
1. Header保存算法
2. Payload保存 Claims，标准claim有专门的 builder 方法

| Claim | 方法                        | 说明           |
| ----- | ------------------------- | ------------ |
| `iss` | `.issuer(String)`         | 签发者          |
| `sub` | `.subject(String)`        | 主题（通常是用户 ID） |
| `aud` | `.audience(List<String>)` | 接收方          |
| `exp` | `.expiresAt(Instant)`     | 过期时间         |
| `nbf` | `.notBefore(Instant)`     | 生效时间         |
| `iat` | `.issuedAt(Instant)`      | 签发时间         |
| `jti` | `.id(String)`             | 唯一标识         |
|       |                           |              |
 可以添加自定义 claim
```java
.claim("role", "ADMIN")
.claim("nickname", "张三")
.claim("tenantId", "t-001")
```
3. Signature签名，由加密算法生成（RS256非对称加密算法/HS256对称加密算法）

## 2.2 JWT签发和验证流程

>**Spring Security 提供**：`JwtEncoder` / `JwtDecoder`

我们自己在配置类里创建 `JwtEncoder` 和 `JwtDecoder`，把它们注册成 Spring Bean；`JwtEncoder` 用 RSA 私钥体系签发 JWT，`JwtDecoder` 用 RSA 公钥验签

1. 填充JwtClaimsSet字段，对应载荷PayLoad
```java
JwtClaimsSet claims = JwtClaimsSet.builder()
        .issuer("zhiguang")                          // iss
        .subject(user.getId().toString())            // sub
        .issuedAt(Instant.now())                     // iat
        .expiresAt(Instant.now().plus(Duration.ofMinutes(15)))  // exp
        .id(UUID.randomUUID().toString())            // jti
        .claim("token_type", "access")               // 自定义
        .claim("role", user.getRole())               // 自定义
        .build();
```

>**`JwtClaimsSet`** 是 **Spring Security 用来构造 JWT payload（claims）的类**

PayLoad：
```json
{
  "iss": "zhiguang",
  "sub": "1001",
  "iat": 1716192000,
  "exp": 1716192900,
  "jti": "a1b2c3d4-...",
  "token_type": "access",
  "role": "ADMIN"
}
```
2. 打包Header和Claims，encode编码返回Jwt对象，获取Jwt对象中的token字符串
```java
jwtEncoder.encode(JwtEncoderParameters.from(claims)).getTokenValue();
```
签发JWT的API链路：
```
JwtClaimsSet（payload 内容）
    ↓ 包装
JwtEncoderParameters（作用是把 "Header" 和 "Claims" 打包在一起）
    ↓ 交给
JwtEncoder.encode(...)   （编码器）
    ↓ 返回
Jwt（Spring Security 的 JWT 对象）
    ↓ 调用
Jwt.getTokenValue()      （拿到真正的 token 字符串）
```

3. ==🟡JWT类的结构==

encode封装信息，返回Jwt类
```java
public class Jwt implements ClaimAccessor, Serializable {
    private final String tokenValue;        // ← 真正的 token 字符串
    private final String issuedAt;          // 签发时间
    private final String expiresAt;         // 过期时间
    private final Map<String, Object> headers;  // header map
    private final Map<String, Object> claims;   // claims map
    // ...
}
```

4. 验证token

decode解析token字符串，返回Jwt类
```java
 Jwt jwt = jwtDecoder.decode(token);  
```


# 三、双Token设计

>Access Token 和 Refresh Token本质都是Jwt，在Claims中，添加 `token_type`来区分

## 3.1 介绍

1. Access Token
- 特点：短时间有效，
- 作用：访问接口

例如：
```
GET /api/v1/user/profile
```
携带：
```
Authorization:Bearer access_token
```

2. Refresh Token
- 特点：长期有效
- 作用：换新的 Access Token

```
Access Token过期
        ↓
客户端发送Refresh Token
        ↓
服务器验证
        ↓
生成新的Access Token
```

3. 为什么需要两个Token？
```
短命 Access Token   → 泄露影响小（很快就过期）
     +
长命 Refresh Token  → 用户不用频繁登录
     +
Refresh 可撤销      → 万一泄露，服务端能主动失效
```

>一个 token 不可能同时满足"短命（安全）+ 长命（体验）" → 拆成两个，各司其职



## 3.2 基于 Redis 的刷新令牌白名单存储

Access Token 只存储在客户端
Refresh Token 不仅存储客户端，也存储服务端 Redis（白名单）

1. 双token载荷信息区分
Access Token的claims：
```java
JwtClaimsSet claims = JwtClaimsSet.builder()  
        .issuer(properties.getJwt().getIssuer()) //签发者
        .issuedAt(issuedAt)                      //签发时间
        .expiresAt(expiresAt)                    //过期时间（短）
        .subject(String.valueOf(user.getId()))   //主题（通常是用户Id）
        .id(tokenId)                             //token唯一标识 tokenId（随机生成）
        .claim(CLAIM_TOKEN_TYPE, tokenType)      //双token区分：access token
        .claim(CLAIM_USER_ID, user.getId())      //用户id
        .claim("nickname", user.getNickname())   //用户昵称
        .build();
```

Refresh Token的claims：
```java
JwtClaimsSet claims = JwtClaimsSet.builder()  
        .issuer(properties.getJwt().getIssuer()) //签发者
        .issuedAt(issuedAt)                      //签发时间
        .expiresAt(expiresAt)                    //过期时间（长）
        .subject(String.valueOf(user.getId()))   //主题（通常是用户Id）
        .id(tokenId)                             //token唯一标识 tokenId（随机生成）
        .claim(CLAIM_TOKEN_TYPE, "refresh")      //双token区分：refresh token
        .claim(CLAIM_USER_ID, user.getId())      //用户id
        .build();
```

⭐关键：
>Token中携带用户Id，就代表了携带了用户信息，过滤链处理请求，解析Token，得到Jwt，Controller层通过@AuthenticationPrincipal，从 SecurityContext里取出Jwt，直接传给方法参数，从Jwt中解析出用户Id，拿到用户Id，就可以通过getUserById查询数据库中的User信息。


Refresh Token信息包含tokenId（jti）和userId，保存在Redis中（jti白名单）用于刷新Access Token
>==键空间：`auth:rt:{userId}:{tokenId}`，值固定为 "1"==

在Redis中只保存了UserId和TokenId
- userId为了在服务器取出用户信息生成新的TokenPair
- tokenId为了标识RefreshToken
- value值存什么不重要，只要key还在，就表示RefreshToken没有过期

2. ==**Token刷新**==
过程：
- 用户携带 refreshToken请求，服务器解析token信息
```java
Jwt jwt = jwtService.decode(refreshToken);  
String tokenType = jwtService.extractTokenType(jwt);  
long userId = jwtService.extractUserId(jwt);  
String tokenId = jwtService.extractTokenId(jwt);
```
- 验证tokenType是否正确
- 用userId和tokenId，到Redis中查询`auth:rt:{userId}:{tokenId}`否是值位1（标记存在TTL没有过期）
- 取出用户信息user
- 使旧的refreshToken失效（删除key）
- 根据user，重新生成双Token并保存到Redis中

# 四、Spring Security 
## 4.1 密码加密
>存储在数据库中的是密码的加密结果，不存储真实密码
1. 创建密码编译器
```java
@Bean  
public PasswordEncoder passwordEncoder() {  
    return new BCryptPasswordEncoder();  
}
```

2. 测试使用，对密码123进行编码
```java
@Resource  
PasswordEncoder passwordEncoder;  
  
@Test  
void PasswordEncoder(){  
    String hash = passwordEncoder.encode("123321");  
    System.out.println(hash);  
    System.out.println(passwordEncoder.matches("123321",hash));  
}
```

3. 输出
```
$2a$10$wI6DNNtFt.E6g6muZkHYGu235C./tWW3BSO65njmJgPC6ktWVroAa
true
```

## 4.2 配置文件（过滤配置）

自动鉴权过滤：
- 客户端发送请求
- **Spring Security Filter Chain**
- ==**BearerTokenAuthenticationFilter**==
- **提取accessToken**
- **JwtDecoder(public key验签)**
- **JwtAuthenticationToken**
- **SecurityContext**
- Controller

>BearerTokenAuthenticationFilter 是 Spring Security 过滤器链中的一个过滤器，负责从 HTTP 请求中提取 Bearer Token（Access Token或者 Refresh Token），并交给 Spring Security 验证

过滤配置：
```java
@Bean  
public SecurityFilterChain securityFilterChain(HttpSecurity http) throws Exception {  
    //CSRF关闭：JWT放Authorization头，不放Cookie  
    http.csrf(AbstractHttpConfigurer::disable)  
            //CORS开启：前后端分离 → 前端访问后端跨域→必须允许  
            .cors(Customizer.withDefaults())  
            //"无状态"（Stateless）会话策略,初不创建HttpSession，每个请求都独立认证  
            .sessionManagement(session -> session.sessionCreationPolicy(SessionCreationPolicy.STATELESS))  
            .authorizeHttpRequests(auth -> auth  
                    .requestMatchers("/actuator/health", "/actuator/info").permitAll()  
                    // 公开内容：首页 Feed 不需要登录  
                    .requestMatchers("/api/v1/knowposts/feed").permitAll()  
                    // 知文详情（公开已发布内容，非公开由服务层校验）  
                    .requestMatchers(org.springframework.http.HttpMethod.GET, "/api/v1/knowposts/detail/*").permitAll()  
                    // 知文详情页 RAG 问答（SSE 流式输出）允许匿名访问  
                    .requestMatchers(org.springframework.http.HttpMethod.GET, "/api/v1/knowposts/*/qa/stream").permitAll()  
                    .requestMatchers(  
                            "/api/v1/auth/send-code",  
                            "/api/v1/auth/register",  
                            "/api/v1/auth/login", //登录接口  
                            "/api/v1/auth/token/refresh",  
                            "/api/v1/auth/logout",  
                            "/api/v1/auth/password/reset"  
                    ).permitAll()  
                    .anyRequest().authenticated()  
            )  
            .oauth2ResourceServer(oauth -> oauth.jwt(Customizer.withDefaults()));  
    return http.build();  
}
```

CSRF：**一种攻击** —— 攻击者利用用户登录态，**冒用身份发请求**
CORS：**浏览器机制** —— 限制 JS 跨域请求，服务端配置白名单


# 五、一句话总结

项目采用 Spring Security OAuth2 Resource Server + JWT 实现无状态认证。用户登录后由认证服务基于 RSA256 私钥签发 Access Token 和 Refresh Token，其中 Access Token 用于接口访问，Refresh Token 通过 Redis 保存 jti 白名单实现主动撤销和 Token Rotation。请求进入系统后，由 BearerTokenAuthenticationFilter 提取 Bearer Token，JwtDecoder 使用公钥完成验签和解析，将认证信息存入 SecurityContext，最终通过 @AuthenticationPrincipal 注入 Controller，实现安全访问。