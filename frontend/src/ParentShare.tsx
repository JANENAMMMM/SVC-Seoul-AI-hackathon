import { useRef, useState } from "react";
import type { Snapshot } from "./types";
import { Badge } from "./EvidencePanel";
export function ParentShare({
  snapshot,
  onOpinion,
  outdated = false,
  demo = false,
}: {
  snapshot: Snapshot;
  onOpinion: (day: number, choice: string) => Promise<void>;
  outdated?: boolean;
  demo?: boolean;
}) {
  const [day, setDay] = useState(snapshot.days[0]?.day || 1),
    [message, setMessage] = useState(""),
    [sending, setSending] = useState(false);
  const card = useRef<HTMLDivElement>(null);
  const d = snapshot.days.find((x) => x.day === day)!;
  const displayDate = snapshot.start_date
    ? new Date(
        new Date(snapshot.start_date + "T12:00:00").getTime() +
          (day - 1) * 86400000,
      ).toLocaleDateString("ko-KR", {
        month: "long",
        day: "numeric",
        weekday: "short",
      })
    : "";
  async function save() {
    const canvas = document.createElement("canvas");
    canvas.width = 900;
    const lines: { text: string; size: number; color: string }[] = [];
    for (const s of d.stops.filter((s) => !["move", "base"].includes(s.type))) {
      const text = `${s.start || ""} ${s.type === "rest" ? "쉬어가기" : s.name || s.mode_name || "식사"}`;
      for (let i = 0; i < text.length; i += 23)
        lines.push({ text: text.slice(i, i + 23), size: 32, color: "#222222" });
      if (s.mode_name)
        lines.push({ text: s.mode_name, size: 26, color: "#666666" });
      if (s.cautions?.length)
        lines.push({
          text: "주의: " + s.cautions.join(" · "),
          size: 26,
          color: "#99732c",
        });
      lines.push({ text: "", size: 16, color: "#222222" });
    }
    canvas.height = Math.max(
      1200,
      310 + lines.reduce((n, l) => n + l.size + 14, 0) + 150,
    );
    const ctx = canvas.getContext("2d")!;
    ctx.fillStyle = "#ffffff";
    ctx.fillRect(0, 0, 900, canvas.height);
    ctx.fillStyle = "#222222";
    ctx.font = "bold 48px sans-serif";
    ctx.fillText(`${snapshot.name}, ${day}일차는 이렇게 다녀요`, 55, 100);
    ctx.font = "30px sans-serif";
    ctx.fillText(
      `다낭 ${displayDate} · 예상 걷기 ${d.total_walk_min}분 · 휴식 ${d.rests}회`,
      55,
      160,
    );
    let y = 235;
    for (const line of lines) {
      ctx.font = `${line.size}px sans-serif`;
      ctx.fillStyle = line.color;
      ctx.fillText(line.text, 55, y);
      y += line.size + 14;
    }
    ctx.fillStyle = "#222222";
    ctx.font = "24px sans-serif";
    ctx.fillText(
      "예상 일정입니다. 현장 상황에 따라 달라질 수 있어요.",
      55,
      canvas.height - 100,
    );
    ctx.fillText(
      demo
        ? "시연 데이터 · 의견 버튼은 공유 웹에서 눌러주세요."
        : "의견은 카톡으로 받은 공유 웹 링크에서 남겨주세요.",
      55,
      canvas.height - 55,
    );
    canvas.toBlob((blob) => {
      if (!blob) return;
      const url = URL.createObjectURL(blob),
        a = document.createElement("a");
      a.href = url;
      a.download = `반걸음-${day}일차.png`;
      a.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    }, "image/png");
  }
  if (!d) return <p>공유할 일정이 없어요.</p>;
  return (
    <div className="parent-wrap">
      <div className="parent-brand">
        반걸음 <span>부모님의 속도로</span>
      </div>
      {demo && (
        <div className="demo-notice">
          시연 데이터 · 의견은 이 기기에만 저장됩니다.
        </div>
      )}
      {outdated && (
        <div className="warning-box">
          이전 버전의 일정입니다. 자녀에게 최신 일정을 확인해주세요.
        </div>
      )}
      <nav className="day-tabs">
        {snapshot.days.map((x) => (
          <button
            key={x.day}
            className={day === x.day ? "active" : ""}
            onClick={() => setDay(x.day)}
          >
            {x.day}일차
          </button>
        ))}
      </nav>
      <div className="parent-card" ref={card}>
        <div className="eyebrow">하루 일정</div>
        <h1>
          {snapshot.name},<br />
          {day}일차는 이렇게 다녀요.
        </h1>
        {displayDate && <p>{displayDate} · 다낭</p>}
        <div className="parent-totals">
          <strong>예상 걷기 {d.total_walk_min}분</strong>
          <span>쉬는 시간 {d.rests}회</span>
          <Badge value={d.grade} />
        </div>
        {d.stops
          .filter((s) => s.type !== "base")
          .map((s, i) => (
            <div className={"parent-stop " + s.type} key={i}>
              <time>{s.start || ""}</time>
              <div>
                <strong>
                  {s.type === "rest"
                    ? "☕ 잠시 쉬어가요"
                    : s.type === "move"
                      ? `${s.transport === "taxi" ? "차량" : "도보"} 이동 · 예상 ${s.minutes || 0}분`
                      : s.name || s.mode_name || "식사"}
                </strong>
                {s.mode_name && <p>{s.mode_name}</p>}
                {!!s.cautions?.length && (
                  <p className="parent-caution">
                    주의 · {s.cautions.join(" · ")}
                  </p>
                )}
              </div>
            </div>
          ))}
        <p className="muted">
          보행·이동 시간은 예상값이에요. 현장 상황에 따라 달라질 수 있어요.
        </p>
      </div>
      <section className="parent-opinions">
        <h2>이 일정, 어떠세요?</h2>
        <p>의견을 보내주시면 자녀가 확인해요.</p>
        {["좋아요", "힘들 것 같아요", "여기는 꼭 가고 싶어요"].map((choice) => (
          <button
            disabled={sending}
            key={choice}
            onClick={async () => {
              setSending(true);
              try {
                await onOpinion(day, choice);
                setMessage("의견을 보냈어요. 자녀가 확인한 뒤 일정을 바꿔요.");
              } catch (e) {
                setMessage(
                  e instanceof Error
                    ? e.message
                    : "전달하지 못했어요. 다시 눌러주세요.",
                );
              } finally {
                setSending(false);
              }
            }}
          >
            {choice}
          </button>
        ))}
        {message && <p role="status">{message}</p>}
      </section>
      <button className="button secondary full" onClick={save}>
        하루 카드 이미지 저장
      </button>
    </div>
  );
}
