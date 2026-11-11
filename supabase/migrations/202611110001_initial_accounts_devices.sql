-- Yvan.IA — première migration Supabase
-- À exécuter dans Supabase > SQL Editor sur le projet Yvan.IA.
-- Les tables sont isolées par auth.uid() et RLS est activé.

create table if not exists public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  display_name text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create or replace function public.yvan_create_profile()
returns trigger language plpgsql security definer set search_path = ''
as $$
begin
  insert into public.profiles (id, display_name)
  values (new.id, coalesce(new.raw_user_meta_data ->> 'display_name', split_part(new.email, '@', 1)))
  on conflict (id) do nothing;
  return new;
end;
$$;

drop trigger if exists yvan_auth_user_created on auth.users;
create trigger yvan_auth_user_created
after insert on auth.users
for each row execute procedure public.yvan_create_profile();

create table if not exists public.user_devices (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  device_name text not null,
  platform text not null check (platform in ('windows','android','web')),
  status text not null default 'pending' check (status in ('pending','paired','offline','revoked')),
  last_seen_at timestamptz,
  created_at timestamptz not null default now(),
  revoked_at timestamptz
);
create index if not exists user_devices_user_id_idx on public.user_devices(user_id);

create table if not exists public.device_pairing_sessions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  token_hash text not null unique,
  expires_at timestamptz not null,
  consumed_at timestamptz,
  created_at timestamptz not null default now()
);
create index if not exists pairing_sessions_user_id_idx on public.device_pairing_sessions(user_id);
create index if not exists pairing_sessions_expiry_idx on public.device_pairing_sessions(expires_at);

create table if not exists public.approved_folders (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  device_id uuid not null references public.user_devices(id) on delete cascade,
  display_path text not null,
  folder_label text not null,
  enabled boolean not null default true,
  created_at timestamptz not null default now(),
  unique (device_id, display_path)
);
create index if not exists approved_folders_user_id_idx on public.approved_folders(user_id);

create table if not exists public.device_audit_events (
  id bigint generated always as identity primary key,
  user_id uuid not null references auth.users(id) on delete cascade,
  device_id uuid references public.user_devices(id) on delete set null,
  event_type text not null,
  details jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
create index if not exists device_audit_user_created_idx on public.device_audit_events(user_id, created_at desc);

alter table public.profiles enable row level security;
alter table public.user_devices enable row level security;
alter table public.device_pairing_sessions enable row level security;
alter table public.approved_folders enable row level security;
alter table public.device_audit_events enable row level security;

drop policy if exists "profile owner reads own profile" on public.profiles;
create policy "profile owner reads own profile" on public.profiles
for select to authenticated using (id = (select auth.uid()));

drop policy if exists "profile owner updates own profile" on public.profiles;
create policy "profile owner updates own profile" on public.profiles
for update to authenticated using (id = (select auth.uid())) with check (id = (select auth.uid()));

drop policy if exists "device owner manages own devices" on public.user_devices;
create policy "device owner manages own devices" on public.user_devices
for all to authenticated using (user_id = (select auth.uid())) with check (user_id = (select auth.uid()));

drop policy if exists "owner manages own pairing sessions" on public.device_pairing_sessions;
create policy "owner manages own pairing sessions" on public.device_pairing_sessions
for all to authenticated using (user_id = (select auth.uid())) with check (user_id = (select auth.uid()));

drop policy if exists "owner manages own approved folders" on public.approved_folders;
create policy "owner manages own approved folders" on public.approved_folders
for all to authenticated using (
  user_id = (select auth.uid()) and exists (
    select 1 from public.user_devices d where d.id = device_id and d.user_id = (select auth.uid())
  )
) with check (
  user_id = (select auth.uid()) and exists (
    select 1 from public.user_devices d where d.id = device_id and d.user_id = (select auth.uid())
  )
);

drop policy if exists "owner reads own audit events" on public.device_audit_events;
create policy "owner reads own audit events" on public.device_audit_events
for select to authenticated using (user_id = (select auth.uid()));

-- Aucun accès anonyme. Les opérations d'agent Windows seront ajoutées
-- avec des fonctions RPC dédiées et des jetons d'appareil à portée limitée.
