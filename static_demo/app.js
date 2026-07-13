// Static demo build of the Autumn PM interview assistant.
// No backend: window.fetch is shimmed to serve canned data so all the original
// render logic runs unchanged. Write actions (generate / save / upload / search)
// return a friendly "this is a static demo" message.

const DEMO = (() => {
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
      { question: "你怎么判断它是否成功？", answer_summary: "看 DAU 和报名人数。", evidence: "我说主要看 DAU 和报名人数，后来 DAU 涨了。", assessment: "指标选择方向对，但没有定义口径，也没说明与目标的关系。", score: 2, next_practice: "用『北极星+护栏』框架重述一遍这个项目的成功标准。" },
    ],
    skill_diagnosis: [
      { skill_id: "product_sense", skill_name: "产品判断", score: 3, exact_score: 3.1, confidence: "medium", evidence_coverage: 0.7, evidence: "目标是提升同学报名率。", diagnosis: "能说明目标，但用户问题和优先级依据还不够具体。", dimensions: [
        { id: "user_problem", label: "用户问题", weight: 30, score: 3, status: "observed", evidence: "目标是提升同学报名率。", rationale: "有目标，但未展开用户障碍。" },
        { id: "goal_definition", label: "目标定义", weight: 20, score: 3, status: "observed", evidence: "目标是提升同学报名率。", rationale: "目标方向清楚，缺少口径。" },
        { id: "tradeoff", label: "方案取舍", weight: 30, score: 4, status: "observed", evidence: "我把需求拆成两期，先上线报名提醒。", rationale: "能在资源约束下做取舍。" },
        { id: "prioritization", label: "优先级判断", weight: 20, score: 2, status: "missing", evidence: "（无转写原文可佐证）", rationale: "没有说明优先级依据。" },
      ], gaps: [{ gap_id: "product_sense__user_problem", severity: "medium", evidence: "目标是提升同学报名率。", impact: "问题定义浅会削弱方案说服力。" }], practice_plan: { action: "重写一次问题定义", prompt: "报名率低的具体用户障碍是什么？", success_criteria: ["明确目标用户", "说明问题场景", "解释优先级依据"], follow_up_question: "如果报名率不提升，你会先检查哪一层？" }, next_practice: "重写一次问题定义。" },
      { skill_id: "story_ownership", skill_name: "项目主导力", score: 4, exact_score: 3.8, confidence: "high", evidence_coverage: 0.9, evidence: "我把需求拆成两期，先上线报名提醒。", diagnosis: "个人决策和取舍清晰，但结果复盘还未闭环。", dimensions: [
        { id: "scope", label: "职责边界", weight: 30, score: 4, status: "observed", evidence: "我把需求拆成两期。", rationale: "能说明个人负责的决策。" },
        { id: "decision", label: "关键决策", weight: 30, score: 4, status: "observed", evidence: "先上线报名提醒。", rationale: "有明确的先后取舍。" },
        { id: "collaboration", label: "协作推进", weight: 15, score: 3, status: "observed", evidence: "运营想多做活动入口、开发觉得时间不够。", rationale: "识别了分歧，但对齐动作不完整。" },
        { id: "result_learning", label: "结果复盘", weight: 25, score: 2, status: "missing", evidence: "但具体数值记不清了。", rationale: "结果未量化，复盘无法闭环。" },
      ], gaps: [{ gap_id: "story_ownership__result", severity: "medium", evidence: "但具体数值记不清了。", impact: "缺少结果会让主导力难以验证。" }], practice_plan: { action: "补齐项目结果复盘", prompt: "这个取舍带来了什么可量化变化？", success_criteria: ["给出变化幅度", "说明样本和周期", "总结下一次如何调整"], follow_up_question: "如果结果不如预期，你会承担哪一部分责任？" }, next_practice: "补齐项目结果复盘。" },
      { skill_id: "metrics_experiment", skill_name: "指标与实验", score: 2, exact_score: 2.1, confidence: "high", evidence_coverage: 0.75, evidence: "因为用户多了，报名应该也会更多。", diagnosis: "能想到结果指标，但把相关关系当成因果关系，缺少验证设计。", dimensions: [
        { id: "definition", label: "指标定义", weight: 25, score: 2, status: "observed", evidence: "主要看 DAU 和报名人数。", rationale: "说出指标，但没有口径。" },
        { id: "decomposition", label: "指标拆解", weight: 20, score: 2, status: "missing", evidence: "（无转写原文可佐证）", rationale: "未拆解到转化链路。" },
        { id: "attribution", label: "归因意识", weight: 30, score: 1, status: "contradicted", evidence: "因为用户多了，报名应该也会更多。", rationale: "直接把相关当作因果。" },
        { id: "experiment_quantify", label: "实验与量化", weight: 25, score: 2, status: "missing", evidence: "但具体数值记不清了。", rationale: "缺少实验和结果数字。" },
      ], gaps: [{ gap_id: "metrics_experiment__attribution", severity: "high", evidence: "因为用户多了，报名应该也会更多。", impact: "无法证明方案带来了目标结果。" }, { gap_id: "metrics_experiment__quantify", severity: "high", evidence: "但具体数值记不清了。", impact: "无法评估影响大小。" }], practice_plan: { action: "重写一次指标定义", prompt: "如何证明报名人数增长确实由报名提醒带来？", success_criteria: ["定义核心和护栏指标", "说明归因假设", "给出验证方法"], follow_up_question: "如果 DAU 上升但报名率不变，你如何判断问题？" }, next_practice: "用北极星+护栏指标重写成功标准。" },
      { skill_id: "execution_collaboration", skill_name: "推进与协作", score: 3, exact_score: 3.0, confidence: "medium", evidence_coverage: 0.55, evidence: "运营想多做活动入口、开发觉得时间不够。", diagnosis: "能识别资源冲突并做范围取舍，但没有讲清对齐和风险跟踪。", dimensions: [
        { id: "planning", label: "计划与风险", weight: 25, score: 3, status: "observed", evidence: "我把需求拆成两期。", rationale: "有基本的分期计划。" },
        { id: "alignment", label: "跨团队对齐", weight: 25, score: 3, status: "observed", evidence: "运营想多做活动入口、开发觉得时间不够。", rationale: "识别分歧，但缺少对齐动作。" },
        { id: "resource_tradeoff", label: "资源取舍", weight: 20, score: 4, status: "observed", evidence: "先上线报名提醒。", rationale: "能在时间约束下收敛范围。" },
        { id: "closure", label: "落地闭环", weight: 30, score: 2, status: "missing", evidence: "（无转写原文可佐证）", rationale: "没有具体上线和复盘闭环。" },
      ], gaps: [{ gap_id: "execution_collaboration__closure", severity: "medium", evidence: "（无转写原文可佐证）", impact: "无法判断方案是否真正落地。" }], practice_plan: { action: "补一段协作闭环", prompt: "你如何让运营和开发接受这个分期方案？", success_criteria: ["说明对齐对象", "说明冲突处理", "说明上线后的跟踪动作"], follow_up_question: "开发仍然不同意时，你会如何升级决策？" }, next_practice: "补一段协作闭环。" },
      { skill_id: "structured_communication", skill_name: "结构化表达", score: 3, exact_score: 3.0, confidence: "medium", evidence_coverage: 0.55, evidence: "看 DAU 和报名人数。", diagnosis: "能先给出指标答案，但遇到追问时解释容易跳到结论。", dimensions: [
        { id: "structure", label: "表达结构", weight: 30, score: 3, status: "observed", evidence: "看 DAU 和报名人数。", rationale: "答案简短，但缺少分层。" },
        { id: "directness", label: "结论先行", weight: 20, score: 4, status: "observed", evidence: "看 DAU 和报名人数。", rationale: "能直接回答问题。" },
        { id: "precision", label: "信息精确度", weight: 25, score: 2, status: "observed", evidence: "用户多了，报名应该也会更多。", rationale: "因果表述不精确。" },
        { id: "probe_response", label: "追问应对", weight: 25, score: 3, status: "observed", evidence: "这里我答得比较虚。", rationale: "能意识到薄弱点，但没有补充完整。" },
      ], gaps: [{ gap_id: "structured_communication__probe", severity: "medium", evidence: "这里我答得比较虚。", impact: "追问时缺少可继续展开的结构。" }], practice_plan: { action: "用结论-依据-验证重答", prompt: "把指标答案压缩成三段式表达。", success_criteria: ["先说结论", "补充判断依据", "给出验证方式"], follow_up_question: "面试官质疑你的指标选择时，你先回应哪一点？" }, next_practice: "用结论-依据-验证重答。" },
      { skill_id: "business_context", skill_name: "业务与岗位理解", score: 2, exact_score: 2.4, confidence: "low", evidence_coverage: 0.25, evidence: "", diagnosis: "当前转写没有足够证据证明你如何连接 AI 产品岗位和业务目标。", dimensions: [
        { id: "jd_link", label: "JD 连接", weight: 30, score: 2, status: "missing", evidence: "（无转写原文可佐证）", rationale: "没有记录岗位要求的对应回答。" },
        { id: "user_business", label: "用户与业务", weight: 25, score: 2, status: "missing", evidence: "（无转写原文可佐证）", rationale: "业务影响没有展开。" },
        { id: "market_context", label: "市场语境", weight: 20, score: 2, status: "not_applicable", evidence: "（无转写原文可佐证）", rationale: "本场记录没有市场类问题。" },
        { id: "role_fit", label: "岗位适配", weight: 25, score: 2, status: "missing", evidence: "（无转写原文可佐证）", rationale: "缺少岗位适配证据。" },
      ], gaps: [{ gap_id: "business_context__jd_link", severity: "low", evidence: "（无转写原文可佐证）", impact: "数据不足，不能下确定结论。" }], practice_plan: { action: "补充岗位连接素材", prompt: "为什么这个项目能证明你适合 AI 产品经理岗位？", success_criteria: ["连接 JD 要求", "说明业务价值", "给出个人证据"], follow_up_question: "这个项目中最能迁移到目标岗位的能力是什么？" }, next_practice: "补充岗位连接素材。" },
    ],
    action_plan: [
      { id: "act1", action: "用北极星+护栏指标重写这个项目的成功定义", priority: "高", reason: "指标是本场最大失分点。", done: false },
      { id: "act2", action: "补齐项目关键数字并做一版量化结果收尾", priority: "中", reason: "结果模糊会削弱说服力。", done: false },
    ],
    schema_version: "2.0",
    score_summary: { coach_score: 68, score_scale: 100, strongest_skill: "story_ownership", priority_skills: ["metrics_experiment", "business_context"], training_band: "需要针对性训练" },
    review_quality: { transcript_chars: 420, answered_questions: 4, evidence_coverage: 0.72, confidence: "medium", data_quality: "项目决策有原文证据，但结果数字和归因证据不足。" },
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
    has_review: true, action_count: 2, open_actions: 2, resume_name: "", updated_at: "2026-09-18T10:00:00",
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
    reviewed_interviews: 3, total_interviews: 3, stage: "emerging",
    recurring_gaps: [{ title: "指标定义与归因偏弱", occurrences: 2 }, { title: "结果缺乏量化", occurrences: 2 }],
    skill_summary: [{ skill_id: "metrics_experiment", average_score: 2.7, observations: 3, latest_score: 3, trend: "improving" }, { skill_id: "structured_communication", average_score: 3, observations: 3, latest_score: 3, trend: "stable" }],
    open_actions: [
      { action: "用北极星+护栏指标重写这个项目的成功定义", reason: "指标是本场最大失分点。", priority: "高", from: "示例科技 · 业务一面" },
    ],
    timeline: [{ id: "demo1", company: "示例科技", role: "AI 产品经理实习生", round_name: "业务一面", date: "2026-09-18" }],
  };

  const growthReport = {
    summary: "跨 3 场演示复盘，指标与结果证据仍是重复缺口，但结构化表达开始稳定；下一轮训练要把“指标定义—归因验证—量化结果”连成一个可复述故事。",
    stage_assessment: "当前处于成长早期：已经能做出范围取舍，但还没有稳定地用数据证明决策有效。这个结论只用于安排训练，不代表录用概率。",
    growth_signals: [{ title: "项目取舍更清晰", evidence: "近 2 场都能说明分期或范围收敛。", interpretation: "项目主导力的决策证据开始稳定。" }, { title: "指标回答有改善", evidence: "最近一场补充了核心指标，但归因和护栏指标仍缺失。", interpretation: "方向在改善，尚未形成完整实验闭环。" }],
    recurring_patterns: [{ skill: "指标与实验 · 归因意识", occurrences: 2, evidence: "两场复盘都出现“结果上涨但无法说明因果”的证据。", recommendation: "下一次用对照组、时间窗口和护栏指标重答。" }, { skill: "项目主导力 · 结果复盘", occurrences: 2, evidence: "能讲决策，但关键结果缺少数值、样本和周期。", recommendation: "为每个项目故事建立结果数字卡。" }],
    priority_training: [{ action: "完成一次指标闭环重答", why_now: "它同时影响指标与实验、结构化表达和项目结果复盘。", success_criterion: "核心指标、护栏指标、归因假设、验证方法和结果数字齐全。" }],
    data_quality: "演示用跨场样本，长期记忆由确定性聚合得到；模型只负责解释趋势，不自动修改历史证据。",
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
      { url: "https://www.nowcoder.com/", title: "公开面经候选（演示资料）", platform: "牛客", summary: "静态演示用的合成候选：展示指标定义、A/B 实验与归因主题的相关度提示，不对应可验证原帖。", published_date: "", screening: { recommendation: "needs_review", relevance: 72, reason: "演示相关度提示，需打开真实原帖确认" } },
    ],
    trace: [
      { round: 1, reasoning: "先用公司+岗位+一面直搜", action: "search", query: "字节 产品经理 一面 面经", added: 0 },
      { round: 2, reasoning: "首轮无达标，换岗位同义词+平台", action: "search", query: "字节跳动 AI产品 实习 一面 牛客", added: 1 },
      { round: 3, reasoning: "已收集到 1 条待确认，预算内主动停", action: "stop", stop_reason: "达成部分目标，交人工摘录", added: 0 },
    ],
    stop_reason: "达成部分目标，交人工摘录",
    found_enough: false,
    search_meta: {
      platform: "xiaohongshu",
      platform_label: "小红书",
      queries_tried: ["site:xiaohongshu.com/explore 字节 产品经理 一面 指标 面经", "site:xiaohongshu.com 字节 AI产品 项目深挖"],
      result_count: 1,
      empty_reason: "",
    },
  };

  const jdAnalysis = { role_title: "AI 产品经理实习生", responsibilities: ["需求分析与用户反馈闭环", "跨团队推进产品迭代"], requirements: ["指标设计", "数据验证方案", "结构化拆解问题"], keywords: ["AI 产品", "指标", "实验", "协作"], interview_focus: ["项目深挖", "指标与归因", "产品 case"], search_topics: ["项目深挖", "指标与实验", "AI 产品 case"] };
  const overrides = window.AUTUMN_DEMO_DATA || {};
  return { interview, interviewSummary, resume, resumeSummary, research, memory, growthReport, skills, noteQuestions, agentResult, jdAnalysis, ...overrides };
})();

