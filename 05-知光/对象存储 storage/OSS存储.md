
# 一、使用配置

| 概念                | 你可以理解成              |
| ----------------- | ------------------- |
| `Bucket`          | OSS里的“总文件夹 / 存储桶”   |
| `ObjectKey`       | 某个文件在 Bucket 里的唯一名字 |
| `Endpoint`        | OSS服务器地址            |
| `AccessKeyId`     | 账号身份                |
| `AccessKeySecret` | 账号密码/密钥             |
| `publicDomain`    | 对外访问文件的域名           |

OssProperties.java

```java
@Data
@Component
@ConfigurationProperties(prefix = "oss")
public class OssProperties {

    private String endpoint;
    private String accessKeyId;
    private String accessKeySecret;
    private String bucket;
    private String publicDomain;
    private String folder = "avatars";
}
```

application.yml

```yaml
oss:  
  endpoint: oss-cn-beijing.aliyuncs.com  
  access-key-id: ${OSS_ACCESS_KEY_ID}
  access-key-secret: ${OSS_ACCESS_KEY_SECRET}
  bucket: zhiguangccy  
  public-domain:  
  folder: avatars
```

access-key-id 会自动映射 accessKeyId（这就是 Spring Boot 的 relaxed binding）

依赖
```xml
<!-- 阿里云 OSS SDK：对象存储直传/签名/上传下载 -->  
<dependency>  
    <groupId>com.aliyun.oss</groupId>  
    <artifactId>aliyun-sdk-oss</artifactId>  
    <version>3.17.3</version>  
</dependency>
```


# 二、方式1：后端直传（小文件上传）

客户端请求：用户id + file文件
后端响应给客户端：新的用户信息

>适合小文件上传，头像.png 为例

S1：接受用户 id 和 文件名
```java
public String uploadAvatar(long userId, MultipartFile file)
```
S2：上传之前确认 OSS 配置完整（防御性编程写法）
```java
ensureConfigured();
```
写法
```java
private void ensureConfigured() {  
    if (props.getEndpoint() == null   
			|| props.getAccessKeyId() == null   
			|| props.getAccessKeySecret() == null   
			|| props.getBucket() == null) {  
        throw new BusinessException(ErrorCode.BAD_REQUEST, "对象存储未配置");  
    }  
}
```

S3：拼接形成 OSS中的 ObjecKey
```java
String objectKey =
        props.getFolder() 
        + "/"
        + userId
        + "-"
        + Instant.now().toEpochMilli()
        + ext;
```

假设
```
folder = avatars
userId = 1
时间戳 = 1760000000000
ext = .png
```
最终的 key
```
avatars/1-1760000000000.png
```
S4：创建OSS客户端，需要：服务器、id、密码
```java
OSS client =
        new OSSClientBuilder().build(
                props.getEndpoint(),
                props.getAccessKeyId(),
                props.getAccessKeySecret()
        );
```
S5：创建 put 请求
```java
PutObjectRequest request =
        new PutObjectRequest(
                props.getBucket(), //桶
                objectKey,         //objectKey 文件名
                file.getInputStream() //文件内容
        );
```
S6：发送到阿里云OSS
```java
client.putObject(request);
```
返回URL
```java
return publicUrl(objectKey);
```
publicUrl负责将 objectKey 转换为 url
```java
private String publicUrl(String objectKey) {  
    if (props.getPublicDomain() != null && !props.getPublicDomain().isBlank()) {  
        return props.getPublicDomain().replaceAll("/$", "") + "/" + objectKey;  
    }  
    return "https://" + props.getBucket() + "." + props.getEndpoint() + "/" + objectKey;  
}
```
例如
```
avatars/1-1760000000000.png
      对应
https://cdn.zhiguang.com/avatars/1-1760000000000.png
```

以上传头像为例子，整个流程：
```
前端上传 MultipartFile
        ↓
Spring Boot接收
        ↓
生成 objectKey
        ↓
MultipartFile.getInputStream()
        ↓
OSS SDK
        ↓
OSS保存文件
        ↓
生成URL
        ↓
users.avatar保存URL
```

