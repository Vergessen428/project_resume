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
      { skill_id: "metrics_experiment", skill_name: "指标与实验", score: 2, evidence: "大意是用户多了报名就会多。", diagnosis: "把相关当因果，缺少归因意识。", next_practice: "练习拆解一个指标到可验证的因果链。" },
      { skill_id: "story_ownership", skill_name: "项目主导力", score: 4, evidence: "我把需求拆成两期，先上线报名提醒。", diagnosis: "有清晰的个人决策和取舍。", next_practice: "补上决策带来的量化结果。" },
    ],
    action_plan: [
      { id: "act1", action: "用北极星+护栏指标重写这个项目的成功定义", priority: "高", reason: "指标是本场最大失分点。", done: false },
      { id: "act2", action: "补齐项目关键数字并做一版量化结果收尾", priority: "中", reason: "结果模糊会削弱说服力。", done: false },
    ],
    follow_up: "下一场面试前，准备一个能讲清指标定义、归因和量化结果的完整项目故事。",
  };

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
    id: "r1", title: "字节 AI 产品经理实习 一面面经", url: "https://www.nowcoder.com/", platform: "牛客",
    company: "字节跳动", role: "产品经理", round_name: "一面", published_date: "2026-09-05",
    tags: "指标, case, 一面", status: "auto_approved", confidence: 86,
    source_text: "一面主要问了项目：如何定义指标、如何做 A/B 实验、遇到的取舍。面试官很关注指标口径和归因，会追问『为什么是这个指标』。整体偏考察数据敏感度和结构化表达。",
    comments_text: "",
    assessment: {
      recommendation: "auto_approved", confidence: 86,
      summary: "包含具体的一面考察点（指标定义、A/B 实验、归因追问），与目标岗位高度相关，可作为公开参考。",
      claims: ["一面会追问指标口径与归因", "考察 A/B 实验设计", "重视结构化表达"],
      credibility_signals: ["有具体题目细节", "与岗位相关度高"],
      concerns: ["单一来源，未交叉验证", "面试因人而异"],
      review_reason: "细节具体、相关性强、无明显矛盾，置信度达标可自动通过。",
    },
    updated_at: "2026-09-05T12:00:00",
  };

  const memory = {
    reviewed_interviews: 1, total_interviews: 1,
    recurring_gaps: [{ title: "指标定义与归因偏弱", occurrences: 1 }, { title: "结果缺乏量化", occurrences: 1 }],
    skill_summary: [{ skill_id: "metrics_experiment", average_score: 2, observations: 1, latest_score: 2 }],
    open_actions: [
      { action: "用北极星+护栏指标重写这个项目的成功定义", reason: "指标是本场最大失分点。", priority: "高", from: "示例科技 · 业务一面" },
    ],
    timeline: [{ id: "demo1", company: "示例科技", role: "AI 产品经理实习生", round_name: "业务一面", date: "2026-09-18" }],
  };

  const skills = [
    { id: "product_sense", name: "产品判断", focus: "用户问题、目标定义、方案取舍与优先级。" },
    { id: "story_ownership", name: "项目主导力", focus: "个人职责边界、关键动作、结果与复盘，而非团队泛泛叙述。" },
    { id: "metrics_experiment", name: "指标与实验", focus: "指标定义、拆解、归因、实验设计和量化结果。" },
    { id: "execution_collaboration", name: "推进与协作", focus: "跨团队分歧、资源约束、风险取舍和落地闭环。" },
    { id: "structured_communication", name: "结构化表达", focus: "结论先行、信息层次、追问应对与表达简洁度。" },
    { id: "business_context", name: "业务与岗位理解", focus: "将个人经历连接到 JD、公司业务和具体岗位场景。" },
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
      { url: "https://www.nowcoder.com/discuss/xxx", title: "字节 AI 产品经理实习 一面面经", platform: "牛客", summary: "提到指标定义、A/B 实验与归因追问，整体考察数据敏感度和结构化表达。", published_date: "2026-09-05", screening: { recommendation: "needs_review", relevance: 72, reason: "相关度高但需读原文确认" } },
    ],
    trace: [
      { round: 1, reasoning: "先用公司+岗位+一面直搜", action: "search", query: "字节 产品经理 一面 面经", added: 0 },
      { round: 2, reasoning: "首轮无达标，换岗位同义词+平台", action: "search", query: "字节跳动 AI产品 实习 一面 牛客", added: 1 },
      { round: 3, reasoning: "已收集到 1 条待确认，预算内主动停", action: "stop", stop_reason: "达成部分目标，交人工摘录", added: 0 },
    ],
    stop_reason: "达成部分目标，交人工摘录",
    found_enough: false,
  };

  return { interview, interviewSummary, resume, resumeSummary, research, memory, skills, noteQuestions, agentResult };
})();

