-- Spengler Digital CAD – Teile aus dem CAD für die App (Zentrale). Neu; bestehende Tabellen werden nicht verändert.
-- Das Add-in schreibt je Teil Masse, Zuschnitt und app_data (Daten für measurementAlsVorlage() der App, Art «Freies Profil»).
-- Die App übernimmt ein Teil als Massaufnahme (eigene Speicher-Logik der App) und setzt dann measurement_id/status.
create table public.cad_teile (
  id uuid primary key default gen_random_uuid(),
  company_id uuid not null default public.my_company_id() references public.companies(id) on delete cascade,
  project_id bigint references public.projects(id) on delete set null,
  auftrag text not null check (length(auftrag) between 1 and 40),
  dokument text not null default '' check (length(dokument) <= 200),
  teil_nr integer not null default 0,
  teil_label text not null default '' check (length(teil_label) <= 60),
  name text not null default '' check (length(name) <= 200),
  stueck integer not null default 1 check (stueck >= 0),
  material_name text not null default '' check (length(material_name) <= 200),
  staerke_mm numeric,
  zuschnitt_breite_mm numeric,
  zuschnitt_laenge_mm numeric,
  flaeche_mm2 numeric,
  vorlage_name text not null default '' check (length(vorlage_name) <= 200),
  vorlage_version integer,
  operationen jsonb not null default '[]'::jsonb,
  app_data jsonb not null default '{}'::jsonb,
  measurement_id bigint references public.measurements(id) on delete set null,
  status text not null default 'neu' check (status in ('neu', 'uebernommen')),
  addin_version text not null default '' check (length(addin_version) <= 40),
  geaendert_von uuid default auth.uid(),
  geaendert_am timestamptz not null default now(),
  unique (company_id, auftrag, dokument, teil_nr)
);
create index cad_teile_projekt on public.cad_teile (company_id, project_id);
alter table public.cad_teile enable row level security;
create policy tenant_boundary_cad_teile on public.cad_teile as restrictive for all to authenticated
  using (company_id = public.my_company_id()) with check (company_id = public.my_company_id());
create policy cad_teile_lesen on public.cad_teile for select to authenticated using (public.my_company_id() is not null);
create policy cad_teile_einfuegen on public.cad_teile for insert to authenticated with check (public.my_company_id() is not null);
create policy cad_teile_aendern on public.cad_teile for update to authenticated
  using (public.my_company_id() is not null) with check (public.my_company_id() is not null);
grant select, insert, update on public.cad_teile to authenticated;
