-- Spengler Digital CAD (Fusion-Add-in) – Grundlagen in der Datenbank der Spengler-Digital-App
-- Neu, nichts Bestehendes wird verändert. Folgt dem Muster der App:
--   * tenant_boundary_* (RESTRICTIVE): nur Daten der eigenen Firma (my_company_id())
--   * has_permission('vorlagen', 'view'|'edit'): Admin darf ändern, Mitarbeiter sehen (pro Person übersteuerbar)
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
  using (public.has_permission('vorlagen', 'view'));
create policy cad_daten_insert_permission on public.cad_daten for insert to authenticated
  with check (public.has_permission('vorlagen', 'edit'));
create policy cad_daten_update_permission on public.cad_daten for update to authenticated
  using (public.has_permission('vorlagen', 'edit')) with check (public.has_permission('vorlagen', 'edit'));
-- Kein DELETE: gelöscht wird über geloescht = true (Papierkorb, wiederherstellbar).

create policy tenant_boundary_cad_daten_versionen on public.cad_daten_versionen as restrictive for all to authenticated
  using (company_id = public.my_company_id()) with check (company_id = public.my_company_id());
create policy cad_daten_versionen_select_permission on public.cad_daten_versionen for select to authenticated
  using (public.has_permission('vorlagen', 'view'));
create policy cad_daten_versionen_insert_permission on public.cad_daten_versionen for insert to authenticated
  with check (public.has_permission('vorlagen', 'edit'));

grant select, insert, update on public.cad_daten to authenticated;
grant select, insert on public.cad_daten_versionen to authenticated;
grant usage on sequence public.cad_daten_versionen_id_seq to authenticated;

-- Rechte: das bestehende Recht «vorlagen» der App (Massaufnahme-Vorlagen; Admin ändern, Mitarbeiter sehen,
-- pro Person übersteuerbar). Ein eigenes Recht würde eine Änderung an permission_settings_resource_check verlangen.

-- ---------------------------------------------------------------- 3D-Geometrie (Storage)
insert into storage.buckets (id, name, public, file_size_limit) values ('cad', 'cad', false, 52428800);

create policy "cad read own company" on storage.objects for select to authenticated
  using (bucket_id = 'cad' and (storage.foldername(name))[1] = public.my_company_id()::text
         and public.has_permission('vorlagen', 'view'));
create policy "cad upload own company" on storage.objects for insert to authenticated
  with check (bucket_id = 'cad' and (storage.foldername(name))[1] = public.my_company_id()::text
              and (storage.foldername(name))[2] = 'details' and position('..' in name) = 0
              and public.has_permission('vorlagen', 'edit'));
create policy "cad update own company" on storage.objects for update to authenticated
  using (bucket_id = 'cad' and (storage.foldername(name))[1] = public.my_company_id()::text
         and public.has_permission('vorlagen', 'edit'))
  with check (bucket_id = 'cad' and (storage.foldername(name))[1] = public.my_company_id()::text
              and public.has_permission('vorlagen', 'edit'));

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