const DEMO_WRITE_MESSAGE = "这是静态演示版：可以浏览完整示例，但保存、AI 复盘、上传和联网搜索需要在完整版（本地或带后端的部署）中体验。";

// Route /api/* to canned data. Any write (non-GET) returns the demo message.
window.fetch = async (url, options = {}) => {
  const method = (options.method || 'GET').toUpperCase();
  const path = String(url).split('?')[0];
  const json = (body, status = 200) => new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });

  // These POST endpoints serve canned data so the demo can showcase the feature.
  if (path === '/api/extract-jd') return json({ ok: true, analysis: DEMO.jdAnalysis });
  if (path === '/api/note-questions') return json({ ok: true, questions: DEMO.noteQuestions });
  if (path === '/api/research/candidate') return json({ ok: true, research: DEMO.research, existing: true });
  if (path === '/api/research/discover') return json({ ok: true, candidates: DEMO.agentResult.collected, search_meta: DEMO.agentResult.search_meta });
  if (path === '/api/research/agent') return json({ ok: true, collected: DEMO.agentResult.collected, trace: DEMO.agentResult.trace, stop_reason: DEMO.agentResult.stop_reason, found_enough: DEMO.agentResult.found_enough, search_meta: DEMO.agentResult.search_meta });
  if (path === '/api/growth-report') return json({ ok: true, report: DEMO.growthReport, memory: DEMO.memory });

  if (method !== 'GET') {
    return json({ ok: false, error: DEMO_WRITE_MESSAGE }, 403);
  }
  if (path === '/api/health') return json({ ok: true, provider: 'gemini', model: 'gemini-3.1-flash-lite', active_provider: 'gemini', providers: ['gemini'], demo_mode: true, can_write: false });
  if (path === '/api/interviews') return json({ ok: true, interviews: [DEMO.interviewSummary] });
  if (path === `/api/interviews/${DEMO.interview.id}`) return json({ ok: true, interview: DEMO.interview });
  if (path === '/api/resumes') return json({ ok: true, resumes: [DEMO.resumeSummary] });
  if (path === `/api/resumes/${DEMO.resume.id}`) return json({ ok: true, resume: DEMO.resume });
  if (path === '/api/research') return json({ ok: true, research: [DEMO.research], stats: { total: 1, usable: 0, needs_review: 1 } });
  if (path === `/api/research/${DEMO.research.id}`) return json({ ok: true, research: DEMO.research });
  if (path === '/api/growth-memory') return json({ ok: true, memory: DEMO.memory });
  if (path === '/api/skills') return json({ ok: true, skills: DEMO.skills });
  return json({ ok: false, error: '静态演示中没有这个接口。' }, 404);
};

