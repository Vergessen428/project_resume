// Static-only fixture overrides. Keep these clearly synthetic and never present them as verified posts.
window.AUTUMN_DEMO_DATA_OVERRIDES = {
  research: {
    id: "r1",
    title: "小红书公开候选（演示资料）",
    url: "https://www.xiaohongshu.com/explore/demo-pm-coach",
    platform: "小红书",
    platform_id: "xiaohongshu",
    company: "示例公司",
    role: "产品经理",
    round_name: "一面",
    published_date: "",
    tags: "演示, 相关性, 一面",
    status: "needs_review",
    confidence: 0,
    screening: {
      recommendation: "needs_review",
      relevance: 72,
      relevance_breakdown: { company_match: 30, role_match: 25, round_match: 10, topic_match: 12, interview_specificity: 0, recency: 0 },
      reason: "岗位和主题命中，但这是演示候选，必须打开原帖确认具体面试内容。",
    },
    source_kind: "demo_synthetic",
    provenance_status: "manual_check_required",
    search_query: "site:xiaohongshu.com/explore 示例公司 产品经理 一面 指标 面经",
    retrieved_at: "2026-09-05T12:00:00+00:00",
    source_text: "这是静态 Demo 的合成资料卡，用来展示小红书公开搜索候选、相关度拆解和人工确认流程，不对应任何真实原帖。",
    comments_text: "",
    assessment: {
      recommendation: "needs_review",
      confidence: 0,
      summary: "演示合成内容，不对应可验证的原帖；需要人工打开真实链接并摘录正文。",
      claims: [],
      question_leads: [{
        question: "如果报名提醒上线后 DAU 上升但报名率不变，你如何区分触达、转化和归因问题？",
        topic: "指标归因",
        evidence: "",
        evidence_status: "unverified",
      }],
      credibility_signals: [],
      concerns: ["演示合成内容", "当前链接不是原帖", "必须人工确认原帖正文"],
      review_reason: "搜索候选不自动进入可信资料库。",
    },
    updated_at: "2026-09-05T12:00:00",
  },
  agentResult: {
    collected: [{
      url: "https://www.xiaohongshu.com/explore/demo-pm-coach",
      title: "小红书候选资料（演示，待人工打开确认）",
      platform: "小红书",
      platform_id: "xiaohongshu",
      summary: "演示候选：仅用于展示平台限定搜索、相关度分解和来源状态，不是可引用原帖。",
      published_date: "",
      search_query: "site:xiaohongshu.com/explore 字节 产品经理 一面 指标 面经",
      source_kind: "demo_synthetic",
      provenance_status: "manual_check_required",
      fetch_status: "shell_only",
      fetch: { fetch_status: "shell_only", fetch_reason: "静态演示不联网；真实后端会尝试读取公开 HTML，遇到脚本壳则保留待确认。" },
      screening: {
        recommendation: "needs_review",
        relevance: 72,
        relevance_breakdown: { company_match: 30, role_match: 25, round_match: 10, topic_match: 12, interview_specificity: 0, recency: 0 },
        reason: "岗位和主题命中，但这是演示候选，必须打开原帖确认具体面试内容。",
      },
    }],
    persisted: [],
    assessed: [],
    skipped: [],
    trace: [
      { round: 1, reasoning: "先用平台限定词搜索公司、岗位和轮次", action: "search", query: "site:xiaohongshu.com/explore 字节 产品经理 一面 指标 面经", added: 1 },
      { round: 2, reasoning: "已尝试读取公开页面；演示环境不联网，保留待确认状态", action: "fetch", query: "打开候选公开链接并提取可见正文", added: 0, fetched: 0 },
      { round: 3, reasoning: "不把搜索摘要或页面壳当作证据", action: "stop", stop_reason: "候选仍需来源确认后才能进入可信资料库。", added: 0 },
    ],
    stop_reason: "候选仍需来源确认后才能进入可信资料库。",
    found_enough: false,
    search_meta: {
      platform: "xiaohongshu",
      platform_label: "小红书",
      queries_tried: ["site:xiaohongshu.com/explore 字节 产品经理 一面 指标 面经", "site:xiaohongshu.com/explore 字节 AI产品 项目深挖"],
      result_count: 1,
      fetch_status_counts: { shell_only: 1 },
      failure_reasons: ["静态演示未联网；真实后端会记录公开页读取失败原因。"],
      empty_reason: "",
    },
  },
};
// Full static fixture data lives in demo_data.js so page logic and demo content stay separate.
window.AUTUMN_DEMO_DATA = (() => {
  const review = {
    summary: "整体表达清楚，但对指标的定义和归因偏弱：能说出看 DAU 和报名人数，却没讲清为什么选这两个指标、如何归因。项目主导力有亮点（主动把需求拆成两期），但结果量化模糊。",
    strengths: [
      { title: "主动做取舍", evidence: "我把需求拆成两期，先上线报名提醒。", why_it_worked: "在资源约束下给出了可落地的优先级方案，体现项目主导力。" },
    ],
    gaps: [
      { title: "指标定义与归因偏弱", evidence: "大意是用户多了报名就会多。", improvement: "先定义北极星指标与护栏指标，再讲清 DAU 与报名之间的因果假设和验证方式。" },
      { title: "结果缺乏量化", evidence: "但具体数值记不清了。", improvement: "复盘时补齐关键数字（提升幅度、样本、周期），用结构化结果收尾。" },
    ],
    questions: [
      { question: "你怎么判断它是否成功？", answer_summary: "看 DAU 和报名人数。", evidence: "我说主要看 DAU 和报名人数，后来 DAU 涨了。", assessment: "指标选择方向对，但没有定义口径，也没说明与目标的关系。", score: 2, skills: ["metrics_experiment", "structured_communication"], evidence_quality: "verified", next_practice: "用『北极星+护栏』框架重述一遍这个项目的成功标准。" },
    ],
    skill_diagnosis: [
      { skill_id: "product_sense", skill_name: "产品判断", score: 3, exact_score: 3.4, confidence: "high", evidence_coverage: 0.8, evidence: "目标是提升同学报名率。", diagnosis: "能说明目标，但用户问题和优先级依据还不够具体。", dimensions: [
        { id: "user_problem", label: "用户问题", weight: 30, score: 3, status: "observed", evidence: "目标是提升同学报名率。", rationale: "有目标，但未展开用户障碍。" },
        { id: "goal_definition", label: "目标定义", weight: 20, score: 3, status: "observed", evidence: "目标是提升同学报名率。", rationale: "目标方向清楚，缺少口径。" },
        { id: "tradeoff", label: "方案取舍", weight: 30, score: 4, status: "observed", evidence: "我把需求拆成两期，先上线报名提醒。", rationale: "能在资源约束下做取舍。" },
        { id: "prioritization", label: "优先级判断", weight: 20, score: null, status: "missing", evidence: "（无转写原文可佐证）", rationale: "没有说明优先级依据。" },
      ], gaps: [{ gap_id: "product_sense__user_problem", severity: "medium", evidence: "目标是提升同学报名率。", impact: "问题定义浅会削弱方案说服力。" }], practice_plan: { action: "重写一次问题定义", prompt: "报名率低的具体用户障碍是什么？", success_criteria: ["明确目标用户", "说明问题场景", "解释优先级依据"], follow_up_question: "如果报名率不提升，你会先检查哪一层？" }, next_practice: "重写一次问题定义。" },
      { skill_id: "story_ownership", skill_name: "项目主导力", score: 4, exact_score: 3.8, confidence: "high", evidence_coverage: 0.75, evidence: "我把需求拆成两期，先上线报名提醒。", diagnosis: "个人决策和取舍清晰，但结果复盘还未闭环。", dimensions: [
        { id: "scope", label: "职责边界", weight: 30, score: 4, status: "observed", evidence: "我把需求拆成两期。", rationale: "能说明个人负责的决策。" },
        { id: "decision", label: "关键决策", weight: 30, score: 4, status: "observed", evidence: "先上线报名提醒。", rationale: "有明确的先后取舍。" },
        { id: "collaboration", label: "协作推进", weight: 15, score: 3, status: "observed", evidence: "运营想多做活动入口、开发觉得时间不够。", rationale: "识别了分歧，但对齐动作不完整。" },
        { id: "result_learning", label: "结果复盘", weight: 25, score: null, status: "missing", evidence: "但具体数值记不清了。", rationale: "结果未量化，复盘无法闭环。" },
      ], gaps: [{ gap_id: "story_ownership__result", severity: "medium", evidence: "但具体数值记不清了。", impact: "缺少结果会让主导力难以验证。" }], practice_plan: { action: "补齐项目结果复盘", prompt: "这个取舍带来了什么可量化变化？", success_criteria: ["给出变化幅度", "说明样本和周期", "总结下一次如何调整"], follow_up_question: "如果结果不如预期，你会承担哪一部分责任？" }, next_practice: "补齐项目结果复盘。" },
      { skill_id: "metrics_experiment", skill_name: "指标与实验", score: 1, exact_score: 1.5, confidence: "medium", evidence_coverage: 0.55, evidence: "因为用户多了，报名应该也会更多。", diagnosis: "能想到结果指标，但把相关关系当成因果关系，缺少验证设计。", dimensions: [
        { id: "definition", label: "指标定义", weight: 25, score: 2, status: "observed", evidence: "主要看 DAU 和报名人数。", rationale: "说出指标，但没有口径。" },
        { id: "decomposition", label: "指标拆解", weight: 20, score: null, status: "missing", evidence: "（无转写原文可佐证）", rationale: "未拆解到转化链路。" },
        { id: "attribution", label: "归因意识", weight: 30, score: 1, status: "contradicted", evidence: "因为用户多了，报名应该也会更多。", rationale: "直接把相关当作因果。" },
        { id: "experiment_quantify", label: "实验与量化", weight: 25, score: null, status: "missing", evidence: "但具体数值记不清了。", rationale: "缺少实验和结果数字。" },
      ], gaps: [{ gap_id: "metrics_experiment__attribution", severity: "high", evidence: "因为用户多了，报名应该也会更多。", impact: "无法证明方案带来了目标结果。" }, { gap_id: "metrics_experiment__quantify", severity: "high", evidence: "但具体数值记不清了。", impact: "无法评估影响大小。" }], practice_plan: { action: "重写一次指标定义", prompt: "如何证明报名人数增长确实由报名提醒带来？", success_criteria: ["定义核心和护栏指标", "说明归因假设", "给出验证方法"], follow_up_question: "如果 DAU 上升但报名率不变，你如何判断问题？" }, next_practice: "用北极星+护栏指标重写成功标准。" },
      { skill_id: "execution_collaboration", skill_name: "推进与协作", score: 3, exact_score: 3.3, confidence: "medium", evidence_coverage: 0.7, evidence: "运营想多做活动入口、开发觉得时间不够。", diagnosis: "能识别资源冲突并做范围取舍，但没有讲清对齐和风险跟踪。", dimensions: [
        { id: "planning", label: "计划与风险", weight: 25, score: 3, status: "observed", evidence: "我把需求拆成两期。", rationale: "有基本的分期计划。" },
        { id: "alignment", label: "跨团队对齐", weight: 25, score: 3, status: "observed", evidence: "运营想多做活动入口、开发觉得时间不够。", rationale: "识别分歧，但缺少对齐动作。" },
        { id: "resource_tradeoff", label: "资源取舍", weight: 20, score: 4, status: "observed", evidence: "先上线报名提醒。", rationale: "能在时间约束下收敛范围。" },
        { id: "closure", label: "落地闭环", weight: 30, score: null, status: "missing", evidence: "（无转写原文可佐证）", rationale: "没有具体上线和复盘闭环。" },
      ], gaps: [{ gap_id: "execution_collaboration__closure", severity: "medium", evidence: "（无转写原文可佐证）", impact: "无法判断方案是否真正落地。" }], practice_plan: { action: "补一段协作闭环", prompt: "你如何让运营和开发接受这个分期方案？", success_criteria: ["说明对齐对象", "说明冲突处理", "说明上线后的跟踪动作"], follow_up_question: "开发仍然不同意时，你会如何升级决策？" }, next_practice: "补一段协作闭环。" },
      { skill_id: "structured_communication", skill_name: "结构化表达", score: 3, exact_score: 3.0, confidence: "high", evidence_coverage: 1.0, evidence: "看 DAU 和报名人数。", diagnosis: "能先给出指标答案，但遇到追问时解释容易跳到结论。", dimensions: [
        { id: "structure", label: "表达结构", weight: 30, score: 3, status: "observed", evidence: "看 DAU 和报名人数。", rationale: "答案简短，但缺少分层。" },
        { id: "directness", label: "结论先行", weight: 20, score: 4, status: "observed", evidence: "看 DAU 和报名人数。", rationale: "能直接回答问题。" },
        { id: "precision", label: "信息精确度", weight: 25, score: 2, status: "observed", evidence: "用户多了，报名应该也会更多。", rationale: "因果表述不精确。" },
        { id: "probe_response", label: "追问应对", weight: 25, score: 3, status: "observed", evidence: "这里我答得比较虚。", rationale: "能意识到薄弱点，但没有补充完整。" },
      ], gaps: [{ gap_id: "structured_communication__probe", severity: "medium", evidence: "这里我答得比较虚。", impact: "追问时缺少可继续展开的结构。" }], practice_plan: { action: "用结论-依据-验证重答", prompt: "把指标答案压缩成三段式表达。", success_criteria: ["先说结论", "补充判断依据", "给出验证方式"], follow_up_question: "面试官质疑你的指标选择时，你先回应哪一点？" }, next_practice: "用结论-依据-验证重答。" },
      { skill_id: "business_context", skill_name: "业务与岗位理解", score: null, exact_score: null, confidence: "low", evidence_coverage: 0.0, evidence: "（无转写原文可佐证）", diagnosis: "当前转写没有足够证据证明你如何连接 AI 产品岗位和业务目标。", dimensions: [
        { id: "jd_link", label: "JD 连接", weight: 30, score: null, status: "missing", evidence: "（无转写原文可佐证）", rationale: "没有记录岗位要求的对应回答。" },
        { id: "user_business", label: "用户与业务", weight: 25, score: null, status: "missing", evidence: "（无转写原文可佐证）", rationale: "业务影响没有展开。" },
        { id: "market_context", label: "市场语境", weight: 20, score: null, status: "not_applicable", evidence: "（无转写原文可佐证）", rationale: "本场记录没有市场类问题。" },
        { id: "role_fit", label: "岗位适配", weight: 25, score: null, status: "missing", evidence: "（无转写原文可佐证）", rationale: "缺少岗位适配证据。" },
      ], gaps: [{ gap_id: "business_context__jd_link", severity: "low", evidence: "（无转写原文可佐证）", impact: "数据不足，不能下确定结论。" }], practice_plan: { action: "补充岗位连接素材", prompt: "为什么这个项目能证明你适合 AI 产品经理岗位？", success_criteria: ["连接 JD 要求", "说明业务价值", "给出个人证据"], follow_up_question: "这个项目中最能迁移到目标岗位的能力是什么？" }, next_practice: "补充岗位连接素材。" },
    ],
    action_plan: [
      { id: "act1", action_key: "action-demo-metrics", action: "用北极星+护栏指标重写这个项目的成功定义", priority: "高", reason: "指标是本场最大失分点。", success_criteria: ["定义核心和护栏指标", "说明归因假设", "给出验证方法"], next_validation: "下一场被追问成功标准时，先说指标口径再说验证。", source_skill_ids: ["metrics_experiment"], source_gap_ids: ["metrics_experiment__attribution"], source_interview_id: "demo-interview", source_interview_date: "2026-09-18", source_company: "示例科技", source_role: "AI 产品经理实习生", source_round_name: "业务一面", acceptance_status: "pending", done: false, training_progress: { pre_test: true, rewrite: true, post_test: false, attempt_count: 2 }, attempts: [{ phase: "pre_test", response: "看 DAU 和报名人数。" }, { phase: "rewrite", response: "核心看报名转化率，DAU 作为背景指标，再用分组实验验证报名提醒的增量。" }] },
      { id: "act2", action_key: "action-demo-quantify", action: "补齐项目关键数字并做一版量化结果收尾", priority: "中", reason: "结果模糊会削弱说服力。", success_criteria: ["给出变化幅度", "说明样本和周期", "说清结果如何影响下一步"], next_validation: "下一场项目深挖时，用结果数字完成结尾。", source_skill_ids: ["metrics_experiment", "story_ownership"], source_gap_ids: ["metrics_experiment__quantify"], source_interview_id: "demo-interview", source_interview_date: "2026-09-18", source_company: "示例科技", source_role: "AI 产品经理实习生", source_round_name: "业务一面", acceptance_status: "pending", done: false, training_progress: { pre_test: false, rewrite: false, post_test: false, attempt_count: 0 }, attempts: [] },
    ],
    schema_version: "2.1",
    scored_by: { provider: "demo_fixture", model: "static-sample", prompt_version: "2.1", rubric_version: "pm-rubric-2.0", scored_at: "2026-09-18T10:00:00+00:00" },
    score_summary: { coach_score: 60, score_scale: 100, strongest_skill: "story_ownership", priority_skills: ["metrics_experiment"], training_band: "需要针对性训练" },
    review_quality: { transcript_chars: 212, answered_questions: 1, evidence_coverage: 0.63, confidence: "medium", data_quality: "项目决策有原文证据，但结果数字和归因证据不足。" },
    follow_up: "下一场面试前，准备一个能讲清指标定义、归因和量化结果的完整项目故事。",
  };

  const demoEvidenceProfiles = {
    product_sense: { specificity: 2, ownership: 2, causality: 1, result_quality: 1, reflection: 1, probe_resilience: 1 },
    story_ownership: { specificity: 3, ownership: 3, causality: 2, result_quality: 1, reflection: 1, probe_resilience: 2 },
    metrics_experiment: { specificity: 1, ownership: 1, causality: 0, result_quality: 1, reflection: 0, probe_resilience: 1 },
    execution_collaboration: { specificity: 2, ownership: 2, causality: 2, result_quality: 1, reflection: 1, probe_resilience: 1 },
    structured_communication: { specificity: 1, ownership: 2, causality: 1, result_quality: 1, reflection: 1, probe_resilience: 1 },
    business_context: { specificity: 0, ownership: 0, causality: 0, result_quality: 0, reflection: 0, probe_resilience: 0 },
  };
  review.skill_diagnosis.forEach(skill => { skill.evidence_profile = demoEvidenceProfiles[skill.skill_id] || {}; });

  const interview = {
    id: "demo1",
    company: "示例科技",
    role: "AI 产品经理实习生",
    round_name: "业务一面",
    date: "2026-09-18",
    status: "已面试",
    outcome: "pending", outcome_source: "self_reported",
    job_description: "负责 AI 产品需求分析、指标设计、跨团队推进和用户反馈闭环。要求能清晰拆解问题并使用数据验证方案。",
    resume_context: "",
    resume_id: "",
    resume_name: "",
    transcript: "面试官让我先介绍一个自己主导的项目，我讲了校园活动小程序，目标是提升同学报名率。\n他问我怎么判断项目是否成功，我说主要看 DAU 和报名人数，后来 DAU 涨了。\n接着追问为什么是这两个指标，这里我答得比较虚，大意是用户多了报名就会多。\n又问项目里最大的分歧，我说运营想多做活动入口、开发觉得时间不够，我把需求拆成两期，先上线报名提醒。\n最后问这个取舍带来什么结果，我说第一周报名比以前多了一些，但具体数值记不清了。",
    personal_notes: "面试时被追问指标定义，回答得比较虚。",
    jd_analysis: null,
    review,
  };

  const interviewSummary = {
    id: interview.id, company: interview.company, role: interview.role,
    round_name: interview.round_name, date: interview.date, status: interview.status,
    has_review: true, action_count: 2, open_actions: 2, outcome: "pending", resume_name: "", updated_at: "2026-09-18T10:00:00",
  };

  const resume = {
    id: "resume1", name: "产品 PM v2", target_role: "AI 产品经理",
    content: "教育背景：某大学，市场营销。\n项目经历：校园活动小程序（负责人）——用户调研、PRD、埋点设计、两周迭代。\n技能：SQL、Axure、数据分析。\n求职方向：AI 产品经理。",
    updated_at: "2026-09-10T09:00:00",
  };
  const resumeSummary = { id: resume.id, name: resume.name, target_role: resume.target_role, updated_at: resume.updated_at };

  const research = {
    id: "r1", title: "公开面经示例（演示资料）", url: "https://www.nowcoder.com/", platform: "牛客",
    company: "示例公司", role: "产品经理", round_name: "一面", published_date: "",
    tags: "演示, 相关性, 一面", status: "needs_review", confidence: 0,
    source_text: "一面主要问了项目：如何定义指标、如何做 A/B 实验、遇到的取舍。面试官很关注指标口径和归因，会追问『为什么是这个指标』。整体偏考察数据敏感度和结构化表达。",
    comments_text: "",
    assessment: {
      recommendation: "needs_review", confidence: 0,
      summary: "这是静态 Demo 的合成示例，用来展示相关性提示与人工确认流程，不对应一篇可验证的原帖。",
      claims: [],
      credibility_signals: [],
      concerns: ["演示合成内容，不对应可验证原帖", "完整版必须人工摘录原文后再预审"],
      review_reason: "演示资料不应被当作真实面经；完整版需要先打开原帖并摘录正文。",
    },
    updated_at: "2026-09-05T12:00:00",
  };

  const memory = {
    memory_version: "1.3", generated_at: "2026-09-18T10:05:00+00:00", reviewed_interviews: 3, total_interviews: 3, stage: "emerging", comparability: "mixed_model", mixed_scoring: true, scoring_providers: ["demo_fixture", "legacy_unknown"], scoring_models: ["static-sample", "legacy_unknown"],
    recurring_gaps: [{ gap_key: "metrics_experiment__attribution", canonical_gap_id: "metrics_experiment__attribution", title: "指标定义与归因偏弱", occurrences: 2, sources: [{ interview_id: "demo1", company: "示例科技", role: "AI 产品经理实习生", round_name: "业务一面", date: "2026-09-18", evidence: "因为用户多了，报名应该也会更多。" }, { interview_id: "demo2", company: "示例科技", role: "AI 产品经理实习生", round_name: "业务二面", date: "2026-09-10", evidence: "结果上涨了，但没有说明对照和归因。" }] }, { gap_key: "metrics_experiment__quantify", canonical_gap_id: "metrics_experiment__quantify", title: "结果缺乏量化", occurrences: 2, sources: [{ interview_id: "demo1", company: "示例科技", role: "AI 产品经理实习生", round_name: "业务一面", date: "2026-09-18", evidence: "但具体数值记不清了。" }, { interview_id: "demo3", company: "示例科技", role: "AI 产品经理实习生", round_name: "HR 面", date: "2026-09-03", evidence: "提升了一些，具体幅度没有记录。" }] }],
    gap_overrides: [],
    skill_summary: [{ skill_id: "metrics_experiment", average_score: 2.7, observations: 3, latest_score: 3, trend: "improving", trend_comparable: false }, { skill_id: "structured_communication", average_score: 3, observations: 3, latest_score: 3, trend: "stable", trend_comparable: false }],
    outcome_signal: { status: "insufficient_data", sample_count: 0, minimum_descriptive_sample: 4, minimum_stable_sample: 6, group_minimum: 2, passed: { count: 0, average_coach_score: null }, failed: { count: 0, average_coach_score: null }, direction: "unknown", comparability: "mixed_model", interpretation: "当前没有明确的通过/未通过自报结果，样本不足，不展示分数与结果的比较。" },
    open_actions: [
      { action: "用北极星+护栏指标重写这个项目的成功定义", reason: "指标是本场最大失分点。", priority: "高", from: "示例科技 · 业务一面" },
    ],
    timeline: [{ id: "demo1", company: "示例科技", role: "AI 产品经理实习生", round_name: "业务一面", date: "2026-09-18", outcome: "pending", updated_at: "2026-09-18T10:00:00", review_schema_version: "2.1" }, { id: "demo2", company: "示例科技", role: "AI 产品经理实习生", round_name: "业务二面", date: "2026-09-10", outcome: "", updated_at: "2026-09-10T10:00:00", review_schema_version: "2.1" }, { id: "demo3", company: "示例科技", role: "AI 产品经理实习生", round_name: "HR 面", date: "2026-09-03", outcome: "", updated_at: "2026-09-03T10:00:00", review_schema_version: "2.1" }],
    audit: { aggregation: "deterministic", algorithm_version: "growth-memory-1.3", replayable: true, input_count: 3, inputs: [{ interview_id: "demo3", date: "2026-09-03", review_schema_version: "2.1", scored_by: { provider: "legacy_unknown", model: "legacy_unknown", prompt_version: "legacy_unknown", rubric_version: "legacy_unknown" } }, { interview_id: "demo2", date: "2026-09-10", review_schema_version: "2.1", scored_by: { provider: "demo_fixture", model: "static-sample", prompt_version: "2.1", rubric_version: "pm-rubric-2.0" } }, { interview_id: "demo1", date: "2026-09-18", review_schema_version: "2.1", scored_by: { provider: "demo_fixture", model: "static-sample", prompt_version: "2.1", rubric_version: "pm-rubric-2.0" } }], override_keys: [], notes: ["静态演示使用三场合成记录；真实数据由本地结构化记录重新计算，趋势优先使用 exact_score。"] },
  };

  const growthReport = {
    summary: "跨 3 场演示复盘，指标与结果证据仍是重复缺口，但结构化表达开始稳定；下一轮训练要把“指标定义—归因验证—量化结果”连成一个可复述故事。",
    stage_assessment: "当前处于成长早期：已经能做出范围取舍，但还没有稳定地用数据证明决策有效。这个结论只用于安排训练，不代表录用概率。",
    growth_signals: [{ title: "项目取舍更清晰", evidence: "近 2 场都能说明分期或范围收敛。", interpretation: "项目主导力的决策证据开始稳定。" }, { title: "指标回答有改善", evidence: "最近一场补充了核心指标，但归因和护栏指标仍缺失。", interpretation: "方向在改善，尚未形成完整实验闭环。" }],
    recurring_patterns: [{ skill: "指标与实验 · 归因意识", occurrences: 2, evidence: "两场复盘都出现“结果上涨但无法说明因果”的证据。", recommendation: "下一次用对照组、时间窗口和护栏指标重答。" }, { skill: "项目主导力 · 结果复盘", occurrences: 2, evidence: "能讲决策，但关键结果缺少数值、样本和周期。", recommendation: "为每个项目故事建立结果数字卡。" }],
    priority_training: [{ action: "完成一次指标闭环重答", why_now: "它同时影响指标与实验、结构化表达和项目结果复盘。", success_criterion: "核心指标、护栏指标、归因假设、验证方法和结果数字齐全。", source: "示例科技 · 业务一面" }],
    data_quality: "当前演示没有明确的通过/未通过自报结果，长期记忆由三场合成记录确定性聚合得到；混合评分版本和样本不足都会阻止趋势或结果比较。outcome 仅为自报训练反馈，不是录用预测。",
    report_grounding: { grounded: true, memory_version: "1.3", algorithm_version: "growth-memory-1.3", source_interview_count: 3, pattern_count: 2, action_count: 1, note: "静态演示：结构化趋势、次数、来源和训练行动来自预置的确定性长期记忆；模型未参与生成。" },
  };

  const skills = [
    { id: "product_sense", name: "产品判断", focus: "用户问题、目标定义、方案取舍与优先级。", score_anchors: { "1": "没有定义问题", "3": "能说明目标和基本取舍", "5": "连接用户、业务、约束和验证" } },
    { id: "story_ownership", name: "项目主导力", focus: "个人职责边界、关键动作、结果与复盘，而非团队泛泛叙述。", score_anchors: { "1": "只描述团队工作", "3": "能说明个人动作和结果", "5": "决策、结果、复盘形成闭环" } },
    { id: "metrics_experiment", name: "指标与实验", focus: "指标定义、拆解、归因、实验设计和量化结果。", score_anchors: { "1": "没有可核对指标", "3": "能定义指标但验证不完整", "5": "指标、归因、实验和结果闭环" } },
    { id: "execution_collaboration", name: "推进与协作", focus: "跨团队分歧、资源约束、风险取舍和落地闭环。", score_anchors: { "1": "没有推进动作", "3": "能描述协调和基本落地", "5": "解释分歧、取舍、风险和闭环" } },
    { id: "structured_communication", name: "结构化表达", focus: "结论先行、信息层次、追问应对与表达简洁度。", score_anchors: { "1": "回答与问题脱节", "3": "结构基本清楚但有遗漏", "5": "结论、证据、取舍和复盘清晰" } },
    { id: "business_context", name: "业务与岗位理解", focus: "将个人经历连接到 JD、公司业务和具体岗位场景。", score_anchors: { "1": "没有岗位连接", "3": "能对应部分 JD 要求", "5": "能连接公司业务、岗位和个人证据" } },
  ];

  const noteQuestions = [
    { id: "hit_1", type: "命中", question: "面试官追问校园活动小程序的指标时，你是怎么定义“成功”的？口径讲清了吗？", why_asked: "简历核心项目 × JD 指标设计要求" },
    { id: "hit_2", type: "命中", question: "被问到需求取舍（活动入口 vs 报名提醒）时，你的决策依据是什么？", why_asked: "命中 JD 的问题拆解与推进能力" },
    { id: "gap_1", type: "补刀", question: "JD 强调数据验证方案，你有没有被问到 A/B 实验或归因？答得如何？", why_asked: "JD 要求但简历未体现的实验能力" },
    { id: "gap_2", type: "补刀", question: "跨团队推进闭环这块，面试官有没有追问你如何对齐目标、收敛分歧？", why_asked: "JD 要求跨团队推进，简历偏弱" },
    { id: "common_1", type: "通用", question: "这场面试里，哪个问题你答得最卡？当时你是怎么回应的？", why_asked: "定位当场最大失分点" },
    { id: "common_2", type: "通用", question: "面完你最后悔哪句话没说出来，或哪个点没讲清？", why_asked: "捕捉遗漏，供下场改进" },
  ];

  const agentResult = {
    collected: [
      { url: "https://www.xiaohongshu.com/explore/demo-pm-coach", title: "小红书公开面经候选（演示资料）", platform: "小红书", summary: "静态演示用的合成候选：展示指标定义、A/B 实验与归因主题的相关度提示，不对应可验证原帖。", published_date: "", source_kind: "demo_synthetic", provenance_status: "manual_check_required", screening: { recommendation: "needs_review", relevance: 72, reason: "演示相关度提示，需打开真实原帖确认" } },
    ],
    trace: [
      { round: 1, reasoning: "静态演示不联网；先用公司+岗位+一面直搜", action: "search", query: "字节 产品经理 一面 面经", added: 0 },
      { round: 2, reasoning: "静态演示不联网；首轮无达标，换岗位同义词并保持平台限定", action: "search", query: "site:xiaohongshu.com/explore 字节跳动 AI产品 实习 一面", added: 1 },
      { round: 3, reasoning: "已收集到 1 条待确认，预算内主动停", action: "stop", stop_reason: "达成部分目标，交人工摘录", added: 0 },
    ],
    stop_reason: "达成部分目标，交人工摘录",
    found_enough: false,
    search_meta: {
      platform: "xiaohongshu",
      platform_label: "小红书",
      queries_tried: ["site:xiaohongshu.com/explore 字节 产品经理 一面 指标 面经", "site:xiaohongshu.com/explore 字节 AI产品 项目深挖"],
      result_count: 1,
      fetch_status_counts: { shell_only: 1 },
      failure_reasons: ["静态演示未联网；真实后端会记录公开页读取失败原因。"],
      empty_reason: "",
    },
  };

  const jdAnalysis = { role_title: "AI 产品经理实习生", responsibilities: ["需求分析与用户反馈闭环", "跨团队推进产品迭代"], requirements: ["指标设计", "数据验证方案", "结构化拆解问题"], keywords: ["AI 产品", "指标", "实验", "协作"], interview_focus: ["项目深挖", "指标与归因", "产品 case"], search_topics: ["项目深挖", "指标与实验", "AI 产品 case"] };
  const overrides = window.AUTUMN_DEMO_DATA_OVERRIDES || {};
  return { interview, interviewSummary, resume, resumeSummary, research, memory, growthReport, skills, noteQuestions, agentResult, jdAnalysis, ...overrides };
})();
