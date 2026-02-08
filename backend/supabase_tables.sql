-- Supabase schema for fights and judgments
-- Run this in the Supabase SQL editor (requires service role or owner)

-- Drop if exists (safe to run in a dev project)
drop table if exists public.judgments cascade;
drop table if exists public.fights cascade;

create table public.fights (
  id uuid default gen_random_uuid() primary key,
  external_id text,
  metadata jsonb default '{}'::jsonb,
  created_at timestamptz default now()
);

create table public.judgments (
  id uuid default gen_random_uuid() primary key,
  fight_id uuid references public.fights(id) on delete cascade,
  judge text,
  scores jsonb,
  created_at timestamptz default now()
);

-- Indexes for quick lookups
create index if not exists idx_fights_external_id on public.fights(external_id text_pattern_ops);
create index if not exists idx_judgments_fight on public.judgments(fight_id);