// ---- Original app logic below (unchanged) ----
const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];
const interviewForm = $('#interview-form');
const interviewFields = ['company', 'role', 'round_name', 'date', 'status', 'job_description', 'resume_context', 'transcript', 'personal_notes'];
const app = { selectedId: null, current: null, interviews: [], resumes: [], research: [], researchCandidates: [], resumeId: '', jdAnalysis: null, selectedAudio: null, selectedResumeFile: null, editingResumeId: null, editingResearchId: null, noteQuestions: [] };
const ACCESS_TOKEN_KEY = 'autumn-assistant-access-token';

async function api(url, options = {}) {
  const response = await fetch(url, { headers: { 'Content-Type': 'application/json', ...accessHeaders(), ...(options.headers || {}) }, ...options });
  const data = await response.json();
  if (response.status === 401) throw Error('需要访问口令。');
  if (!response.ok || !data.ok) throw Error(data.error || '请求没有完成。');
  return data;
}
function accessHeaders() { const token = sessionStorage.getItem(ACCESS_TOKEN_KEY); return token ? { 'X-App-Token': token } : {}; }
function toast(message) { const box = $('#toast'); box.textContent = message; box.hidden = false; clearTimeout(toast.timer); toast.timer = setTimeout(() => box.hidden = true, 5000); }
function busy(button, isBusy, label) { button.disabled = isBusy; button.textContent = isBusy ? label : button.dataset.label; }
function field(name) { return interviewForm.elements.namedItem(name); }
function setView(viewId) { $$('.view').forEach(view => view.classList.toggle('active', view.id === viewId)); $$('.nav-button').forEach(button => button.classList.toggle('active', button.dataset.view === viewId)); const titles = { 'review-view': '面试复盘', 'research-view': '面经资料库', 'growth-view': '阶段成长报告', 'resume-view': '简历库' }; $('#page-title').textContent = viewId === 'review-view' && app.current ? `${app.current.company} · ${app.current.role}` : titles[viewId]; $('#top-eyebrow').textContent = viewId === 'review-view' ? 'INTERVIEW REVIEW WORKSPACE · V3' : 'AUTUMN PM COACH · V3'; }
function interviewPayload() { const data = Object.fromEntries(interviewFields.map(name => [name, field(name).value])); const resume = app.resumes.find(item => item.id === app.resumeId); return { ...data, resume_id: app.resumeId, resume_name: resume?.name || app.current?.resume_name || '', jd_analysis: app.jdAnalysis, research_context: app.researchCandidates }; }

function renderInterviewList() { const list = $('#interview-list'); list.replaceChildren(); $('#interview-total').textContent = app.interviews.length; if (!app.interviews.length) { list.innerHTML = '<p class="empty-copy">还没有面试档案。</p>'; return; } app.interviews.forEach(item => { const button = document.createElement('button'); button.type = 'button'; button.className = `interview-item ${item.id === app.selectedId ? 'active' : ''}`; button.innerHTML = `<strong></strong><span></span>`; button.querySelector('strong').textContent = `${item.company} · ${item.role}`; button.querySelector('span').textContent = `${item.round_name || '面试'} · ${item.date || '未填写日期'}${item.has_review ? ' · 已复盘' : ''}`; button.onclick = () => loadInterview(item.id); list.append(button); }); }
function renderMetrics() { $('#metric-total').textContent = app.interviews.length; $('#metric-actions').textContent = app.interviews.reduce((sum, item) => sum + item.open_actions, 0); $('#metric-reviews').textContent = app.interviews.filter(item => item.has_review).length; const usable = app.research.filter(item => ['approved', 'auto_approved'].includes(item.status)).length; $('#metric-research').textContent = usable; $('#research-nav-count').textContent = usable; }
async function refreshInterviews() { app.interviews = (await api('/api/interviews')).interviews; renderInterviewList(); renderMetrics(); }
async function refreshResumes() { app.resumes = (await api('/api/resumes')).resumes; const select = $('#resume-select'); const old = app.resumeId; select.replaceChildren(new Option('暂不关联简历', '')); app.resumes.forEach(item => select.add(new Option(`${item.name}${item.target_role ? ' · ' + item.target_role : ''}`, item.id))); select.value = old; renderResumeList(); }
async function refreshResearch() { const data = await api('/api/research'); app.research = data.research; $('#research-total').textContent = data.stats.total; $('#research-usable').textContent = data.stats.usable; $('#research-review').textContent = data.stats.needs_review; renderResearchList(); renderMetrics(); }

