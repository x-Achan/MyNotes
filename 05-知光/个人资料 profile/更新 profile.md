
# 一、请求和响应

1. profile更新：ProfilePatchRequest
```java
@Size(min = 1, max = 64, message = "昵称长度需在 1-64 之间") String nickname,  
@Size(max = 512, message = "个人描述长度不能超过 512") String bio,  
@Pattern(regexp = "(?i)MALE|FEMALE|OTHER|UNKNOWN", message = "性别取值为 MALE/FEMALE/OTHER/UNKNOWN") String gender,  
@PastOrPresent(message = "生日不能晚于今天") LocalDate birthday,  
@Pattern(regexp = "^[a-zA-Z0-9_]{4,32}$", message = "知光号仅支持字母、数字、下划线，长度 4-32") String zgId,  
@Size(max = 128, message = "学校名称长度不能超过 128") String school,  
String tagJson
```

>注意，这里存在请求参数都为空的情况

2. 响应：返回更新后的用户信息
```java
public record ProfileResponse(  
        Long id,  
        String nickname,  
        String avatar,   //头像
        String bio,  
        String zgId,  
        String gender,  
        LocalDate birthday,  
        String school,  
        String phone,  
        String email,  
        String tagJson  
) {}
```

# 二、过程

1. 更新 profile





2. 更新 avatar



查询 zg_id 是否重复，排除自己

```xml
<select id="existsByZgIdExceptId" resultType="boolean">  
    SELECT EXISTS(  
    SELECT 1  
    FROM users  
    WHERE zg_id = #{zgId}  
    AND id != #{excludeId}  
    )  
</select>
```

更新 profile，动态SQL
```xml
<update id="updateProfile" parameterType="com.zhiguang.user.domain.User">  
    UPDATE users  
    <set>  
        <if test="nickname != null">nickname = #{nickname},</if>  
        <if test="bio != null">bio = #{bio},</if>  
        <if test="gender != null">gender = #{gender},</if>  
        <if test="birthday != null">birthday = #{birthday},</if>  
        <if test="zgId != null">zg_id = #{zgId},</if>  
        <if test="school != null">school = #{school},</if>  
        <if test="avatar != null">avatar = #{avatar},</if>  
        <if test="tagsJson != null">tags_json = #{tagsJson},</if>  
        updated_at = NOW()  
    </set>  
    WHERE id = #{id}  
</update>
```

