-- HITL 피드백 루프: 유저(자녀·부모님)와 MD의 조정 기록, MD 임시 점수.
-- 새 scoring_ 테이블 2개만 만든다. 기존 테이블은 바꾸지 않는다.
-- 서버(Secret key)만 접근: RLS를 켜고 정책을 두지 않아 anon/authenticated 키로는 읽고 쓸 수 없다.

create table if not exists public.scoring_feedback (
    id text primary key,
    created_at timestamptz not null default now(),
    actor_role text not null check (actor_role in ('child', 'parent', 'md')),
    actor_id text,
    target text not null check (target in ('score', 'itinerary')),
    place_id text,
    plan_ref text,
    raw_text text,
    parsed jsonb,
    status text not null default 'proposed'
        check (status in ('proposed', 'rejudged', 'approved', 'rejected', 'applied')),
    approved_by text,
    decided_at timestamptz,
    before_json jsonb,
    after_json jsonb,
    llm_usage jsonb
);
create index if not exists scoring_feedback_place_idx on public.scoring_feedback (place_id, target, status);

create table if not exists public.scoring_overrides (
    id text primary key,
    feedback_id text not null references public.scoring_feedback (id),
    place_id text not null,
    mode text,
    dimension text not null check (dimension in ('climb', 'walking', 'heat', 'crowd')),
    score integer not null check (score between 1 and 10),
    reason text,
    active boolean not null default true,
    created_at timestamptz not null default now()
);
create index if not exists scoring_overrides_active_idx on public.scoring_overrides (place_id) where active;

alter table public.scoring_feedback enable row level security;
alter table public.scoring_overrides enable row level security;