const DEMO_WRITE_MESSAGE = "这是静态演示版：可以浏览完整示例，但保存、AI 复盘、上传和联网搜索需要在完整版（本地或带后端的部署）中体验。";

// Route /api/* to canned data. Any write (non-GET) returns the demo message.
window.fetch = async (url, options = {}) => {
  const method = (options.method || 'GET').toUpperCase();
  const path = String(url).split('?')[0];
  const json = (body, status = 200) => new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });

  // These POST endpoints serve canned data so the demo can showcase the feature.
  if (path === '/api/note-questions') return json({ ok: true, questions: DEMO.noteQuestions });
  if (path === '/api/research/agent') return json({ ok: true, collected: DEMO.agentResult.collected, trace: DEMO.agentResult.trace, stop_reason: DEMO.agentResult.stop_reason, found_enough: DEMO.agentResult.found_enough });

  if (method !== 'GET') {
    return json({ ok: false, error: DEMO_WRITE_MESSAGE }, 403);
  }
  if (path === '/api/health') return json({ ok: true, provider: 'gemini', model: 'gemini-3.1-flash-lite', active_provider: 'gemini', providers: ['gemini'], demo_mode: true, can_write: false });
  if (path === '/api/interviews') return json({ ok: true, interviews: [DEMO.interviewSummary] });
  if (path === `/api/interviews/${DEMO.interview.id}`) return json({ ok: true, interview: DEMO.interview });
  if (path === '/api/resumes') return json({ ok: true, resumes: [DEMO.resumeSummary] });
  if (path === `/api/resumes/${DEMO.resume.id}`) return json({ ok: true, resume: DEMO.resume });
  if (path === '/api/research') return json({ ok: true, research: [DEMO.research], stats: { total: 1, usable: 1, needs_review: 0 } });
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
const app = { selectedId: null, current: null, interviews: [], resumes: [], research: [], resumeId: '', jdAnalysis: null, selectedAudio: null, selectedResumeFile: null, editingResumeId: null, editingResearchId: null, noteQuestions: [] };
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
function interviewPayload() { const data = Object.fromEntries(interviewFields.map(name => [name, field(name).value])); const resume = app.resumes.find(item => item.id === app.resumeId); return { ...data, resume_id: app.resumeId, resume_name: resume?.name || app.current?.resume_name || '', jd_analysis: app.jdAnalysis }; }

function renderInterviewList() { const list = $('#interview-list'); list.replaceChildren(); $('#interview-total').textContent = app.interviews.length; if (!app.interviews.length) { list.innerHTML = '<p class="empty-copy">还没有面试档案。</p>'; return; } app.interviews.forEach(item => { const button = document.createElement('button'); button.type = 'button'; button.className = `interview-item ${item.id === app.selectedId ? 'active' : ''}`; button.innerHTML = `<strong></strong><span></span>`; button.querySelector('strong').textContent = `${item.company} · ${item.role}`; button.querySelector('span').textContent = `${item.round_name || '面试'} · ${item.date || '未填写日期'}${item.has_review ? ' · 已复盘' : ''}`; button.onclick = () => loadInterview(item.id); list.append(button); }); }
function renderMetrics() { $('#metric-total').textContent = app.interviews.length; $('#metric-actions').textContent = app.interviews.reduce((sum, item) => sum + item.open_actions, 0); $('#metric-reviews').textContent = app.interviews.filter(item => item.has_review).length; const usable = app.research.filter(item => ['approved', 'auto_approved'].includes(item.status)).length; $('#metric-research').textContent = usable; $('#research-nav-count').textContent = usable; }
async function refreshInterviews() { app.interviews = (await api('/api/interviews')).interviews; renderInterviewList(); renderMetrics(); }
async function refreshResumes() { app.resumes = (await api('/api/resumes')).resumes; const select = $('#resume-select'); const old = app.resumeId; select.replaceChildren(new Option('暂不关联简历', '')); app.resumes.forEach(item => select.add(new Option(`${item.name}${item.target_role ? ' · ' + item.target_role : ''}`, item.id))); select.value = old; renderResumeList(); }
async function refreshResearch() { const data = await api('/api/research'); app.research = data.research; $('#research-total').textContent = data.stats.total; $('#research-usable').textContent = data.stats.usable; $('#research-review').textContent = data.stats.needs_review; renderResearchList(); renderMetrics(); }

