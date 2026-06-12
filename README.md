# A股行业板块热力图

基于大盘云图API的MA20站上率数据，自动生成可交互的行业热力图看板。

手机访问：[https://killuahong-hub.github.io/a-share-heatmap/](https://killuahong-hub.github.io/a-share-heatmap/)

## 功能

- 26个一级行业 × 30个交易日热力图，色阶/红绿直觉两种配色
- 5日动量排行、板块轮动信号（金叉/死叉）、市场均线叠加
- 行业下钻：点击查看86个二级行业明细
- 移动端自适应，手机浏览器直接打开

## 自动更新

GitHub Actions 每个交易日 16:30（北京时间）自动运行 Python 脚本获取最新数据，生成 HTML 并部署到 GitHub Pages。

## 数据来源

[大盘云图](https://sckd.dapanyuntu.com/) — MA20站上率（股价站上20日均线的个股占比）

## 文件结构

```
├── .github/workflows/deploy.yml   # GitHub Actions 定时部署
├── scripts/update_data.py         # 数据获取 + 聚合 + HTML生成
├── assets/template.html           # 响应式HTML模板
└── docs/index.html                # 生成的看板页面（自动部署）
```
