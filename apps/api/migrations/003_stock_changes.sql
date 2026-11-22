-- Owner bot restocks: every attempt (applied or rejected by Shopify's compare-and-swap) is recorded.
create table if not exists public.stock_changes (
  id                 bigint generated always as identity primary key,
  created_at         timestamptz not null default now(),
  chat_id            text not null,              -- Telegram chat that confirmed the change
  product            text not null,              -- variant display name
  inventory_item_id  text not null,
  from_qty           int not null,               -- stock when the change was proposed
  to_qty             int not null,               -- stock the owner confirmed
  final_qty          int,                        -- stock read back from Shopify afterwards
  status             text not null check (status in ('applied', 'rejected')),
  error              text
);
create index if not exists stock_changes_created_idx on public.stock_changes (created_at);

alter table public.stock_changes enable row level security;
revoke all on public.stock_changes from anon, authenticated;
