from django.shortcuts import render, redirect							# render  -> HTML-Seite anzeigen redirect -> Weiterleitung zu einer anderen Seite
												# djangoshortcuts -> abkuerzungen fuer haeufige Aufgaben
from django.contrib import messages								# django.contrib -> sammlungsmodul von Django . messages -> Meldungen an Benutzer (success, error, info)
from django.conf import settings								# settings -> Zugriff auf BASE_DIR (ProjektHauptordner) conf-> Djangomodul für Konfiguration, stellt sich das einstellungen ueber all gleich sind da
from django.http import JsonResponse, HttpResponse						# HTTP = HTTPanfrageen(request), HTTPantworten(response)- JsonResponse= wandelt eine Pythondatei automatisch in eine Jsondatei umHttpResponse -> normale HTTP-Antwort (z. B. CSV, XML)

from django.http import FileResponse								# FileResponse -> Datei als Download ausliefern (z. B. JSON Download)
from pathlib import Path									# Path -> Dateipfade sicher bauen (funktioniert auf Linux/Windows)pathlib= pythonmodul fuer datei pfade

import json											# json -> JSON lesen und schreiben
											
												


# ======== Berichte JSON Speicher =========

REPORTS_FILE = Path(settings.BASE_DIR) / "data" / "berichte.json"				# Pfad: /projektordner/data/berichte.json

 
def _ensure_reports():										
    REPORTS_FILE.parent.mkdir(exist_ok=True)
    if not REPORTS_FILE.exists():
        REPORTS_FILE.write_text("[]", encoding="utf-8")
 
def _load_reports():										 
    _ensure_reports()										 # Sicherstellen, dass Datei existiert
    return json.loads(REPORTS_FILE.read_text(encoding="utf-8"))					 # Datei als Text lesen und JSON in Python umwandeln
 
def _save_reports(reports):
    _ensure_reports()
    REPORTS_FILE.write_text(
        json.dumps(reports, ensure_ascii=False, indent=2),					# [ensure_ascii=False] verhindert, dass Umlaute in Zahlen-Codes umgewandelt werden
        encoding="utf-8"
    )												# Python-Liste als JSON formatiert speichern

# ======== Module JSON Speicher =========

MODULE_FILE = Path(settings.BASE_DIR) / "data" / "module.json"
def _load_modules():
   if not MODULE_FILE.exists():
       MODULE_FILE.parent.mkdir(exist_ok=True)
       MODULE_FILE.write_text('["SA"]', encoding="utf-8")					 # Standardinhalt schreiben (unser Beispiel SA)
   return json.loads(MODULE_FILE.read_text(encoding="utf-8"))
def _save_modules(modules):
   MODULE_FILE.write_text(
       json.dumps(modules, ensure_ascii=False, indent=2),
       encoding="utf-8"
   )

# ============ User JSON Speicher ============

USERS_FILE = Path(settings.BASE_DIR) / "data" / "users.json"

def _ensure_store():				
    USERS_FILE.parent.mkdir(exist_ok=True)							 # Ordner erstellen, falls er fehlt
    if not USERS_FILE.exists():
        USERS_FILE.write_text("[]", encoding="utf-8")

def _load_users():
    _ensure_store()
    return json.loads(USERS_FILE.read_text(encoding="utf-8"))					 # Python-Liste als JSON speichern

