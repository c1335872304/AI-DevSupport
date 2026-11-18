# Qwen / 阿里云百炼：安装 SDK

厂商：Alibaba Cloud；产品范围：Qwen API；核对日期：2026-10-19。
官方来源：[安装SDK](https://help.aliyun.com/zh/model-studio/install-sdk)。
内容类型：官方正文快照；保留原文与示例，非摘要。核对日期不等于规则生效日。
资料仅用于对应厂商规则检索，本地业务工具不代表厂商生产账户核查。

---

# 安装SDK

> 您可以使用阿里云百炼官方的 DashScope SDK（支持 Python 和 Java），也可以通过 OpenAI 官方提供的多语言 SDK（如 Python、Node.js、Java、Go）来调用阿里云百炼的 OpenAI 兼容接口。

<meta property="og:title" content="安装SDK" />

<Note>
  如需通过 AOQ 调用 Realtime API 支持的实时语音或多模态模型，请参见[AOQ SDK 下载](/zh/model-studio/realtime-sdk-download)。支持的模型及协议请参见[模型与协议支持范围](/zh/model-studio/realtime-api-overview#rtov-s02h2)。
</Note>

## 安装SDK <span id="75aa2ffbb2afo" />

<Tabs>
  <Tab title="Python">
    需要`python >= 3.9`。

    您可以通过OpenAI的Python SDK或DashScope的Python SDK来调用阿里云百炼平台上的模型。

    <Tabs>
      <Tab title="安装 OpenAI Python SDK">
        通过运行以下命令安装或升级 OpenAI Python SDK：

        ```bash
        # 如果运行失败，您可以将pip替换成pip3再运行
        pip install -U openai
        ```

        当终端出现`Successfully installed ... openai-x.x.x`的提示后，表示您已经成功安装OpenAI Python SDK。
      </Tab>

      <Tab title="安装 DashScope Python SDK">
        通过运行以下命令安装或升级 DashScope Python SDK：

        ```bash
        # 如果运行失败，您可以将pip替换成pip3再运行
        pip install -U dashscope
        ```

        当终端出现`Successfully installed ... dashscope-x.x.x`的提示后，表示您已经成功安装DashScope Python SDK。
      </Tab>
    </Tabs>
  </Tab>

  <Tab title="Java">
    <Tabs>
      <Tab title="DashScope">
        在项目中添加 [DashScope Java SDK](https://mvnrepository.com/artifact/com.alibaba/dashscope-sdk-java) 依赖，并将 `the-latest-version` 替换为最新的版本号。

        ### Gradle <span id="2a4ae7065aqql" />

        ```gradle
        dependencies {
            implementation group: 'com.alibaba', name: 'dashscope-sdk-java', version: 'the-latest-version'
        }
        ```

        ### Maven <span id="388a11b5c1ws1" />

        ```xml
        <dependency>
            <groupId>com.alibaba</groupId>
            <artifactId>dashscope-sdk-java</artifactId>
            <version>the-latest-version</version>
        </dependency>
        ```
      </Tab>

      <Tab title="OpenAI">
        在项目中添加 [OpenAI Java SDK](https://github.com/openai/openai-java?tab=readme-ov-file#openai-java-api-library) 依赖，并将 `the-latest-version` 替换为最新的版本号。（推荐设置为`3.5.0`）

        需要`Java8 或更高版本`。

        ### Gradle <span id="aabcb504d1u08" />

        ```gradle
        dependencies {
            implementation("com.openai:openai-java:the-latest-version")
        }
        ```

        ### Maven <span id="2d04e8a81bsn1" />

        ```xml
        <dependency>
          <groupId>com.openai</groupId>
          <artifactId>openai-java</artifactId>
          <version>the-latest-version</version>
        </dependency>
        ```
      </Tab>
    </Tabs>
  </Tab>

  <Tab title="Node.js">
    <Tabs>
      <Tab title="OpenAI">
        您可以在终端运行以下命令：

        ```bash
        npm install --save openai
        # 或者
        yarn add openai
        ```

        <Note>
          如果安装失败，您可以通过配置镜像源的方法来完成安装，如：

          ```bash
          npm config set registry https://registry.npmmirror.com/
          ```

          配置镜像源后，您可以重新运行安装SDK的命令。
        </Note>

        当终端出现`added xx package in xxs`的提示后，表示您已经成功安装OpenAI SDK。您可以使用`npm list openai`查询具体版本信息。
      </Tab>
    </Tabs>
  </Tab>

  <Tab title="Go">
    <Tabs>
      <Tab title="OpenAI">
        OpenAI 提供了[Go 语言的 SDK](https://github.com/openai/openai-go#openai-go-api-library)（需要 `Go 1.22+`），您可以在项目目录下通过以下命令来安装：

        ```go
        go get 'github.com/openai/openai-go/v3'
        ```

        或者设置固定的版本进行安装：

        ```go
        go get -u 'github.com/openai/openai-go/v3@v3.8.1'
        ```

        > 如访问服务器超时，可设置阿里云镜像代理：`go env -w GOPROXY=https://mirrors.aliyun.com/goproxy/,direct`

        在代码中使用以下命令进行导入：

        ```bash
        import (
        	"github.com/openai/openai-go/v3" // imported as openai
        )
        ```
      </Tab>
    </Tabs>
  </Tab>
</Tabs>

## 后续步骤 <span id="1d2281f6d0inh" />

成功完成 SDK 的安装后，您可以：

- 查阅百炼控制台选择适合您业务场景的模型。
- 使用[文本生成模型](/zh/model-studio/qwen-api-reference)、[图像生成模型](/zh/model-studio/text-to-image-v2-api-reference)、[视频生成模型](/zh/model-studio/legacy-image-to-video-api-reference)、[语音合成模型](/zh/model-studio/cosyvoice-python-sdk)、[语音识别模型](/zh/model-studio/paraformer-real-time-speech-recognition-python-sdk)、[向量模型](/zh/model-studio/text-embedding-synchronous-api)、[排序模型](/zh/model-studio/text-rerank-api)开始构建您的应用。
- 了解 [与 OpenAI API 的兼容性详情](/zh/model-studio/compatibility-of-openai-with-dashscope)。
