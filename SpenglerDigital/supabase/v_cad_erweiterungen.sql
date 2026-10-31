-- Spengler Digital CAD – Erweiterungen: Fertigungsstatus je Auftrag, gemeinsames Änderungsprotokoll, Bild im Fehlerbericht.
-- Neu bzw. nur ergänzend; bestehende Tabellen der App (projects, rates, …) werden vom Add-in nur GELESEN.
-- Gleiches Muster wie v_cad_testergebnisse.sql (tenant_boundary_* restrictive, my_company_id()).

-- Bildschirmfoto zum Fehlerbericht (Base64-JPEG, klein)
alter table public.cad_testergebnisse add column bild text not null default '' check (length(bild) <= 600000);

-- Fertigungsstatus je Auftrag (Auftragsnummer wie im Ordnernamen), von allen PCs der Firma gesehen
create table public.cad_auftragsstatus (
  id uuid primary key default gen_random_uuid(),
  company_id uuid not null default public.my_company_id() references public.companies(id) on delete cascade,
  auftrag text not null check (length(auftrag) between 1 and 40),
  status text not null check (status in ('offen', 'in_arbeit', 'gefertigt', 'geliefert')),
  notiz text not null default '' check (length(notiz) <= 1000),
  geaendert_von uuid default auth.uid(),
  geaendert_am timestamptz not null default now(),
  unique (company_id, auftrag)
);
alter table public.cad_auftragsstatus enable row level security;
create policy tenant_boundary_cad_auftragsstatus on public.cad_auftragsstatus as restrictive for all to authenticated
  using (company_id = public.my_company_id()) with check (company_id = public.my_company_id());
create policy cad_auftragsstatus_lesen on public.cad_auftragsstatus for select to authenticated using (public.my_company_id() is not null);
create policy cad_auftragsstatus_einfuegen on public.cad_auftragsstatus for insert to authenticated with check (public.my_company_id() is not null);
create policy cad_auftragsstatus_aendern on public.cad_auftragsstatus for update to authenticated
  using (public.my_company_id() is not null) with check (public.my_company_id() is not null);
grant select, insert, update on public.cad_auftragsstatus to authenticated;

-- Änderungsprotokoll der Vorlagen/Materialien (nur anfügen und lesen)
create table public.cad_aenderungen (
  id bigint generated always as identity primary key,
  company_id uuid not null default public.my_company_id() references public.companies(id) on delete cascade,
  zeit timestamptz not null default now(),
  benutzer text not null default '' check (length(benutzer) <= 200),
  aktion text not null check (length(aktion) <= 80),
  name text not null default '' check (length(name) <= 200),
  version integer,
  vorlage_id text not null default '' check (length(vorlage_id) <= 80),
  geaendert_von uuid default auth.uid()
);
create index cad_aenderungen_zeit on public.cad_aenderungen (company_id, zeit desc);
alter table public.cad_aenderungen enable row level security;
create policy tenant_boundary_cad_aenderungen on public.cad_aenderungen as restrictive for all to authenticated
  using (company_id = public.my_company_id()) with check (company_id = public.my_company_id());
create policy cad_aenderungen_lesen on public.cad_aenderungen for select to authenticated using (public.my_company_id() is not null);
create policy cad_aenderungen_einfuegen on public.cad_aenderungen for insert to authenticated with check (public.my_company_id() is not null);
grant select, insert on public.cad_aenderungen to authenticated;
