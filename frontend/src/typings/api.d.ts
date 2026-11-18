/**
 * Namespace Api
 *
 * All backend api type
 */
declare namespace Api {
  namespace Common {
    /** common params of paginating */
    interface PaginatingCommonParams {
      /** current page number */
      page?: number;
      number: number;
      /** page size */
      size?: number;
      /** total count */
      totalElements: number;
    }

    /** common params of paginating query list data */
    interface PaginatingQueryRecord<T = any> extends PaginatingCommonParams {
      data: T[];
      content: T[];
    }

    /** common search params of table */
    type CommonSearchParams = Pick<Common.PaginatingCommonParams, 'page' | 'size'>;
  }

  /**
   * namespace Auth
   *
   * backend api module: "auth"
   */
  namespace Auth {
    interface LoginToken {
      token: string;
      refreshToken: string;
    }

    interface UserInfo {
      id: number;
      username: string;
      role: 'USER' | 'SUPPORT' | 'ADMIN';
      orgTags: string[];
      primaryOrg: string;
    }
  }

  /**
   * namespace Route
   *
   * backend api module: "route"
   */
  namespace Route {
    type ElegantConstRoute = import('@elegant-router/types').ElegantConstRoute;

    interface MenuRoute extends ElegantConstRoute {
      id: string;
    }

    interface UserRoute {
      routes: MenuRoute[];
      home: import('@elegant-router/types').LastLevelRouteKey;
    }
  }

  namespace OrgTag {
    interface Item {
      tagId: string;
      name: string;
      description: string;
      parentTag: string | null;
      uploadMaxSizeBytes: number | null;
      uploadMaxSizeMb: number | null;
      children?: Item[];
    }

    type List = Common.PaginatingQueryRecord<Item>;

    type Details = Pick<Item, 'tagId' | 'name' | 'description'>;
    type Mine = {
      orgTags: string[];
      primaryOrg: string;
      orgTagDetails: Details[];
    };
  }

  namespace User {
    interface UsageQuota {
      enabled: boolean;
      usedTokens: number;
      limitTokens: number;
      remainingTokens: number;
      requestCount: number;
    }

    interface UsageSnapshot {
      day: string;
      chatRequestCount: number;
      llm: UsageQuota;
      embedding: UsageQuota;
    }

    interface TokenRecord {
      id: number;
      recordDate: string;
      tokenType: 'LLM' | 'EMBEDDING';
      changeType: 'INCREASE' | 'CONSUME';
      amount: number;
      balanceBefore: number | null;
      balanceAfter: number | null;
      reason: string;
      remark: string | null;
      requestCount: number;
      createdAt: string;
    }

    type SearchParams = CommonType.RecordNullable<
      Common.CommonSearchParams & {
        keyword: string;
        orgTag: string;
        status: number;
      }
    >;

    type Item = {
      userId: string;
      username: string;
      role?: Api.Auth.UserInfo['role'];
      status: number;
      orgTags: Pick<OrgTag.Item, 'tagId' | 'name'>[];
      primaryOrg: string;
      createdAt: string;
      usage: UsageSnapshot;
      chatUsage?: string;
      llmUsage?: string;
      embeddingUsage?: string;
    };

    type List = Common.PaginatingQueryRecord<Item>;
  }

  /**
   * namespace Recharge
   *
   * backend api module: "recharge"
   */
  namespace Recharge {
    /** 充值套餐 */
    interface Package {
      id: number;
      packageName: string;
      packagePrice: number; // 单位分
      packageDesc: string;
      packageBenefit: string;
      llmToken: number; // LLM token 数量
      embeddingToken: number; // Embedding token 数量
      enabled: boolean;
      createdAt: string;
      updatedAt: string;
    }

    /** 订单信息 */
    interface OrderInfo {
      outTradeNo: string;
      appId: string;
      prePayId: string;
      expireTime: number;
    }