def _save_users(users):
    _ensure_store()
    USERS_FILE.write_text(
        json.dumps(users, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

# ======== JSON Export ==================

def _check_vip_or_admin(request):
    return request.session.get("role") in ["vip", "admin"]
def export_json(request):									# Zugriff nur fuer VIP oder Admin
   if not _check_vip_or_admin(request):
       return redirect("uebersicht")
   reports = _load_reports()									# Alle Berichte laden
   user_email = request.session.get("email")
   eigene = [r for r in reports if r["user"] == user_email]					# Nur eigene Berichte filtern									
   json_bytes = json.dumps(
       eigene,
       indent=2,
	
   ).encode("utf-8")										# JSON in Bytes umwandeln (Download)
   file_like = io.BytesIO(json_bytes)								# Bytes als Datei im Speicher behandeln
   return FileResponse(
       file_like,
       as_attachment=True,
       filename="berichte.json",
       content_type="application/json"
   ) 												# FileResponse als Download zurueckgeben
# ================ CSV Export ==================

def export_csv(request):
   if not _check_vip_or_admin(request):
       return redirect("uebersicht")
   reports = _load_reports()
   user_email = request.session.get("email")
   eigene = [r for r in reports if r["user"] == user_email]
   response = HttpResponse(content_type="text/csv")						# HTTP Antwort als CSV definieren
   response["Content-Disposition"] = 'attachment; filename="berichte.csv"'			# Browser soll Download starten
   writer = csv.writer(response)								# CSV-Writer erstellen
   writer.writerow(["Datum", "Modul", "Minuten", "Beschreibung"])				# Kopfzeile schreiben
   for r in eigene:
       writer.writerow([
           r.get("datum"),
           r.get("modul"),
           r.get("minuten"),
           r.get("content")
       ])
   return response										# CSV Download zurueckgeben

# =============== XML Export ==================

def export_xml(request):
   if not _check_vip_or_admin(request):
       return redirect("uebersicht")
   reports = _load_reports()
   user_email = request.session.get("email")
   eigene = [r for r in reports if r["user"] == user_email]
   root = ET.Element("berichte")								# XML Root erstellen
   for r in eigene:										# Jeden Bericht als XML-Knoten anhaengen
       bericht = ET.SubElement(root, "bericht")
       ET.SubElement(bericht, "datum").text = r.get("datum", "")
       ET.SubElement(bericht, "modul").text = r.get("modul", "")
       ET.SubElement(bericht, "minuten").text = str(r.get("minuten", 0))
       ET.SubElement(bericht, "beschreibung").text = r.get("content", "")
   xml_data = ET.tostring(root, encoding="utf-8")						# XML in Bytes umwandeln
   response = HttpResponse(xml_data, content_type="application/xml")				# HTTP Antwort als XML senden
   response["Content-Disposition"] = 'attachment; filename="berichte.xml"'			# Browser soll Download starten
   return response

# =============== LOGIN =============

def benutzer_login(request):
   if request.method == "POST":									# Wenn Formular abgeschickt wurde
       email = (request.POST.get("email") or "").strip().lower()				# Werte aus dem Formular holen (POST)
       password = (request.POST.get("password") or "").strip()
       requested_role = request.POST.get("role")
       users = _load_users()									# Benutzerliste laden
       user = next((u for u in users if u.get("email", "").lower() == email), None)		# Benutzer anhand E-Mail suchen											
       if user and not user.get("is_active", True):
           messages.error(request, "Dein Konto wurde gesperrt.")
           return render(request, "login.html")
       												# Email oder Passwort falsch
       if not user or user.get("password") != password:						# Benutzer gesperrt?
           messages.error(request, "Email oder Passwort ist falsch.")
           return render(request, "login.html")
       actual_role = user.get("role", "simple")							# Tatsaechtliche Rolle aus gespeicherten Userdaten						
       allowed = False										# Erlaubnis pruefen darf der Benutzer requested_role nutzen?
       if actual_role == "admin":
           allowed = requested_role in ["admin", "vip", "simple"]
       elif actual_role == "vip":
           allowed = requested_role in ["vip", "simple"]
       else:
           allowed = requested_role == "simple"
       if not allowed:
           messages.error(request, "Diese Rolle darfst du nicht verwenden.")
           return render(request, "login.html")
       request.session["username"] = user["username"]						# Session setzen: damit weiss das System, wer eingeloggt ist
       request.session["email"] = user["email"]
       request.session["role"] = requested_role
       return redirect("uebersicht")								# Nach Login zur Uebersicht
   return render(request, "login.html")

# ================== REGISTRIEREN ===========================

def registrieren(request):									# Wenn Formular abgeschickt wurde
    if request.method == "POST":
        fname = (request.POST.get("vorname") or "").strip()					# Formulardaten holen
        lname = (request.POST.get("nachname") or "").strip()
        email = (request.POST.get("email") or "").strip().lower()
        password = (request.POST.get("password") or "").strip()
        if not fname or not lname or not email or not password:					
            messages.error(request, "Bitte alle Felder ausfuellen.")
            return render(request, "registrieren.html")
        users = _load_users()
        if any(u["email"].lower() == email for u in users):					# Pruefen: E-Mail bereits vorhanden?
            messages.error(request, "Email bereits registriert.")
            return render(request, "registrieren.html")
        username = email.split("@")[0]								# Username automatisch aus Email bauen (Teil vor @)
        users.append({
            "username": username,
            "first_name": fname,
            "last_name": lname,
            "email": email,
            "password": password,
            "role": "simple",
            "is_active": True
        })
        _save_users(users)									# Speichern
        messages.success(request, "Registrierung erfolgreich. Bitte einloggen.")
        return redirect("login")								# Weiterleitung zur Login-Seite
    return render(request, "registrieren.html")							# Wenn GET: Seite anzeigen
    

# =================== LOGOUT ==========================

def logout_view(request):
    request.session.flush()									# Session komplett leeren (Logout)
    return redirect("login")

# ================== Gemeinsame Daten  Header / Dashboard ===================

def _ctx(request):										# Standard-Kontext fuer viele Seiten
    return {
        "username": request.session.get("username"),
        "role": request.session.get("role")
    }

# =================== Seiten ==========================

def uebersicht(request):									# Basisdaten (username + role) in ctx speichern
   ctx = _ctx(request)
   reports = _load_reports()									# Alle gespeicherten Berichte laden
   user_email = request.session.get("email")
   
   eigene_berichte = [
       r for r in reports if r.get("user") == user_email
   ]												# Nur eigene Berichte
   
   gesamt_minuten = sum(r.get("minuten", 0) for r in eigene_berichte)				# Gesamtminuten berechnen
   gesamt_stunden = round(gesamt_minuten / 60, 2)						# Gesamtstunden berechnen min : 60
   
   module = {}											# Minuten pro Modul sammeln
   for r in eigene_berichte:									# Modulname aus Bericht holen (Fallback falls fehlt)
       modul = r.get("modul", "Unbekannt")
       module[modul] = module.get(modul, 0) + r.get("minuten", 0)				# Min addieren				
   # Modul-Details fuer Tabelle vorbereiten
   module_details = []
   for modul, minuten in module.items():
       module_details.append({
           "name": modul,
           "minuten": minuten,
           "stunden": round(minuten / 60, 2),
                  })
   ctx["gesamt_minuten"] = gesamt_minuten							# Werte in Kontext speichern
   ctx["gesamt_stunden"] = gesamt_stunden
   ctx["module_details"] = module_details
   return render(request, "uebersicht.html", ctx)						# Template rendern

def berichte(request):
    ctx = _ctx(request)										# Standard-Kontext
    ctx["modules"] = _load_modules()								# Module fuer Dropdown laden
 
    if request.method == "POST":
        reports = _load_reports()
 
        new_report = {
            "id": len(reports) + 1,
            "user": request.session.get("email"),
            "username": request.session.get("username"),
            "datum": request.POST.get("datum"),
            "modul": request.POST.get("modul"),
            "minuten": int(request.POST.get("minuten")),
            "content": request.POST.get("content", "")
        }
 
        reports.append(new_report)
        _save_reports(reports)									# Speichern
        return redirect("meine_berichte")
 
    return render(request, "berichte.html", ctx)


def meine_berichte(request):
    ctx = _ctx(request)										# Standard-Kontext
    reports = _load_reports()
    user_email = request.session.get("email")
    eigene_berichte = [
        r for r in reports if r["user"] == user_email
    ]												# Nur eigene Berichte filtern
 
    ctx["berichte"] = eigene_berichte
    ctx["gesamt_minuten"] = sum(r["minuten"] for r in eigene_berichte)
    return render(request, "meine_berichte.html", ctx)

def bericht_loeschen(request, bericht_id):
    reports = _load_reports()
    user_email = request.session.get("email")
 
    reports = [
        r for r in reports
        if not (r["id"] == bericht_id and r["user"] == user_email)
    ]												# Bericht entfernen: nur wenn ID und User passen
 
    _save_reports(reports)									# Speichern
    return redirect("meine_berichte")

# =============== berichte bearbeiten =================

def bericht_bearbeiten(request, bericht_id):
   reports = _load_reports()
   user_email = request.session.get("email")
   bericht = next(
       (r for r in reports if r["id"] == bericht_id and r["user"] == user_email),		# Bericht suchen, der zu ID und User passt
       None
   )
   if not bericht:
       return redirect("meine_berichte")
   if request.method == "POST":									# Wenn Formular abgesendet wurde: Werte aktualisieren
       bericht["datum"] = request.POST.get("datum")
       bericht["modul"] = request.POST.get("modul")
       bericht["minuten"] = int(request.POST.get("minuten"))
       bericht["content"] = request.POST.get("content")
       _save_reports(reports)
       return redirect("meine_berichte")
   return render(request, "berichte.html", {
       **_ctx(request),
       "edit": True,
       "bericht": bericht,
       "modules": _load_modules()  
   })												# Wenn GET: Berichte-Formular im Edit-Modus anzeigen

# =============== Rollenwechsel speichern (Antrag) =================

ROLE_REQUESTS_FILE = Path(settings.BASE_DIR) / "data" / "role_requests.json"

def _load_role_requests():
    if not ROLE_REQUESTS_FILE.exists():
        ROLE_REQUESTS_FILE.write_text("[]", encoding="utf-8")
    return json.loads(ROLE_REQUESTS_FILE.read_text(encoding="utf-8"))

def _save_role_requests(requests):
    ROLE_REQUESTS_FILE.write_text(
        json.dumps(requests, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

def einstellungen(request):
    ctx = _ctx(request)   
    if request.method == "POST":
        zielrolle = request.POST.get("zielrolle")
        begruendung = request.POST.get("begruendung", "")
        reqs = _load_role_requests()								# Antraege laden
        new_request = {
            "id": len(reqs) + 1,
            "username": request.session.get("username"),
            "email": request.session.get("email"),
            "current_role": request.session.get("role"),
            "requested_role": zielrolle,
            "reason": begruendung,
            "status": "offen"
        }

        reqs.append(new_request)								# Antrag speichern
        _save_role_requests(reqs)
        return redirect("einstellungen")
    return render(request, "einstellungen.html", ctx)
 
def rollen_antraege(request):									# Rolle aus Session holen
    role = request.session.get("role")
    if role != "admin":
        messages.error(request, "Kein Zugriff. Nur Administratoren duerfen dies sehen.")
        return redirect("uebersicht")
    role_requests = _load_role_requests()
    return render(request, "rollen_antraege.html", {
        "username": request.session.get("username"),
        "role": role,
        "role_requests": role_requests
    })												# Seite anzeigen

def rolle_genehmigen(request, request_id):
    role_requests = _load_role_requests()
    users = _load_users()
    req = next((r for r in role_requests if r["id"] == request_id), None)			# Antrag suchen
    if not req:
        messages.error(request, "Antrag nicht gefunden.")
        return redirect("rollen_antraege")
    for u in users:										# Passenden Benutzer finden und Rolle aendern
        if u["email"].lower() == req["email"].lower():
            u["role"] = req["requested_role"]
            break
    _save_users(users)
    role_requests = [r for r in role_requests if r["id"] != request_id]				# Antrag entfernen (weil erledigt)

    _save_role_requests(role_requests)
    return redirect("rollen_antraege")

def rolle_ablehnen(request, request_id):
    role_requests = _load_role_requests()
    role_requests = [r for r in role_requests if r["id"] != request_id]				# Antrag entfernen
    _save_role_requests(role_requests)
    return redirect("rollen_antraege")

# ================= Import Berichte =====================
# ================= Import Berichte (NUR JSON) =====================
 
def import_berichte(request):									# Zugriff nur fuer VIP und Admin
    if request.session.get("role") not in ["vip", "admin"]:
        return redirect("uebersicht")								
    if request.method != "POST":								# Nur POST-Anfragen erlauben (Formular-Upload)
        return redirect("meine_berichte")
   
    datei = request.FILES.get("datei")								# Datei aus dem Upload holen
    if not datei:
        messages.error(request, "Keine Datei ausgewaehlt.")
        return redirect("meine_berichte")
    
    name = datei.name.lower()									# Nur JSON-Dateien erlauben
    if not name.endswith(".json"):
        return redirect("meine_berichte")
    user_email = request.session.get("email")
    reports = _load_reports()									# Alte Berichte dieses Users entfernen (Import = Ersetzen)
 
   
    reports = [r for r in reports if r.get("user") != user_email]
    try:

        daten = json.load(datei)								# JSON-Datei einlesen
        for b in daten:										# Neue Berichte aus JSON hinzufuegen
            reports.append({
                "id": len(reports) + 1,
                "user": user_email,
                "username": request.session.get("username"),
                "datum": b.get("datum"),
                "modul": b.get("modul"),
                "minuten": int(b.get("minuten", 0)),
                "content": b.get("content", "")
            })
 
    except Exception:
        messages.error(request, "Fehler beim Import der JSON-Datei.")
        return redirect("meine_berichte")
    _save_reports(reports)
    messages.success(request, "Berichte erfolgreich importiert.")
    return redirect("meine_berichte")
 

# =============== Module verwalten ===============================

def module_verwalten(request):
 
   if request.session.get("role") != "admin":
       return redirect("uebersicht")
   modules = _load_modules()
   if request.method == "POST":									 # Nur speichern, wenn Name da ist und nicht doppelt
       neues_modul = request.POST.get("modul")
       if neues_modul and neues_modul not in modules:
           modules.append(neues_modul)
           _save_modules(modules)
   return render(request, "module_verwalten.html", {
       **_ctx(request),
       "modules": modules
   })
def modul_loeschen(request, modul_name):
   
   if request.session.get("role") != "admin":							# Modul entfernen, wenn vorhanden
       return redirect("uebersicht")
   modules = _load_modules()
   if modul_name in modules:
       modules.remove(modul_name)
       _save_modules(modules)
   return redirect("module_verwalten")

# =============== Benutzer verwalten =================

def benutzer_verwalten(request):
   if request.session.get("role") != "admin":
       return redirect("uebersicht")
   users = _load_users()
   return render(request, "benutzer_verwalten.html", {
       "username": request.session.get("username"),
       "role": request.session.get("role"),
       "users": users
   })												# render zeigt eine andere Seite an

# =============== Benutzer sperren =================

def benutzer_sperren(request, email):
   if request.session.get("role") != "admin":
       return redirect("uebersicht")								# redirect springt zu einer anderen view
   users = _load_users()
   for u in users:
       
       if u["email"] == email and u["email"] != request.session.get("email"):			# Admin darf sich selbst nicht sperren
           u["is_active"] = False
   _save_users(users)
   return redirect("benutzer_verwalten")

def benutzer_entsperren(request, email):
   if request.session.get("role") != "admin":
       return redirect("uebersicht")
   users = _load_users()
   for u in users:										# Benutzer suchen und entsperren
       if u["email"] == email:
           u["is_active"] = True
   _save_users(users)
   return redirect("benutzer_verwalten")