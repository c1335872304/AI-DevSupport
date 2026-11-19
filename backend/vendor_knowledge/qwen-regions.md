# Qwen / 阿里云百炼：地域说明

厂商：Alibaba Cloud；产品范围：Qwen API；核对日期：2026-10-19。
官方来源：[选择地域、服务部署范围和接入域名](https://help.aliyun.com/zh/model-studio/regions)。
内容类型：官方正文快照；保留原文与示例，非摘要。核对日期不等于规则生效日。
资料仅用于对应厂商规则检索，本地业务工具不代表厂商生产账户核查。

---

# 选择地域、服务部署范围和接入域名

> 调用百炼前先选择 地域 、 服务部署范围、接入域名：

<meta property="og:title" content="选择地域、服务部署范围和接入域名" />

## 地域概述 <span id="h2-region-overview" />

地域决定<strong>接入点和数据存储位置</strong>，就近选择可降低延迟。

- 服务部署范围：决定<strong>推理执行位置</strong>，有数据合规需求选择特定地理边界的部署范围，无合规需求选择全球部署范围（推理资源池更大）；
- 接入域名：影响<strong>并发上限、超时等服务保障</strong>，各地域具有独立的接入域名。

一次完整的模型调用流程如下：

1. 应用经接入域名将请求发送到所选<strong>地域</strong>，请求数据存于该地域；
2. 接入地域将请求转发至<strong>服务部署范围</strong>内的推理节点完成计算（传输全程加密）；
3. 推理结果回到接入地域存储，再响应给应用（用户静态数据始终存于所选地域）。

<img src="https://help-static-aliyun-doc.aliyuncs.com/assets/img/zh-CN/9377607871/CAEQchiBgICkyp3I_hkiIGFjZmY5ZThjZWM2MzRkMmJhNTk5NWVmYTkwMWY3ZGI07466796_20260515102254.505.svg" alt="image" />

## 选择地域和服务部署范围 <span id="h2_recommend" />

不同地域支持不同的服务部署范围，百炼将在所选范围内进行推理调度。例如美国（弗吉尼亚）支持全球和美国，德国（法兰克福）支持全球和欧盟等。各地域支持的服务部署范围和接入方式，请参见[华北2（北京）](/zh/model-studio/beijing-access-information)、[新加坡](/zh/model-studio/singapore-regional-access-information)、[美国（弗吉尼亚）](/zh/model-studio/usa-virginia-global)、[德国（法兰克福）](/zh/model-studio/germany-frankfurt-global)、[日本（东京）](/zh/model-studio/japan-tokyo-global)、[中国香港](/zh/model-studio/hong-kong-china-global)。

## 选择接入域名 <span id="39f66b0187bsx" />

百炼为模型推理 API 提供业务空间专属、DashScope 和试用三种接入域名，适用于从试用体验到企业级生产的不同场景。推荐使用<strong>业务空间专属域名</strong>，各域名的核心差异如下：

<table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}>
  <colgroup>
    <col style={{ width: "12.49%" }} />

    <col style={{ width: "33.81%" }} />

    <col style={{ width: "28.86%" }} />

    <col style={{ width: "24.84%" }} />
  </colgroup>

  <thead>
    <tr>
      <th style={{ verticalAlign: "top" }}>
        <strong>对比项</strong>
      </th>

      <th style={{ verticalAlign: "top" }}>
        <strong>业务空间专属域名（推荐）</strong>
      </th>

      <th style={{ verticalAlign: "top" }}>
        <strong>DashScope 域名（现有域名）</strong>
      </th>

      <th style={{ verticalAlign: "top" }}>
        <strong>试用域名</strong>
      </th>
    </tr>
  </thead>

  <tbody>
    <tr>
      <td style={{ verticalAlign: "top" }}>
        <strong>域名格式</strong>
      </td>

      <td style={{ verticalAlign: "top" }}>
        `{WorkspaceId}.{region}.maas.aliyuncs.com`
      </td>

      <td style={{ verticalAlign: "top" }}>
        `dashscope.aliyuncs.com`

        > 以华北2（北京）地域为例
      </td>

      <td style={{ verticalAlign: "top" }}>
        `trial.{region}.maas.aliyuncs.com`
      </td>
    </tr>

    <tr>
      <td style={{ verticalAlign: "top" }}>
        <strong>适用场景</strong>
      </td>

      <td style={{ verticalAlign: "top" }}>
        推荐在生产环境中使用，具备更高并发承载能力与网络隔离性，保障大流量场景下的稳定、低延迟访问体验。
      </td>

      <td style={{ verticalAlign: "top" }}>
        存量业务兼容，建议[迁移至业务空间专属域名](/zh/model-studio/regions#h2_migrate_domain)。DashScope 域名（dashscope.aliyuncs.com）自2026年9月30日起不再支持新特性。
      </td>

      <td style={{ verticalAlign: "top" }}>
        快速体验、功能验证，不建议用于生产环境。
      </td>
    </tr>

    <tr>
      <td style={{ verticalAlign: "top" }}>
        <strong>鉴权方式</strong>
      </td>

      <td style={{ verticalAlign: "top" }}>
        仅访问当前业务空间
      </td>

      <td style={{ verticalAlign: "top" }}>
        可访问所有业务空间
      </td>

      <td style={{ verticalAlign: "top" }}>
        可访问所有业务空间
      </td>
    </tr>

    <tr>
      <td style={{ verticalAlign: "top" }}>
        <strong>限流额度</strong>
      </td>

      <td style={{ verticalAlign: "top" }}>
        RPM、TPM 按模型区分，主账号维度合并计算
      </td>

      <td style={{ verticalAlign: "top" }}>
        RPM、TPM 按模型区分，主账号维度合并计算
      </td>

      <td style={{ verticalAlign: "top" }}>
        RPM 为1000（主账号维度），TPM 按模型区分
      </td>
    </tr>

    <tr>
      <td style={{ verticalAlign: "top" }}>
        <strong>请求超时</strong>
      </td>

      <td style={{ verticalAlign: "top" }}>
        3600 秒
      </td>

      <td style={{ verticalAlign: "top" }}>
        600 秒
      </td>

      <td style={{ verticalAlign: "top" }}>
        600 秒
      </td>
    </tr>

    <tr>
      <td style={{ verticalAlign: "top" }}>
        <strong>协议支持</strong>
      </td>

      <td style={{ verticalAlign: "top" }}>
        HTTP、SSE、<Link href="/zh/model-studio/realtime-websocket-overview">WebSocket</Link>、<Link href="/zh/model-studio/realtime-webrtc-access">WebRTC</Link>、<Link href="/zh/model-studio/realtime-aoq-access">AOQ</Link>（AI over QUIC）
      </td>

      <td style={{ verticalAlign: "top" }}>
        HTTP、SSE、<Link href="/zh/model-studio/realtime-websocket-overview">WebSocket</Link>
      </td>

      <td style={{ verticalAlign: "top" }}>
        HTTP、SSE
      </td>
    </tr>

    <tr>
      <td style={{ verticalAlign: "top" }}>
        <strong>SLA</strong>
      </td>

      <td style={{ verticalAlign: "top" }}>
        99.9%
      </td>

      <td style={{ verticalAlign: "top" }}>
        99.9%
      </td>

      <td style={{ verticalAlign: "top" }}>
        不提供
      </td>
    </tr>
  </tbody>
</table>

## 各地域接入信息 <span id="h2_cc92e61c" />

每个地域有独立的接入域名、API Key 和模型列表，<strong>不能跨地域混用</strong>。

<table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}><colgroup><col style={{ width: "8%" }} /><col style={{ width: "10%" }} /><col style={{ width: "26%" }} /><col style={{ width: "20%" }} /><col style={{ width: "22%" }} /><col style={{ width: "7%" }} /><col style={{ width: "7%" }} /></colgroup><thead><tr><th style={{ verticalAlign: "top" }}><p><strong>地域</strong></p></th><th style={{ verticalAlign: "top" }}><p><strong>地域ID</strong></p></th><th style={{ verticalAlign: "top" }}><p><strong>业务空间专属域名</strong></p></th><th style={{ verticalAlign: "top" }}><p><strong>DashScope 域名</strong></p></th><th style={{ verticalAlign: "top" }}><p><strong>试用域名</strong></p></th><th style={{ verticalAlign: "top" }}><p><strong>API Key 入口</strong></p></th><th style={{ verticalAlign: "top" }}><p><strong>模型列表</strong></p></th></tr></thead><tbody><tr><td style={{ verticalAlign: "top" }}><p>华北2（北京）</p></td><td style={{ verticalAlign: "top" }}><p><code>cn-beijing</code></p></td><td style={{ verticalAlign: "top" }}><p><code>\{WorkspaceId}.cn-beijing.maas.aliyuncs.com</code></p></td><td style={{ verticalAlign: "top" }}><p><code>dashscope.aliyuncs.com</code></p></td><td style={{ verticalAlign: "top" }}><p><code>trial.cn-beijing.maas.aliyuncs.com</code></p></td><td style={{ verticalAlign: "top" }}><p><a href="https://bailian.console.aliyun.com/cn-beijing/model/settings/api-key">API Key</a></p></td><td style={{ verticalAlign: "top" }}><p><a href="https://bailian.console.aliyun.com/cn-beijing/model/market">可用模型</a></p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>新加坡</p></td><td style={{ verticalAlign: "top" }}><p><code>ap-southeast-1</code></p></td><td style={{ verticalAlign: "top" }}><p><code>\{WorkspaceId}.ap-southeast-1.maas.aliyuncs.com</code></p></td><td style={{ verticalAlign: "top" }}><p><code>dashscope-intl.aliyuncs.com</code></p></td><td style={{ verticalAlign: "top" }}><p><code>trial.ap-southeast-1.maas.aliyuncs.com</code></p></td><td style={{ verticalAlign: "top" }}><p><a href="https://bailian.console.aliyun.com/ap-southeast-1/model/settings/api-key">API Key</a></p></td><td style={{ verticalAlign: "top" }}><p><a href="https://bailian.console.aliyun.com/ap-southeast-1/model/market">可用模型</a></p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>德国（法兰克福）</p></td><td style={{ verticalAlign: "top" }}><p><code>eu-central-1</code></p></td><td style={{ verticalAlign: "top" }}><p><code>\{WorkspaceId}.eu-central-1.maas.aliyuncs.com</code></p></td><td style={{ verticalAlign: "top" }}><p>不支持</p></td><td style={{ verticalAlign: "top" }}><p>暂不支持</p></td><td style={{ verticalAlign: "top" }}><p><a href="https://bailian.console.aliyun.com/eu-central-1/model/settings/api-key">API Key</a></p></td><td style={{ verticalAlign: "top" }}><p><a href="https://bailian.console.aliyun.com/eu-central-1/model/market">可用模型</a></p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>日本（东京）</p></td><td style={{ verticalAlign: "top" }}><p><code>ap-northeast-1</code></p></td><td style={{ verticalAlign: "top" }}><p><code>\{WorkspaceId}.ap-northeast-1.maas.aliyuncs.com</code></p></td><td style={{ verticalAlign: "top" }}><p>不支持</p></td><td style={{ verticalAlign: "top" }}><p>暂不支持</p></td><td style={{ verticalAlign: "top" }}><p><a href="https://bailian.console.aliyun.com/ap-northeast-1/model/settings/api-key">API Key</a></p></td><td style={{ verticalAlign: "top" }}><p><a href="https://bailian.console.aliyun.com/ap-northeast-1/model/market">可用模型</a></p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>中国香港</p></td><td style={{ verticalAlign: "top" }}><p><code>cn-hongkong</code></p></td><td style={{ verticalAlign: "top" }}><p><code>\{WorkspaceId}.cn-hongkong.maas.aliyuncs.com</code></p></td><td style={{ verticalAlign: "top" }}><p><code>cn-hongkong.dashscope.aliyuncs.com</code></p></td><td style={{ verticalAlign: "top" }}><p><code>trial.cn-hongkong.maas.aliyuncs.com</code></p></td><td style={{ verticalAlign: "top" }}><p><a href="https://bailian.console.aliyun.com/cn-hongkong/model/settings/api-key">API Key</a></p></td><td style={{ verticalAlign: "top" }}><p><a href="https://bailian.console.aliyun.com/cn-hongkong/model/market">可用模型</a></p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>美国（弗吉尼亚）</p></td><td style={{ verticalAlign: "top" }}><p><code>us-east-1</code></p></td><td style={{ verticalAlign: "top" }}><p><code>\{WorkspaceId}.us-east-1.maas.aliyuncs.com</code></p></td><td style={{ verticalAlign: "top" }}><p><code>dashscope-us.aliyuncs.com</code></p></td><td style={{ verticalAlign: "top" }}><p>暂不支持</p></td><td style={{ verticalAlign: "top" }}><p><a href="https://bailian.console.aliyun.com/us-east-1/model/settings/api-key">API Key</a></p></td><td style={{ verticalAlign: "top" }}><p><a href="https://bailian.console.aliyun.com/us-east-1/model/market">可用模型</a></p></td></tr></tbody></table>

