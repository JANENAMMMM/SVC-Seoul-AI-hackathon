import { useState } from "react";
import type { Fixture, Place } from "./types";
import { Badge, dimNames } from "./EvidencePanel";
import { grade } from "./api";
export function readDemoReviews(): string[] {
  try {
    return JSON.parse(
      sessionStorage.getItem("bangeoreum-demo-reviews") || "[]",
    );
  } catch {
    return [];
  }
}
export function DemoReview({
  places,
  fixture,
  history,
  onEvidence,
}: {
  places: Place[];
  fixture: Fixture | undefined;
  history: boolean;
  onEvidence: (id: string) => void;
}) {
  const [reviewed, setReviewed] = useState<string[]>(readDemoReviews),
    [checked, setChecked] = useState<string[]>([]),
    [selected, setSelected] = useState(""),
    [message, setMessage] = useState("");
  const candidates = places.filter((p) => p.status !== "ok"),
    rows = candidates.filter((p) =>
      history ? reviewed.includes(p.place_id) : !reviewed.includes(p.place_id),
    );
  const current = rows.find((p) => p.place_id === selected) || rows[0],
    data = current && fixture?.evidence[current.place_id];
  function complete(ids: string[]) {
    const next = [...new Set([...reviewed, ...ids])];
    sessionStorage.setItem("bangeoreum-demo-reviews", JSON.stringify(next));
    setReviewed(next);
    setChecked([]);
    setMessage(`${ids.length}건을 검수 완료로 표시했습니다.`);
    window.dispatchEvent(new Event("bangeoreum-demo-review-change"));
  }
  return (
    <>
      <p className="muted">
        {history
          ? "시연에서 검토한 기록입니다."
          : "자동 평가에서 확인이 필요한 관광지를 먼저 검토합니다."}
      </p>
      <div className="demo-review-grid">
        <section>
          <div className="inline spread">
            <h3>
              {history ? "검수 완료" : "검수 대기"} {rows.length}건
            </h3>
            {!history && (
              <button
                className="button secondary"
                disabled={!checked.length}
                onClick={() => complete(checked)}
              >
                선택 검수 완료 ({checked.length})
              </button>
            )}
          </div>
          {!rows.length && (
            <div className="empty">
              {history
                ? "아직 검토한 기록이 없습니다."
                : "대기 중인 관광지가 없습니다."}
            </div>
          )}
          {rows.map((p) => (
            <article key={p.place_id} className="demo-review-row">
              {!history && (
                <input
                  type="checkbox"
                  aria-label={p.name_ko + " 검수 선택"}
                  checked={checked.includes(p.place_id)}
                  onChange={(e) =>
                    setChecked(
                      e.target.checked
                        ? [...checked, p.place_id]
                        : checked.filter((id) => id !== p.place_id),
                    )
                  }
                />
              )}
              <div>
                <button
                  className="stop-title"
                  onClick={() => setSelected(p.place_id)}
                >
                  {p.name_ko}
                </button>
                <div className="inline">
                  <Badge value={p.modes.standard.grade} />
                  <span className="tag">
                    {history ? "검수 완료 · 시연" : "확인 필요"}
                  </span>
                </div>
                <p>
                  {p.modes.standard.cautions.join(" · ") ||
                    "평가 근거 확인 필요"}
                </p>
                <button
                  className="text-button"
                  onClick={() => {
                    setSelected(p.place_id);
                    onEvidence(p.place_id);
                  }}
                >
                  평가 근거 보기
                </button>
              </div>
            </article>
          ))}
          {message && (
            <p role="status" className="notice">
              {message}
            </p>
          )}
        </section>
        <section className="demo-review-summary">
          {current && data ? (
            <>
              <div className="eyebrow">검토할 평가</div>
              <h3>{current.name_ko}</h3>
              <p>
                현재 등급을 바꾸기 전에 각 항목의 근거와 관람 조건을 확인하세요.
              </p>
              <div className="inline">
                <Badge value={current.modes.standard.grade} />
                <span className="muted">표준 관람 기준</span>
              </div>
              {data.dimensions.map((d) => (
                <div key={d.dimension} className="demo-dimension">
                  <div className="inline spread">
                    <b>{dimNames[d.dimension]}</b>
                    <Badge value={grade(d.score)} />
                  </div>
                  <p>{d.rationale}</p>
                </div>
              ))}
              <p>
                저장된 평가 {data.verification.runs}회 · 인용·수치 검증 통과{" "}
                {data.verification.valid}회
              </p>
              <div className="demo-review-actions">
                <button
                  className="button secondary"
                  onClick={() => onEvidence(current.place_id)}
                >
                  출처와 관람 조건 확인
                </button>
                {!history && (
                  <button
                    className="button primary"
                    onClick={() => complete([current.place_id])}
                  >
                    검수 완료로 표시
                  </button>
                )}
              </div>
            </>
          ) : (
            <>
              <h3>{history ? "검수 기록" : "검수 대기"}</h3>
              <p>목록에서 관광지를 선택하면 평가 근거가 표시됩니다.</p>
            </>
          )}
        </section>
      </div>
      <p className="demo-review-note">
        검수 상태를 체험하는 시연입니다. 원본 평가와 공개 점수는 변경되지
        않습니다.
      </p>
    </>
  );
}