    /** 充值订单 */
    interface Order {
      id: number;
      tradeNo: string;
      userId: string;
      packageId: number;
      amount: number; // 单位分
      llmToken: number; // LLM token 数量
      embeddingToken: number; // Embedding token 数量
      wxTransactionId: string;
      status: 'NOT_PAY' | 'PAYING' | 'SUCCEED' | 'FAIL' | 'CANCELLED';
      description: string;
      payTime: string | null;
      createdAt: string;
      updatedAt: string;
    }
  }

  namespace Admin {
    interface RateLimitPolicy {
      max: number;
      windowSeconds: number;
      enabled: boolean;
    }

    interface RateLimitSettings {
      register: RateLimitPolicy;
      login: RateLimitPolicy;
      chat: RateLimitPolicy;
    }

    interface ModelProviderItem {
      provider: string;
      displayName: string;
      apiStyle: string;
      apiBaseUrl: string;
      model: string;
      dimension: number | null;
      enabled: boolean;
      active: boolean;
      hasApiKey: boolean;
      maskedApiKey: string;
      apiKeyInput?: string;
    }

    interface ModelProviderScopeSettings {
      scope: 'llm' | 'embedding';
      activeProvider: string;
      providers: ModelProviderItem[];
    }

    interface ModelProviderSettings {
      llm: ModelProviderScopeSettings;
      embedding: ModelProviderScopeSettings;
    }

    interface ConnectivityTestResult {
      success: boolean;
      message: string;
      latencyMs: number;
    }

    interface UsageTrendPoint {
      day: string;
      chatRequestCount: number;
      llmUsedTokens: number;
      llmRequestCount: number;
      embeddingUsedTokens: number;
      embeddingRequestCount: number;
    }

    interface UsageRankingItem {
      userId: string;
      username: string;
      scope: 'llm' | 'embedding';
      usedTokens: number;
      limitTokens: number;
      remainingTokens: number;
      requestCount: number;
    }

    interface UsageAlert {
      level: 'critical' | 'warning';
      userId: string;
      username: string;
      scope: 'llm' | 'embedding';
      usedTokens: number;
      limitTokens: number;
      remainingTokens: number;
      requestCount: number;
      usageRatio: number;
      message: string;
    }

    interface UsageOverview {
      days: number;
      today: UsageTrendPoint;
      trends: UsageTrendPoint[];
      llmRankings: UsageRankingItem[];
      embeddingRankings: UsageRankingItem[];
      alerts: UsageAlert[];
    }
  }

  namespace Support {
    type HandoffStatus = 'OPEN' | 'IN_PROGRESS' | 'RESOLVED' | 'CLOSED';
    type HandoffPriority = 'LOW' | 'NORMAL' | 'HIGH' | 'URGENT';

    type SearchParams = CommonType.RecordNullable<
      Common.CommonSearchParams & {
        status: HandoffStatus;
        priority: HandoffPriority;
        category: string;
        keyword: string;
        userId: string;
      }
    >;

    interface HandoffListItem {
      handoffId: string;
      userId: string;
      username?: string | null;
      conversationId: string | null;
      generationId: string | null;
      category: string;
      priority: HandoffPriority;
      status: HandoffStatus;
      summary: string;
      requestedBy: string;
      assignedTo: string | null;
      createdAt: string;
      updatedAt: string;
    }

    interface HandoffDetail extends HandoffListItem {
      reason: string;
      resolutionNote: string | null;
    }

    interface HandoffStatistics {
      status: Partial<Record<HandoffStatus, number>>;
      priority: Partial<Record<HandoffPriority, number>>;
    }

    type HandoffList = Common.PaginatingQueryRecord<HandoffListItem> & {
      statistics: HandoffStatistics;
    };
  }

  namespace KnowledgeBase {
    interface SearchParams {
      userId: string;
      query: string;
      topK: number;
    }

