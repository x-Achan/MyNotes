想要一个完全干净的新 commit 历史，常见做法是：创建一个没有历史的新分支（orphan），重新提交，然后让旧分支失去引用

```bash
git switch --orphan clean-main
```
创建一个没有历史的新分支 clean-main，并切换过去

清空暂存区
```bash
# 把暂存区恢复成 HEAD 对应版本
git restore --staged .

# 从暂存区移除所有文件（不是删除文件）
git rm -r --cached .
```