function resetInterview() { app.selectedId = null; app.current = null; app.resumeId = ''; app.jdAnalysis = null; app.selectedAudio = null; app.noteQuestions = []; renderNoteQuestions([]); interviewFields.forEach(name => field(name).value = name === 'status' ? '待复盘' : ''); $('#resume-select').value = ''; $('#resume-preview').textContent = '选择一份简历；保存面试时会记录当时的内容快照。'; $('#jd-analysis').hidden = true; $('#audio-state').textContent = '尚未选择录音'; $('#consent-check').checked = false; $('#page-title').textContent = '新建一场面试复盘'; setSaveState('未保存'); setReviewState('等待资料'); renderReview(null); renderInterviewList(); setView('review-view'); }
function setSaveState(text, kind = '') { $('#save-state').textContent = text; $('#save-state').className = `save-state ${kind}`; }
function setReviewState(text, kind = '') { $('#review-state').textContent = text; $('#review-state').className = `review-state ${kind}`; }
function fillInterview(record) { interviewFields.forEach(name => field(name).value = record?.[name] || ''); app.resumeId = record?.resume_id || ''; $('#resume-select').value = app.resumeId; app.jdAnalysis = record?.jd_analysis || null; renderJd(); $('#resume-preview').textContent = record?.resume_name ? `已关联：${record.resume_name}。此场面试已保存当时的简历快照。` : '暂未关联简历。'; }
async function loadInterview(id) { try { app.current = (await api(`/api/interviews/${id}`)).interview; app.selectedId = id; fillInterview(app.current); $('#page-title').textContent = `${app.current.company} · ${app.current.role}`; setSaveState('已保存', 'saved'); setReviewState(app.current.review ? '已生成' : '等待复盘', app.current.review ? 'ready' : ''); renderReview(app.current.review); renderInterviewList(); setView('review-view'); } catch (error) { toast(error.message); } }
async function saveInterview() { toast(DEMO_WRITE_MESSAGE); throw Error(DEMO_WRITE_MESSAGE); }

