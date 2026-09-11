想要一个完全干净的新 commit 历史，常见做法是：创建一个没有历史的新分支（orphan），重新提交，然后让旧分支失去引用

```bash
git switch --orphan clean-main
```
创建一个没有历史的新分支 clean-main，并切换过去

>普通branch基于已有commit创建，共享历史；orphan创建没有父commit的新历史，常用于清理历史或创建独立分支。

创建一个和新的分支（指针）和当前分支共享历史
```bash
git branch dev # 用的更多，开发新功能/修复bug

git switch dev
```

清空暂存区
```bash
# 把暂存区恢复成 HEAD 对应版本
git restore --staged .

# 从暂存区移除所有文件（不是删除文件）
git rm -r --cached .
```

加上--cached，就是让 git 删除该文件（忽略），但是本地还在

让 git 停止跟踪已经提交的文件
```bash
# 停止跟踪某个文件的命令
git rm --cached 文件或目录

git rm -r --cached .obsidian

# 查看忽略的文件
git status --ignored
```
解释：
```
rm
删除

-r
递归目录

--cached
只删除Git管理

不删除本地文件
```

分支只是一个指向 commit 的指针



## 版本管理
1. `git restore`：撤销工作区/暂存区修改  
撤销工作区修改
```bash
git restore User.java
```

暂存区取消，文件回到工作区
```bash
git restore --staged 文件

git restore --staged User.java
```


2. `git reset`：移动 HEAD，调整版本状态  

三种：
soft
```bash
HEAD移动
保留暂存
```
mixed（删除commit，保留代码）
```bash
HEAD移动
清空暂存
保留文件
```
hard
```bash
HEAD移动
删除修改
```


3.  ==revert==
==`git revert`：创建一个新的反向 commit 撤销历史==
==revert 不删除历史，而是创建一个新的反向 commit（企业最推荐）==
```bash
A
|
B
|
C
|
C'
```


## 合并与冲突

- merge

- merge冲突




main代表生产稳定代码，直接开发容易引入未测试代码。通常通过feature分支开发，测试完成后合并到develop，再发布到main

Git 企业分支开发流程总结

企业分支模型
```bash
                 main
                  |
              (上线代码)
                  |
              develop
             /       \
            /         \
 feature/login     feature/order
```

```bash
拉取代码

↓

切换 develop

↓

git pull 更新代码

↓

创建 feature 分支

↓

开发功能

↓

git add

↓

git commit

↓

git push feature 分支

↓

创建 Pull Request # Pull Request 是向团队申请：「请把我的分支代码合并到目标分支」

↓

Code Review

↓

merge 到 develop

↓

删除 feature 分支

↓

版本稳定后发布到 main
```


merge 就是把一个分支的提交历史和代码变化合并到另一个分支
merge 和 rebase 区别？

>merge 是将两个分支历史合并，会产生新的 merge commit，保留完整分支结构；rebase 是将当前分支的提交重新应用到目标分支最新位置，会修改提交历史，使历史更加线性。

什么时候使用 rebase？

回答：

> 通常在个人开发分支同步主分支代码时使用 rebase，使提交历史保持整洁；不建议对已经共享的公共分支进行 rebase