function resetInterview() { app.selectedId = null; app.current = null; app.resumeId = ''; app.jdAnalysis = null; app.researchCandidates = []; app.selectedAudio = null; app.noteQuestions = []; renderNoteQuestions([]); renderJdResearch({ candidates: [] }); interviewFields.forEach(name => field(name).value = name === 'status' ? '待复盘' : ''); $('#resume-select').value = ''; $('#resume-preview').textContent = '选择一份简历；保存面试时会记录当时的内容快照。'; $('#jd-analysis').hidden = true; $('#audio-state').textContent = '尚未选择录音'; $('#consent-check').checked = false; $('#page-title').textContent = '新建一场面试复盘'; setSaveState('未保存'); setReviewState('等待资料'); renderReview(null); renderInterviewList(); setView('review-view'); }
function setSaveState(text, kind = '') { $('#save-state').textContent = text; $('#save-state').className = `save-state ${kind}`; }
function setReviewState(text, kind = '') { $('#review-state').textContent = text; $('#review-state').className = `review-state ${kind}`; }
function fillInterview(record) { interviewFields.forEach(name => field(name).value = record?.[name] || ''); app.resumeId = record?.resume_id || ''; app.jdAnalysis = record?.jd_analysis || null; app.researchCandidates = record?.research_context || []; $('#resume-select').value = app.resumeId; renderJd(); renderJdResearch({ candidates: app.researchCandidates }); $('#resume-preview').textContent = record?.resume_name ? `已关联：${record.resume_name}。此场面试已保存当时的简历快照。` : '暂未关联简历。'; }
async function loadInterview(id) { try { app.current = (await api(`/api/interviews/${id}`)).interview; app.selectedId = id; fillInterview(app.current); $('#page-title').textContent = `${app.current.company} · ${app.current.role}`; setSaveState('已保存', 'saved'); setReviewState(app.current.review ? '已生成' : '等待复盘', app.current.review ? 'ready' : ''); renderReview(app.current.review); renderInterviewList(); setView('review-view'); } catch (error) { toast(error.message); } }
async function saveInterview() { toast(DEMO_WRITE_MESSAGE); throw Error(DEMO_WRITE_MESSAGE); }