function reviewSection(title) { const section = document.createElement('section'); section.className = 'review-section'; const heading = document.createElement('h4'); heading.textContent = title; section.append(heading); return section; }
function renderCoachItems(root, title, items, detailKey) { if (!items?.length) return; const section = reviewSection(title); const grid = document.createElement('div'); grid.className = 'coach-grid'; items.forEach(item => { const card = document.createElement('article'); card.className = 'coach-item'; card.innerHTML = '<strong></strong><p class="evidence"></p><p class="detail"></p>'; card.querySelector('strong').textContent = item.title || '观察项'; card.querySelector('.evidence').textContent = `证据：${item.evidence || '未提供'}`; card.querySelector('.detail').textContent = item[detailKey] || ''; grid.append(card); }); section.append(grid); root.append(section); }
function renderReview(review) { const root = $('#review-content'); root.replaceChildren(); root.hidden = !review; $('#review-empty').hidden = !!review; if (!review) return; const summary = document.createElement('div'); summary.className = 'review-summary'; summary.textContent = review.summary || ''; root.append(summary); renderCoachItems(root, '表现亮点', review.strengths, 'why_it_worked'); renderCoachItems(root, '需要补强', review.gaps, 'improvement'); if (review.skill_diagnosis?.length) { const section = reviewSection('PM 能力诊断'); const grid = document.createElement('div'); grid.className = 'skill-score-grid'; review.skill_diagnosis.forEach(skill => { const card = document.createElement('article'); card.className = 'skill-score'; card.innerHTML = '<div><strong></strong><span></span></div><p class="evidence"></p><p></p><p class="next"></p>'; card.querySelector('strong').textContent = skill.skill_name || skill.skill_id || 'PM 能力'; card.querySelector('span').textContent = `${skill.score}/5`; card.querySelector('.evidence').textContent = `证据：${skill.evidence || '未提供'}`; card.querySelectorAll('p')[1].textContent = skill.diagnosis || ''; card.querySelector('.next').textContent = `练习：${skill.next_practice || ''}`; grid.append(card); }); section.append(grid); root.append(section); } if (review.questions?.length) { const section = reviewSection('逐题复盘'); const list = document.createElement('div'); list.className = 'question-list'; review.questions.forEach(question => { const card = document.createElement('article'); card.className = 'question-item'; card.innerHTML = '<div class="question-top"><strong></strong><span class="score"></span></div><p class="answer"></p><p class="evidence"></p><p class="assessment"></p><p class="next"></p>'; card.querySelector('strong').textContent = question.question; card.querySelector('.score').textContent = `${question.score}/5`; card.querySelector('.answer').textContent = question.answer_summary || ''; card.querySelector('.evidence').textContent = `证据：${question.evidence || ''}`; card.querySelector('.assessment').textContent = question.assessment || ''; card.querySelector('.next').textContent = `练习：${question.next_practice || ''}`; list.append(card); }); section.append(list); root.append(section); } if (review.action_plan?.length) { const section = reviewSection('下一步行动'); const list = document.createElement('div'); list.className = 'action-list'; review.action_plan.forEach(action => { const row = document.createElement('label'); row.className = `action-item ${action.done ? 'done' : ''}`; row.innerHTML = '<input type="checkbox" /><div><strong></strong><span></span></div><b></b>'; const checkbox = row.querySelector('input'); checkbox.checked = !!action.done; checkbox.onchange = () => { checkbox.checked = !!action.done; toast(DEMO_WRITE_MESSAGE); }; row.querySelector('strong').textContent = action.action; row.querySelector('span').textContent = action.reason; row.querySelector('b').textContent = action.priority || '中'; list.append(row); }); section.append(list); root.append(section); } if (review.follow_up) { const section = reviewSection('后续建议'); const text = document.createElement('div'); text.className = 'follow-up'; text.textContent = review.follow_up; section.append(text); root.append(section); } }
function renderJd() { const root = $('#jd-analysis'); root.replaceChildren(); if (!app.jdAnalysis) { root.hidden = true; return; } root.hidden = false; const title = document.createElement('strong'); title.textContent = app.jdAnalysis.role_title || '岗位画像'; root.append(title); [['职责', 'responsibilities'], ['要求', 'requirements'], ['关键词', 'keywords'], ['可能追问', 'interview_focus']].forEach(([label, key]) => { if (!app.jdAnalysis[key]?.length) return; const group = document.createElement('div'); group.innerHTML = '<span></span><ul></ul>'; group.querySelector('span').textContent = label; app.jdAnalysis[key].forEach(item => { const li = document.createElement('li'); li.textContent = item; group.querySelector('ul').append(li); }); root.append(group); }); }
function demoWrite() { toast(DEMO_WRITE_MESSAGE); }

const NOTE_TYPE_CLASS = { '命中': 'hit', '补刀': 'gap', '通用': 'common' };
async function generateNoteQuestions() { const button = $('#note-questions'); busy(button, true, '正在出题...'); try { const data = await api('/api/note-questions', { method: 'POST', body: JSON.stringify({ job_description: field('job_description').value, resume_context: field('resume_context').value }) }); app.noteQuestions = data.questions || []; renderNoteQuestions(app.noteQuestions); } catch (error) { toast(error.message); } finally { busy(button, false, ''); } }
function renderNoteQuestions(questions) { const panel = $('#note-questions-panel'); panel.replaceChildren(); panel.hidden = !questions.length; if (!questions.length) return; questions.forEach(q => { const card = document.createElement('article'); card.className = 'note-question'; card.dataset.id = q.id; card.innerHTML = '<div class="note-question-head"><span class="note-badge"></span><strong></strong></div><p class="note-why"></p><textarea rows="2" placeholder="趁记忆新鲜，简短记下..."></textarea>'; const badge = card.querySelector('.note-badge'); badge.textContent = q.type || '问题'; badge.classList.add(NOTE_TYPE_CLASS[q.type] || 'common'); card.querySelector('strong').textContent = q.question; card.querySelector('.note-why').textContent = q.why_asked ? `为什么问：${q.why_asked}` : ''; panel.append(card); }); const actions = document.createElement('div'); actions.className = 'note-questions-actions'; const merge = document.createElement('button'); merge.type = 'button'; merge.className = 'secondary-button compact-button'; merge.textContent = '把问答整理进转写'; merge.onclick = collectNoteAnswersIntoTranscript; actions.append(merge); panel.append(actions); }
function collectNoteAnswersIntoTranscript() { const blocks = []; $$('#note-questions-panel .note-question').forEach(card => { const answer = card.querySelector('textarea').value.trim(); if (!answer) return; const question = card.querySelector('strong').textContent; blocks.push(`Q: ${question}\nA: ${answer}`); }); if (!blocks.length) { toast('先填写至少一个回答，再并入转写。'); return; } const transcript = field('transcript'); const addition = `【面后速记】\n${blocks.join('\n\n')}`; transcript.value = transcript.value.trim() ? `${transcript.value.trim()}\n\n${addition}` : addition; setSaveState('有未保存修改'); toast('已并入转写，可继续补充或生成复盘。'); }