将url保存到user中，包装成响应返回给客户端

# 三、方式2：预签名+前端直传（大文件上传）

客户端请求：场景sence（文章/图片） + postId知文id + 文件类型 + 文件扩展名
服务器返回给前端：objectKey + putUrl + headers +expiresIn，这些信息主要是为了让前端能狗上传文件

对于大文件（知文），不适合通过后端上产，所以采用预签名url，前端负责上传

>预签名 URL：后端给前端开一张“临时上传许可证”

后端用自己的 AccessKey，生成一个10分钟有效的URL,前端拿到这个URL，在规定时间内，向规定objectKey，执行规定操作PUT

预签名完整链路，以知文为例：

S1：客户端先：
```
POST /api/v1/storage/presign
```

预签名请求 StoragePresignRequest：
```java
public record StoragePresignRequest(  
        @NotBlank String scene, // knowpost_content | knowpost_image  
        @NotBlank String postId, // 字符串避免前端精度丢失  
        @NotBlank String contentType,  // 文件类型
        String ext  //扩展名
) {}
```
例如：
```
{
    "scene": "knowpost_image",
    "postId": "10001",
    "contentType": "image/png",
    "ext": "png"
}
```

S2：重要：后端在发预签名 URL 之前先做权限校验（确保发送知文的人和当前登录用户是同一个人）
```java
// 权限校验：postId 必须属于当前用户  
long userId = jwtService.extractUserId(jwt);
KnowPost post = knowPostMapper.findById(postId);  

if (post == null  
        || post.getCreatorId() == null  
        || post.getCreatorId() != userId) {  
    throw new BusinessException(ErrorCode.BAD_REQUEST, "草稿不存在或无权限");  
}
```

S3：取变量生成ObjectKey，都是字符串处理，具体省略
S4：生成 put url，过期时间自己定，在generatePresignedPutUrl中，主要通过OSS提供的API来生成预签名

```java
int expiresIn = 600; // 10 分钟  
String putUrl = ossStorageService
					.generatePresignedPutUrl(
						objectKey, 
						request.contentType(), 
						expiresIn);
```

S4.1：确认配置，创建OSS客户端
```java
ensureConfigured();  
OSS client = new OSSClientBuilder()  
        .build(props.getEndpoint(),   
                props.getAccessKeyId(),   
                props.getAccessKeySecret());'
```

S4.2：调用OSS 提供的 API 实现
```java
// 有效期
Date expiration = new Date(System.currentTimeMillis() + expiresInSeconds * 1000L);  
//API:生成预签名请求
GeneratePresignedUrlRequest request = new GeneratePresignedUrlRequest(
											props.getBucket(), 
											objectKey, 
											HttpMethod.PUT);  

// API：设置有效期 & 文件类型											
request.setExpiration(expiration);  
if (contentType != null && !contentType.isBlank()) {  
    request.setContentType(contentType);  
} 
// API:根据请求生成 put url
URL url = client.generatePresignedUrl(request);  
//返回字符串
return url.toString();
```

S5：返回 StoragePresignResponse 响应
```java
return new StoragePresignResponse(objectKey, putUrl, headers, expiresIn);
```


预签名返回给前端的响应
```java
public record StoragePresignResponse(  
        String objectKey,  // 文件在OSS中的路径 objectKey
        String putUrl,     // 前端直传用的 put url
        Map<String, String> headers,  // 上传时必须带的请求头
        int expiresIn     // url 有效期
) {}
```

S6：客户端收到，上传文件到 OSS上
```json
{
    "objectKey": "posts/10001/images/20261009/abc123.png",
    "putUrl": "https://......Signature=xxx",
    "headers": {
        "Content-Type": "image/png"
    },
    "expiresIn": 600
}
```

整个后端流程：
```
JWT取得userId
↓
查询KnowPost
↓
确认这个post属于当前用户
↓
生成objectKey
↓
生成Presigned PUT URL
↓
返回客户端
```