function reviewSection(title) { const section = document.createElement('section'); section.className = 'review-section'; const heading = document.createElement('h4'); heading.textContent = title; section.append(heading); return section; }
function renderCoachItems(root, title, items, detailKey) { if (!items?.length) return; const section = reviewSection(title); const grid = document.createElement('div'); grid.className = 'coach-grid'; items.forEach(item => { const card = document.createElement('article'); card.className = 'coach-item'; card.innerHTML = '<strong></strong><p class="evidence"></p><p class="detail"></p>'; card.querySelector('strong').textContent = item.title || '观察项'; card.querySelector('.evidence').textContent = `证据：${item.evidence || '未提供'}`; card.querySelector('.detail').textContent = item[detailKey] || ''; grid.append(card); }); section.append(grid); root.append(section); }
function renderReview(review) { const root = $('#review-content'); root.replaceChildren(); root.hidden = !review; $('#review-empty').hidden = !!review; if (!review) return; const summary = document.createElement('div'); summary.className = 'review-summary'; summary.textContent = review.summary || ''; root.append(summary); renderCoachItems(root, '表现亮点', review.strengths, 'why_it_worked'); renderCoachItems(root, '需要补强', review.gaps, 'improvement'); if (review.skill_diagnosis?.length) { const section = reviewSection('PM 能力诊断'); const grid = document.createElement('div'); grid.className = 'skill-score-grid'; review.skill_diagnosis.forEach(skill => { const card = document.createElement('article'); card.className = 'skill-score'; card.innerHTML = '<div><strong></strong><span></span></div><p class="evidence"></p><p></p><p class="next"></p>'; card.querySelector('strong').textContent = skill.skill_name || skill.skill_id || 'PM 能力'; card.querySelector('span').textContent = `${skill.score}/5`; card.querySelector('.evidence').textContent = `证据：${skill.evidence || '未提供'}`; card.querySelectorAll('p')[1].textContent = skill.diagnosis || ''; card.querySelector('.next').textContent = `练习：${skill.next_practice || ''}`; grid.append(card); }); section.append(grid); root.append(section); } if (review.questions?.length) { const section = reviewSection('逐题复盘'); const list = document.createElement('div'); list.className = 'question-list'; review.questions.forEach(question => { const card = document.createElement('article'); card.className = 'question-item'; card.innerHTML = '<div class="question-top"><strong></strong><span class="score"></span></div><p class="answer"></p><p class="evidence"></p><p class="assessment"></p><p class="next"></p>'; card.querySelector('strong').textContent = question.question; card.querySelector('.score').textContent = `${question.score}/5`; card.querySelector('.answer').textContent = question.answer_summary || ''; card.querySelector('.evidence').textContent = `证据：${question.evidence || ''}`; card.querySelector('.assessment').textContent = question.assessment || ''; card.querySelector('.next').textContent = `练习：${question.next_practice || ''}`; list.append(card); }); section.append(list); root.append(section); } if (review.action_plan?.length) { const section = reviewSection('下一步行动'); const list = document.createElement('div'); list.className = 'action-list'; review.action_plan.forEach(action => { const row = document.createElement('label'); row.className = `action-item ${action.done ? 'done' : ''}`; row.innerHTML = '<input type="checkbox" /><div><strong></strong><span></span></div><b></b>'; const checkbox = row.querySelector('input'); checkbox.checked = !!action.done; checkbox.onchange = () => { checkbox.checked = !!action.done; toast(DEMO_WRITE_MESSAGE); }; row.querySelector('strong').textContent = action.action; row.querySelector('span').textContent = action.reason; row.querySelector('b').textContent = action.priority || '中'; list.append(row); }); section.append(list); root.append(section); } if (review.follow_up) { const section = reviewSection('后续建议'); const text = document.createElement('div'); text.className = 'follow-up'; text.textContent = review.follow_up; section.append(text); root.append(section); } }
function renderShortTermMemory(review) { const section = reviewSection('本场短期记忆'); const card = document.createElement('div'); card.className = 'memory-callout'; card.innerHTML = '<strong></strong><p></p><span></span>'; const summary = review.score_summary || {}; card.querySelector('strong').textContent = summary.priority_skills?.length ? `优先训练：${summary.priority_skills.join('、')}` : '本场训练重点'; card.querySelector('p').textContent = review.follow_up || '把本场证据转成下一次可验收的练习。'; card.querySelector('span').textContent = `本场保留：${review.action_plan?.length || 0} 个行动 · 评分只表示训练优先级`; section.append(card); return section; }
function renderScoreSummary(review) {
  const summary = review.score_summary || {}; const quality = review.review_quality || {}; const card = document.createElement('section'); card.className = 'score-summary'; card.innerHTML = '<div class="score-summary-main"><span class="eyebrow">COACHING SIGNAL</span><strong></strong><span></span></div><div class="score-summary-stats"><div><span>证据覆盖</span><strong></strong></div><div><span>诊断置信度</span><strong></strong></div><div><span>训练阶段</span><strong></strong></div></div><p class="score-summary-note"></p>'; card.querySelector('.score-summary-main strong').textContent = summary.coach_score != null ? `${summary.coach_score}/100` : '待生成'; card.querySelector('.score-summary-main span:last-child').textContent = summary.training_band || '训练信号'; card.querySelector('.score-summary-stats div:nth-child(1) strong').textContent = `${Math.round((quality.evidence_coverage || 0) * 100)}%`; card.querySelector('.score-summary-stats div:nth-child(2) strong').textContent = quality.confidence || '未知'; card.querySelector('.score-summary-stats div:nth-child(3) strong').textContent = summary.priority_skills?.length ? `优先补强 ${summary.priority_skills.length} 项` : '暂无优先项'; card.querySelector('.score-summary-note').textContent = quality.data_quality || '评分仅用于训练优先级，不代表录用判断。'; return card;
}
function renderBasicSkillCard(skill) {
  const card = document.createElement('article'); card.className = 'skill-score'; card.innerHTML = '<div class="skill-score-head"><div><strong></strong><small></small></div><span></span></div><p class="evidence"></p><p class="skill-diagnosis-copy"></p><details><summary>展开评分依据</summary><div class="dimension-list"></div><div class="skill-gap-list"></div><div class="practice-plan"></div></details>'; card.querySelector('.skill-score-head strong').textContent = skill.skill_name || skill.skill_id || 'PM 能力'; card.querySelector('.skill-score-head small').textContent = `${skill.confidence || '未知'} 置信度 · 覆盖 ${Math.round((skill.evidence_coverage || 0) * 100)}%`; card.querySelector('.skill-score-head > span').textContent = `${skill.score}/5`; card.querySelector('.evidence').textContent = `证据：${skill.evidence || '未提供'}`; card.querySelector('.skill-diagnosis-copy').textContent = skill.diagnosis || '暂无诊断。'; const dimensions = card.querySelector('.dimension-list'); (skill.dimensions || []).forEach(dimension => { const row = document.createElement('div'); row.className = 'dimension-row'; row.innerHTML = '<div><strong></strong><span></span></div><p></p><small></small>'; row.querySelector('strong').textContent = dimension.label || dimension.id; row.querySelector('span').textContent = dimension.score == null ? '未展示' : `${dimension.score}/5`; row.querySelector('p').textContent = `状态：${dimension.status || 'unknown'} · ${dimension.rationale || ''}`; row.querySelector('small').textContent = `证据：${dimension.evidence || '未提供'}`; dimensions.append(row); }); const gaps = card.querySelector('.skill-gap-list'); (skill.gaps || []).forEach(gap => { const item = document.createElement('p'); item.textContent = `缺口 ${gap.severity || 'medium'}：${gap.impact || gap.gap_id} · 证据：${gap.evidence || '未提供'}`; gaps.append(item); }); const plan = skill.practice_plan || {}; if (plan.action || plan.prompt || plan.success_criteria?.length) { const practice = card.querySelector('.practice-plan'); practice.innerHTML = '<strong>下一步训练</strong><p></p><ul></ul><small></small>'; practice.querySelector('p').textContent = plan.prompt ? `${plan.action || '训练'}：${plan.prompt}` : (plan.action || skill.next_practice || '补充一轮练习'); (plan.success_criteria || []).forEach(item => { const li = document.createElement('li'); li.textContent = item; practice.querySelector('ul').append(li); }); practice.querySelector('small').textContent = plan.follow_up_question ? `下一条追问：${plan.follow_up_question}` : ''; } return card;
}
function renderSkillCard(skill) { const card = renderBasicSkillCard(skill); const profile = document.createElement('div'); profile.className = 'evidence-profile'; const labels = { specificity: '具体性', ownership: '个人归因', causality: '因果验证', result_quality: '结果质量', reflection: '复盘迁移', probe_resilience: '追问韧性' }; profile.textContent = `证据剖面：${Object.entries(labels).map(([key, label]) => `${label} ${skill.evidence_profile?.[key] ?? 0}/3`).join(' · ')}`; card.querySelector('.skill-diagnosis-copy').after(profile); return card; }
function renderReview(review) { const root = $('#review-content'); root.replaceChildren(); root.hidden = !review; $('#review-empty').hidden = !!review; if (!review) return; root.append(renderScoreSummary(review)); const summary = document.createElement('div'); summary.className = 'review-summary'; summary.textContent = review.summary || ''; root.append(summary); renderCoachItems(root, '表现亮点', review.strengths, 'why_it_worked'); renderCoachItems(root, '需要补强', review.gaps, 'improvement'); if (review.skill_diagnosis?.length) { const section = reviewSection('PM 能力诊断'); const grid = document.createElement('div'); grid.className = 'skill-score-grid'; review.skill_diagnosis.forEach(skill => grid.append(renderSkillCard(skill))); section.append(grid); root.append(section); } if (review.questions?.length) { const section = reviewSection('逐题复盘'); const list = document.createElement('div'); list.className = 'question-list'; review.questions.forEach(question => { const card = document.createElement('article'); card.className = 'question-item'; card.innerHTML = '<div class="question-top"><strong></strong><span class="score"></span></div><p class="answer"></p><p class="evidence"></p><p class="assessment"></p><p class="question-meta"></p><p class="next"></p>'; card.querySelector('strong').textContent = question.question; card.querySelector('.score').textContent = `${question.score}/5`; card.querySelector('.answer').textContent = question.answer_summary || ''; card.querySelector('.evidence').textContent = `证据：${question.evidence || ''}`; card.querySelector('.assessment').textContent = question.assessment || ''; card.querySelector('.question-meta').textContent = `证据状态：${question.evidence_quality || 'unknown'}${question.skills?.length ? ` · 能力：${question.skills.join('、')}` : ''}`; card.querySelector('.next').textContent = `练习：${question.next_practice || ''}`; list.append(card); }); section.append(list); root.append(section); } if (review.action_plan?.length) { const section = reviewSection('下一步行动'); const list = document.createElement('div'); list.className = 'action-list'; review.action_plan.forEach(action => { const row = document.createElement('label'); row.className = `action-item ${action.done ? 'done' : ''}`; row.innerHTML = '<input type="checkbox" /><div><strong></strong><span></span></div><b></b>'; const checkbox = row.querySelector('input'); checkbox.checked = !!action.done; checkbox.onchange = () => { checkbox.checked = !!action.done; toast(DEMO_WRITE_MESSAGE); }; row.querySelector('strong').textContent = action.action; row.querySelector('span').textContent = action.reason; row.querySelector('b').textContent = action.priority || '中'; list.append(row); }); section.append(list); root.append(section); } if (review.follow_up) { const section = reviewSection('后续建议'); const text = document.createElement('div'); text.className = 'follow-up'; text.textContent = review.follow_up; section.append(text); root.append(section); } }

