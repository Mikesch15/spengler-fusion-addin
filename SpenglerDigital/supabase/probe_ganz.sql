begin;
-- Spengler Digital CAD (Fusion-Add-in) – Grundlagen in der Datenbank der Spengler-Digital-App
-- Neu, nichts Bestehendes wird verändert. Folgt dem Muster der App:
--   * tenant_boundary_* (RESTRICTIVE): nur Daten der eigenen Firma (my_company_id())
--   * has_permission('cad_vorlagen', 'view'|'edit'): Admin darf ändern, Mitarbeiter sehen (pro Person übersteuerbar)
--
-- cad_daten            Kantenvorlagen, 3D-Detailvorlagen, Materialprofile des Add-ins (ganzer Datensatz als jsonb)
-- cad_daten_versionen  jede frühere Fassung (per Trigger, wie die lokalen Versionen im Add-in)
-- Bucket «cad»         3D-Detailgeometrie (.f3d) unter <company_id>/details/…
-- cad_addin_releases / cad_addin_blobs   Programm-Updates des Add-ins (nur lesbar; geschrieben nur vom Betreiber)

-- ---------------------------------------------------------------- Daten
create table public.cad_daten (
  id uuid primary key default gen_random_uuid(),
  company_id uuid not null default public.my_company_id() references public.companies(id) on delete cascade,
  typ text not null check (typ in ('kantenvorlage', 'detailvorlage', 'materialprofil')),
  record_id text not null check (record_id ~ '^[A-Za-z0-9_.-]{1,80}$'),
  daten jsonb not null,
  version integer not null default 1 check (version >= 1),
  schema_version integer not null default 1,
  geloescht boolean not null default false,
  created_by uuid default auth.uid(),
  updated_by uuid default auth.uid(),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (company_id, typ, record_id)
);
create index cad_daten_company_idx on public.cad_daten (company_id, updated_at);

create table public.cad_daten_versionen (
  id bigserial primary key,
  company_id uuid not null references public.companies(id) on delete cascade,
  typ text not null,
  record_id text not null,
  version integer not null,
  daten jsonb not null,
  geloescht boolean not null default false,
  geaendert_von uuid,
  geaendert_am timestamptz not null default now()
);
create index cad_daten_versionen_idx on public.cad_daten_versionen (company_id, typ, record_id, version);

-- Vor jeder Änderung: alte Fassung ablegen, Zeit/Bearbeiter setzen. SECURITY INVOKER: läuft mit den Rechten des
-- Bearbeiters, die Versionstabelle prüft selbst Firma und Recht (keine Umgehung von RLS).
create or replace function public.cad_daten_vor_aenderung()
returns trigger language plpgsql security invoker set search_path = public as $$
begin
  if new.company_id <> old.company_id or new.typ <> old.typ or new.record_id <> old.record_id then
    raise exception 'Firma, Typ und Kennung eines CAD-Datensatzes sind unveränderlich';
  end if;
  insert into public.cad_daten_versionen (company_id, typ, record_id, version, daten, geloescht, geaendert_von)
  values (old.company_id, old.typ, old.record_id, old.version, old.daten, old.geloescht, old.updated_by);
  new.updated_at := now();
  new.updated_by := auth.uid();
  return new;
end $$;
create trigger cad_daten_vor_aenderung before update on public.cad_daten
  for each row execute function public.cad_daten_vor_aenderung();

alter table public.cad_daten enable row level security;
alter table public.cad_daten_versionen enable row level security;

create policy tenant_boundary_cad_daten on public.cad_daten as restrictive for all to authenticated
  using (company_id = public.my_company_id()) with check (company_id = public.my_company_id());
create policy cad_daten_select_permission on public.cad_daten for select to authenticated
  using (public.has_permission('cad_vorlagen', 'view'));
create policy cad_daten_insert_permission on public.cad_daten for insert to authenticated
  with check (public.has_permission('cad_vorlagen', 'edit'));
create policy cad_daten_update_permission on public.cad_daten for update to authenticated
  using (public.has_permission('cad_vorlagen', 'edit')) with check (public.has_permission('cad_vorlagen', 'edit'));
