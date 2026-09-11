持久层框架

- @Mapper
 应用程序在运行时，会自动的为该接口创建一个实现类对象（代理对象），并且会自动将该实现类对象存入IOC容器
 - Select("SQL语句")

辅助配置
sql提示
配置myBatis的日志输出

数据库连接池是个容器，负责分配和管理数据库连接（Connection）
允许应用程序重复使用一个现有的数据库连接，而不是再重新建立一个
释放空闲时间超过最大空闲时间的连接，来避免因为没有释放连接而引起的数据库连接遗漏
资源重用
提升响应速度
避免连接遗漏

标准接口：DataSource
Hikari（SpringBoot默认连接池）

- 删除
@Delete("SQL语句")
```mysql
@Delete("delete from user where id = #{id}")
public void deleteByID(Integer id){
}
```
占位符传递参数传递
#{...}：占位符，执行时会被替换为 ？，生成预编译SQL

Mybatis执行DML语句时，由int类型的返回值，表示DML语句执行影响的记录数

- 新增
@Insert("SQL语句")
参数多的时候，传入太多参数不方便，将多个参数封装到一个对象中，更改为传入对象，在SQL中传入对象的属性名

- 修改
@Update(SQL语句)
同样传入对象...

- 查询
@Select(SQL语句)
 @Param 为接口的方法形参起名，用于多个形参时使用
基于官方骨架创建的springboot项目中，接口编译时会保留方法形参名，@Param注解 可以省略

- XML映射配置 
在MyBatis中，既可以通过注解配置SQL语句，也可以通过XML配置文件配置SQL语句
默认规则：
XML映射文件的名称与Mapper接口名称一致，并且将XML映射文件和Mapper接口放置在相同包下（同包同名）
XML映射文件的namespace属性为Mapper接口全限定名一致
XML映射文件中SQL语句的id与Mapper接口中的方法名一致，并保持返回类型一致

如何选择？简单的用注解方式，复杂的用XML

MyBatisX辅助插件

SpringBoot配置文件：yaml/yml
- 定义对象/Map集合
- 定义数组/List/Set集合