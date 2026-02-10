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