-- Kein DELETE: gelöscht wird über geloescht = true (Papierkorb, wiederherstellbar).

create policy tenant_boundary_cad_daten_versionen on public.cad_daten_versionen as restrictive for all to authenticated
  using (company_id = public.my_company_id()) with check (company_id = public.my_company_id());
create policy cad_daten_versionen_select_permission on public.cad_daten_versionen for select to authenticated
  using (public.has_permission('cad_vorlagen', 'view'));
create policy cad_daten_versionen_insert_permission on public.cad_daten_versionen for insert to authenticated
  with check (public.has_permission('cad_vorlagen', 'edit'));

grant select, insert, update on public.cad_daten to authenticated;
grant select, insert on public.cad_daten_versionen to authenticated;
grant usage on sequence public.cad_daten_versionen_id_seq to authenticated;

-- Rechte wie bei den Massaufnahme-Vorlagen: Admin ändern, Mitarbeiter sehen
insert into public.permission_settings (role, resource, can_view, can_edit, scope, edit_scope)
values ('admin', 'cad_vorlagen', true, true, 'all', 'all'), ('employee', 'cad_vorlagen', true, false, 'all', 'all');

-- ---------------------------------------------------------------- 3D-Geometrie (Storage)
insert into storage.buckets (id, name, public, file_size_limit) values ('cad', 'cad', false, 52428800);

create policy "cad read own company" on storage.objects for select to authenticated
  using (bucket_id = 'cad' and (storage.foldername(name))[1] = public.my_company_id()::text
         and public.has_permission('cad_vorlagen', 'view'));
create policy "cad upload own company" on storage.objects for insert to authenticated
  with check (bucket_id = 'cad' and (storage.foldername(name))[1] = public.my_company_id()::text
              and (storage.foldername(name))[2] = 'details' and position('..' in name) = 0
              and public.has_permission('cad_vorlagen', 'edit'));
create policy "cad update own company" on storage.objects for update to authenticated
  using (bucket_id = 'cad' and (storage.foldername(name))[1] = public.my_company_id()::text
         and public.has_permission('cad_vorlagen', 'edit'))
  with check (bucket_id = 'cad' and (storage.foldername(name))[1] = public.my_company_id()::text
              and public.has_permission('cad_vorlagen', 'edit'));

-- ---------------------------------------------------------------- Programm-Updates
-- Ein Release ist eine Dateiliste [{pfad, sha256, groesse}]. Inhalte liegen inhaltsadressiert in cad_addin_blobs
-- (text: utf8 bzw. base64). Das Add-in lädt nur Dateien, deren Prüfsumme sich von der installierten unterscheidet.
create table public.cad_addin_releases (
  version text primary key check (version ~ '^[0-9]+\.[0-9]+\.[0-9]+$'),
  dateien jsonb not null,
  hinweise text not null default '',
  aktiv boolean not null default true,
  veroeffentlicht_am timestamptz not null default now()
);
create table public.cad_addin_blobs (
  sha256 text primary key check (sha256 ~ '^[0-9a-f]{64}$'),
  kodierung text not null check (kodierung in ('utf8', 'base64')),
  inhalt text not null
);
alter table public.cad_addin_releases enable row level security;
alter table public.cad_addin_blobs enable row level security;
-- Lesen: angemeldete Benutzer einer aktiven Firma. Schreiben: keine Policy → nur Betreiber (service/postgres).
create policy cad_addin_releases_lesen on public.cad_addin_releases for select to authenticated
  using (public.my_company_id() is not null);
create policy cad_addin_blobs_lesen on public.cad_addin_blobs for select to authenticated
  using (public.my_company_id() is not null);
grant select on public.cad_addin_releases, public.cad_addin_blobs to authenticated;
-- Probelauf: Migration + RLS-Prüfung in EINER Transaktion, am Ende ROLLBACK (verändert nichts).
-- Benutzer: A1 Admin Firma A, E1 Mitarbeiter Firma A, A2 Admin Firma B.
create temp table probe (nr serial, test text, ok boolean, info text);
grant all on probe to authenticated; grant usage on sequence probe_nr_seq to authenticated;
create or replace function pg_temp.als(uid uuid) returns void language plpgsql as $$
begin
  perform set_config('request.jwt.claims', json_build_object('sub', uid, 'role', 'authenticated')::text, true);
  perform set_config('role', 'authenticated', true);