    interface SearchResult {
      fileMd5: string;
      chunkId: number;
      textContent: string;
      score: number;
      fileName: string;
    }

    interface UploadState {
      tasks: UploadTask[];
      activeUploads: Set<string>; // 当前正在上传的任务ID
    }

    interface KnowledgeMetadata {
      category?: string | null;
      product?: string | null;
      region?: string | null;
      channel?: string | null;
      effective_date?: string | null;
      version?: string | null;
      error_code?: string | null;
      plan?: string | null;
    }

    interface Form {
      orgTag: string | null;
      orgTagName: string | null;
      uploadMaxSizeBytes?: number | null;
      uploadMaxSizeMb?: number | null;
      isPublic: boolean;
      knowledgeMetadata: KnowledgeMetadata;
      fileList: import('naive-ui').UploadFileInfo[];
    }

    interface UploadTask {
      id?: number;
      file: File;
      chunk: Blob | null;
      fileMd5: string;
      chunkIndex: number;
      totalSize: number;
      fileName: string;
      userId?: string;
      orgTag: string | null;
      orgTagName?: string | null;
      public: boolean;
      isPublic: boolean;
      uploadedChunks: number[];
      progress: number;
      status: UploadStatus;
      estimatedEmbeddingTokens?: number;
      estimatedChunkCount?: number;
      actualEmbeddingTokens?: number;
      actualChunkCount?: number;
      vectorizationStatus?: 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED' | null;
      vectorizationErrorMessage?: string | null;
      activeVectorVersion?: string | null;
      activeIndexAvailable?: boolean;
      knowledgeMetadata?: KnowledgeMetadata;
      createdAt?: string;
      mergedAt?: string;
      requestIds?: string[]; // 请求ID，用于取消上传
    }
    type List = Common.PaginatingQueryRecord<UploadTask>;

    type Merge = Pick<UploadTask, 'fileMd5' | 'fileName'>;

    interface Progress {
      uploaded: number[];
      progress: number;
      totalChunks: number;
    }

    interface MergeResult {
      objectUrl: string;
      estimatedEmbeddingTokens?: number;
      estimatedChunkCount?: number;
    }
  }

  namespace Chat {
    type GenerationStatus = 'STREAMING' | 'COMPLETED' | 'FAILED' | 'CANCELLED';

    interface ReferenceEvidence {
      citationId?: string | null;
      indexVersion?: string | null;
      fileMd5: string;
      fileName: string;
      pageNumber?: number | null;
      anchorText?: string | null;
      retrievalMode?: 'HYBRID' | 'TEXT_ONLY' | null;
      retrievalLabel?: string | null;
      retrievalQuery?: string | null;
      matchedChunkText?: string | null;
      evidenceSnippet?: string | null;
      score?: number | null;
      chunkId?: number | null;
    }

    interface Input {
      message: string;
      conversationId?: string;
    }

    interface Output {
      chunk: string;
    }

    interface AgentToolEvent {
      id?: string;
      tool: string;
      status: 'executing' | 'success' | 'failed';
      timestamp?: number;
      durationMs?: number;
      resultStatus?: 'SUCCESS' | 'ERROR' | 'TIMEOUT' | 'DENIED' | 'CANCELLED';
      error?: string | null;
      agentStep?: number;
      agent?: string | null;
      skill?: string | null;
    }

