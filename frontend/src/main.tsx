import React, { useCallback, useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import { api, post, grade, ApiError } from "./api";
import type {
  Fixture,
  Place,
  Itinerary,
  Day,
  Command,
  Proposal,
  Evidence,
  Source,
  Snapshot,
  Feedback,
  Opinion,
} from "./types";
import { Badge, EvidencePanel } from "./EvidencePanel";
import { RouteMap } from "./RouteMap";
import { ParentShare } from "./ParentShare";
import { MdComparison } from "./MdComparison";
import { DemoReview, readDemoReviews } from "./DemoReview";
import { SourceFootprint } from "./SourceFootprint";
import "./style.css";

type Trip = { id: string; owner_key: string; version: number };
type Conditions = { name: string; avoid_tags: string[]; must_places: string[] };
const tagOptions = ["계단·오르막", "긴 보행", "더위 노출", "혼잡"];
/** src/scoring/verify.py의 GRADE_CUTS(3, 5)·WEIGHTS와 같은 값. 기준이 바뀌면 함께 고친다. */
const GRADE_RANGE = { 하: "1~3", 중: "4~5", 상: "6 이상" } as const;

function GradeLegend({ compact = false }: { compact?: boolean }) {
  return (
    <div className={"grade-legend" + (compact ? " compact" : "")}>
      <p>
        <b>상·중·하</b>는 관광지 자체의 부담 정도예요(개인 체력이 아님).{" "}
        {(["하", "중", "상"] as const).map((g) => (
          <span key={g} className="range">
            {g} {GRADE_RANGE[g]}
          </span>
        ))}
      </p>
      {!compact && (
        <p className="muted">
          오르막 3 · 보행 3 · 더위 2 · 혼잡 1의 가중 평균(1~10점)이고, 7점
          이상인 항목은 주의 태그로 따로 표시해요.
        </p>
      )}
      <p className="muted">
        AI가 수집한 자료를 인용해 반복 채점하고, 운영자가 검수·승인해요.
      </p>
    </div>
  );
}

function App() {
  const [demo, setDemo] = useState(
    !new URLSearchParams(location.search).has("live"),
  );
  const [view, setView] = useState<"customer" | "md">("md"),
    [tab, setTab] = useState("route"),
    [mdTab, setMdTab] = useState("evaluation");
  const [fixture, setFixture] = useState<Fixture>(),
    [places, setPlaces] = useState<Place[]>([]),
    [itinerary, setItinerary] = useState<Itinerary>();
  const [selected, setSelected] = useState("dad-02"),
    [day, setDay] = useState(1),
    [evidence, setEvidence] = useState<Evidence>(),
    [sources, setSources] = useState<Source[]>([]);
  const [proposal, setProposal] = useState<Proposal>(),
    [fid, setFid] = useState(""),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [notice, setNotice] = useState("");
  const [trip, setTrip] = useState<Trip>(),
    [conditions, setConditions] = useState<Conditions>({
      name: "엄마",
      avoid_tags: ["계단·오르막"],
      must_places: [],
    });
  const [setup, setSetup] = useState(false),
    [age, setAge] = useState(64),
    [gender, setGender] = useState("female"),
    [duration, setDuration] = useState("15_30min"),
    [food, setFood] = useState("every_2_3_days"),
    [avoidIngredients, setAvoidIngredients] = useState<string[]>([]),
    [placeIds, setPlaceIds] = useState([
      "dad-02",
      "dad-03",
      "dad-05",
      "dad-06",
      "dad-09",
    ]),
    [days, setDays] = useState(3);
  const [startDate, setStartDate] = useState("");
  const [demoReviewed, setDemoReviewed] = useState<string[]>(readDemoReviews);
  useEffect(() => {
    const update = () => setDemoReviewed(readDemoReviews());
    window.addEventListener("bangeoreum-demo-review-change", update);
    return () =>
      window.removeEventListener("bangeoreum-demo-review-change", update);
  }, []);
  const [secondAge, setSecondAge] = useState(67),
    [secondGender, setSecondGender] = useState("male"),
    [secondDuration, setSecondDuration] = useState("15_30min"),
    [secondFood, setSecondFood] = useState("every_2_3_days");
  const [share, setShare] = useState<{
      snapshot: Snapshot;
      token?: string;
      outdated?: boolean;
    }>(),
    [shareUrl, setShareUrl] = useState("");
  const [parent, setParent] = useState<Snapshot>(),
    [parentOutdated, setParentOutdated] = useState(false);
  const [opinions, setOpinions] = useState<Opinion[]>([]),
    [mdAuth, setMdAuth] = useState(false),
    [mdToken, setMdToken] = useState(""),
    [mdText, setMdText] = useState("");
  const [feedback, setFeedback] = useState<Feedback[]>([]),
    [review, setReview] = useState<Record<string, unknown>>(),
    [checked, setChecked] = useState<string[]>([]),
    [bulkResults, setBulkResults] = useState<string[]>([]),
    [status, setStatus] = useState("proposed"),
    [freeText, setFreeText] = useState("");
  const [liveEvaluation, setLiveEvaluation] = useState<{
    runs: number;
    matched_dimensions: number;
  }>();
  const parentToken = location.pathname.startsWith("/share/")
    ? decodeURIComponent(location.pathname.slice(7))
    : null;
  const selection = useCallback((id: string) => setSelected(id), []);
  async function run(task: () => Promise<void>) {
    setBusy(true);
    setError("");
    try {
      await task();
    } catch (e) {
      setError(e instanceof Error ? e.message : "요청을 처리하지 못했어요.");
      if (e instanceof ApiError && e.status === 409 && trip) {
        const latest = await api<{ itinerary: Itinerary; version: number }>(
          `/ui/trips/${trip.id}`,
          {},
          trip.owner_key,
        ).catch(() => null);
        if (latest) {
          setItinerary(latest.itinerary);
          setTrip({ ...trip, version: latest.version });
          setProposal(undefined);
        }
      }
    } finally {
      setBusy(false);
    }
  }
  useEffect(() => {
    fetch("/demo.json")
      .then((r) => {
        if (!r.ok) throw Error("시연 자료를 읽지 못했어요.");
        return r.json();
      })
      .then(setFixture)
      .catch((e) => setError(e.message));
  }, []);
  useEffect(() => {
    if (parentToken) {
      api<{ snapshot: Snapshot; outdated: boolean }>(
        `/ui/shares/${encodeURIComponent(parentToken)}`,
      )
        .then((r) => {
          setParent(r.snapshot);
          setParentOutdated(r.outdated);
        })
        .catch((e) => setError(e.message));
      return;
    }
    setProposal(undefined);
    setShare(undefined);
    setTrip(undefined);
    setOpinions([]);
    setError("");
    if (demo && fixture) {
      setPlaces(fixture.catalog);
      setItinerary(fixture.before);
      setConditions({
        name: "엄마",
        avoid_tags: ["계단·오르막"],
        must_places: ["dad-02"],
      });
      setSetup(false);
      setDay(
        fixture.before.days.find((d) =>
          d.stops.some((s) => s.place_id === "dad-02"),
        )?.day || 1,
      );
    } else if (!demo) {
      setItinerary(undefined);
      setSetup(true);
      api<Place[]>("/ui/catalog")
        .then(setPlaces)
        .catch((e) => setError(e.message));
      const saved = sessionStorage.getItem("bangeoreum-trip");
      if (saved) {
        const t = JSON.parse(saved) as Trip;
        api<{ itinerary: Itinerary; version: number; conditions: Conditions }>(
          `/ui/trips/${t.id}`,
          {},
          t.owner_key,
        )
          .then((r) => {
            setTrip({ ...t, version: r.version });
            setItinerary(r.itinerary);
            setConditions(r.conditions);
            const profile = (
              r.itinerary.request.travelers as {
                age: number;
                gender: string;
                walking_duration: string;
                korean_need: string;
                avoid_ingredients: string[];
              }[]
            )?.[0];
            if (profile) {
              setAge(profile.age);
              setGender(profile.gender);
              setDuration(profile.walking_duration || "15_30min");
              setFood(profile.korean_need);
              setAvoidIngredients(profile.avoid_ingredients || []);
            }
            setDays(r.itinerary.days.length);
            const second = (
              r.itinerary.request.travelers as {
                age: number;
                gender: string;
                walking_duration: string;
                korean_need: string;
              }[]
            )?.[1];
            if (second) {
              setSecondAge(second.age);
              setSecondGender(second.gender);
              setSecondDuration(second.walking_duration || "15_30min");
              setSecondFood(second.korean_need);
            }
            setStartDate(String(r.itinerary.request.start_date || ""));
            setPlaceIds((r.itinerary.request.place_ids as string[]) || []);
            setSetup(false);
          })
          .catch(() => sessionStorage.removeItem("bangeoreum-trip"));
      }
    }
  }, [demo, fixture, parentToken]);
  useEffect(() => {
    let active = true;
    setSources([]);
    if (demo && fixture) {
      setEvidence(fixture.evidence[selected]);
      setSources(fixture.sources[selected] || []);
    } else if (!demo) {
      api<Evidence>(`/ui/evidence/${selected}`)
        .then((r) => {
          if (active) setEvidence(r);
        })
        .catch((e) => {
          if (active) setError(e.message);
        });
      api<Source[]>(`/ui/evidence/${selected}/sources`)
        .then((r) => {
          if (active) setSources(r);
        })
        .catch(() => {});
    }
    return () => {
      active = false;
    };
  }, [selected, demo, fixture]);
  async function loadFeedback() {
    if (demo) {
      setFeedback([]);
      return;
    }
    const entries = await api<Feedback[]>(
      `/ui/md/feedback?status=${encodeURIComponent(status)}`,
    );
    setFeedback(entries);
    setMdAuth(true);
  }
  useEffect(() => {
    if (view === "md" && mdTab !== "evaluation") run(loadFeedback);
  }, [mdTab, status, demo]);
  useEffect(() => {
    if (trip) sessionStorage.setItem("bangeoreum-trip", JSON.stringify(trip));
  }, [trip]);
  useEffect(() => {
    setChecked([]);
    setReview(undefined);
  }, [status, demo]);
  async function loadOpinions() {
    if (demo) {
      setOpinions(
        JSON.parse(sessionStorage.getItem("bangeoreum-demo-opinions") || "[]"),
      );
      return;
    }
    if (trip)
      setOpinions(
        await api<Opinion[]>(
          `/ui/trips/${trip.id}/opinions`,
          {},
          trip.owner_key,
        ),
      );
  }
  function resetDemo() {
    if (fixture) {
      setItinerary(fixture.before);
      setConditions({
        name: "엄마",
        avoid_tags: ["계단·오르막"],
        must_places: ["dad-02"],
      });
      setSelected("dad-02");
      setOpinions([]);
      sessionStorage.removeItem("bangeoreum-demo-opinions");
      sessionStorage.removeItem("bangeoreum-demo-reviews");
      setDemoReviewed([]);
      setProposal(undefined);
      setFid("");
      setNotice("시연을 처음으로 되돌렸어요.");
      setDay(
        fixture.before.days.find((d) =>
          d.stops.some((s) => s.place_id === "dad-02"),
        )?.day || 1,
      );
    }
  }
  async function previewCommand(command?: Command) {
    if (!itinerary) return;
    await run(async () => {
      let result: { feedback_id: string | null; proposal: Proposal };
      if (demo) {
        if (!command)
          throw Error("자유 입력은 실제 연결 모드에서 사용할 수 있어요.");
        const key = command.op + ":" + (command.place_id || command.day || "");
        const p = fixture?.scenarios[key];
        if (!p)
          throw Error(
            "이 조정은 시연 시나리오에 없어요. 실제 연결 모드에서 사용할 수 있어요.",
          );
        if (itinerary !== fixture?.before)
          throw Error(
            "고정 시나리오를 다시 시작한 뒤 다른 조정을 선택해주세요.",
          );
        result = { feedback_id: "demo-proposal", proposal: p };
      } else {
        if (!trip) throw Error("먼저 부모님 조건으로 일정을 만들어주세요.");
        result = await api(
          `/ui/trips/${trip.id}/preview`,
          post({
            commands: command ? [command] : [],
            feedback: command ? null : freeText,
          }),
          trip.owner_key,
        );
      }
      if (!result.feedback_id) {
        setNotice(result.proposal.clarification || "변경할 내용이 없어요.");
        return;
      }
      setProposal(result.proposal);
      setFid(result.feedback_id);
      setTab("adjust");
      setNotice("변경안을 만들었어요. 승인 전까지 현재 일정은 그대로예요.");
    });
  }
  async function decide(approve: boolean) {
    if (!proposal || !itinerary) return;
    await run(async () => {
      if (demo) {
        if (approve) setItinerary(proposal.itinerary);
      } else if (trip) {
        const result = await api<{ itinerary?: Itinerary; version?: number }>(
          `/ui/trips/${trip.id}/proposals/${fid}/${approve ? "approve" : "reject"}`,
          post(),
          trip.owner_key,
        );
        if (approve && result.itinerary) {
          setItinerary(result.itinerary);
          setTrip({ ...trip, version: result.version! });
        }
      }
      setProposal(undefined);
      setFid("");
      setNotice(
        approve
          ? "승인했어요. 동선과 관람 방식에 반영했어요."
          : "변경안을 취소했어요. 현재 일정은 그대로예요.",
      );
      if (approve) setTab("route");
    });
  }
  async function createTrip() {
    await run(async () => {
      if (demo) {
        setSetup(false);
        setNotice(
          "시연은 준비된 부모님 조건과 일정으로 진행해요. 조건 반영은 실제 연결 모드에서 확인할 수 있어요.",
        );
        return;
      }
      const profile = await api(
        "/profile",
        post({
          age,
          gender,
          walking_duration: duration,
          korean_need: food,
          avoid_ingredients: avoidIngredients,
        }),
      );
      const result = await api<Trip & { itinerary: Itinerary }>(
        trip ? `/ui/trips/${trip.id}` : "/ui/trips",
        {
          ...post({
            request: {
              travelers:
                conditions.name === "부모님"
                  ? [
                      profile,
                      await api(
                        "/profile",
                        post({
                          age: secondAge,
                          gender: secondGender,
                          walking_duration: secondDuration,
                          korean_need: secondFood,
                          avoid_ingredients: avoidIngredients,
                        }),
                      ),
                    ]
                  : [profile],
              place_ids: placeIds,
              days,
              start_date: startDate || null,
            },
            conditions,
            expected_version: trip?.version,
          }),
          method: trip ? "PUT" : "POST",
        },
        trip?.owner_key,
      );
      setTrip({
        id: result.id,
        owner_key: result.owner_key || trip!.owner_key,
        version: result.version,
      });
      setItinerary(result.itinerary);
      setProposal(undefined);
      setFid("");
      setDay(1);
      setSetup(false);
      setTab("route");
      setNotice("부모님 조건에 맞춰 예상 동선을 만들었어요.");
    });
  }
  function snapshotOf(it: Itinerary): Snapshot {
    return {
      name: conditions.name,
      start_date: String(it.request.start_date || ""),
      days: it.days.map((d) => ({
        day: d.day,
        grade: grade(d.difficulty),
        total_walk_min: d.total_walk_min,
        rests: d.stops.filter((s) => s.type === "rest").length,
        stops: d.stops.map((s) => ({
          ...s,
          name: s.restaurant?.name || s.name,
          ...(s.place_id &&
          places.find((p) => p.place_id === s.place_id)?.modes[
            s.mode || "standard"
          ]
            ? {
                grade: places.find((p) => p.place_id === s.place_id)!.modes[
                  s.mode || "standard"
                ].grade,
                cautions: places.find((p) => p.place_id === s.place_id)!.modes[
                  s.mode || "standard"
                ].cautions,
              }
            : {}),
        })),
      })),
    };
  }
  async function openShare() {
    await run(async () => {
      if (!itinerary) throw Error("먼저 일정을 만들어주세요.");
      if (demo) {
        setShare({ snapshot: snapshotOf(itinerary) });
        setShareUrl("");
        return;
      }
      if (!trip) return;
      const result = await api<{ snapshot: Snapshot; token: string }>(
        `/ui/trips/${trip.id}/shares`,
        post(),
        trip.owner_key,
      );
      setShare(result);
      setShareUrl(`${location.origin}/share/${result.token}`);
    });
  }
  async function sendOpinion(d: number, choice: string, token?: string) {
    if (demo && !parentToken) {
      const list: Opinion[] = [
        { id: Date.now(), day: d, choice, version: 1, reviewed: false },
        ...JSON.parse(
          sessionStorage.getItem("bangeoreum-demo-opinions") || "[]",
        ),
      ];
      sessionStorage.setItem("bangeoreum-demo-opinions", JSON.stringify(list));
      setOpinions(list);
    } else
      await api(
        `/ui/shares/${encodeURIComponent(token || parentToken || "")}/opinions`,
        post({ day: d, choice }),
      );
  }
  const current =
    itinerary?.days.find((d) => d.day === day) || itinerary?.days[0];
  const shown =
    proposal?.itinerary.days.find((d) => d.day === current?.day) || current;
  const selectedPlace = places.find((p) => p.place_id === selected);
  const canMoreKorean = itinerary?.state.korean_need_override
    ? itinerary.state.korean_need_override !== "daily"
    : !(
        itinerary?.request.travelers as { korean_need: string }[] | undefined
      )?.some((p) => p.korean_need === "daily");
  const affected = current?.stops
    .filter((s) => s.type === "attraction")
    .map((s) => ({ s, p: places.find((p) => p.place_id === s.place_id) }))
    .filter((x) => x.p) as { s: Day["stops"][0]; p: Place }[] | undefined;
  const validCandidates =
    affected?.filter(({ s, p }) =>
      p.modes[s.mode || "standard"].cautions.some((t) =>
        conditions.avoid_tags.includes(t),
      ),
    ) || [];
  const removable = validCandidates.filter(
    ({ p }) => !conditions.must_places.includes(p.place_id),
  );
  const totalRuns = fixture
    ? Object.values(fixture.evidence).reduce(
        (a, e) => a + e.verification.runs,
        0,
      )
    : 0;
  const totalMatched = fixture
    ? Object.values(fixture.evidence).reduce(
        (a, e) => a + e.verification.matched_dimensions,
        0,
      )
    : 0;
  function chips(view: Place["modes"]["standard"]) {
    return (
      <>
        <Badge value={view.grade} />
        {view.cautions.map((t) => (
          <span key={t} className="tag caution">
            {t}
          </span>
        ))}
      </>
    );
  }
  const WALK_ANSWER: Record<string, string> = {
    under_15min: "15분 미만",
    "15_30min": "15~30분",
    "30_60min": "30~60분",
    "1_2hour": "1~2시간",
    over_2hour: "2시간 이상",
  };
  function pinsOf(): Record<string, number> {
    const st = (
      itinerary?.request as { state?: { pins?: Record<string, number> } }
    )?.state;
    return st?.pins ?? {};
  }
  /** 화면의 일정(Day)에서 실제로 관찰되는 사실만 규칙으로 요약한다. */
  function dayRules(d: Day): { title: string; body: string }[] {
    const rules: { title: string; body: string }[] = [];
    const rests = d.stops.filter((s) => s.type === "rest");
    const moves = d.stops.filter((s) => s.type === "move");
    const taxis = moves.filter((s) => s.transport === "taxi");
    const meals = d.stops.filter((s) => s.type === "meal" && s.start);
    const answer =
      WALK_ANSWER[
        (
          itinerary?.request as {
            travelers?: { walking_duration?: string }[];
          }
        )?.travelers?.[0]?.walking_duration || ""
      ];
    rules.push({
      title: "한 번에 걷는 시간",
      body:
        `이 날 최대 ${d.max_continuous_walk_min}분` +
        (answer ? ` · 부모님 답변(${answer}) 반영` : "") +
        (rests.some((s) => s.reason)
          ? ` · 한도를 넘지 않도록 쉬어가기 ${rests.length}회`
          : ""),
    });
    if (moves.length)
      rules.push({
        title: "이동 수단",
        body: taxis.length
          ? `도보가 길거나 한도를 넘는 구간은 차량 ${taxis.length}회 · 거리 기반 추정`
          : "이동 구간은 모두 도보 · 거리 기반 추정",
      });
    const fixed = Object.entries(pinsOf())
      .filter(([, n]) => n === d.day)
      .map(([id]) => places.find((p) => p.place_id === id)?.name_ko || id);
    if (fixed.length)
      rules.push({
        title: "꼭 갈 곳",
        body: `${fixed.join(", ")} · ${d.day}일차에 고정하고 변경 후에도 유지 여부를 검사`,
      });
    if (meals.length)
      rules.push({
        title: "식사 시간",
        body: `${meals.map((m) => m.start).join(" · ")} 확보`,
      });
    return rules;
  }
  function timeline(d: Day) {
    let n = 0;
    return (
      <div className="timeline">
        {d.stops
          .filter((s) => s.type !== "base")
          .map((s, i) => {
            const p = places.find((p) => p.place_id === s.place_id),
              v = p?.modes[s.mode || "standard"];
            const changed =
              !!proposal &&
              s.type === "attraction" &&
              current?.stops.find((o) => o.place_id === s.place_id)?.mode !==
                s.mode;
            return (
              <div
                className={
                  "timeline-stop " +
                  s.type +
                  (selected === s.place_id ? " selected" : "") +
                  (changed ? " changed" : "")
                }
                key={`${s.place_id || s.type}-${i}`}
              >
                <div className="timeline-rail">
                  <span>
                    {s.type === "attraction"
                      ? ++n
                      : s.type === "rest"
                        ? "☕"
                        : s.type === "meal"
                          ? "○"
                          : "↓"}
                  </span>
                </div>
                <div className="stop-body">
                  {s.type === "move" ? (
                    <p className="move-line">
                      {s.transport === "taxi" ? "차량" : "도보"} 이동{" "}
                      <b>예상 {s.minutes}분</b>
                      {s.transport === "taxi" && (
                        <span className="move-why">
                          도보가 길거나 연속 보행 한도를 넘어 차량으로 이동
                        </span>
                      )}
                    </p>
                  ) : (
                    <>
                      <div className="inline spread">
                        <time>
                          {s.start} — {s.end}
                        </time>
                        {changed && <span className="tag success">변경안</span>}
                      </div>
                      <button
                        className="stop-title"
                        onClick={() => s.place_id && setSelected(s.place_id)}
                      >
                        {s.type === "rest"
                          ? "잠시 쉬어가요"
                          : s.restaurant?.name ||
                            s.name ||
                            s.mode_name ||
                            "식사"}
                      </button>
                      {s.mode_name && <p className="muted">{s.mode_name}</p>}
                      {s.type === "attraction" && (
                        <p className="why-line">
                          <b>배치 이유</b>{" "}
                          {[
                            s.place_id && pinsOf()[s.place_id] === d.day
                              ? `꼭 갈 곳 · ${d.day}일차 고정`
                              : null,
                            s.note,
                            s.walk_min != null
                              ? `관람 중 걷기 예상 ${s.walk_min}분`
                              : null,
                          ]
                            .filter(Boolean)
                            .join(" · ")}
                        </p>
                      )}
                      {v && <div className="inline wrap">{chips(v)}</div>}
                      {v && (
                        <p className="reason-line">
                          {v.cautions.length
                            ? `${v.cautions.join(" · ")} 주의가 필요한 관람 방식이에요.`
                            : "이 관람 방식에는 높은 부담 주의 태그가 없어요."}{" "}
                          <button
                            onClick={() => {
                              setSelected(p!.place_id);
                              setEvidenceOpen(true);
                            }}
                          >
                            평가 근거 ↗
                          </button>
                        </p>
                      )}
                      {s.type === "rest" && (
                        <p className="why-line">
                          <b>배치 이유</b>{" "}
                          {s.reason || "휴식 시간을 확보했어요"}
                        </p>
                      )}
                      {s.type === "rest" && (
                        <p className="muted">
                          휴식 시간 확보 · 실제 쉴 장소는 현장에서 확인
                        </p>
                      )}
                    </>
                  )}
                </div>
              </div>
            );
          })}
        {proposal &&
          current?.stops
            .filter(
              (s) =>
                s.type === "attraction" &&
                !d.stops.some((x) => x.place_id === s.place_id),
            )
            .map((s) => (
              <div key={s.place_id} className="removed">
                −{" "}
                {s.name ||
                  places.find((p) => p.place_id === s.place_id)?.name_ko}{" "}
                · 변경안에서 제외
              </div>
            ))}
      </div>
    );
  }
  const [evidenceOpen, setEvidenceOpen] = useState(false);
  async function reviewOpinion(o: Opinion) {
    if (!demo && trip)
      await api(
        `/ui/trips/${trip.id}/opinions/${o.id}/review`,
        post(),
        trip.owner_key,
      );
    else
      sessionStorage.setItem(
        "bangeoreum-demo-opinions",
        JSON.stringify(
          opinions.map((x) => (x.id === o.id ? { ...x, reviewed: true } : x)),
        ),
      );
    await loadOpinions();
    setDay(o.day);
    setTab("adjust");
    setSetup(false);
    setNotice("의견을 확인했어요. 변경안을 승인하기 전까지 일정은 그대로예요.");
  }
  function adjustments() {
    return (
      <>
        <div className="eyebrow">일정 변경</div>
        <h2>일정 조정</h2>
        <p className="muted">현재 일정의 주의사항을 바탕으로 제안해요.</p>
        {!proposal && (
          <div className="suggestions">
            {removable.length > 0 && (
              <button
                disabled={busy || !!proposal}
                onClick={() =>
                  previewCommand({
                    op: "remove_place",
                    place_id: removable[0].p.place_id,
                  })
                }
              >
                <span>↗</span>{" "}
                {removable[0].p.modes[
                  removable[0].s.mode || "standard"
                ].cautions.includes("계단·오르막")
                  ? "계단 많은 곳 빼줘"
                  : "주의 부담이 있는 장소 빼줘"}
                <small>{removable[0].p.name_ko} 제외안 확인</small>
              </button>
            )}
            {affected
              ?.filter(
                ({ s, p }) =>
                  s.mode !== "short" &&
                  p.modes.short.score < p.modes[s.mode || "standard"].score,
              )
              .sort(
                (a, b) =>
                  Number(b.p.place_id === selected) -
                  Number(a.p.place_id === selected),
              )
              .slice(0, 2)
              .map(({ p }) => (
                <button
                  key={p.place_id}
                  disabled={busy || !!proposal}
                  onClick={() =>
                    previewCommand({
                      op: "set_mode",
                      place_id: p.place_id,
                      mode: "short",
                    })
                  }
                >
                  <span>↘</span> 이곳은 짧게 관람할래
                  <small>
                    {p.name_ko} · {p.modes.short.name}
                  </small>
                </button>
              ))}
            {!!affected?.some(({ s }) => s.mode !== "short") && (
              <button
                disabled={busy || !!proposal}
                onClick={() =>
                  previewCommand({ op: "lighten_day", day: current!.day })
                }
              >
                <span>☕</span> 오늘을 가볍게 해줘
                <small>{current?.day}일차를 짧은 관람 위주로</small>
              </button>
            )}
            {canMoreKorean && (
              <button
                disabled={busy || !!proposal}
                onClick={() => previewCommand({ op: "more_korean_meals" })}
              >
                <span>○</span> 한식을 더 넣어줘
                <small>현재 선호에서 한 단계 더 자주</small>
              </button>
            )}
          </div>
        )}
        {proposal && current && (
          <section className="proposal" aria-label="변경안">
            <span className="tag success">승인 대기 · 현재 일정은 유지 중</span>
            <h3>이렇게 달라져요</h3>
            <ol className="changes">
              {proposal.change_summary
                .split("\n")
                .map((line) =>
                  line.replace(
                    /가장 힘든 날 난이도 (\d+) → (\d+)/,
                    (_, a, b) =>
                      `가장 부담스러운 날: ${grade(Number(a))} → ${grade(Number(b))}`,
                  ),
                )
                .filter(Boolean)
                .slice(0, 3)
                .map((s, i) => (
                  <li key={i}>{s}</li>
                ))}
            </ol>
            <div className="compare-numbers">
              <span>
                현재 <Badge value={grade(current.difficulty)} />
                <b>{current.total_walk_min}분</b>
                <small>예상 보행</small>
              </span>
              <i>→</i>
              <span>
                변경안 <Badge value={grade(shown?.difficulty)} />
                <b>{shown?.total_walk_min}분</b>
                <small>예상 보행</small>
              </span>
            </div>
            <p className="reason-block">
              <b>변경 근거</b>
              <br />
              선택한 부모님 조건과 장소의 관람 방식별 평가를 사용해 같은 일정
              엔진으로 다시 계산했어요. 공개 장소 점수는 바꾸지 않아요.
            </p>
            <div className="changed-place-views">
              {current.stops
                .filter(
                  (s) =>
                    s.type === "attraction" &&
                    proposal.itinerary.days
                      .flatMap((d) => d.stops)
                      .some(
                        (a) => a.place_id === s.place_id && a.mode !== s.mode,
                      ),
                )
                .map((s) => {
                  const p = places.find((p) => p.place_id === s.place_id)!;
                  const after = proposal.itinerary.days
                    .flatMap((d) => d.stops)
                    .find((a) => a.place_id === s.place_id)!;
                  return (
                    <div key={s.place_id}>
                      <b>{p.name_ko}</b>
                      <div className="inline">
                        <Badge value={p.modes[s.mode || "standard"].grade} />→
                        <Badge
                          value={p.modes[after.mode || "standard"].grade}
                        />
                      </div>
                      <small>{p.modes[after.mode || "standard"].name}</small>
                    </div>
                  );
                })}
            </div>
            {proposal.clarification && <p>{proposal.clarification}</p>}
            <div className="inline">
              <button
                className="button primary"
                disabled={busy}
                onClick={() => decide(true)}
              >
                이 변경 승인
              </button>
              <button
                className="button secondary"
                disabled={busy}
                onClick={() => decide(false)}
              >
                되돌리기
              </button>
            </div>
          </section>
        )}
        <details className="free-input">
          <summary>직접 요청하고 싶어요</summary>
          <textarea
            aria-label="일정 조정 요청"
            value={freeText}
            onChange={(e) => setFreeText(e.target.value)}
            placeholder="원하는 변경을 알려주세요"
            maxLength={1000}
          />
          <button
            className="button secondary"
            disabled={busy || demo || !!proposal || !freeText.trim()}
            onClick={() => previewCommand()}
          >
            변경안 확인
          </button>
          {demo && <small>자유 입력은 실제 연결 모드에서 지원해요.</small>}
        </details>
        <div className="notice">
          변경 내용과 이유를 확인한 뒤 승인하면 일정에 반영돼요.
        </div>
        <section className="mobile-opinions">
          <button className="text-button" onClick={() => run(loadOpinions)}>
            부모님 의견 확인 ↻
          </button>
          {opinions.map((o) => (
            <article className="opinion" key={o.id}>
              <b>
                {o.day}일차 · {o.choice}
              </b>
              <small>
                공유 버전 {o.version} · {o.reviewed ? "확인함" : "미확인"}
              </small>
              {!o.reviewed && (
                <button onClick={() => run(() => reviewOpinion(o))}>
                  확인하고 조정하기
                </button>
              )}
            </article>
          ))}
        </section>
      </>
    );
  }
  function conditionsForm() {
    return (
      <div className="conditions-form">
        <div className="eyebrow">부모님의 속도를 알려주세요</div>
        <h2>부모님 여행 조건</h2>
        <label>누구의 여행인가요?</label>
        <div className="segmented">
          {["엄마", "아빠", "부모님"].map((n) => (
            <button
              className={conditions.name === n ? "active" : ""}
              key={n}
              onClick={() => setConditions({ ...conditions, name: n })}
            >
              {n}
            </button>
          ))}
        </div>
        <div className="form-row">
          <label>
            나이
            <select
              value={age}
              onChange={(e) => setAge(Number(e.target.value))}
            >
              {Array.from({ length: 51 }, (_, i) => i + 40).map((a) => (
                <option key={a}>{a}</option>
              ))}
            </select>
          </label>
          <label>
            보행속도 기준
            <select value={gender} onChange={(e) => setGender(e.target.value)}>
              <option value="female">여성 기준</option>
              <option value="male">남성 기준</option>
            </select>
          </label>
        </div>
        <label>
          출발일 · 선택
          <input
            type="date"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
          />
        </label>
        <label>쉬지 않고 얼마나 걸으실 수 있나요?</label>
        <div className="choice-grid">
          {[
            ["under_15min", "15분 미만"],
            ["15_30min", "15~30분"],
            ["30_60min", "30~60분"],
            ["1_2hour", "1~2시간"],
            ["over_2hour", "2시간 이상"],
          ].map(([v, t]) => (
            <button
              key={v}
              className={duration === v ? "active" : ""}
              onClick={() => setDuration(v)}
            >
              {t}
            </button>
          ))}
        </div>
        <label>피하고 싶은 부담</label>
        <div className="choice-grid">
          {tagOptions.map((t) => (
            <button
              key={t}
              className={conditions.avoid_tags.includes(t) ? "active" : ""}
              onClick={() =>
                setConditions({
                  ...conditions,
                  avoid_tags: conditions.avoid_tags.includes(t)
                    ? conditions.avoid_tags.filter((x) => x !== t)
                    : [...conditions.avoid_tags, t],
                })
              }
            >
              {t}
            </button>
          ))}
        </div>
        <small>
          선택은 조정 추천에 사용돼요. 해당 부담이 남으면 계속 주의 표시를 해요.
        </small>
        <label>한식은 얼마나 자주 원하시나요?</label>
        <div className="choice-grid">
          {[
            ["daily", "매일"],
            ["every_2_3_days", "2~3일마다"],
            ["none", "필요 없어요"],
          ].map(([v, t]) => (
            <button
              key={v}
              className={food === v ? "active" : ""}
              onClick={() => setFood(v)}
            >
              {t}
            </button>
          ))}
        </div>
        {conditions.name === "부모님" && (
          <section className="second-profile">
            <h3>두 번째 부모님 조건</h3>
            <p className="muted">
              두 분 중 더 짧은 보행 한도와 식사 조건을 함께 반영해요.
            </p>
            <div className="form-row">
              <label>
                나이
                <select
                  aria-label="두 번째 부모님 나이"
                  value={secondAge}
                  onChange={(e) => setSecondAge(Number(e.target.value))}
                >
                  {Array.from({ length: 51 }, (_, i) => i + 40).map((a) => (
                    <option key={a}>{a}</option>
                  ))}
                </select>
              </label>
              <label>
                보행속도 기준
                <select
                  aria-label="두 번째 부모님 보행속도 기준"
                  value={secondGender}
                  onChange={(e) => setSecondGender(e.target.value)}
                >
                  <option value="female">여성 기준</option>
                  <option value="male">남성 기준</option>
                </select>
              </label>
            </div>
            <label>
              쉬지 않고 걷는 시간
              <select
                aria-label="두 번째 부모님 보행 시간"
                value={secondDuration}
                onChange={(e) => setSecondDuration(e.target.value)}
              >
                {[
                  ["under_15min", "15분 미만"],
                  ["15_30min", "15~30분"],
                  ["30_60min", "30~60분"],
                  ["1_2hour", "1~2시간"],
                  ["over_2hour", "2시간 이상"],
                ].map(([v, t]) => (
                  <option value={v} key={v}>
                    {t}
                  </option>
                ))}
              </select>
            </label>
            <label>
              한식 빈도
              <select
                aria-label="두 번째 부모님 한식 빈도"
                value={secondFood}
                onChange={(e) => setSecondFood(e.target.value)}
              >
                <option value="daily">매일</option>
                <option value="every_2_3_days">2~3일마다</option>
                <option value="none">필요 없어요</option>
              </select>
            </label>
          </section>
        )}
        <label>피할 식재료 · 두 분이면 함께 반영</label>
        <div className="choice-grid">
          {[
            ["seafood", "해산물"],
            ["pork", "돼지고기"],
            ["dairy", "유제품"],
            ["nuts", "견과류"],
          ].map(([v, t]) => (
            <button
              key={v}
              className={avoidIngredients.includes(v) ? "active" : ""}
              onClick={() =>
                setAvoidIngredients(
                  avoidIngredients.includes(v)
                    ? avoidIngredients.filter((x) => x !== v)
                    : [...avoidIngredients, v],
                )
              }
            >
              {t}
            </button>
          ))}
        </div>
        <div className="form-row">
          <label>
            다낭에서
            <select
              value={days}
              onChange={(e) => setDays(Number(e.target.value))}
            >
              {[2, 3, 4, 5, 6, 7].map((n) => (
                <option key={n} value={n}>
                  {n}일
                </option>
              ))}
            </select>
          </label>
        </div>
        <label>가고 싶은 장소 · 선택한 장소를 다시 누르면 제외</label>
        <div className="place-choices">
          {places.map((p) => (
            <div key={p.place_id}>
              <button
                className={placeIds.includes(p.place_id) ? "active" : ""}
                onClick={() => {
                  setPlaceIds(
                    placeIds.includes(p.place_id)
                      ? placeIds.filter((id) => id !== p.place_id)
                      : [...placeIds, p.place_id],
                  );
                  if (placeIds.includes(p.place_id))
                    setConditions({
                      ...conditions,
                      must_places: conditions.must_places.filter(
                        (id) => id !== p.place_id,
                      ),
                    });
                }}
              >
                {p.name_ko}
              </button>
              {placeIds.includes(p.place_id) && (
                <button
                  aria-label={p.name_ko + " 꼭 갈 곳"}
                  className={
                    conditions.must_places.includes(p.place_id)
                      ? "star active"
                      : "star"
                  }
                  onClick={() =>
                    setConditions({
                      ...conditions,
                      must_places: conditions.must_places.includes(p.place_id)
                        ? conditions.must_places.filter(
                            (id) => id !== p.place_id,
                          )
                        : [...conditions.must_places, p.place_id],
                    })
                  }
                >
                  ★
                </button>
              )}
            </div>
          ))}
        </div>
        <small>
          ★는 꼭 가고 싶은 곳. 자동 제외하지 않고, 배치할 수 없으면 알려드려요.
        </small>
        <button
          className="button primary full"
          disabled={busy || !placeIds.length}
          onClick={createTrip}
        >
          {busy
            ? "일정을 계산하고 있어요…"
            : demo
              ? "시연 일정 보기"
              : "부모님 조건으로 일정 만들기"}
        </button>
      </div>
    );
  }
  async function mdLogin() {
    await run(async () => {
      await api("/ui/md/session", post({ token: mdToken }));
      setMdToken("");
      setMdAuth(true);
      setLiveEvaluation(await api("/ui/md/evaluation"));
      setNotice("운영자 로그인 완료");
      await loadFeedback();
    });
  }
  async function mdAction(id: string, action: string) {
    await api(`/ui/md/feedback/${id}/${action}`, post());
    await loadFeedback();
    setReview(await api(`/ui/md/feedback/${id}`));
    if (action === "approve") {
      setPlaces(await api("/ui/catalog"));
      setEvidence(await api(`/ui/evidence/${selected}`));
      setSources(await api(`/ui/evidence/${selected}/sources`));
      setLiveEvaluation(await api("/ui/md/evaluation"));
      // The old personal itinerary was calculated with the previous catalog.
      setItinerary(undefined);
      setSetup(true);
      setProposal(undefined);
    }
    setNotice("처리 결과를 갱신했어요.");
  }
  function mdReview() {
    return (
      <div className="review-content">
        <div className="eyebrow">평가 검수</div>
        <h2>평가 검수</h2>
        {demo ? (
          <DemoReview
            places={places}
            fixture={fixture}
            history={mdTab === "history"}
            onEvidence={(id) => {
              setSelected(id);
              setEvidenceOpen(true);
            }}
          />
        ) : (
          <>
            <div className="review-filter">
              <select
                aria-label="검수 상태"
                value={status}
                onChange={(e) => setStatus(e.target.value)}
              >
                {["proposed", "rejudged", "applied", "rejected"].map((s, i) => (
                  <option key={s} value={s}>
                    {["제안", "재채점 완료", "승인", "반려"][i]}
                  </option>
                ))}
              </select>
              <button
                className="button secondary"
                disabled={busy}
                onClick={() => run(loadFeedback)}
              >
                새로고침
              </button>
              <button
                className="button primary"
                disabled={busy || !checked.length}
                onClick={() =>
                  run(async () => {
                    const results = [];
                    for (const id of checked) {
                      try {
                        await api(`/ui/md/feedback/${id}/approve`, post());
                        results.push(id + " · 승인");
                      } catch (e) {
                        results.push(
                          id +
                            " · 실패: " +
                            (e instanceof Error ? e.message : ""),
                        );
                      }
                    }
                    setBulkResults(results);
                    setChecked([]);
                    await loadFeedback();
                  })
                }
              >
                선택 승인 ({checked.length})
              </button>
            </div>
            {bulkResults.map((s) => (
              <p key={s}>{s}</p>
            ))}
            <div className="feedback-list">
              {!feedback.length && (
                <p className="empty">이 상태의 검수 건이 없습니다.</p>
              )}
              {feedback.map((f) => (
                <div key={f.id} className="feedback-row">
                  <input
                    type="checkbox"
                    aria-label={f.id + " 선택"}
                    disabled={f.status !== "rejudged"}
                    checked={checked.includes(f.id)}
                    onChange={(e) =>
                      setChecked(
                        e.target.checked
                          ? [...checked, f.id]
                          : checked.filter((id) => id !== f.id),
                      )
                    }
                  />
                  <button
                    onClick={() =>
                      run(async () =>
                        setReview(await api(`/ui/md/feedback/${f.id}`)),
                      )
                    }
                  >
                    <b>{f.raw_text || f.id}</b>
                    <small>
                      {f.status} · {f.created_at}
                    </small>
                  </button>
                </div>
              ))}
            </div>
            {review && (
              <section className="review-detail">
                <h3>검수 상세</h3>
                <p>{String(review.raw_text || "")}</p>
                <MdComparison review={review} places={places} />
                <details>
                  <summary>해석과 검수 원자료</summary>
                  <pre>{JSON.stringify(review.parsed, null, 2)}</pre>
                </details>
                <div className="inline">
                  <button
                    className="button secondary"
                    disabled={busy || review.status !== "proposed"}
                    onClick={() =>
                      run(() => mdAction(String(review.id), "rejudge"))
                    }
                  >
                    재채점 · 유료 호출
                  </button>
                  <button
                    className="button primary"
                    disabled={busy || review.status !== "rejudged"}
                    onClick={() =>
                      run(() => mdAction(String(review.id), "approve"))
                    }
                  >
                    공개 점수 승인
                  </button>
                  <button
                    className="button secondary"
                    disabled={
                      busy ||
                      ["applied", "rejected"].includes(String(review.status))
                    }
                    onClick={() =>
                      run(() => mdAction(String(review.id), "reject"))
                    }
                  >
                    반려
                  </button>
                </div>
              </section>
            )}
            <section className="md-compose">
              <h3>현장 의견으로 재검토 요청</h3>
              <p className="muted">
                장소와 항목, 확인한 사실을 적어주세요. 의견을 그대로 점수로 쓰지
                않고 AI가 근거를 확인해 재평가합니다.
              </p>
              <textarea
                aria-label="MD 검수 의견"
                value={mdText}
                onChange={(e) => setMdText(e.target.value)}
                maxLength={1000}
              />
              <button
                className="button secondary"
                disabled={busy || !mdText.trim()}
                onClick={() =>
                  run(async () => {
                    const out = await api<{
                      question?: string;
                      feedback_id?: string;
                    }>("/ui/md/feedback", post({ text: mdText }));
                    setNotice(
                      out.question ||
                        "재검토 제안을 기록했어요. 재채점은 별도 버튼으로 실행해요.",
                    );
                    await loadFeedback();
                  })
                }
              >
                의견 해석·제안 만들기
              </button>
            </section>
          </>
        )}
      </div>
    );
  }
  if (parentToken)
    return (
      <>
        <div className="toast-area">
          {error && (
            <div role="alert" className="error-box">
              {error}
            </div>
          )}
        </div>
        {parent ? (
          <ParentShare
            snapshot={parent}
            outdated={parentOutdated}
            onOpinion={(d, c) => sendOpinion(d, c, parentToken)}
          />
        ) : (
          <p className="loading">공유 일정을 확인하고 있어요.</p>
        )}
      </>
    );
  return (
    <>
      <header className="app-header">
        <a className="brand" href="/">
          <strong>반걸음</strong>
          <small>부모님 맞춤 여행</small>
        </a>
        <nav className="workspace-switch" aria-label="사용자 화면">
          <button
            className={view === "customer" ? "active" : ""}
            onClick={() => setView("customer")}
          >
            고객 화면
          </button>
          <button
            className={view === "md" ? "active" : ""}
            onClick={() => setView("md")}
          >
            운영자 화면
          </button>
        </nav>
        <div className="header-actions">
          <button
            className={"mode-toggle " + (demo ? "demo" : "")}
            onClick={() => {
              setDemo(!demo);
              setMdAuth(false);
            }}
          >
            {demo ? "● 시연 데이터" : "● 실제 연결"}
          </button>
          {demo && (
            <button className="text-button" onClick={resetDemo}>
              시연 초기화
            </button>
          )}
          {!demo && mdAuth && (
            <button
              className="text-button"
              onClick={() =>
                run(async () => {
                  await api("/ui/md/session", { method: "DELETE" });
                  setMdAuth(false);
                })
              }
            >
              로그아웃
            </button>
          )}
        </div>
      </header>
      <div className="mode-strip">
        {demo
          ? "시연 일정 · 실제 관광지 평가 기록을 바탕으로 구성했습니다."
          : "실제 연결 · 보행·이동 시간은 예상값 · 여행일 예보 미연결"}
      </div>
      <div className="toast-area" aria-live="polite">
        {error && (
          <div role="alert" className="error-box">
            {error}
            <button aria-label="오류 닫기" onClick={() => setError("")}>
              ×
            </button>
          </div>
        )}
        {notice && (
          <div className="success-box">
            {notice}
            <button aria-label="알림 닫기" onClick={() => setNotice("")}>
              ×
            </button>
          </div>
        )}
        {busy && (
          <div className="busy">
            처리 중이에요. 현재 확정 일정은 유지됩니다…
          </div>
        )}
      </div>
      {view === "md" ? (
        <>
          <section className="page-heading">
            <div>
              <div className="eyebrow">여행 관리 / 다낭</div>
              <h1>관광지 난이도 관리</h1>
              <p>
                다낭 관광지의 보행 부담, 관람 조건과 평가 근거를 확인하세요.
              </p>
            </div>
          </section>
          <nav className="md-nav">
            {[
              ["evaluation", "평가 현황"],
              ["pending", "승인 대기"],
              ["history", "조정 기록"],
            ].map(([v, t]) => (
              <button
                key={v}
                className={mdTab === v ? "active" : ""}
                onClick={() => {
                  setMdTab(v);
                  setStatus(v === "history" ? "applied" : "proposed");
                }}
              >
                {t}
              </button>
            ))}
          </nav>
          {mdTab === "evaluation" ? (
            <>
              <div className="overview-stats">
                <div>
                  <span>평가 관광지</span>
                  <strong>
                    {places.length}
                    <small>곳</small>
                  </strong>
                </div>
                <div>
                  <span>평가 기록</span>
                  <strong>
                    {demo ? totalRuns : (liveEvaluation?.runs ?? "—")}
                    <small>회</small>
                  </strong>
                </div>
                <div>
                  <span>평가 항목 근거</span>
                  <strong>
                    {demo
                      ? totalMatched
                      : (liveEvaluation?.matched_dimensions ?? "—")}
                    <small>/ {places.length * 4}</small>
                  </strong>
                </div>
                <div>
                  <span>검수 필요</span>
                  <strong>
                    {
                      places.filter(
                        (p) =>
                          p.status !== "ok" &&
                          !(demo && demoReviewed.includes(p.place_id)),
                      ).length
                    }
                    <small>곳</small>
                  </strong>
                </div>
              </div>
              <main className="md-layout">
                <aside className="place-sidebar">
                  <div className="inline spread">
                    <h2>다낭 평가 목록</h2>
                    <span className="tag">{places.length}곳</span>
                  </div>
                  <p className="muted">표준 관람 기준</p>
                  <GradeLegend />
                  <div className="place-list">
                    {places.map((p, i) => (
                      <button
                        key={p.place_id}
                        className={selected === p.place_id ? "active" : ""}
                        onClick={() => setSelected(p.place_id)}
                      >
                        <span className="list-number">
                          {String(i + 1).padStart(2, "0")}
                        </span>
                        <span>
                          <b>{p.name_ko}</b>
                          <small>
                            {p.status !== "ok" &&
                              (demo && demoReviewed.includes(p.place_id)
                                ? "검수 완료 · "
                                : "검수 필요 · ")}
                            {p.modes.standard.cautions.join(" · ") ||
                              "높은 부담 태그 없음"}
                          </small>
                        </span>
                        <Badge value={p.modes.standard.grade} compact />
                      </button>
                    ))}
                  </div>
                </aside>
                <section className="place-overview">
                  <div className="eyebrow">관광지 상세</div>
                  <h2>{selectedPlace?.name_ko}</h2>
                  <p className="muted">
                    관람 방식과 이동 부담을 비교하고 평가 출처를 확인하세요.
                  </p>
                  <SourceFootprint data={evidence} />
                  {current && (
                    <RouteMap
                      day={{
                        ...current,
                        stops: [
                          {
                            type: "attraction",
                            place_id: selected,
                            mode: "standard",
                          },
                        ],
                      }}
                      places={places}
                      selected={selected}
                      onSelect={selection}
                    />
                  )}
                  {evidence && (
                    <section className="environment-summary">
                      <div className="inline spread">
                        <h3>월별 더위와 실외 노출</h3>
                        <span className="tag">기후·그늘·실외 노출</span>
                      </div>
                      <div className="environment-data">
                        <strong>
                          {evidence.climate?.monthly_mean_apparent_max_c?.[
                            "7"
                          ] ?? "—"}
                          <small>℃</small>
                        </strong>
                        <p>
                          다낭 7월 일 최고 체감온도의 월평균
                          <br />
                          <small>
                            {evidence.climate?.period || "관측 기간 확인 필요"}{" "}
                            · 과거 기후 / 여행일 예보 아님
                          </small>
                        </p>
                      </div>
                      <div className="inline verification-inline">
                        <span>
                          저장된 실행 <b>{evidence.verification.runs}회</b>
                        </span>
                        <span>
                          검증 통과 <b>{evidence.verification.valid}회</b>
                        </span>
                        <span>
                          점수·근거{" "}
                          <b>
                            {evidence.verification.matched_dimensions}/4 연결
                          </b>
                        </span>
                      </div>
                      <p className="muted">
                        실제 채점에 사용한 월과 조건은 오른쪽 인용 근거에서
                        확인하세요.
                      </p>
                    </section>
                  )}
                  <h3>관람 방식별 난이도</h3>
                  <div className="mode-cards">
                    {selectedPlace &&
                      (["short", "standard", "full"] as const).map((m) => (
                        <article key={m}>
                          <span className="eyebrow">
                            {m === "short"
                              ? "부담을 줄이는 선택"
                              : m === "standard"
                                ? "일반적인 관람"
                                : "더 넓게 둘러보기"}
                          </span>
                          <h3>{selectedPlace.modes[m].name}</h3>
                          <div className="inline wrap">
                            {chips(selectedPlace.modes[m])}
                          </div>
                          {Object.values(selectedPlace.modes[m].dimensions)
                            .flatMap((d) => d.conditions)
                            .slice(0, 2)
                            .map((c, i) => (
                              <p key={i}>{c}</p>
                            ))}
                        </article>
                      ))}
                  </div>
                  <div className="insight-card">
                    <span>↗</span>
                    <div>
                      <h3>종합 등급과 주의 태그를 함께 확인하세요</h3>
                      <p>
                        종합 부담이 ‘중’이어도 계단이 많으면 별도 주의 태그로
                        표시합니다. 이 평가가 고객의 동선과 조정 추천으로
                        이어집니다.
                      </p>
                      <button
                        className="text-button"
                        onClick={() => {
                          setView("customer");
                          setSelected("dad-02");
                          setDay(
                            itinerary?.days.find((d) =>
                              d.stops.some((s) => s.place_id === "dad-02"),
                            )?.day || 1,
                          );
                        }}
                      >
                        고객 일정에서 확인 →
                      </button>
                    </div>
                  </div>
                </section>
                <aside className="evidence-sidebar">
                  <EvidencePanel
                    data={evidence}
                    sources={sources}
                    operator
                    reviewed={demo && demoReviewed.includes(selected)}
                  />
                </aside>
              </main>
            </>
          ) : !demo && !mdAuth ? (
            <div className="login-card">
              <h2>운영자 인증</h2>
              <p>
                운영자에게 제공된 인증값으로 로그인하세요. 인증 후에는 서버
                세션을 사용합니다.
              </p>
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  mdLogin();
                }}
              >
                <input
                  type="password"
                  aria-label="운영자 인증값"
                  value={mdToken}
                  onChange={(e) => setMdToken(e.target.value)}
                  autoComplete="off"
                />
                <button className="button primary" disabled={busy}>
                  로그인
                </button>
              </form>
            </div>
          ) : (
            mdReview()
          )}
        </>
      ) : (
        <>
          <section className="page-heading customer-heading">
            <div>
              <div className="eyebrow">여행 일정 / 다낭</div>
              <h1>부모님 다낭 여행</h1>
              <p>
                {conditions.name}의 다낭 여행 · 동선 위에서 부담을 확인하고
                바꿔보세요.
              </p>
            </div>
            <button
              className="button primary"
              disabled={busy || !itinerary || !!proposal}
              onClick={openShare}
            >
              부모님께 공유 ↗
            </button>
          </section>
          <div className="profile-strip">
            <span>
              ◉ {conditions.name}:{" "}
              {demo
                ? "선택: 15~30분 보행 · 일정 계산: 연속 20분 기준"
                : {
                    under_15min: "15분 미만",
                    "15_30min": "15~30분",
                    "30_60min": "30~60분",
                    "1_2hour": "1~2시간",
                    over_2hour: "2시간 이상",
                  }[duration]}{" "}
              {conditions.name === "부모님" &&
                !demo &&
                ` / 두 번째: ${{ under_15min: "15분 미만", "15_30min": "15~30분", "30_60min": "30~60분", "1_2hour": "1~2시간", over_2hour: "2시간 이상" }[secondDuration]}`}{" "}
              · {conditions.avoid_tags.join(" · ") || "추가 주의 선택 없음"}
            </span>
            <button
              className="inline-edit"
              onClick={() => {
                setSetup(true);
                setTab("conditions");
              }}
            >
              조건 수정
            </button>
          </div>
          {setup ? (
            <section className="setup-layout">
              {conditionsForm()}
              <div className="setup-story">
                <span>↗</span>
                <h2>
                  덜 걷는 여행보다,
                  <br />
                  원하시는 곳을
                  <br />
                  무리 없이.
                </h2>
                <p>
                  지도에 없는 관광지 내부의 계단·보행·더위·혼잡까지 확인합니다.
                </p>
                <p>선택한 장소를 바꾸기 전에는 반드시 변경안을 보여드려요.</p>
                {itinerary && (
                  <button
                    className="button secondary"
                    onClick={() => {
                      setSetup(false);
                      setTab("route");
                    }}
                  >
                    현재 일정으로 돌아가기
                  </button>
                )}
              </div>
            </section>
          ) : (
            <main className={"customer-layout tab-" + tab}>
              <aside className="condition-sidebar">
                <div className="eyebrow">여행의 기준</div>
                <h2>부모님 조건</h2>
                <div className="profile-avatar">
                  {conditions.name === "아빠" ? "아" : "엄"}
                </div>
                <h3>{conditions.name}의 걸음에 맞춰</h3>
                <p className="muted">
                  선택한 보행 시간을 기준으로 이동과 쉬는 시간을 계산해요.
                </p>
                <h4>주의할 부담</h4>
                <div className="inline wrap">
                  {conditions.avoid_tags.map((t) => (
                    <span className="tag caution" key={t}>
                      {t}
                    </span>
                  ))}
                </div>
                <h4>꼭 가고 싶은 곳</h4>
                <p>
                  {conditions.must_places
                    .map((id) => places.find((p) => p.place_id === id)?.name_ko)
                    .join(" · ") || "아직 선택하지 않았어요"}
                </p>
                <button
                  className="button secondary full"
                  disabled={!!proposal}
                  onClick={() => {
                    setSetup(true);
                    setTab("conditions");
                  }}
                >
                  조건 다시 고르기
                </button>
                <hr />
                <button
                  className="text-button"
                  onClick={() => run(loadOpinions)}
                >
                  부모님 의견 확인 ↻
                </button>
                {opinions.map((o) => (
                  <article className="opinion" key={o.id}>
                    <b>
                      {o.day}일차 · {o.choice}
                    </b>
                    <small>
                      공유 버전 {o.version} · {o.reviewed ? "확인함" : "미확인"}
                    </small>
                    {!o.reviewed && (
                      <button
                        onClick={() =>
                          run(async () => {
                            if (!demo && trip)
                              await api(
                                `/ui/trips/${trip.id}/opinions/${o.id}/review`,
                                post(),
                                trip.owner_key,
                              );
                            else {
                              const list = opinions.map((x) =>
                                x.id === o.id ? { ...x, reviewed: true } : x,
                              );
                              sessionStorage.setItem(
                                "bangeoreum-demo-opinions",
                                JSON.stringify(list),
                              );
                            }
                            await loadOpinions();
                            setDay(o.day);
                            setTab("adjust");
                            setNotice(
                              "의견을 확인했어요. 조정안을 고른 뒤 승인하면 반영돼요.",
                            );
                          })
                        }
                      >
                        확인하고 조정하기
                      </button>
                    )}
                  </article>
                ))}
                <div className="notice">
                  지도와 이동·보행 시간은 예상 정보예요. 실제 이동 상황에 따라
                  달라질 수 있어요.
                </div>
              </aside>
              <section className="route-panel">
                <div className="inline spread">
                  <div>
                    <div className="eyebrow">일자별 일정</div>
                    <h2>전체 동선</h2>
                  </div>
                  <span className="tag">
                    {proposal ? "변경안 미리보기" : "확정 일정"}
                  </span>
                </div>
                <nav className="day-tabs">
                  {itinerary?.days.map((d) => (
                    <button
                      className={current?.day === d.day ? "active" : ""}
                      key={d.day}
                      onClick={() => setDay(d.day)}
                    >
                      {d.day}일차 <span>{grade(d.difficulty)}</span>
                    </button>
                  ))}
                </nav>
                {current && shown && (
                  <>
                    <div className="day-metrics">
                      <div>
                        <span>하루 총부담</span>
                        <strong>
                          <Badge value={grade(shown.difficulty)} />
                        </strong>
                        {proposal && (
                          <small>
                            현재 {grade(current.difficulty)} → 변경안{" "}
                            {grade(shown.difficulty)}
                          </small>
                        )}
                      </div>
                      <div>
                        <span>예상 보행</span>
                        <strong>
                          {shown.total_walk_min}
                          <small>분</small>
                        </strong>
                        {proposal && (
                          <small>현재 {current.total_walk_min}분 →</small>
                        )}
                      </div>
                      <div>
                        <span>최장 연속 보행</span>
                        <strong>
                          {shown.max_continuous_walk_min}
                          <small>분</small>
                        </strong>
                        {proposal && (
                          <small>
                            현재 {current.max_continuous_walk_min}분 →
                          </small>
                        )}
                      </div>
                      <div>
                        <span>쉬어가기</span>
                        <strong>
                          {shown.stops.filter((s) => s.type === "rest").length}
                          <small>회</small>
                        </strong>
                      </div>
                    </div>
                    <section
                      className="rule-panel"
                      aria-label="이 날 적용된 규칙"
                    >
                      <h3>이 날 적용된 규칙</h3>
                      <ul>
                        {dayRules(shown).map((r) => (
                          <li key={r.title}>
                            <b>{r.title}</b>
                            <span>{r.body}</span>
                          </li>
                        ))}
                      </ul>
                      <GradeLegend compact />
                      <p className="rule-note">
                        화면의 일정에서 확인되는 값만 요약했어요. 점수·보행
                        시간은 설계 기준 추정이며 현장 측정 결과가 아닙니다.
                      </p>
                    </section>
                    <RouteMap
                      day={shown}
                      before={proposal ? current : undefined}
                      places={places}
                      selected={selected}
                      onSelect={selection}
                    />
                    <div className="inline spread timeline-heading">
                      <h3>{current.day}일차 · 하루의 흐름</h3>
                      <span className="muted">
                        관광지 안에서 걷는 시간도 포함
                      </span>
                    </div>
                    {timeline(shown)}
                    <details className="assumptions">
                      <summary>계산 기준·예상값·미배치 장소 확인</summary>
                      <p>
                        이동 시간은 거리 기반 추정, 보행 시간은 점수·보행속도
                        기반 추정입니다. 실제 길찾기·현장 측정 결과가 아닙니다.
                      </p>
                      <p>
                        하루 부담은 가장 부담스러운 관람과 연속 배치 규칙으로
                        계산한 설계 지표입니다.
                      </p>
                      {itinerary?.assumptions.map((s, i) => (
                        <p key={i}>{s}</p>
                      ))}
                      {itinerary?.unscheduled.map((s) => (
                        <p key={s.place_id}>
                          {
                            places.find((p) => p.place_id === s.place_id)
                              ?.name_ko
                          }
                          : {s.reason}
                        </p>
                      ))}
                    </details>
                  </>
                )}
              </section>
              <aside className="adjust-panel">{adjustments()}</aside>
            </main>
          )}
          <nav className="mobile-tabs">
            {[
              ["route", "동선"],
              ["adjust", "조정" + (proposal ? " ①" : "")],
              ["conditions", "조건"],
            ].map(([v, t]) => (
              <button
                className={tab === v ? "active" : ""}
                key={v}
                onClick={() => {
                  setTab(v);
                  if (v === "conditions") setSetup(true);
                  else setSetup(false);
                }}
              >
                {t}
              </button>
            ))}
          </nav>
        </>
      )}
      <footer className="app-footer">
        반걸음 · 부모님 맞춤 여행 <span>다낭 여행 일정 · 난이도 평가</span>
      </footer>
      {evidenceOpen && (
        <div className="modal-backdrop" onClick={() => setEvidenceOpen(false)}>
          <section
            role="dialog"
            aria-modal="true"
            aria-label="장소 평가 근거"
            className="modal evidence-modal"
            onClick={(e) => e.stopPropagation()}
          >
            <button
              className="close-button"
              aria-label="근거 닫기"
              onClick={() => setEvidenceOpen(false)}
            >
              ×
            </button>
            <EvidencePanel data={evidence} sources={sources} />
          </section>
        </div>
      )}
      {share && (
        <div className="modal-backdrop" onClick={() => setShare(undefined)}>
          <section
            role="dialog"
            aria-modal="true"
            aria-label="부모님 공유"
            className="modal share-modal"
            onClick={(e) => e.stopPropagation()}
          >
            <button
              className="close-button"
              aria-label="공유 닫기"
              onClick={() => setShare(undefined)}
            >
              ×
            </button>
            {shareUrl && (
              <div className="share-link">
                <label>카톡에 붙여넣을 공유 링크</label>
                <input readOnly value={shareUrl} aria-label="공유 링크" />
                <button
                  className="button secondary"
                  onClick={() =>
                    run(async () => {
                      await navigator.clipboard.writeText(shareUrl);
                      setNotice("공유 링크를 복사했어요.");
                    })
                  }
                >
                  링크 복사
                </button>
                <small>
                  이 링크를 가진 분은 일정 조회와 의견 남기기가 가능합니다.
                </small>
              </div>
            )}
            <ParentShare
              snapshot={share.snapshot}
              demo={demo}
              onOpinion={(d, c) => sendOpinion(d, c, share.token)}
            />
          </section>
        </div>
      )}
    </>
  );
}

createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