end $$;
-- 1 Admin A legt an
select pg_temp.als('56a11f26-8d3d-4a99-b2e3-5fe7344d0fc5');
do $$ begin
  insert into public.cad_daten (typ, record_id, daten) values ('kantenvorlage', 'kv-probe1', '{"name":"Probe"}');
  insert into probe(test, ok) values ('Admin A darf anlegen', true);
exception when others then insert into probe(test, ok, info) values ('Admin A darf anlegen', false, sqlerrm); end $$;
do $$ begin
  update public.cad_daten set daten = '{"name":"Probe 2"}', version = 2 where record_id = 'kv-probe1';
  insert into probe(test, ok, info) values ('Admin A ändert → Version abgelegt', (select count(*) = 1 from public.cad_daten_versionen where record_id = 'kv-probe1'), null);
exception when others then insert into probe(test, ok, info) values ('Admin A ändert', false, sqlerrm); end $$;
do $$ begin
  insert into public.cad_daten (company_id, typ, record_id, daten) values ('b0057c43-02b3-4af5-b392-f3c5332edd6a', 'kantenvorlage', 'kv-fremd', '{}');
  insert into probe(test, ok) values ('Admin A darf NICHT in Firma B schreiben', false);
exception when others then insert into probe(test, ok, info) values ('Admin A darf NICHT in Firma B schreiben', true, sqlerrm); end $$;
do $$ begin
  delete from public.cad_daten where record_id = 'kv-probe1';
  insert into probe(test, ok, info) values ('Löschen wirkt nicht (nur Papierkorb)', (select count(*) = 1 from public.cad_daten where record_id = 'kv-probe1'), null);
end $$;
reset role;
-- 2 Mitarbeiter A: sehen ja, ändern nein
select pg_temp.als('c8ed732b-d4c5-4ccc-844a-773662746bca');
insert into probe(test, ok) select 'Mitarbeiter A sieht die Vorlage', count(*) = 1 from public.cad_daten where record_id = 'kv-probe1';
do $$ begin
  insert into public.cad_daten (typ, record_id, daten) values ('kantenvorlage', 'kv-ma', '{}');
  insert into probe(test, ok) values ('Mitarbeiter A darf NICHT anlegen', false);
exception when others then insert into probe(test, ok, info) values ('Mitarbeiter A darf NICHT anlegen', true, sqlerrm); end $$;
do $$ declare n int; begin
  update public.cad_daten set version = 9 where record_id = 'kv-probe1';
  get diagnostics n = row_count;
  insert into probe(test, ok, info) values ('Mitarbeiter A darf NICHT ändern', n = 0, n || ' Zeilen');
exception when others then insert into probe(test, ok, info) values ('Mitarbeiter A darf NICHT ändern', true, sqlerrm); end $$;
insert into probe(test, ok) select 'Mitarbeiter A liest Releases', count(*) >= 0 from public.cad_addin_releases;
do $$ begin
  insert into public.cad_addin_releases (version, dateien) values ('9.9.9', '[]');
  insert into probe(test, ok) values ('Releases nicht schreibbar', false);
exception when others then insert into probe(test, ok, info) values ('Releases nicht schreibbar', true, sqlerrm); end $$;
reset role;
-- 3 Admin Firma B sieht nichts von A
select pg_temp.als('665e202d-5fae-42e9-8d8f-677348931e82');
insert into probe(test, ok) select 'Firma B sieht nichts von A', count(*) = 0 from public.cad_daten;
insert into probe(test, ok) select 'Firma B sieht keine Versionen von A', count(*) = 0 from public.cad_daten_versionen;
reset role;
do $$ begin raise exception E'PROBE-ERGEBNIS (wird zurueckgenommen):\n%', (select string_agg(nr || ' ' || case when ok then 'OK ' else 'FEHLER ' end || test || coalesce(' [' || info || ']', ''), E'\n' order by nr) from probe); end $$;
