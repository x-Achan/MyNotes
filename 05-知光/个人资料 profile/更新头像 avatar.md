
# 请求

```java
@PostMapping("/avatar")  
public ProfileResponse uploadAvatar(@AuthenticationPrincipal Jwt jwt,  
                                    @RequestPart("file") MultipartFile file) {  
    long userId = jwtService.extractUserId(jwt);  
    String url = ossStorageService.uploadAvatar(userId, file);  
  
    return profileService.updateAvatar(userId, url);  
}
```

从 multipart里找 part 名 "file" → 包装成 MultipartFile → 注入 file
```java
@RequestPart("file") MultipartFile file
```

| 部分                  | 含义                                 |
| ------------------- | ---------------------------------- |
| **`@RequestPart`**  | 从 `multipart/form-data` 的某个 part 取 |
| **`"file"`**        | part 名字（前端表单里字段名必须是 `file`）        |
| **`MultipartFile`** | Spring 的文件封装类                      |

文件存 OSS，数据库存 URL