function renderResumeList() { const list = $('#resume-list'); list.replaceChildren(); if (!app.resumes.length) { list.innerHTML = '<p class="empty-copy">还没有简历版本。</p>'; return; } app.resumes.forEach(item => { const button = document.createElement('button'); button.type = 'button'; button.className = `interview-item ${item.id === app.editingResumeId ? 'active' : ''}`; button.innerHTML = '<strong></strong><span></span>'; button.querySelector('strong').textContent = item.name; button.querySelector('span').textContent = item.target_role || '未填写目标岗位'; button.onclick = () => loadResume(item.id); list.append(button); }); }
function resetResume() { app.editingResumeId = null; app.selectedResumeFile = null; ['resume-name', 'resume-target', 'resume-content'].forEach(id => $(`#${id}`).value = ''); $('#resume-file').value = ''; $('#resume-file-consent').checked = false; $('#resume-file-state').textContent = '尚未选择文件'; renderResumeList(); }
async function loadResume(id) { try { const resume = (await api(`/api/resumes/${id}`)).resume; app.editingResumeId = id; $('#resume-name').value = resume.name; $('#resume-target').value = resume.target_role; $('#resume-content').value = resume.content; renderResumeList(); setView('resume-view'); } catch (error) { toast(error.message); } }
async function selectResume() { app.resumeId = $('#resume-select').value; if (!app.resumeId) { field('resume_context').value = ''; $('#resume-preview').textContent = '暂未关联简历。'; return; } try { const resume = (await api(`/api/resumes/${app.resumeId}`)).resume; field('resume_context').value = resume.content; $('#resume-preview').textContent = `已关联：${resume.name}。保存面试时会记录当时的内容快照。`; } catch (error) { toast(error.message); } }

