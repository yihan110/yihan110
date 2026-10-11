# ZhaoLei note-organizer 处理脚本

```python
import os

def organize(path):
    # 读取笔记并生成摘要
    text = open(path, encoding="utf-8").read()
    return text[:200]
```