function renderJd() { const root = $('#jd-analysis'); root.replaceChildren(); if (!app.jdAnalysis) { root.hidden = true; return; } root.hidden = false; const title = document.createElement('strong'); title.textContent = app.jdAnalysis.role_title || '岗位画像'; root.append(title); [['职责', 'responsibilities'], ['要求', 'requirements'], ['关键词', 'keywords'], ['可能追问', 'interview_focus'], ['搜索主题', 'search_topics']].forEach(([label, key]) => { if (!app.jdAnalysis[key]?.length) return; const group = document.createElement('div'); group.innerHTML = '<span></span><ul></ul>'; group.querySelector('span').textContent = label; app.jdAnalysis[key].forEach(item => { const li = document.createElement('li'); li.textContent = item; group.querySelector('ul').append(li); }); root.append(group); }); }
function renderJdResearch(data) { const root = $('#jd-research-handoff'); const candidates = data?.candidates || []; root.hidden = !candidates.length; if (!candidates.length) return; root.querySelector('strong').textContent = `已按 JD 自动发现 ${candidates.length} 条面经线索`; root.querySelector('span').textContent = 'Agent 已展示查询路径和公开页读取状态；静态演示不联网，候选仍不会直接成为事实证据。'; }
async function extractJd() { const button = $('#extract-jd'); busy(button, true, '解析并搜索演示...'); try { const data = await api('/api/extract-jd', { method: 'POST', body: JSON.stringify({ job_description: field('job_description').value }) }); app.jdAnalysis = data.analysis; app.researchCandidates = DEMO.agentResult.collected || []; renderJd(); renderJdResearch({ candidates: app.researchCandidates }); toast('静态演示：JD 已拆解，并已展示按 JD 自动识别的公开候选资料。'); } catch (error) { toast(error.message); } finally { busy(button, false, ''); } }
function demoWrite() { toast(DEMO_WRITE_MESSAGE); }

const NOTE_TYPE_CLASS = { '命中': 'hit', '补刀': 'gap', '通用': 'common' };
async function generateNoteQuestions() { const button = $('#note-questions'); busy(button, true, '正在出题...'); try { const data = await api('/api/note-questions', { method: 'POST', body: JSON.stringify({ job_description: field('job_description').value, resume_context: field('resume_context').value, jd_analysis: app.jdAnalysis, research_context: app.researchCandidates }) }); app.noteQuestions = data.questions || []; renderNoteQuestions(app.noteQuestions); } catch (error) { toast(error.message); } finally { busy(button, false, ''); } }
function renderNoteQuestions(questions) { const panel = $('#note-questions-panel'); panel.replaceChildren(); panel.hidden = !questions.length; if (!questions.length) return; questions.forEach(q => { const card = document.createElement('article'); card.className = 'note-question'; card.dataset.id = q.id; card.innerHTML = '<div class="note-question-head"><span class="note-badge"></span><strong></strong></div><p class="note-why"></p><textarea rows="2" placeholder="趁记忆新鲜，简短记下..."></textarea>'; const badge = card.querySelector('.note-badge'); badge.textContent = q.type || '问题'; badge.classList.add(NOTE_TYPE_CLASS[q.type] || 'common'); card.querySelector('strong').textContent = q.question; const researchBasis = q.research_basis?.length ? ` · 公开线索：${q.research_basis.join('；')}` : (app.researchCandidates.length ? ' · 已参考 JD 自动发现的公开线索' : ''); card.querySelector('.note-why').textContent = q.why_asked ? `为什么问：${q.why_asked}${researchBasis}` : researchBasis; panel.append(card); }); const actions = document.createElement('div'); actions.className = 'note-questions-actions'; const merge = document.createElement('button'); merge.type = 'button'; merge.className = 'secondary-button compact-button'; merge.textContent = '把问答整理进转写'; merge.onclick = collectNoteAnswersIntoTranscript; actions.append(merge); panel.append(actions); }
function collectNoteAnswersIntoTranscript() { const blocks = []; $$('#note-questions-panel .note-question').forEach(card => { const answer = card.querySelector('textarea').value.trim(); if (!answer) return; const question = card.querySelector('strong').textContent; blocks.push(`Q: ${question}\nA: ${answer}`); }); if (!blocks.length) { toast('先填写至少一个回答，再并入转写。'); return; } const transcript = field('transcript'); const addition = `【面后速记】\n${blocks.join('\n\n')}`; transcript.value = transcript.value.trim() ? `${transcript.value.trim()}\n\n${addition}` : addition; setSaveState('有未保存修改'); toast('已并入转写，可继续补充或生成复盘。'); }

function renderResumeList() { const list = $('#resume-list'); list.replaceChildren(); if (!app.resumes.length) { list.innerHTML = '<p class="empty-copy">还没有简历版本。</p>'; return; } app.resumes.forEach(item => { const button = document.createElement('button'); button.type = 'button'; button.className = `interview-item ${item.id === app.editingResumeId ? 'active' : ''}`; button.innerHTML = '<strong></strong><span></span>'; button.querySelector('strong').textContent = item.name; button.querySelector('span').textContent = item.target_role || '未填写目标岗位'; button.onclick = () => loadResume(item.id); list.append(button); }); }
function resetResume() { app.editingResumeId = null; app.selectedResumeFile = null; ['resume-name', 'resume-target', 'resume-content'].forEach(id => $(`#${id}`).value = ''); $('#resume-file').value = ''; $('#resume-file-consent').checked = false; $('#resume-file-state').textContent = '尚未选择文件'; renderResumeList(); }
async function loadResume(id) { try { const resume = (await api(`/api/resumes/${id}`)).resume; app.editingResumeId = id; $('#resume-name').value = resume.name; $('#resume-target').value = resume.target_role; $('#resume-content').value = resume.content; renderResumeList(); setView('resume-view'); } catch (error) { toast(error.message); } }
async function selectResume() { app.resumeId = $('#resume-select').value; if (!app.resumeId) { field('resume_context').value = ''; $('#resume-preview').textContent = '暂未关联简历。'; return; } try { const resume = (await api(`/api/resumes/${app.resumeId}`)).resume; field('resume_context').value = resume.content; $('#resume-preview').textContent = `已关联：${resume.name}。保存面试时会记录当时的内容快照。`; } catch (error) { toast(error.message); } }

