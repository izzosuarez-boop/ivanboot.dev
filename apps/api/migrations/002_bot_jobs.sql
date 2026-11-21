-- Owner bot scheduled reports: remembers the last local date each job ran, so a restart never sends a
-- report twice and a report missed while the server was down is sent once it is back.
create table if not exists public.bot_jobs (
  name        text primary key,          -- 'daily_digest' | 'weekly_report'
  last_run    date not null,             -- local date (DIGEST_TZ) of the last successful send
  updated_at  timestamptz not null default now()
);

alter table public.bot_jobs enable row level security;
revoke all on public.bot_jobs from anon, authenticated;
