import type { Language } from "@/lib/i18n";


export const KNOWN_PROJECTION_ISSUE_CODES = [
  "phase_started_while_another_phase_open",
  "phase_completed_without_open_phase",
  "phase_completed_mismatch",
  "duplicate_exile_record",
  "duplicate_death_record",
  "multiple_exit_records",
  "event_actor_already_out",
  "event_target_already_out",
  "candidate_withdrew_without_declaration",
  "sheriff_elected_while_badge_held",
  "badge_transfer_without_current_sheriff",
  "badge_transfer_actor_mismatch",
  "badge_destroyed_without_holder",
  "badge_reassigned_after_destroyed",
  "duplicate_vote_by_voter",
  "explicit_tie_mismatch",
  "multiple_explicit_outcomes_for_ballot",
  "multiple_night_resolved_events",
  "duplicate_active_logical_sequence",
  "unknown_participant_reference",
  "unsupported_event_type",
  "event_game_mismatch",
  "missing_format_snapshot",
  "participant_count_snapshot_mismatch",
  "recorded_role_not_in_snapshot",
  "invalid_projection_payload",
] as const;

export type KnownProjectionIssueCode = typeof KNOWN_PROJECTION_ISSUE_CODES[number];

type IssueCopy = {
  title: string;
  explanation: string;
};

