-- Additive UI sharing only. Applied files must not be edited after deployment.
CREATE TABLE public.ui_trips (
  id text PRIMARY KEY,
  owner_hash text NOT NULL,
  itinerary jsonb NOT NULL,
  conditions jsonb NOT NULL,
  version integer NOT NULL DEFAULT 1 CHECK (version > 0),
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE public.ui_proposals (
  id text PRIMARY KEY REFERENCES public.scoring_feedback(id),
  trip_id text NOT NULL REFERENCES public.ui_trips(id),
  base_version integer NOT NULL
);
CREATE TABLE public.ui_shares (
  token_hash text PRIMARY KEY,
  trip_id text NOT NULL REFERENCES public.ui_trips(id),
  version integer NOT NULL,
  snapshot jsonb NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE public.ui_opinions (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  trip_id text NOT NULL REFERENCES public.ui_trips(id),
  share_hash text NOT NULL REFERENCES public.ui_shares(token_hash),
  version integer NOT NULL,
  day integer NOT NULL CHECK (day BETWEEN 1 AND 14),
  choice text NOT NULL CHECK (choice IN ('좋아요', '힘들 것 같아요', '여기는 꼭 가고 싶어요')),
  reviewed boolean NOT NULL DEFAULT false,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ui_opinions_trip_created ON public.ui_opinions(trip_id,created_at DESC);
CREATE INDEX ui_shares_trip ON public.ui_shares(trip_id);
ALTER TABLE public.ui_trips ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ui_proposals ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ui_shares ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ui_opinions ENABLE ROW LEVEL SECURITY;
-- No public PostgREST policies: owned server APIs are the only access path.
REVOKE ALL ON public.ui_trips, public.ui_proposals, public.ui_shares, public.ui_opinions FROM anon, authenticated;
REVOKE ALL ON SEQUENCE public.ui_opinions_id_seq FROM anon, authenticated;
