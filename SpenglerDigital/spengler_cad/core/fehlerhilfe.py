"""Fehlermeldungen als Lösung: erkennt typische Fusion-/Add-in-Meldungen und sagt, was man tun kann. Reine Logik ohne Fusion."""

REGELN = [  # (Stichwörter – alle klein, mindestens eines muss vorkommen, Hilfetext)
    (("sm_generic_failure", "generic_failure"), "Fusion kann diese Form nicht bauen. Versuche: etwas kleineren Winkel (z. B. 179° statt 180°), grösseren Radius, "
     "kürzeren Schenkel oder die Nachbarkante zuerst bearbeiten."),
    (("biegezone", "keine aussenkante", "freie aussenkante"), "Die gewählte Kante liegt in einer Biegung oder ist keine freie Blechkante. Wähle die Kante am Blechrand "
     "(nicht an der Rundung) – am besten die Kante der Blechdicke."),
    (("nicht zu einem blechkörper", "kein blechkörper", "blechkörper"), "Der Körper ist kein Blech. Im Arbeitsbereich «Blech» einen Blechkörper erstellen "
     "(Konvertieren in Blech) oder den richtigen Körper wählen."),
    (("gehrung",), "Die Gehrung klappt nur, wenn die Kanten zusammenhängen und gleich viele Schritte haben. Prüfe, ob die Kanten an der Ecke wirklich zusammenstossen; "
     "sonst einzeln bauen und die Ecke in Fusion von Hand ausklinken."),
    (("kein auftrag", "es ist kein auftrag aktiv"), "Zuerst «Auftrag wählen» oder «Neuer Auftrag» – der Auftrag bestimmt Teilenummer, Ordner und App-Projekt."),
    (("kein materialprofil", "materialprofil zugeordnet"), "Unter «Vorlagen & Einstellungen → Materialien» ein Profil anlegen und im Dialog wählen."),
    (("nicht angemeldet", "anmelden", "nicht erreichbar", "timeout", "urlopen", "getaddrinfo"), "Die App ist nicht erreichbar. Internetverbindung und Anmeldung unter «Konto» prüfen – "
     "lokal arbeiten geht weiter, der Abgleich kommt später."),
    (("access violation", "zugriffsverletzung"), "Fusion ist an dieser Stelle instabil. Dokument speichern, Fusion neu starten und den Schritt nochmals versuchen; "
     "bitte «Protokoll senden», damit der Fehler untersucht werden kann."),
    (("kürzer als", "mindestlänge", "zu kurz"), "Der Schenkel ist zu kurz für diese Dicke und diesen Radius. Länge erhöhen oder den Radius verkleinern."),
    (("abwicklung",), "Für die Abwicklung muss der Körper ein gültiges Blech sein und alle Biegungen müssen zusammenhängen. Prüfe zuerst in Fusion «Abwicklung erstellen»."),
    (("ungültig", "invalid"), "Eine Auswahl ist ungültig geworden (Fusion hat das Modell neu berechnet). Befehl nochmals starten und die Kanten neu wählen."),
]


def hilfe(text):
    """→ Lösungstext (str) oder None, wenn nichts Passendes bekannt ist."""
    t = (text or "").lower()
    gefunden = []
    for woerter, antwort in REGELN:
        if any(w in t for w in woerter) and antwort not in gefunden:
            gefunden.append(antwort)
    return "\n".join("• " + a for a in gefunden[:2]) if gefunden else None


def mit_hilfe(text):
    h = hilfe(text)
    return "%s\n\nSo geht es weiter:\n%s" % (text, h) if h else text