const ISSUE_MESSAGES: Record<KnownProjectionIssueCode, Record<Language, IssueCopy>> = {
  phase_started_while_another_phase_open: {
    zh: { title: "阶段开始记录重叠", explanation: "上一显式阶段尚未结束时又记录了新的阶段开始，请检查相关事件。" },
    en: { title: "Overlapping phase starts", explanation: "A new explicit phase started while another remained open. Review the linked records." },
  },
  phase_completed_without_open_phase: {
    zh: { title: "阶段结束缺少开始记录", explanation: "系统未找到对应的显式阶段开始记录。" },
    en: { title: "Phase completed without a start", explanation: "No matching explicit phase-start record was found." },
  },
  phase_completed_mismatch: {
    zh: { title: "阶段开始与结束不一致", explanation: "结束事件的轮次或阶段与当前开放记录不一致。" },
    en: { title: "Phase completion mismatch", explanation: "The completion record differs from the open phase or round." },
  },
  duplicate_exile_record: {
    zh: { title: "存在多条放逐记录", explanation: "同一参与者有多条有效放逐事实，请检查是否应纠正事件。" },
    en: { title: "Multiple exile records", explanation: "The participant has more than one effective exile record." },
  },
  duplicate_death_record: {
    zh: { title: "存在多条死亡记录", explanation: "同一参与者有多条有效死亡事实，请检查是否应纠正事件。" },
    en: { title: "Multiple death records", explanation: "The participant has more than one effective death record." },
  },
  multiple_exit_records: {
    zh: { title: "存在多类出局记录", explanation: "该参与者同时或重复出现明确出局记录，系统保留全部事实。" },
    en: { title: "Multiple exit records", explanation: "Several explicit exit records exist; the projection retains every fact." },
  },
  event_actor_already_out: {
    zh: { title: "行动者此前已有出局记录", explanation: "这只是记录一致性提示，不代表规则违规判定。" },
    en: { title: "Actor already had an exit record", explanation: "This is a consistency notice, not a rules violation." },
  },
  event_target_already_out: {
    zh: { title: "目标此前已有出局记录", explanation: "这只是记录一致性提示，不代表规则违规判定。" },
    en: { title: "Target already had an exit record", explanation: "This is a consistency notice, not a rules violation." },
  },
  candidate_withdrew_without_declaration: {
    zh: { title: "退选缺少参选记录", explanation: "候选人未见明确参选记录即出现退选事实。" },
    en: { title: "Withdrawal without declaration", explanation: "The candidate withdrew without a recorded declaration." },
  },
  sheriff_elected_while_badge_held: {
    zh: { title: "已有警长时再次当选", explanation: "存在多个明确警长记录，当前展示采用最后一条明确事实。" },
    en: { title: "Sheriff elected while badge held", explanation: "Multiple explicit sheriff records exist; the latest fact is displayed." },
  },
  badge_transfer_without_current_sheriff: {
    zh: { title: "警徽移交缺少当前持有人", explanation: "移交前未找到明确的当前警长记录。" },
    en: { title: "Badge transfer without a holder", explanation: "No explicit current sheriff was recorded before the transfer." },
  },
  badge_transfer_actor_mismatch: {
    zh: { title: "警徽移交者不一致", explanation: "移交事件的行动者与当前记录的警长不同。" },
    en: { title: "Badge transfer actor mismatch", explanation: "The transfer actor differs from the recorded sheriff." },
  },
  badge_destroyed_without_holder: {
    zh: { title: "撕毁警徽缺少持有人", explanation: "撕毁前未找到明确的当前警长记录。" },
    en: { title: "Badge destroyed without a holder", explanation: "No explicit badge holder was recorded before destruction." },
  },
  badge_reassigned_after_destroyed: {
    zh: { title: "警徽撕毁后重新出现持有人", explanation: "系统保留后续明确记录，并提示检查前后事实。" },
    en: { title: "Badge reassigned after destruction", explanation: "The later explicit holder is retained; review the linked facts." },
  },
  duplicate_vote_by_voter: {
    zh: { title: "同一投票人存在多条有效票", explanation: "系统不会采用最后一票覆盖，无法形成唯一计算票型。" },
    en: { title: "Duplicate effective votes", explanation: "The projection does not choose a last vote, so no unique tally is available." },
  },
  explicit_tie_mismatch: {
    zh: { title: "平票记录与票数不一致", explanation: "显式平票候选人与无歧义票数计算结果不同。" },
    en: { title: "Explicit tie differs from tally", explanation: "The recorded tie candidates differ from the unambiguous arithmetic tally." },
  },
  multiple_explicit_outcomes_for_ballot: {
    zh: { title: "投票存在多个明确结果", explanation: "同一票轮出现多个结果事实，系统不会自行选择正确结果。" },
    en: { title: "Multiple ballot outcomes", explanation: "Several explicit outcomes exist; the projection does not choose one." },
  },
  multiple_night_resolved_events: {
    zh: { title: "夜间存在多条结算记录", explanation: "同一轮夜晚有多条有效结算事实。" },
    en: { title: "Multiple night resolutions", explanation: "The same night has several effective resolution records." },
  },
  duplicate_active_logical_sequence: {
    zh: { title: "有效逻辑位置重复", explanation: "有效时间线中同一逻辑位置出现多条记录。" },
    en: { title: "Duplicate active logical position", explanation: "Several active records occupy the same logical position." },
  },
  unknown_participant_reference: {
    zh: { title: "事件引用未知参与者", explanation: "事件中的参与者标识不属于当前加载的本局参与者。" },
    en: { title: "Unknown participant reference", explanation: "An event references a participant absent from this game context." },
  },
  unsupported_event_type: {
    zh: { title: "投影器尚不支持该事件", explanation: "该事件不会影响推导状态，其余有效事件仍会继续应用。" },
    en: { title: "Unsupported event type", explanation: "This event has no projection effect; remaining effective events still apply." },
  },
  event_game_mismatch: {
    zh: { title: "事件与对局不一致", explanation: "事件记录的 game_id 与当前对局不同。" },
    en: { title: "Event belongs to another game", explanation: "The event game identifier differs from the current game." },
  },
  missing_format_snapshot: {
    zh: { title: "缺少版型快照", explanation: "该对局缺少预期的冻结版型上下文，投影仍尽量返回记录状态。" },
    en: { title: "Format snapshot missing", explanation: "Expected frozen format context is absent; recorded state is still projected." },
  },
  participant_count_snapshot_mismatch: {
    zh: { title: "参与者数量与快照不一致", explanation: "当前参与者数量和冻结版型人数不同。" },
    en: { title: "Participant count differs from snapshot", explanation: "The current participant count differs from the frozen format count." },
  },
  recorded_role_not_in_snapshot: {
    zh: { title: "赛果角色不在快照中", explanation: "当前赛果记录的角色名称未出现在冻结角色清单中。" },
    en: { title: "Recorded role absent from snapshot", explanation: "A current result role is missing from the frozen role inventory." },
  },
  invalid_projection_payload: {
    zh: { title: "事件载荷无法唯一解释", explanation: "结构化载荷不满足投影所需形态，系统使用安全默认值继续。" },
    en: { title: "Projection payload cannot be interpreted", explanation: "The payload cannot be projected unambiguously; safe defaults were used." },
  },
};

export function projectionIssueMessage(code: string, language: Language): IssueCopy & {
  known: boolean;
} {
  const known = ISSUE_MESSAGES[code as KnownProjectionIssueCode];
  if (known) return { ...known[language], known: true };
  return {
    title: language === "zh" ? "未知投影提示" : "Unknown projection issue",
    explanation: language === "zh"
      ? "当前客户端尚未识别该提示，请根据技术代码检查相关记录。"
      : "This client does not recognize the issue yet. Review the linked records and code.",
    known: false,
  };
}
