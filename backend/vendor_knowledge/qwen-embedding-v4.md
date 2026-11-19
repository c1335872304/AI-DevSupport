# Qwen / 阿里云百炼：text-embedding-v4

厂商：Alibaba Cloud；产品范围：Qwen API；核对日期：2026-10-19。
官方来源：[text-embedding-v4](https://help.aliyun.com/zh/model-studio/text-embedding-v4)。
内容类型：官方正文快照；保留原文与示例，非摘要。核对日期不等于规则生效日。
资料仅用于对应厂商规则检索，本地业务工具不代表厂商生产账户核查。

---

# text-embedding-v4

> 通用文本向量V4版本，是通义实验室基于Qwen3训练的多语言文本统一向量模型，相较V3版本在文本检索、聚类、分类性能大幅提升；在MTEB多语言、中英、Code检索等评测任务上效果提升15%~40%；支持64~2048维用户自定义向量维度。

<meta property="og:title" content="text-embedding-v4" />

## 推理服务供应商 <span id="h-490b2834e6" />

`text-embedding-v4`模型的推理服务供应商为阿里云百炼。

## 模型能力 <span id="h-55c4216db8" />

<Tabs>
  <Tab title="华北2（北京）">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%" }}><colgroup><col style={{ width: "25%" }} /><col style={{ width: "25%" }} /><col style={{ width: "25%" }} /><col style={{ width: "25%" }} /></colgroup><thead><tr><th><p>能力项</p></th><th><p>支持情况</p></th><th><p>能力项</p></th><th><p>支持情况</p></th></tr></thead><tbody><tr><td><p>输入模态</p></td><td><p><strong>Text</strong></p></td><td><p>输出模态</p></td><td><p><strong>Text</strong></p></td></tr><tr><td><p>模型体验</p></td><td><p>支持</p></td><td><p>Function Calling</p></td><td><p>不支持</p></td></tr><tr><td><p>结构化输出</p></td><td><p>不支持</p></td><td><p>联网搜索</p></td><td><p>不支持</p></td></tr><tr><td><p>前缀续写</p></td><td><p>不支持</p></td><td><p>上下文缓存</p></td><td><p>不支持</p></td></tr><tr><td><p>批量推理</p></td><td><p>支持</p></td><td><p>模型调优</p></td><td><p>不支持</p></td></tr></tbody></table>
  </Tab>

  <Tab title="新加坡">
    部署范围：国际

    <table style={{ display: "table", tableLayout: "fixed", width: "100%" }}><colgroup><col style={{ width: "25%" }} /><col style={{ width: "25%" }} /><col style={{ width: "25%" }} /><col style={{ width: "25%" }} /></colgroup><thead><tr><th><p>能力项</p></th><th><p>支持情况</p></th><th><p>能力项</p></th><th><p>支持情况</p></th></tr></thead><tbody><tr><td><p>输入模态</p></td><td><p><strong>Text</strong></p></td><td><p>输出模态</p></td><td><p><strong>Text</strong></p></td></tr><tr><td><p>模型体验</p></td><td><p>支持</p></td><td><p>Function Calling</p></td><td><p>不支持</p></td></tr><tr><td><p>结构化输出</p></td><td><p>不支持</p></td><td><p>联网搜索</p></td><td><p>不支持</p></td></tr><tr><td><p>前缀续写</p></td><td><p>不支持</p></td><td><p>上下文缓存</p></td><td><p>不支持</p></td></tr><tr><td><p>批量推理</p></td><td><p>不支持</p></td><td><p>模型调优</p></td><td><p>不支持</p></td></tr></tbody></table>
  </Tab>

  <Tab title="中国香港">
    部署范围：中国香港

    <table style={{ display: "table", tableLayout: "fixed", width: "100%" }}><colgroup><col style={{ width: "25%" }} /><col style={{ width: "25%" }} /><col style={{ width: "25%" }} /><col style={{ width: "25%" }} /></colgroup><thead><tr><th><p>能力项</p></th><th><p>支持情况</p></th><th><p>能力项</p></th><th><p>支持情况</p></th></tr></thead><tbody><tr><td><p>输入模态</p></td><td><p><strong>Text</strong></p></td><td><p>输出模态</p></td><td><p><strong>Text</strong></p></td></tr><tr><td><p>模型体验</p></td><td><p>不支持</p></td><td><p>Function Calling</p></td><td><p>不支持</p></td></tr><tr><td><p>结构化输出</p></td><td><p>不支持</p></td><td><p>联网搜索</p></td><td><p>不支持</p></td></tr><tr><td><p>前缀续写</p></td><td><p>不支持</p></td><td><p>上下文缓存</p></td><td><p>不支持</p></td></tr><tr><td><p>批量推理</p></td><td><p>不支持</p></td><td><p>模型调优</p></td><td><p>不支持</p></td></tr></tbody></table>
  </Tab>
</Tabs>

## 上下文限制 <span id="h-8f47448b8d" />

<table style={{ display: "table", tableLayout: "fixed", width: "100%" }}><colgroup><col style={{ width: "25%" }} /><col style={{ width: "25%" }} /><col style={{ width: "25%" }} /><col style={{ width: "25%" }} /></colgroup><thead><tr><th><p>参数</p></th><th><p>值</p></th><th><p>参数</p></th><th><p>值</p></th></tr></thead><tbody><tr><td><p>最大输入长度</p></td><td><p>—</p></td><td><p>最大输出长度</p></td><td><p>—</p></td></tr><tr><td><p>上下文长度</p></td><td><p>—</p></td><td /><td /></tr></tbody></table>

## 模型价格 <span id="h-dcec269881" />

本文仅展示模型调用原价，不包含限时优惠等活动信息，请前往[百炼控制台](https://bailian.console.aliyun.com/cn-beijing/model/market)查看活动优惠。

<Tabs>
  <Tab title="华北2（北京）">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%" }}><colgroup><col style={{ width: "33.333333%" }} /><col style={{ width: "33.333333%" }} /><col style={{ width: "33.333333%" }} /></colgroup><thead><tr><th><p>计费项</p></th><th><p>价格（元）</p></th><th><p>单位</p></th></tr></thead><tbody><tr><td><p>向量输入（Batch File）</p></td><td><p>0.25</p></td><td><p>每百万tokens</p></td></tr><tr><td><p>文本输入</p></td><td><p>0.5</p></td><td><p>每百万tokens</p></td></tr></tbody></table>
  </Tab>

  <Tab title="新加坡">
    部署范围：国际

    <table style={{ display: "table", tableLayout: "fixed", width: "100%" }}><colgroup><col style={{ width: "33.333333%" }} /><col style={{ width: "33.333333%" }} /><col style={{ width: "33.333333%" }} /></colgroup><thead><tr><th><p>计费项</p></th><th><p>价格（元）</p></th><th><p>单位</p></th></tr></thead><tbody><tr><td><p>文本输入</p></td><td><p>0.514</p></td><td><p>每百万tokens</p></td></tr></tbody></table>
  </Tab>
</Tabs>

## 限流 <span id="h-fe52fcb451" />

<Tabs>
  <Tab title="华北2（北京）">
    <table style={{ display: "table", tableLayout: "fixed", width: "100%" }}><colgroup><col style={{ width: "50%" }} /><col style={{ width: "50%" }} /></colgroup><thead><tr><th><p>参数</p></th><th><p>值</p></th></tr></thead><tbody><tr><td><p>RPM（每分钟请求数）</p></td><td><p>1800</p></td></tr><tr><td><p>TPM（每分钟tokens）</p></td><td><p>1,200,000</p></td></tr></tbody></table>
  </Tab>

  <Tab title="新加坡">
    部署范围：国际

    <table style={{ display: "table", tableLayout: "fixed", width: "100%" }}><colgroup><col style={{ width: "50%" }} /><col style={{ width: "50%" }} /></colgroup><thead><tr><th><p>参数</p></th><th><p>值</p></th></tr></thead><tbody><tr><td><p>RPM（每分钟请求数）</p></td><td><p>1800</p></td></tr><tr><td><p>TPM（每分钟tokens）</p></td><td><p>1,000,000</p></td></tr></tbody></table>
  </Tab>

  <Tab title="中国香港">
    部署范围：中国香港

    <table style={{ display: "table", tableLayout: "fixed", width: "100%" }}><colgroup><col style={{ width: "50%" }} /><col style={{ width: "50%" }} /></colgroup><thead><tr><th><p>参数</p></th><th><p>值</p></th></tr></thead><tbody><tr><td><p>RPM（每分钟请求数）</p></td><td><p>1800</p></td></tr><tr><td><p>TPM（每分钟tokens）</p></td><td><p>1,200,000</p></td></tr></tbody></table>
  </Tab>
</Tabs>
