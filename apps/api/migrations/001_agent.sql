-- Ardea Skin agent: conversations, messages (with per-turn cost) and owner escalations.
-- RLS is enabled with NO policies: only the backend's secret key (which bypasses RLS) can read/write.
-- The public/publishable key gets nothing.

create table if not exists public.conversations (
  id                uuid primary key,
  created_at        timestamptz not null default now(),
  last_message_at   timestamptz,
  mode              text check (mode in ('skin', 'builder')),
  ref               text,
  visitor_hash      text,
  message_count     int not null default 0,
  input_tokens      int not null default 0,
  output_tokens     int not null default 0,
  cache_read_tokens int not null default 0,
  cost_usd          numeric(12, 6) not null default 0
);

create table if not exists public.messages (
  id              bigint generated always as identity primary key,
  conversation_id uuid not null references public.conversations (id) on delete cascade,
  created_at      timestamptz not null default now(),
  role            text not null check (role in ('user', 'assistant')),
  content         text not null,
  model           text,
  actions         jsonb,
  stop_reason     text,
  latency_ms      int,
  cost_usd        numeric(12, 6)          -- cost of this turn (sum = real spend)
);
create index if not exists messages_conversation_idx on public.messages (conversation_id, created_at);
create index if not exists messages_created_idx on public.messages (created_at);

create table if not exists public.escalations (
  id              bigint generated always as identity primary key,
  ref_code        text not null unique,
  conversation_id uuid references public.conversations (id) on delete set null,
  created_at      timestamptz not null default now(),
  kind            text not null check (kind in ('complaint', 'order_issue', 'medical_question', 'human_request', 'other')),
  summary         text not null,
  contact         text,
  status          text not null default 'open' check (status in ('open', 'notified', 'closed')),
  notified_at     timestamptz
);

alter table public.conversations enable row level security;
alter table public.messages      enable row level security;
alter table public.escalations   enable row level security;
revoke all on public.conversations, public.messages, public.escalations from anon, authenticated;

-- Aggregate numbers the agent can show ("how cheap is this chat?")
create or replace function public.agent_stats()
returns json language sql stable security definer set search_path = public as $$
  select json_build_object(
    'conversations_total', (select count(*) from conversations),
    'conversations_today', (select count(*) from conversations where created_at >= date_trunc('day', now())),
    'visitor_messages_total', (select count(*) from messages where role = 'user'),
    'spend_usd_total', (select coalesce(round(sum(cost_usd), 4), 0) from messages),
    'avg_cost_per_conversation_usd', (select coalesce(round(avg(cost_usd), 6), 0) from conversations where message_count > 0)
  );
$$;
revoke all on function public.agent_stats() from anon, authenticated;
