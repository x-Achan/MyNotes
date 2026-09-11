
MySQL启动服务
```mysql
net start masql80 //启动

net stop mysql80  //停止服务
```

MySQL客户端连接
- MySQL自带的CLI
- cmd 终端命令：mysql -u root -p 

**SQL分类**

1. DDL-数据库操作
```mysql
# 查询所有数据库
show databases;
# 查询当前数据库
select database();
# 创建数据库
create database [if not exists] 数据库名 [default charset 字符集] [collate 排序规则];
# 删除数据库
drop database [if not exists] 数据库名;
# 使用/切换数据库
use 数据库名;
# 查询数据库中所有的表
show tables;
# 查询表结构
desc 表名;
# 查询指定表中的建表语句
show create table 表名;
# 创建表操作
create table 表名(
	字段1 类型 [comment 注释],
	字段2 类型 [comment 注释],
	字段3 类型 [comment 注释],
	.......
)[comment 表注释];
# 修改表名
alter table 表名 rename to 新表名
# 删除表（表中的数据一起删除）
drop table [if exists] 表名; 
truncate table 表名; # 删除指定表，并重新创建该表
# 添加字段
alter table 表名 add 字段名 类型 [comment 注释] [约束];
# 修改字段
alter table 表名 modify 字段名 类型;
alter table 表名 旧字段名 新字段名 类型 [comment 注释] [约束];
# 删除字段
alter table 表名 drop 字段名;
```

----

2. DML-数据操作语言
```mysql
# 1.给指定字段添加数据
insert into 表名(字段名1，字段名2，...) values(值1，值2，...);
# 2.给全部字段添加数据
insert into 表名 values(值1，值2，....);
# 3. 批量添加数据
insert into 表名(字段名1，字段名2，...) values(值1，值2，...)(值1，值2，...)...;
insert into 表名(值1，值2，...)(值1，值2，...)...;
# 4.修改数据
update 表名 set 字段名1 = 值1,字段名2 = 值2,....[where 条件];
# 5.删除数据，如果不加条件，将会删除表中所有数据
delete from 表名 [where 条件]
```
---

3. DQL-数据查询语言
```mysql
select
	字段列表
from
	表名列表
where
	条件列表
	
# 1.查询多个字段
select 字段1,字段2,字段3... from 表名;
select * from 表名;
# 2.设置别名
select 字段1 [AS 别名1],字段2 [AS 别名2] ... from 表名;
# 3.去除重复记录
select distinct 字段列表 from 表名;
# 4.模糊查询
select * from 表名 where 字段 like "%张%" # %张%解释：任意字符 + 张 + 任意字符
# 升序降序
select * from 表名 order by 字段 desc/asc # 降序/升序，默认升序，asc可以省略
# 分组查询
... group by 字段
```
----

4. DCL-数据控制语言（管理数据库的用户，控制访问权限）

```mysql
# 查询用户
use mysql;
select * from user;
# 创建用户
create user '用户名'@'主机名' identified '密码';
# 修改用户密码
alter user '用户名'@'主机名' identified with mysql_native_password by '新密码';
# 删除用户
drop user '用户名'@'主机名';
# 查询权限
show grants for '用户名'@'主机名';
# 授予权限
grant 权限列表 on 数据库.表名 to '用户名'@'主机名';
# 撤销权限
revoke 权限列表 on 数据库.表名 from '用户名'@'主机名';
```

>主机名可以用 % 号通配，这类SQL开发人员操作的比较少，主要是数据库管理人员使用
>授权时，数据库名和表名可以使用 * 进行通配，代表所有





MySQL 数据类型
- 数值类型
TINYINT SAMLLINT MEDIUMINT INT BIGINT FLOAT DOUBLE DECIMAL
例子：
```mysql
age TINYINT UNSIGNED # 无符号型
socore double(4,1) # 4代表整体长度，1代表小数位数
```

- 字符串类型
CHAR VARCHAR TINYBLOB TINYTEXT BLOB TEXT MEDIUMBLOB MEDIUMTEXT LONGBLOB LONGTEXT
例子：
```mysql
gender char(10)# 性别是男/女，定长，使用定长字符串
username varchar(10) # 用户名是变长的，使用变长字符串
```
char 性能高于 varchar

- 日期时间类型
DATE TIME  YEAR DTAETIME TIMESTAMP
例子：
```mysql
birthday date # 年-月-日
```

Logging results to /home/xukaiwen/chenchenyang/runs/pair_geomfix_cgm_history_e3_seed0
Starting training for 3 epochs...

