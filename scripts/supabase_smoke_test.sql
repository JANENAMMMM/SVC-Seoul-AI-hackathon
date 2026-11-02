-- Supabase Dashboard > SQL Editor에서 실행하세요.
-- SDK 확인 후 삭제할 테스트 전용 테이블입니다.
create table public.connection_smoke_test (
    id uuid primary key default gen_random_uuid(),
    message text not null,
    created_at timestamptz not null default now()
);

alter table public.connection_smoke_test enable row level security;
grant select, insert, delete on public.connection_smoke_test to service_role;

-- 테스트가 끝나면 별도로 실행:
-- drop table public.connection_smoke_test;
