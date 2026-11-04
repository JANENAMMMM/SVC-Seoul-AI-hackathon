export type Mode = "standard" | "short" | "full";
export type View = {
  grade: string | null;
  cautions: string[];
  name: string;
  score: number;
  dimensions: Record<
    string,
    { score: number; conditions: string[]; evidence_ids: string[] }
  >;
};
export type Place = {
  place_id: string;
  name_ko: string;
  lat: number;
  lng: number;
  status: string;
  modes: Record<Mode, View>;
};
export type Stop = {
  type: string;
  start?: string;
  end?: string;
  name?: string;
  place_id?: string;
  mode?: Mode;
  mode_name?: string;
  walk_min?: number;
  minutes?: number;
  transport?: string;
  note?: string;
  restaurant?: { name: string };
};
export type Day = {
  day: number;
  stops: Stop[];
  difficulty: number | null;
  total_walk_min: number;
  max_continuous_walk_min: number;
};
export type Itinerary = {
  plan_id: string;
  days: Day[];
  request: Record<string, unknown>;
  state: Record<string, unknown>;
  unscheduled: { place_id: string; reason: string }[];
  assumptions: string[];
  package: { peak: number; mean: number } | null;
};
export type Proposal = {
  itinerary: Itinerary;
  change_summary: string;
  clarification: string | null;
  applied_commands: Command[];
};
export type Command = {
  op: string;
  place_id?: string;
  mode?: Mode;
  day?: number;
};
export type Evidence = {
  place_id: string;
  name_ko: string;
  status: string;
  modes: Record<Mode, View>;
  dimensions: {
    dimension: string;
    score: number;
    weight: number;
    rationale: string | null;
    evidence_ids: string[];
    lower_conditions: { condition: string; evidence_ids: string[] }[];
    upper_conditions: { condition: string; evidence_ids: string[] }[];
    run_id: string | null;
  }[];
  verification: {
    runs: number;
    valid: number;
    matched_dimensions: number;
    issue: string | null;
    method: string;
  };
  climate: {
    source?: string;
    period?: string;
    monthly_mean_apparent_max_c?: Record<string, number>;
  };
  notice: string;
};
export type Source = {
  id: string;
  source: string;
  url?: string;
  text?: string;
  caveat?: string;
  value?: unknown;
  unit?: string;
};
export type Snapshot = {
  name: string;
  start_date?: string;
  days: {
    day: number;
    grade: string | null;
    total_walk_min: number;
    rests: number;
    stops: (Stop & { grade?: string | null; cautions?: string[] })[];
  }[];
};
export type Fixture = {
  catalog: Place[];
  evidence: Record<string, Evidence>;
  sources: Record<string, Source[]>;
  before: Itinerary;
  after: Proposal;
  snapshot: Snapshot;
  provenance: string;
  scenarios: Record<string, Proposal>;
};
export type Feedback = {
  id: string;
  status: string;
  place_id: string | null;
  raw_text: string;
  parsed?: unknown;
  before_json?: unknown;
  after_json?: unknown;
  created_at: string;
};
export type Opinion = {
  id: number;
  day: number;
  choice: string;
  version: number;
  reviewed: boolean;
};
