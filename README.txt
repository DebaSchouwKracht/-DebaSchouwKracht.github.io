Deba Schouwkracht website V3. Upload index.html, style.css, script.js en de volledige map assets naar de root van je GitHub Pages repository. Facebook en WhatsApp zijn gekoppeld. De erkenningsbadge is een eigen ontwerp, geen officieel keurmerk. Voeg uitsluitend echte, geverifieerde klantbeoordelingen toe.

Lokale pagina’s
---------------
Bewerk alleen regio/plaatsen.json. Voeg een object toe met dezelfde velden
als Helmond. Gebruik een unieke plaatsnaam en een unieke slug in kleine
letters met eventueel koppeltekens. De URL krijgt de vorm
https://debaschouwkracht.nl/schoorsteenveger-<slug>.html. Houd een bestaande
slug gelijk om de URL te behouden.

Schrijf een eigen metabeschrijving van 60–165 tekens met de plaatsnaam en
minstens 90 woorden voor intro, lokaal, vraag en antwoord samen. Vermeld
concrete lokale informatie die een klant helpt bij het aanvragen van een
veegbeurt. De bouw stopt bij dubbel gebruik van een plaats of slug en bij
sterk gelijkende lokale teksten, ook bij alleen een andere plaatsnaam.
Controleer zelf of lokale details kloppen en daadwerkelijk iets toevoegen.

Testen en bekijken
-------------------
python3 -m unittest discover -s regio
python3 regio/bouw.py /tmp/deba-voorbeeld
python3 -m http.server 8765 --bind 127.0.0.1 --directory /tmp/deba-voorbeeld

Open http://127.0.0.1:8765/schoorsteenveger-helmond.html. Kies een nieuwe
uitvoermap voor iedere bouw. GitHub Actions bouwt bij pull requests en
pushes naar main en bewaart de complete voorbeeldsite als Actions-artifact.

Publiceren na goedkeuring
-------------------------
Kies bij de eerste goedgekeurde uitrol in Settings > Pages als bron
GitHub Actions. Controleer dat het aangepaste domein debaschouwkracht.nl
bij Pages staat. Start daarna in Actions de workflow ‘Regiopagina’s bouwen’
handmatig op main. Alleen die handmatige uitvoering kan publiceren.
Bij een volgende publicatie volstaat opnieuw de workflow draaien op main.