    interface SkillTrace {
      question?: string;
      initialSkills?: string[];
      activeSkills?: string[];
      dynamicActivations?: string[];
      toolCounts?: Record<string, number>;
      scriptsUsed?: string[];
      referencesRead?: string[];
      stepsUsed?: number;
      totalToolCalls?: number;
      maxParallelWidth?: number;
      failedToolCalls?: number;
      qualityGatesRecommended?: string[];
      qualityGatesUsed?: string[];
      qualityGatesMissing?: string[];
      qualityGatesFailed?: string[];
      qualityGateCoverage?: number;
      qualityGateBlocked?: boolean;
      qualityGateAction?: string;
      workflowEngine?: string;
      graphPath?: string[];
      graphTransitions?: number;
      handoffAttempted?: boolean;
      handoffSuccess?: boolean;
      handoffId?: string | null;
      entities?: Record<string, string>;
      entitySources?: Record<string, string>;
      specialistDecisions?: Array<{
        agent?: string;
        skill?: string;
        toolCalls?: string[];
        durationMs?: number;
        error?: string | null;
      }>;
      dependencyBatches?: Array<{
        batches?: string[][];
        blocked?: string[];
        reason?: string;
        barrier?: string;
        dependencies?: Array<{ tool: string; dependsOn: string }>;
      }>;
    }

    interface Conversation {
      conversationId: string;
    }

    interface DiagnosisEvidence {
      resultStatus?: string;
      evidenceId: string;
      sourceType: 'USER_REPORT' | 'BUSINESS_QUERY' | 'DOCUMENT_RULE';
      scope: string;
      verified: boolean;
      freshness: string;
      tool?: string;
      requestId?: string;
      appId?: string;
      eventAt?: string;
      queriedAt?: string;
      validUntil?: string;
      windowStart?: string;
      windowEnd?: string;
      summary?: string;
      facts?: Array<Record<string, unknown>>;
    }

    interface Diagnosis {
      revision: number;
      candidates?: Array<{ cause: string; title: string; status: 'SUPPORTED' | 'EXCLUDED' | 'UNDETERMINED' }>;
      workflow?: {
        actions?: Array<{ cause: string; instruction: string; recheck: string }>;
        decision?: { serviceId?: string; ruleVersion?: string };
        rechecks?: Array<{ requestId: string; status: string; httpStatus?: number; reason?: string }>;
      };
      executions?: Array<{ generationId: string; status: string; attemptsUsed: number }>;
      diagnosisId: string;
      status: string;
      appId?: string;
      symptom: string;
      missingFields: string[];
      nextAction: string;
      updatedAt: string;
      evidence: DiagnosisEvidence[];
    }

    interface Message {
      workflowStage?: string;
      workflowStageStartedAt?: number;
      errorMessage?: string;
      diagnosisId?: string;
      diagnosis?: Diagnosis;
      role: 'user' | 'assistant';
      content: string;
      status?: 'pending' | 'loading' | 'finished' | 'error';
      timestamp?: string;
      conversationId?: string;
      generationId?: string;
      intent?: string;
      intentConfidence?: number;
      needsHuman?: boolean;
      username?: string;
      referenceMappings?: Record<string, ReferenceEvidence>;
      toolEvents?: AgentToolEvent[];
      activeSkills?: string[];
      skillTrace?: SkillTrace;
      entities?: Record<string, string>;
      entitySources?: Record<string, string>;
      specialistAgents?: string[];
      feedbackRating?: 'good' | 'bad';
    }

    interface Token {
      cmdToken: string;
    }

    interface GenerationSnapshot {
      diagnosisId?: string;
      generationId: string;
      userId: string;
      conversationId: string;
      question: string;
      status: GenerationStatus;
      content: string;
      createdAt: string;
      updatedAt: string;
      errorMessage?: string | null;
      referenceMappings?: Record<string, ReferenceEvidence>;
    }

    interface ConversationSession {
      id: number;
      conversationId: string;
      title: string;
      status: 'ACTIVE' | 'ARCHIVED';
      createdAt: string;
      updatedAt: string;
    }
  }

  namespace Document {
    interface DownloadResponse {
      fileName: string;
      downloadUrl: string;
      fileSize: number;
      fileMd5?: string;
    }

    interface ReferenceDetailResponse extends Chat.ReferenceEvidence {
      textContent?: string;
      contextText?: string;
      contextType?: string;
      referenceNumber: number;
    }
  }
}
