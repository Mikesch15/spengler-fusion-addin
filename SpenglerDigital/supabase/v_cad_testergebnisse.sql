-- Spengler Digital CAD – Testergebnisse aus der Palette (Register «Tests»)
-- Neu, nichts Bestehendes wird verändert. Folgt dem Muster von v_cad_addin_grundlagen.sql:
--   * tenant_boundary_* (RESTRICTIVE): nur Daten der eigenen Firma (my_company_id())
-- Je Firma und Testpunkt steht der zuletzt gemeldete Stand (test_id = Block.Nr aus palette/testplan.json).
-- Schreiben/Lesen darf jedes angemeldete Konto der Firma (Tester sind nicht zwingend Admins). Kein DELETE.
create table public.cad_testergebnisse (
  id uuid primary key default gen_random_uuid(),
  company_id uuid not null default public.my_company_id() references public.companies(id) on delete cascade,
  test_id text not null check (test_id ~ '^[0-9]{1,2}\.[0-9]{1,3}$'),
  text text not null default '' check (length(text) <= 1000),
  status text not null check (status in ('offen', 'ok', 'fehler', 'uebersprungen')),
  notiz text not null default '' check (length(notiz) <= 4000),
  protokoll text not null default '' check (length(protokoll) <= 20000),
  addin_version text not null default '',
  fusion_version text not null default '',
  geaendert_von uuid default auth.uid(),
  geaendert_am timestamptz not null default now(),
  unique (company_id, test_id)
);

alter table public.cad_testergebnisse enable row level security;
create policy tenant_boundary_cad_testergebnisse on public.cad_testergebnisse as restrictive for all to authenticated
  using (company_id = public.my_company_id()) with check (company_id = public.my_company_id());
create policy cad_testergebnisse_lesen on public.cad_testergebnisse for select to authenticated
  using (public.my_company_id() is not null);
create policy cad_testergebnisse_einfuegen on public.cad_testergebnisse for insert to authenticated
  with check (public.my_company_id() is not null);
create policy cad_testergebnisse_aendern on public.cad_testergebnisse for update to authenticated
  using (public.my_company_id() is not null) with check (public.my_company_id() is not null);
grant select, insert, update on public.cad_testergebnisse to authenticated;
