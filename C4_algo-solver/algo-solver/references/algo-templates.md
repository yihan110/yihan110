# 算法模板（Algo Templates）

Step 2/3 可复用的代码骨架。按需复制到 `solution.cpp` / `solution.py` 中修改。
所有模板均遵循 ACM 模式（纯 stdin/stdout）。

---

## 0. C++ 快速输入输出骨架（每个 C++ 题解都先贴这段）

```cpp
#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    // 读入 n
    int n;
    cin >> n;
    // 处理
    // 输出
    return 0;
}
```

> 备注：`bits/stdc++.h` 是 GNU 扩展，PAT / 牛客 / 洛谷 / Codeforces 均支持；若遇不支持的环境，可替换为具体头文件。

---

## 1. 二分查找（标准库）

```cpp
// lower_bound: 第一个 >= x 的下标
auto it = lower_bound(v.begin(), v.end(), x);
// upper_bound: 第一个 > x 的下标
auto it2 = upper_bound(v.begin(), v.end(), x);
long long idx = it - v.begin();
```

```python
import bisect
idx = bisect.bisect_left(v, x)   # 第一个 >= x
idx2 = bisect.bisect_right(v, x) # 第一个 > x
```

---

## 2. 前缀和（一维）

```cpp
vector<long long> pre(n + 1, 0);
for (int i = 1; i <= n; i++) pre[i] = pre[i-1] + a[i];
// 区间 [l, r] 和
long long sum = pre[r] - pre[l-1];
```

---

## 3. 滑动窗口 / 双指针（找满足条件的连续子数组）

```cpp
int l = 0, ans = 0;
unordered_map<int,int> cnt;
for (int r = 0; r < n; r++) {
    cnt[a[r]]++;
    while (cnt.size() > k) { cnt[a[l]]--; if (!cnt[a[l]]) cnt.erase(a[l]); l++; }
    ans = max(ans, r - l + 1);
}
```

---

## 4. 并查集（DSU）

```cpp
vector<int> fa;
int find(int x) { return fa[x] == x ? x : fa[x] = find(fa[x]); }
void merge(int a, int b) { a = find(a); b = find(b); if (a != b) fa[a] = b; }
// 初始化
for (int i = 0; i <= n; i++) fa.push_back(i);
```

```python
fa = list(range(n+1))
def find(x):
    while fa[x] != x:
        fa[x] = fa[fa[x]]
        x = fa[x]
    return x
def merge(a, b):
    a, b = find(a), find(b)
    if a != b: fa[a] = b
```

---

## 5. 快速幂（含取模）

```cpp
long long qpow(long long a, long long b, long long mod) {
    long long r = 1;
    while (b) {
        if (b & 1) r = r * a % mod;
        a = a * a % mod;
        b >>= 1;
    }
    return r;
}
```

---

## 6. 线性筛素数

```cpp
vector<int> primes;
vector<bool> isp(n + 1, true);
for (int i = 2; i <= n; i++) {
    if (isp[i]) primes.push_back(i);
    for (int p : primes) {
        if (1LL * i * p > n) break;
        isp[i * p] = false;
        if (i % p == 0) break;
    }
}
```

---

## 7. 单调栈（下一个更大元素）

```cpp
vector<int> nge(n, -1);
stack<int> st;
for (int i = n - 1; i >= 0; i--) {
    while (!st.empty() && a[st.top()] <= a[i]) st.pop();
    if (!st.empty()) nge[i] = st.top();
    st.push(i);
}
```

---

## 8. Python 大整数 / 高精度

```python
# Python 原生支持任意大整数，无需手写高精度
print(pow(2, 1000))
```

---

## 9. 多组输入直到 EOF

```cpp
int n;
while (cin >> n) {
    // 处理每组
}
```

```python
import sys
for line in sys.stdin:
    n = int(line.strip())
    # 处理每组
```

---

## 10. 浮点数输出精度

```cpp
cout << fixed << setprecision(6) << ans << "\n";
```

```python
print(f"{ans:.6f}")
```

---

> 维护提示：需要新模板时，直接在此文件追加小节即可，主 SKILL.md 工作流无需改动。