function setResearchState(text, kind = '') { $('#research-state').textContent = text; $('#research-state').className = `save-state ${kind}`; }
function resetResearch() { app.editingResearchId = null; ['research-title', 'research-url', 'research-company', 'research-round', 'research-date', 'research-tags', 'research-source', 'research-comments', 'research-notes'].forEach(id => $(`#${id}`).value = ''); $('#research-platform').value = '牛客'; $('#research-role').value = '产品经理'; setResearchState('新资料'); renderResearchList(); }
function fillResearch(record) { app.editingResearchId = record.id; $('#research-title').value = record.title || ''; $('#research-url').value = record.url || ''; $('#research-platform').value = record.platform || '其他'; $('#research-company').value = record.company || ''; $('#research-role').value = record.role || ''; $('#research-round').value = record.round_name || ''; $('#research-date').value = record.published_date || ''; $('#research-tags').value = record.tags || ''; $('#research-source').value = record.source_text || ''; $('#research-comments').value = record.comments_text || ''; $('#research-notes').value = record.notes || ''; setResearchState(record.status === 'candidate' ? '待预审' : '已入库', record.status === 'candidate' ? '' : 'saved'); }
function statusLabel(status) { return ({ candidate: '待预审', auto_approved: 'AI 可用', needs_review: '待确认', approved: '已确认', dismissed: '不使用' })[status] || '未知'; }
function renderResearchList() { const list = $('#research-list'); list.replaceChildren(); if (!app.research.length) { list.innerHTML = '<p class="empty-copy">还没有公开资料。先搜索候选，再摘录原帖正文进行 AI 预审。</p>'; return; } app.research.forEach(record => { const card = document.createElement('article'); card.className = 'research-item'; const assessment = record.assessment || {}; card.innerHTML = '<div class="research-top"><div><a target="_blank" rel="noreferrer"></a><p></p></div><div class="badge-row"><span class="status-badge"></span><span class="confidence"></span></div></div><p class="research-summary"></p><div class="research-meta"></div><div class="research-actions"></div>'; const link = card.querySelector('a'); link.href = record.url; link.textContent = record.title; card.querySelector('.research-top p').textContent = [record.platform, record.company, record.role, record.round_name, record.published_date].filter(Boolean).join(' · '); const badge = card.querySelector('.status-badge'); badge.textContent = statusLabel(record.status); badge.classList.add(record.status); card.querySelector('.confidence').textContent = record.assessment ? `AI 置信度 ${record.confidence}%` : '尚未预审'; card.querySelector('.research-summary').textContent = assessment.summary || (record.source_text || '').slice(0, 240) || '未填写摘要'; card.querySelector('.research-meta').textContent = assessment.concerns?.length ? `限制：${assessment.concerns.join('；')}` : '资料仅作为公开经验参考，复盘中会保留原链接与日期。'; const actions = card.querySelector('.research-actions'); const edit = document.createElement('button'); edit.className = 'secondary-button compact-button'; edit.textContent = '查看/编辑'; edit.onclick = () => { fillResearch(record); setView('research-view'); window.scrollTo({ top: 0, behavior: 'smooth' }); }; actions.append(edit); list.append(card); }); }
function renderDiscovery(candidates) { const root = $('#discovery-results'); root.replaceChildren(); if (!candidates.length) { root.innerHTML = '<p class="empty-copy">没有发现适合的候选资料。换一个更具体的公司、岗位或主题再试。</p>'; return; } }
async function runResearchAgent() { const button = $('#agent-button'); busy(button, true, 'Agent 正在自主调研...'); try { const data = await api('/api/research/agent', { method: 'POST', body: JSON.stringify({ company: $('#discover-company').value, role: $('#discover-role').value, round_name: $('#discover-round').value, topic: $('#discover-topic').value }) }); renderAgentTrace(data.trace, data.stop_reason, data.found_enough); renderAgentCollected(data.collected || []); } catch (error) { toast(error.message); } finally { busy(button, false, ''); } }
function renderAgentTrace(trace, stopReason, foundEnough) { const root = $('#agent-trace'); root.replaceChildren(); root.hidden = !(trace && trace.length); if (!trace || !trace.length) return; trace.forEach(step => { const card = document.createElement('div'); card.className = 'agent-round'; card.innerHTML = '<strong></strong><p></p><p class="agent-query"></p>'; card.querySelector('strong').textContent = `第 ${step.round} 轮 · ${step.action === 'stop' ? '停止' : '搜索'}${step.action === 'search' ? ` · 新增 ${step.added || 0}` : ''}`; card.querySelector('p').textContent = step.reasoning || ''; const q = card.querySelector('.agent-query'); if (step.query) q.textContent = `查询词：${step.query}`; else q.remove(); root.append(card); }); const stop = document.createElement('p'); stop.className = 'agent-stop'; stop.textContent = `${foundEnough ? '已找够待确认资料' : '未达目标数量'} · ${stopReason || '结束'}`; root.append(stop); }
function renderAgentCollected(candidates) { const root = $('#discovery-results'); root.replaceChildren(); if (!candidates.length) { root.innerHTML = '<p class="empty-copy">Agent 未收集到待确认候选。</p>'; return; } candidates.forEach(candidate => { const card = document.createElement('article'); card.className = 'discovery-item'; card.innerHTML = '<a target="_blank" rel="noreferrer"></a><p></p><div><span></span><button class="secondary-button compact-button" type="button">带入资料库</button></div>'; card.querySelector('a').href = candidate.url; card.querySelector('a').textContent = candidate.title; const screening = candidate.screening || {}; card.querySelector('p').textContent = `${candidate.summary || '候选公开资料'}${screening.reason ? ` · 初筛：${screening.reason}` : ''}`; card.querySelector('span').textContent = [candidate.platform, candidate.published_date, screening.relevance != null ? `相关度 ${screening.relevance}` : ''].filter(Boolean).join(' · ') || '公开搜索结果'; card.querySelector('button').onclick = demoWrite; root.append(card); }); }

