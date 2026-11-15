import type { Evidence } from "./types";
export function SourceFootprint({ data }: { data: Evidence | undefined }) {
  if (!data) return null;
  const ids = [
    ...new Set(
      data.dimensions.flatMap((d) => [
        ...d.evidence_ids,
        ...d.lower_conditions.flatMap((c) => c.evidence_ids),
        ...d.upper_conditions.flatMap((c) => c.evidence_ids),
      ]),
    ),
  ];
  const groups: [string, (id: string) => boolean][] = [
    ["GPS 보행 경로", (id) => id.startsWith("gps:")],
    ["OSM 지형·시설", (id) => id.startsWith("osm:")],
    [
      "후기·방문 신호",
      (id) => id.startsWith("rev:") || id.startsWith("topic:"),
    ],
    ["월별 체감온도", (id) => id.startsWith("climate:")],
    ["웹 교차 확인", (id) => /^https?:|^web:/.test(id)],
  ];
  return (
    <section className="source-footprint">
      <div className="inline spread">
        <b>판단에 인용된 자료</b>
        <small>{ids.length}개 인용 항목 · 독립 표본 수 아님</small>
      </div>
      <div className="inline wrap">
        {groups.map(([label, matches]) => {
          const count = ids.filter(matches).length;
          return count ? (
            <span className="tag" key={label}>
              {label} <b>{count}</b>
            </span>
          ) : null;
        })}
      </div>
    </section>
  );
}
