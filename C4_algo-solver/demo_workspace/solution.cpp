#include <bits/stdc++.h>
using namespace std;
// solution.cpp — 两数之和（哈希表，O(n)）· 供提交到 OJ 的版本
int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n;
    cin >> n;
    vector<long long> a(n);
    for (int i = 0; i < n; i++) cin >> a[i];
    long long target;
    cin >> target;
    unordered_map<long long, int> pos;
    for (int i = 0; i < n; i++) {
        long long need = target - a[i];
        if (pos.count(need)) {
            cout << pos[need] << " " << i << "\n";
            return 0;
        }
        pos[a[i]] = i;
    }
    return 0;
}
