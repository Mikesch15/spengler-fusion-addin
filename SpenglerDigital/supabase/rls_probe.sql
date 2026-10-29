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