- <strong>德国（法兰克福）、日本（东京）、中国香港、美国（弗吉尼亚）</strong>地域通过<strong>业务空间（Workspace）</strong>区分服务部署范围，开始调用前需前往业务空间管理页面创建业务空间并选择服务部署范围：[德国（法兰克福）](https://bailian.console.aliyun.com/eu-central-1/settings/workspace)（全球/欧盟）、[日本（东京）](https://bailian.console.aliyun.com/ap-northeast-1/settings/workspace)（全球/日本）、[中国香港](https://bailian.console.aliyun.com/cn-hongkong/settings/workspace)（全球/中国香港）、[美国（弗吉尼亚）](https://bailian.console.aliyun.com/us-east-1/settings/workspace)（全球/美国）。

<Note>
  美国（弗吉尼亚）地域的部署模式已升级。如果正在使用带 `-us` 后缀的模型，请尽快完成切换升级，详情请参见[升级公告](https://www.aliyun.com/notice/118646)。
</Note>

## 迁移至业务空间专属域名 <span id="h2_migrate_domain" />

从 DashScope 域名或试用域名迁移到业务空间专属域名只需两步，无需修改业务逻辑代码：

1. <strong>获取业务空间专属域名</strong>：

   - 方式一：在[API Key 创建](https://bailian.console.aliyun.com/cn-beijing/model/settings/api-key)后的弹窗中，复制 <strong>API Host</strong> 。
   - 方式二：在[业务空间管理](https://bailian.console.aliyun.com/cn-beijing/settings/workspace)页面，复制 <strong>API Host</strong> 列的内容。
2. <strong>替换 Base URL 中的域名</strong>：将原域名替换为业务空间专属域名。以华北2（北京）地域为例，`llm-xxx` 为业务空间 ID：

   - OpenAI 兼容接口：从 `https://dashscope.aliyuncs.com/compatible-mode/v1` 替换为 `https://llm-xxx.cn-beijing.maas.aliyuncs.com/compatible-mode/v1`
   - DashScope 接口：从 `https://dashscope.aliyuncs.com/api/v1` 替换为 `https://llm-xxx.cn-beijing.maas.aliyuncs.com/api/v1`
   - Anthropic 兼容接口：从 `https://dashscope.aliyuncs.com/apps/anthropic` 替换为 `https://llm-xxx.cn-beijing.maas.aliyuncs.com/apps/anthropic`

## 各地域功能支持 <span id="h2_acc79c7f" />

<table style={{ display: "table", tableLayout: "fixed", width: "100%", overflowWrap: "anywhere" }}><colgroup><col style={{ width: "22%" }} /><col style={{ width: "13%" }} /><col style={{ width: "13%" }} /><col style={{ width: "13%" }} /><col style={{ width: "13%" }} /><col style={{ width: "13%" }} /><col style={{ width: "13%" }} /></colgroup><thead><tr><th style={{ verticalAlign: "top" }}><p><strong>功能</strong></p></th><th style={{ verticalAlign: "top" }}><p><strong>华北2（北京）</strong></p></th><th style={{ verticalAlign: "top" }}><p><strong>新加坡</strong></p></th><th style={{ verticalAlign: "top" }}><p><strong>美国（弗吉尼亚）</strong></p></th><th style={{ verticalAlign: "top" }}><p><strong>中国香港</strong></p></th><th style={{ verticalAlign: "top" }}><p><strong>德国（法兰克福）</strong></p></th><th style={{ verticalAlign: "top" }}><p><strong>日本（东京）</strong></p></th></tr></thead><tbody><tr><td style={{ verticalAlign: "top" }}><p>实时推理</p></td><td style={{ verticalAlign: "top" }}><p>支持</p></td><td style={{ verticalAlign: "top" }}><p>支持</p></td><td style={{ verticalAlign: "top" }}><p>支持</p></td><td style={{ verticalAlign: "top" }}><p>支持</p></td><td style={{ verticalAlign: "top" }}><p>支持</p></td><td style={{ verticalAlign: "top" }}><p>支持</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>批量推理</p></td><td style={{ verticalAlign: "top" }}><p>支持</p></td><td style={{ verticalAlign: "top" }}><p>支持</p></td><td style={{ verticalAlign: "top" }}><p>不支持</p></td><td style={{ verticalAlign: "top" }}><p>不支持</p></td><td style={{ verticalAlign: "top" }}><p>不支持</p></td><td style={{ verticalAlign: "top" }}><p>不支持</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>模型体验</p></td><td style={{ verticalAlign: "top" }}><p>支持</p></td><td style={{ verticalAlign: "top" }}><p>支持</p></td><td style={{ verticalAlign: "top" }}><p>支持</p></td><td style={{ verticalAlign: "top" }}><p>支持</p></td><td style={{ verticalAlign: "top" }}><p>支持</p></td><td style={{ verticalAlign: "top" }}><p>支持</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>模型监控（普通）</p></td><td style={{ verticalAlign: "top" }}><p>支持</p></td><td style={{ verticalAlign: "top" }}><p>支持</p></td><td style={{ verticalAlign: "top" }}><p>支持</p></td><td style={{ verticalAlign: "top" }}><p>支持</p></td><td style={{ verticalAlign: "top" }}><p>支持</p></td><td style={{ verticalAlign: "top" }}><p>支持</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>模型监控（高级）</p></td><td style={{ verticalAlign: "top" }}><p>支持</p></td><td style={{ verticalAlign: "top" }}><p>支持</p></td><td style={{ verticalAlign: "top" }}><p>支持</p></td><td style={{ verticalAlign: "top" }}><p>不支持</p></td><td style={{ verticalAlign: "top" }}><p>不支持</p></td><td style={{ verticalAlign: "top" }}><p>不支持</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>模型告警</p></td><td style={{ verticalAlign: "top" }}><p>支持</p></td><td style={{ verticalAlign: "top" }}><p>支持</p></td><td style={{ verticalAlign: "top" }}><p>不支持</p></td><td style={{ verticalAlign: "top" }}><p>不支持</p></td><td style={{ verticalAlign: "top" }}><p>不支持</p></td><td style={{ verticalAlign: "top" }}><p>不支持</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>传输安全</p></td><td style={{ verticalAlign: "top" }}><p>支持</p></td><td style={{ verticalAlign: "top" }}><p>支持</p></td><td style={{ verticalAlign: "top" }}><p>支持</p></td><td style={{ verticalAlign: "top" }}><p>支持</p></td><td style={{ verticalAlign: "top" }}><p>支持</p></td><td style={{ verticalAlign: "top" }}><p>支持</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>权限管理</p></td><td style={{ verticalAlign: "top" }}><p>支持</p></td><td style={{ verticalAlign: "top" }}><p>支持</p></td><td style={{ verticalAlign: "top" }}><p>支持</p></td><td style={{ verticalAlign: "top" }}><p>支持</p></td><td style={{ verticalAlign: "top" }}><p>支持</p></td><td style={{ verticalAlign: "top" }}><p>支持</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>模型调优</p></td><td style={{ verticalAlign: "top" }}><p>支持</p></td><td style={{ verticalAlign: "top" }}><p>不支持</p></td><td style={{ verticalAlign: "top" }}><p>不支持</p></td><td style={{ verticalAlign: "top" }}><p>不支持</p></td><td style={{ verticalAlign: "top" }}><p>不支持</p></td><td style={{ verticalAlign: "top" }}><p>不支持</p></td></tr><tr><td style={{ verticalAlign: "top" }}><p>应用开发</p></td><td style={{ verticalAlign: "top" }}><p>支持</p></td><td style={{ verticalAlign: "top" }}><p>不支持</p></td><td style={{ verticalAlign: "top" }}><p>不支持</p></td><td style={{ verticalAlign: "top" }}><p>不支持</p></td><td style={{ verticalAlign: "top" }}><p>不支持</p></td><td style={{ verticalAlign: "top" }}><p>不支持</p></td></tr></tbody></table>

## 相关文档 <span id="h2_2caf88e3" />

- [通义千问 API 参考](/zh/model-studio/qwen-api-reference)
- [选择模型](/zh/model-studio/models) — 各地域模型及上下文长度
- [模型调用计费](/zh/model-studio/model-pricing) — 各地域价格
- [限流](/zh/model-studio/rate-limit)— RPM、TPM 限制
- [获取与配置 API Key](/zh/model-studio/get-api-key) — 创建和管理 Key
- [Base URL总览](/zh/model-studio/base-url) — 模型服务调用地址
- [Realtime API 协议选型](/zh/model-studio/realtime-api-overview#rtov-protocol-selection)
