-- Bauteilvorlagen (ab Add-in 0.4.37): cad_daten darf den Typ 'bauteilvorlage' speichern. Bereits ausgeführt am Projekt nfgryuzkpwjfmdlmevuy.
alter table public.cad_daten drop constraint cad_daten_typ_check;
alter table public.cad_daten add constraint cad_daten_typ_check check (typ in ('kantenvorlage', 'detailvorlage', 'bauteilvorlage', 'materialprofil'));
