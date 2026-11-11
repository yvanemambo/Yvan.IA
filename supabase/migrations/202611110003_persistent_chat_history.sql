-- Historique persistant des discussions Yvan.IA.
create table if not exists public.chat_history (
  user_id uuid primary key references auth.users(id) on delete cascade,
  messages jsonb not null default '[]'::jsonb,
  updated_at timestamptz not null default now(),
  constraint chat_history_messages_is_array check (jsonb_typeof(messages) = 'array')
);

alter table public.chat_history enable row level security;

drop policy if exists "users read own chat history" on public.chat_history;
create policy "users read own chat history" on public.chat_history
for select to authenticated using (user_id = (select auth.uid()));

drop policy if exists "users insert own chat history" on public.chat_history;
create policy "users insert own chat history" on public.chat_history
for insert to authenticated with check (user_id = (select auth.uid()));

drop policy if exists "users update own chat history" on public.chat_history;
create policy "users update own chat history" on public.chat_history
for update to authenticated using (user_id = (select auth.uid()))
with check (user_id = (select auth.uid()));

grant select, insert, update on public.chat_history to authenticated;

create or replace function public.save_yvan_chat_history(p_messages jsonb)
returns void
language plpgsql
security invoker
set search_path = ''
as $$
begin
  if auth.uid() is null then
    raise exception 'Authentication required';
  end if;
  if jsonb_typeof(p_messages) <> 'array' then
    raise exception 'Messages must be a JSON array';
  end if;
  insert into public.chat_history (user_id, messages, updated_at)
  values (auth.uid(), p_messages, now())
  on conflict (user_id) do update
    set messages = excluded.messages, updated_at = now();
end;
$$;

revoke all on function public.save_yvan_chat_history(jsonb) from public;
revoke all on function public.save_yvan_chat_history(jsonb) from anon;
grant execute on function public.save_yvan_chat_history(jsonb) to authenticated;