function setResearchState(text, kind = '') { $('#research-state').textContent = text; $('#research-state').className = `save-state ${kind}`; }
function resetResearch() { app.editingResearchId = null; ['research-title', 'research-url', 'research-company', 'research-round', 'research-date', 'research-tags', 'research-source', 'research-comments', 'research-notes'].forEach(id => $(`#${id}`).value = ''); $('#research-platform').value = '牛客'; $('#research-role').value = '产品经理'; setResearchState('新资料'); renderResearchList(); }
function fillResearch(record) { app.editingResearchId = record.id; $('#research-title').value = record.title || ''; $('#research-url').value = record.url || ''; $('#research-platform').value = record.platform || '其他'; $('#research-company').value = record.company || ''; $('#research-role').value = record.role || ''; $('#research-round').value = record.round_name || ''; $('#research-date').value = record.published_date || ''; $('#research-tags').value = record.tags || ''; $('#research-source').value = record.source_text || ''; $('#research-comments').value = record.comments_text || ''; $('#research-notes').value = record.notes || ''; setResearchState(record.status === 'candidate' ? '待预审' : '已入库', record.status === 'candidate' ? '' : 'saved'); }
function statusLabel(status) { return ({ candidate: '待预审', auto_approved: 'AI 可用', needs_review: '待确认', approved: '已确认', dismissed: '不使用' })[status] || '未知'; }
function renderResearchList() { const list = $('#research-list'); list.replaceChildren(); if (!app.research.length) { list.innerHTML = '<p class="empty-copy">还没有公开资料。先搜索候选，再摘录原帖正文进行 AI 预审。</p>'; return; } app.research.forEach(record => { const card = document.createElement('article'); card.className = 'research-item'; const assessment = record.assessment || {}; card.innerHTML = '<div class="research-top"><div><a target="_blank" rel="noreferrer"></a><p></p></div><div class="badge-row"><span class="status-badge"></span><span class="confidence"></span></div></div><p class="research-summary"></p><div class="research-meta"></div><div class="research-actions"></div>'; const link = card.querySelector('a'); link.href = record.url; link.textContent = record.title; card.querySelector('.research-top p').textContent = [record.platform, record.company, record.role, record.round_name, record.published_date].filter(Boolean).join(' · '); const badge = card.querySelector('.status-badge'); badge.textContent = statusLabel(record.status); badge.classList.add(record.status); card.querySelector('.confidence').textContent = record.assessment && record.confidence ? `AI 置信度 ${record.confidence}%` : '仅演示字段'; card.querySelector('.research-summary').textContent = assessment.summary || (record.source_text || '').slice(0, 240) || '未填写摘要'; card.querySelector('.research-meta').textContent = assessment.concerns?.length ? `限制：${assessment.concerns.join('；')}` : '资料仅作为公开经验参考，复盘中会保留原链接与日期。'; const actions = card.querySelector('.research-actions'); const edit = document.createElement('button'); edit.className = 'secondary-button compact-button'; edit.textContent = '查看/编辑'; edit.onclick = () => { fillResearch(record); setView('research-view'); window.scrollTo({ top: 0, behavior: 'smooth' }); }; actions.append(edit); list.append(card); }); }
function renderDiscovery(candidates) { const root = $('#discovery-results'); root.replaceChildren(); if (!candidates.length) { root.innerHTML = '<p class="empty-copy">没有发现候选。已尝试小红书公开搜索，但结果稀疏；建议换同义词、轮次，或手动粘贴原帖链接。</p>'; return; } (candidates || []).forEach(candidate => { const card = document.createElement('article'); card.className = 'discovery-item'; card.innerHTML = '<a target="_blank" rel="noreferrer"></a><p></p><div><span></span><button class="secondary-button compact-button" type="button">带入资料库</button></div>'; const screening = candidate.screening || {}; const breakdown = screening.relevance_breakdown ? Object.entries(screening.relevance_breakdown).map(([key, value]) => `${key} ${value}`).join(' / ') : ''; card.querySelector('a').href = candidate.url; card.querySelector('a').textContent = candidate.title; card.querySelector('p').textContent = `${candidate.summary || '公开搜索候选'}${screening.reason ? ` · ${screening.reason}` : ''}`; card.querySelector('span').textContent = [candidate.platform, candidate.provenance_status || '待人工确认', screening.relevance != null ? `相关度 ${screening.relevance}/100` : '', breakdown].filter(Boolean).join(' · '); card.querySelector('button').onclick = demoWrite; root.append(card); }); }
function renderSearchMeta(meta) { const root = $('#search-meta'); root.replaceChildren(); root.hidden = !meta; if (!meta) return; const title = document.createElement('strong'); title.textContent = `${meta.platform_label || '全网'} · 已尝试 ${meta.queries_tried?.length || 0} 条查询 · 候选 ${meta.result_count || 0}`; root.append(title); (meta.queries_tried || []).forEach(query => { const item = document.createElement('span'); item.textContent = `查询：${query}`; root.append(item); }); if (meta.empty_reason) { const reason = document.createElement('span'); reason.textContent = `结果说明：${meta.empty_reason} 建议换公司别名、岗位同义词或轮次，也可以手动粘贴原帖链接。`; root.append(reason); } }
async function runResearchAgent() { const button = $('#agent-button'); busy(button, true, 'Agent 正在自主调研...'); try { const data = await api('/api/research/agent', { method: 'POST', body: JSON.stringify({ company: $('#discover-company').value, role: $('#discover-role').value, round_name: $('#discover-round').value, topic: $('#discover-topic').value, platform: $('#discover-platform').value }) }); renderSearchMeta(data.search_meta); renderAgentTrace(data.trace, data.stop_reason, data.found_enough); renderAgentCollected(data.collected || []); } catch (error) { toast(error.message); } finally { busy(button, false, ''); } }
async function discoverResearch(event) { event.preventDefault(); const button = $('#discover-button'); busy(button, true, '公开搜索演示...'); try { const data = await api('/api/research/discover', { method: 'POST', body: JSON.stringify({ company: $('#discover-company').value, role: $('#discover-role').value, round_name: $('#discover-round').value, topic: $('#discover-topic').value, platform: $('#discover-platform').value }) }); renderSearchMeta(data.search_meta); renderDiscovery(data.candidates || []); } catch (error) { toast(error.message); } finally { busy(button, false, ''); } }
function renderAgentTrace(trace, stopReason, foundEnough) { const root = $('#agent-trace'); root.replaceChildren(); root.hidden = !(trace && trace.length); if (!trace || !trace.length) return; trace.forEach(step => { const card = document.createElement('div'); card.className = 'agent-round'; card.innerHTML = '<strong></strong><p></p><p class="agent-query"></p>'; const label = step.action === 'stop' ? '停止' : step.action === 'fetch' ? '读取公开页' : '搜索'; card.querySelector('strong').textContent = `第 ${step.round} 轮 · ${label}${step.action === 'search' ? ` · 新增 ${step.added || 0}` : ''}${step.action === 'fetch' ? ` · 读取 ${step.fetched || 0}` : ''}`; card.querySelector('p').textContent = step.reasoning || ''; const q = card.querySelector('.agent-query'); if (step.query) q.textContent = `${step.action === 'fetch' ? '动作' : '查询词'}：${step.query}`; else q.remove(); root.append(card); }); const stop = document.createElement('p'); stop.className = 'agent-stop'; stop.textContent = `${foundEnough ? '已找够待确认资料' : '未达目标数量'} · ${stopReason || '结束'}`; root.append(stop); }
function renderAgentCollected(candidates) { const root = $('#discovery-results'); root.replaceChildren(); if (!candidates.length) { root.innerHTML = '<p class="empty-copy">Agent 未收集到待确认候选。</p>'; return; } candidates.forEach(candidate => { const card = document.createElement('article'); card.className = 'discovery-item'; card.innerHTML = '<a target="_blank" rel="noreferrer"></a><p></p><div><span></span><button class="secondary-button compact-button" type="button">带入资料库</button></div>'; card.querySelector('a').href = candidate.url; card.querySelector('a').textContent = candidate.title; const screening = candidate.screening || {}; card.querySelector('p').textContent = `${candidate.summary || '候选公开资料'}${screening.reason ? ` · 初筛：${screening.reason}` : ''}`; card.querySelector('span').textContent = [candidate.platform, candidate.published_date, screening.relevance != null ? `相关度 ${screening.relevance}` : ''].filter(Boolean).join(' · ') || '公开搜索结果'; card.querySelector('button').onclick = demoWrite; root.append(card); }); }

