// 开袋原因文字以后端落库的 open_reason 为准；装袋页与袋明细页共用本组件，
// 同一只袋在两页展示的文字必然一致。首袋原因为空，仅以「—」占位，不编造原因。
export default function BagReason({ reason }: { reason: string }) {
  return <span className="bag-reason">开袋原因：{reason ? reason : "—"}</span>;
}
