import type { Place } from "./types";
import { Badge, dimNames } from "./EvidencePanel";
type View = { grade: string | null; cautions: string[] | null };
type HumanReview = { verdict: string; rationale: string };
export function MdComparison({
  review,
  places,
}: {
  review: Record<string, unknown>;
  places: Place[];
}) {
  const before = (review.before_view || {}) as Record<
    string,
    Record<string, View>
  >;
  const after = (review.after_view || {}) as Record<
    string,
    { view: View; human_review: Record<string, HumanReview> }
  >;
  const ids = [...new Set([...Object.keys(before), ...Object.keys(after)])];
  return (
    <div className="md-comparisons">
      {ids.map((id) => (
        <article key={id} className="md-place-comparison">
          <h3>{places.find((p) => p.place_id === id)?.name_ko || id}</h3>
          <div className="comparison-views">
            <section>
              <h4>변경 전</h4>
              <Badge value={before[id]?.standard?.grade} />
              {before[id]?.standard?.cautions?.map((t) => (
                <span className="tag caution" key={t}>
                  {t}
                </span>
              ))}
              {before[id]?.standard?.cautions === null && (
                <p className="muted">
                  과거 주의 태그는 당시 기록이 없어 비교에서 제외했어요.
                </p>
              )}
            </section>
            <section>
              <h4>재채점 결과 · 표준 관람</h4>
              {after[id] ? (
                <>
                  <Badge value={after[id].view.grade} />
                  {after[id].view.cautions?.map((t) => (
                    <span className="tag caution" key={t}>
                      {t}
                    </span>
                  ))}
                  {before[id]?.standard?.grade === after[id].view.grade && (
                    <p className="muted">
                      등급 유지 · 근거와 조건의 변화도 확인하세요.
                    </p>
                  )}
                </>
              ) : (
                <p className="muted">아직 재채점하지 않았습니다.</p>
              )}
            </section>
          </div>
          {after[id] && (
            <section className="human-review">
              <h4>AI는 MD 의견을 어떻게 다뤘나요?</h4>
              {Object.entries(after[id].human_review).length ? (
                Object.entries(after[id].human_review).map(([dim, r]) => (
                  <div key={dim}>
                    <span className="tag">
                      {dimNames[dim]} ·{" "}
                      {r.verdict === "cited"
                        ? "근거로 인용"
                        : "검토했으나 미인용"}
                    </span>
                    <p>{r.rationale}</p>
                  </div>
                ))
              ) : (
                <p className="muted">
                  저장된 실행에 MD 의견을 인용하거나 검토했다고 확인되는 내용이
                  없습니다.
                </p>
              )}
            </section>
          )}
        </article>
      ))}
    </div>
  );
}