function renderAgentCollected(candidates) { const root = $('#discovery-results'); root.replaceChildren(); if (!candidates.length) { root.innerHTML = '<p class="empty-copy">Agent 未收集到通过来源校验的候选。</p>'; return; } candidates.forEach(candidate => { const card = document.createElement('article'); card.className = 'discovery-item'; card.innerHTML = '<a target="_blank" rel="noreferrer"></a><p></p><div><span></span><button class="secondary-button compact-button" type="button">带入资料库</button></div>'; card.querySelector('a').href = candidate.url; card.querySelector('a').textContent = candidate.title; const screening = candidate.screening || {}; const fetchLabel = candidate.fetch_status === 'fetched_metadata' ? '已自动读取公开页' : candidate.fetch_status === 'shell_only' ? '页面脚本壳' : '仍需人工确认'; card.querySelector('p').textContent = `${candidate.summary || '候选公开资料'}${screening.reason ? ` · 初筛：${screening.reason}` : ''}`; card.querySelector('span').textContent = [candidate.platform, candidate.platform_id ? `来源 ${candidate.platform_id}` : '', screening.relevance != null ? `相关度提示 ${screening.relevance}/100` : '', fetchLabel].filter(Boolean).join(' · '); card.querySelector('button').onclick = demoWrite; root.append(card); }); }

function renderMemory(memory) { const root = $('#memory-summary'); root.replaceChildren(); const items = [{ label: '已复盘面试', value: memory.reviewed_interviews || 0 }, { label: '待完成行动', value: memory.open_actions?.length || 0 }, { label: '重复薄弱点', value: memory.recurring_gaps?.length || 0 }]; items.forEach(item => { const block = document.createElement('div'); block.innerHTML = '<span></span><strong></strong>'; block.querySelector('span').textContent = item.label; block.querySelector('strong').textContent = item.value; root.append(block); }); const patterns = document.createElement('div'); patterns.className = 'memory-patterns'; patterns.innerHTML = '<p>当前重复出现</p>'; (memory.recurring_gaps || []).slice(0, 4).forEach(item => { const tag = document.createElement('span'); tag.textContent = `${item.title} · ${item.occurrences}次`; patterns.append(tag); }); if (!(memory.recurring_gaps || []).length) patterns.append('暂无足够数据'); root.append(patterns); }
function renderSkillList(skills) { const root = $('#skill-list'); root.replaceChildren(); skills.forEach(skill => { const item = document.createElement('div'); item.className = 'skill-definition'; item.innerHTML = '<strong></strong><span></span>'; item.querySelector('strong').textContent = skill.name; const anchors = skill.score_anchors || {}; item.querySelector('span').textContent = `${skill.focus} 评分锚点：1 ${anchors['1'] || '未展示'}；3 ${anchors['3'] || '合格'}；5 ${anchors['5'] || '优秀'}`; root.append(item); }); }
function renderStaticGrowthReport(report) { const root = $('#growth-content'); root.replaceChildren(); root.hidden = false; $('#growth-empty').hidden = true; const summary = document.createElement('div'); summary.className = 'review-summary'; summary.textContent = report.summary; root.append(summary); const assessment = reviewSection('长期记忆判断'); const assessmentText = document.createElement('p'); assessmentText.className = 'body-copy'; assessmentText.textContent = report.stage_assessment; assessment.append(assessmentText); root.append(assessment); renderCoachItems(root, '可观察到的变化', report.growth_signals, 'interpretation'); const patterns = reviewSection('重复出现的缺口'); const patternList = document.createElement('div'); patternList.className = 'pattern-list'; (report.recurring_patterns || []).forEach(pattern => { const row = document.createElement('article'); row.innerHTML = '<strong></strong><span></span><p></p><p class="next"></p>'; row.querySelector('strong').textContent = pattern.skill; row.querySelector('span').textContent = `${pattern.occurrences} 次`; row.querySelector('p').textContent = `证据：${pattern.evidence}`; row.querySelector('.next').textContent = pattern.recommendation; patternList.append(row); }); patterns.append(patternList); root.append(patterns); const training = reviewSection('下一步长期训练'); (report.priority_training || []).forEach(item => { const row = document.createElement('article'); row.className = 'coach-item'; row.innerHTML = '<strong></strong><p></p><p class="next"></p>'; row.querySelector('strong').textContent = item.action; row.querySelector('p').textContent = item.why_now; row.querySelector('.next').textContent = `验收标准：${item.success_criterion}`; training.append(row); }); root.append(training); const quality = reviewSection('数据边界'); const qualityText = document.createElement('p'); qualityText.className = 'body-copy'; qualityText.textContent = report.data_quality; quality.append(qualityText); root.append(quality); }
async function refreshGrowthMemory() { try { const data = await api('/api/growth-memory'); renderMemory(data.memory); $('#growth-state').textContent = data.memory.reviewed_interviews ? '已有记录' : '等待数据'; } catch (error) { toast(error.message); } }

interviewForm.onsubmit = event => { event.preventDefault(); demoWrite(); };
$('#new-interview').onclick = resetInterview;
$('#load-demo').onclick = () => loadInterview(DEMO.interview.id);
$('#review-button').onclick = demoWrite; $('#extract-jd').onclick = extractJd; $('#open-jd-research').onclick = () => setView('research-view'); $('#transcribe-audio').onclick = demoWrite; $('#resume-select').onchange = selectResume; $('#note-questions').onclick = generateNoteQuestions;
$('#audio-file').onchange = event => { app.selectedAudio = event.target.files?.[0] || null; $('#audio-state').textContent = app.selectedAudio ? `${app.selectedAudio.name} · ${(app.selectedAudio.size / 1024 / 1024).toFixed(1)} MB` : '尚未选择录音'; };
$('#transcript-file').onchange = async event => { const file = event.target.files?.[0]; if (!file) return; field('transcript').value = await file.text(); };
$('#new-resume').onclick = resetResume; $('#resume-form').onsubmit = event => { event.preventDefault(); demoWrite(); }; $('#resume-file').onchange = event => { app.selectedResumeFile = event.target.files?.[0] || null; $('#resume-file-state').textContent = app.selectedResumeFile ? `${app.selectedResumeFile.name} · ${(app.selectedResumeFile.size / 1024 / 1024).toFixed(1)} MB` : '尚未选择文件'; }; $('#parse-resume-file').onclick = demoWrite;
function showDemoGrowth() { renderStaticGrowthReport(DEMO.growthReport); $('#growth-empty')?.remove(); $('#growth-state').textContent = '演示报告'; toast('静态演示：展示的是合成跨场记忆，不写入真实记录。'); }
$('#research-new').onclick = resetResearch; $('#research-form').onsubmit = event => { event.preventDefault(); demoWrite(); }; $('#discover-form').onsubmit = discoverResearch; $('#agent-button').onclick = runResearchAgent; $('#generate-growth').onclick = showDemoGrowth;
$$('[data-view]').forEach(button => button.onclick = () => setView(button.dataset.view));
$$('button').forEach(button => button.dataset.label = button.textContent);
async function initializeApp() { resetInterview(); await Promise.all([refreshResumes(), refreshInterviews(), refreshResearch(), refreshGrowthMemory(), api('/api/skills').then(data => renderSkillList(data.skills))]); try { const data = await api('/api/health'); const demoTag = data.demo_mode && !data.can_write ? ' · 只读演示' : ''; $('#model-status').textContent = `${data.active_provider || 'gemini'} · ${data.model}${demoTag}`; $('.status-dot').className = 'status-dot ready'; } catch { $('#model-status').textContent = '静态演示'; $('.status-dot').className = 'status-dot ready'; } }
(async () => { try { await initializeApp(); await loadInterview(DEMO.interview.id); } catch (error) { toast(error.message); } })();