function renderMemory(memory) { const root = $('#memory-summary'); root.replaceChildren(); const items = [{ label: '已复盘面试', value: memory.reviewed_interviews || 0 }, { label: '待完成行动', value: memory.open_actions?.length || 0 }, { label: '重复薄弱点', value: memory.recurring_gaps?.length || 0 }]; items.forEach(item => { const block = document.createElement('div'); block.innerHTML = '<span></span><strong></strong>'; block.querySelector('span').textContent = item.label; block.querySelector('strong').textContent = item.value; root.append(block); }); const patterns = document.createElement('div'); patterns.className = 'memory-patterns'; patterns.innerHTML = '<p>当前重复出现</p>'; (memory.recurring_gaps || []).slice(0, 4).forEach(item => { const tag = document.createElement('span'); tag.textContent = `${item.title} · ${item.occurrences}次`; patterns.append(tag); }); if (!(memory.recurring_gaps || []).length) patterns.append('暂无足够数据'); root.append(patterns); }
function renderSkillList(skills) { const root = $('#skill-list'); root.replaceChildren(); skills.forEach(skill => { const item = document.createElement('div'); item.className = 'skill-definition'; item.innerHTML = '<strong></strong><span></span>'; item.querySelector('strong').textContent = skill.name; item.querySelector('span').textContent = skill.focus; root.append(item); }); }
function renderGrowthReport(report) { const root = $('#growth-content'); root.replaceChildren(); root.hidden = !report; $('#growth-empty').hidden = !!report; if (!report) return; }
async function refreshGrowthMemory() { try { const data = await api('/api/growth-memory'); renderMemory(data.memory); $('#growth-state').textContent = data.memory.reviewed_interviews ? '已有记录' : '等待数据'; } catch (error) { toast(error.message); } }

interviewForm.onsubmit = event => { event.preventDefault(); demoWrite(); };
$('#new-interview').onclick = resetInterview;
$('#load-demo').onclick = () => loadInterview(DEMO.interview.id);
$('#review-button').onclick = demoWrite; $('#extract-jd').onclick = demoWrite; $('#transcribe-audio').onclick = demoWrite; $('#resume-select').onchange = selectResume; $('#note-questions').onclick = generateNoteQuestions;
$('#audio-file').onchange = event => { app.selectedAudio = event.target.files?.[0] || null; $('#audio-state').textContent = app.selectedAudio ? `${app.selectedAudio.name} · ${(app.selectedAudio.size / 1024 / 1024).toFixed(1)} MB` : '尚未选择录音'; };
$('#transcript-file').onchange = async event => { const file = event.target.files?.[0]; if (!file) return; field('transcript').value = await file.text(); };
$('#new-resume').onclick = resetResume; $('#resume-form').onsubmit = event => { event.preventDefault(); demoWrite(); }; $('#resume-file').onchange = event => { app.selectedResumeFile = event.target.files?.[0] || null; $('#resume-file-state').textContent = app.selectedResumeFile ? `${app.selectedResumeFile.name} · ${(app.selectedResumeFile.size / 1024 / 1024).toFixed(1)} MB` : '尚未选择文件'; }; $('#parse-resume-file').onclick = demoWrite;
$('#research-new').onclick = resetResearch; $('#research-form').onsubmit = event => { event.preventDefault(); demoWrite(); }; $('#discover-form').onsubmit = event => { event.preventDefault(); demoWrite(); }; $('#agent-button').onclick = runResearchAgent; $('#generate-growth').onclick = demoWrite;
$$('[data-view]').forEach(button => button.onclick = () => setView(button.dataset.view));
$$('button').forEach(button => button.dataset.label = button.textContent);
async function initializeApp() { resetInterview(); await Promise.all([refreshResumes(), refreshInterviews(), refreshResearch(), refreshGrowthMemory(), api('/api/skills').then(data => renderSkillList(data.skills))]); try { const data = await api('/api/health'); const demoTag = data.demo_mode && !data.can_write ? ' · 只读演示' : ''; $('#model-status').textContent = `${data.active_provider || 'gemini'} · ${data.model}${demoTag}`; $('.status-dot').className = 'status-dot ready'; } catch { $('#model-status').textContent = '静态演示'; $('.status-dot').className = 'status-dot ready'; } }
(async () => { try { await initializeApp(); await loadInterview(DEMO.interview.id); } catch (error) { toast(error.message); } })();
