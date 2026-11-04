import { useRef, useState } from "react";
import type { Evidence, Source } from "./types";
import { safeUrl, grade } from "./api";
export const dimNames: Record<string, string> = {
  climb: "계단·오르막",
  walking: "보행량",
  heat: "더위 노출",
  crowd: "혼잡·대기",
};
const icons: Record<string, string> = {
  climb: "↗",
  walking: "↔",
  heat: "☀",
  crowd: "≋",
};
export function Badge({
  value,
  compact = false,
}: {
  value: string | null | undefined;
  compact?: boolean;
}) {
  return (
    <span
      className={"grade grade-" + value}
      aria-label={"난이도 " + (value || "미확인")}
    >
      {compact ? value || "미확인" : `부담 ${value || "미확인"}`}
    </span>
  );
}
export function EvidencePanel({
  data,
  sources,
  operator = false,
  reviewed = false,
}: {
  data: Evidence | undefined;
  sources: Source[];
  operator?: boolean;
  reviewed?: boolean;
}) {
  const [month, setMonth] = useState("7");
  const panel = useRef<HTMLDivElement>(null);
  if (!data)
    return <div className="empty">장소를 선택하면 평가 근거를 보여드려요.</div>;
  const climate = data.climate?.monthly_mean_apparent_max_c;
  return (
    <div className="evidence-panel" ref={panel}>
      <div className="eyebrow">
        {operator ? "난이도 평가 근거" : "왜 이 부담인가요?"}
      </div>
      <h2>{data.name_ko}</h2>
      <div className="inline">
        <Badge value={data.modes.standard.grade} />
        <span className="muted">표준 관람 기준</span>
        <span className={"status " + (data.status === "ok" ? "" : "warning")}>
          {reviewed
            ? "검수 완료 · 시연"
            : data.status === "ok"
              ? "인용 연결 확인"
              : "검수 필요"}
        </span>
      </div>
      <div className="axis-summary" aria-label="네 가지 평가 항목">
        {data.dimensions.map((d) => (
          <button
            key={d.dimension}
            onClick={() =>
              panel.current
                ?.querySelector(`[data-dimension="${d.dimension}"]`)
                ?.scrollIntoView({ behavior: "smooth", block: "start" })
            }
          >
            <span>{dimNames[d.dimension]}</span>
            <Badge value={grade(d.score)} compact />
          </button>
        ))}
      </div>
      <div className="dimension-grid">
        {data.dimensions.map((d) => (
          <section
            className={"dimension dim-" + d.dimension}
            key={d.dimension}
            data-dimension={d.dimension}
          >
            <div className="dimension-head">
              <span>
                {icons[d.dimension]} {dimNames[d.dimension]}
              </span>
              <Badge value={grade(d.score)} />
            </div>
            <div
              className="meter"
              aria-label={dimNames[d.dimension] + " 내부 평가 " + d.score}
            >
              <i style={{ width: `${d.score * 10}%` }} />
            </div>
            <p className="rationale-preview">
              {d.rationale || "현재 점수와 연결된 설명을 확인해야 합니다."}
            </p>
            <details className="rationale-detail">
              <summary>판단 이유 전체 보기</summary>
              <p>{d.rationale || "연결된 설명을 확인해야 합니다."}</p>
            </details>
            {d.lower_conditions.length > 0 && (
              <div className="condition">
                <b>부담이 줄어드는 조건</b>
                {d.lower_conditions.map((c, i) => (
                  <p key={i}>{c.condition}</p>
                ))}
              </div>
            )}
            <details>
              <summary>인용 근거 {d.evidence_ids.length}개</summary>
              {d.evidence_ids.map((id) => {
                const record = sources.find((s) => s.id === id);
                const href = safeUrl(record?.url) || safeUrl(id);
                return (
                  <div className="citation" key={id}>
                    {href ? (
                      <a href={href} target="_blank" rel="noreferrer">
                        {record?.source || "웹 출처"} ↗
                      </a>
                    ) : (
                      <b>{record?.source || id.split(":")[0]}</b>
                    )}
                    <p>{record?.text || id}</p>
                    {record?.caveat && <small>{record.caveat}</small>}
                    {!record && !href && (
                      <small>원문 상세 조회가 필요합니다.</small>
                    )}
                  </div>
                );
              })}
            </details>
          </section>
        ))}
      </div>
      <section className="climate-card">
        <div className="inline spread">
          <h3>더위 평가에 사용한 기후 자료</h3>
          <span className="tag">과거 기후</span>
        </div>
        <p>
          기온 하나가 아니라 <b>체감온도 · 실외 노출 · 그늘</b>을 함께 봅니다.
        </p>
        {climate ? (
          <>
            <div className="climate-number">
              <strong>
                {climate[month]}
                <small>℃</small>
              </strong>
              <label>
                다낭 {month}월<br />일 최고 체감온도의 월평균
              </label>
              <select
                aria-label="기후 조회 월"
                value={month}
                onChange={(e) => setMonth(e.target.value)}
              >
                {Array.from({ length: 12 }, (_, i) => (
                  <option key={i + 1} value={i + 1}>
                    {i + 1}월
                  </option>
                ))}
              </select>
            </div>
            <div className="climate-bars">
              {Object.entries(climate)
                .sort((a, b) => Number(a[0]) - Number(b[0]))
                .map(([m, t]) => (
                  <button
                    key={m}
                    className={m === month ? "active" : ""}
                    aria-label={`${m}월 ${t}도`}
                    onClick={() => setMonth(m)}
                  >
                    <i style={{ height: Math.max(12, (t - 15) * 2.5) }} />
                    <small>{m}</small>
                  </button>
                ))}
            </div>
            <small>
              관측 기간 {data.climate.period} ·{" "}
              <a
                href={safeUrl(data.climate.source)}
                target="_blank"
                rel="noreferrer"
              >
                Open-Meteo 원자료 ↗
              </a>
            </small>
          </>
        ) : (
          <p>월별 기후 원자료를 확인해야 합니다.</p>
        )}
        <div className="notice">
          월 선택은 자료 조회입니다. 점수는 자동 변경되지 않습니다.
          <br />
          실제 채점에 사용한 월은 위 인용·판단 이유에서 확인하세요. 여행일
          예보는 미연결입니다.
        </div>
      </section>
      <section className="verification-card">
        <div className="eyebrow">평가 확인 절차</div>
        <h3>평가·검증 기록</h3>
        <ol className="pipeline">
          <li>자료 조회</li>
          <li>AI 차원별 평가</li>
          <li>인용·수치 검증</li>
          <li>반복 결과 집계</li>
          <li>MD 검수</li>
        </ol>
        <div className="verification-stats">
          <div>
            <strong>{data.verification.runs}</strong>
            <small>저장된 실행</small>
          </div>
          <div>
            <strong>{data.verification.valid}</strong>
            <small>4개 축 검증 통과</small>
          </div>
          <div>
            <strong>{data.verification.matched_dimensions}/4</strong>
            <small>최종 점수와 근거 연결</small>
          </div>
        </div>
        {data.verification.issue && (
          <p className="warning">{data.verification.issue}</p>
        )}
        <p className="muted">{data.notice}</p>
        <details>
          <summary>평가 기준·내부 점수·실행 기록</summary>
          <p>
            계단 3 : 보행 3 : 더위 2 : 혼잡 1의 가중평균을 코드로 계산합니다. 하
            ≤ 3 · 중 ≤ 5 · 상 ≥ 6. 주의 태그는 개별 평가 축 7 이상에 표시합니다.
          </p>
          <p>집계: {data.verification.method}</p>
          {data.dimensions.map((d) => (
            <p key={d.dimension}>
              {dimNames[d.dimension]} {d.score}/10 ·{" "}
              <code>{d.run_id || "연결 미확인"}</code>
            </p>
          ))}
        </details>
      </section>
    </div>
  );
}
