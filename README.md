# EV Smart Charge Planner

Een universele slimme laadplanner voor elektrische auto's en laadpalen.

Het project berekent wanneer een auto het beste kan laden op basis van dynamische energieprijzen, laadvermogen, benodigde energie, zonneforecast en een optionele deadline. De laadpaal wordt uitsluitend aangestuurd door lokale veiligheidscontroles.

> Status: HACS-MVP. De persoonlijke Node-RED-flow wordt niet gepubliceerd.

## HACS-installatie

De repository is ingericht als een HACS custom integration. Voor installatie via HACS:

1. Open `HACS → Integraties`.
2. Kies het menu rechtsboven en selecteer `Aangepaste repositories`.
3. Voeg de URL van deze GitHub-repository toe.
4. Kies categorie `Integration`.
5. Installeer `EV Smart Charge Planner`.
6. Herstart Home Assistant.
7. Voeg de integratie toe via `Instellingen → Apparaten & diensten → Integratie toevoegen`.
8. Open daarna links in de sidebar `EV Smart Charge`.

Voor lokaal testen kan de map `custom_components/ev_smart_charge` rechtstreeks naar `/config/custom_components/` worden gekopieerd.

## Versies en updates

De integratie gebruikt GitHub-tags en releases. HACS toont daardoor versies in plaats van alleen losse commits.

De huidige stabiele versie is:

```text
v0.5.3
```

Na een nieuwe release:

1. Open HACS.
2. Ga naar `Integraties → Updates`.
3. Kies `EV Smart Charge Planner`.
4. Installeer de nieuwe versie.
5. Herstart Home Assistant.

Gebruik voor testen bij voorkeur eerst een nieuwere release in HACS. De `main`-branch bevat ontwikkelwijzigingen die nog niet als stabiele versie zijn gemarkeerd.

## Telegram instellen

De integratie gebruikt de bestaande Telegram-integratie van Home Assistant. Er wordt geen bot-token in deze integratie opgeslagen.

Open na installatie de opties van de integratie en vul in:

- `Telegramberichten inschakelen`: aan;
- `Telegram-service`: meestal `telegram_bot.send_message`;
- `Telegram chat-ID`: vul hier je eigen chat-ID in.

De integratie maakt daarna tekstentiteiten aan waarmee de templates vanuit het dashboard kunnen worden aangepast:

Het sidebar-panel zoekt de eigen entities ook op basis van hun suffix. Daardoor blijven bestaande Home Assistant-object-ID's werken als Home Assistant bij een herinstallatie een extra naamdeel heeft toegevoegd. Als er nog geen entities zichtbaar zijn, moet eerst de configuratieflow van de integratie worden afgerond.

```text
text.ev_smart_charge_telegram_template_test
text.ev_smart_charge_telegram_template_plan
text.ev_smart_charge_telegram_template_start
text.ev_smart_charge_telegram_template_done
text.ev_smart_charge_telegram_template_stop
text.ev_smart_charge_telegram_template_blocked
```

Beschikbare templatevelden zijn onder andere `{soc}`, `{target}`, `{plan_start}`, `{plan_end}`, `{plan_kwh}`, `{plan_cost}`, `{plan_ere}`, `{plan_net}`, `{session_kwh}`, `{session_cost}`, `{session_ere}` en `{session_net}`.

Op het meegeleverde dashboard staan knoppen om ieder berichttype afzonderlijk te testen. De services zijn ook rechtstreeks te gebruiken:

```yaml
action: ev_smart_charge.telegram_test
```

```yaml
action: ev_smart_charge.telegram_send
data:
  event: plan
```

De automatische meldingen zijn:

- plan aangemaakt;
- laden gestart;
- laden klaar;
- handmatig gestopt;
- laden geblokkeerd door de veiligheidscontrole.

Zet Telegram uit tijdens het testen met de schakelaar als je geen automatische meldingen wilt ontvangen.

## Setup wizard en veilige migratie

Vanaf v0.5.0 staat er een setup wizard in het sidebar-panel `EV Smart Charge`. De wizard:

1. zoekt passende auto-, laadpaal-, tarief- en zonne-entiteiten;
2. toont per veld een duidelijke naam, de entity-ID en de reden voor de suggestie;
3. laat de koppelingen en energieprovider opslaan;
4. voert een verbindingstest uit zonder de laadpaal te schakelen;
5. staat standaard op `Alleen monitoren/testen (Node-RED)`.

### Koppelingen controleren en wijzigen

Onder `Apparaat en sensoren` toont het sidebar-panel nu per bron een live controle:

- groen `Goed`: de gekozen entity bestaat en levert een bruikbare waarde;
- oranje `Controleren`: de entity bestaat, maar bijvoorbeeld de tariefforecast bevat nog geen blokken;
- rood `Niet goed`: de verplichte entity ontbreekt, bestaat niet meer of is tijdelijk onbeschikbaar;
- grijs `Optioneel`: een niet-verplichte bron, zoals zonneforecast, is niet gekoppeld.

Dezelfde koppelingen zijn ook te wijzigen via de native Home Assistant-configuratie:
`Instellingen → Apparaten & diensten → Configuraties → EV Smart Charge Planner → Koppelingen wijzigen`.
De knop opent de volledige auto-, laadpaal-, tarief- en zonnekeuze opnieuw. Na opslaan wordt de integratie automatisch met de nieuwe bronnen bijgewerkt. De actie schakelt de laadpaal niet.

In deze standaardmodus leest de integratie de sensoren uit, berekent lokale plannen en toont testresultaten, maar zet zij nooit de laadpaal aan of uit. Daardoor kan de HACS-integratie naast de bestaande Node-RED-flow draaien tijdens het testen. Zet pas `HACS mag besturen` aan nadat Node-RED voor deze laadpaal is uitgeschakeld; gebruik nooit twee actieve besturingen tegelijk.

De tariefprovider is instelbaar op automatisch, Zonneplan, Tibber, ANWB Dynamisch of generiek. De planner verwacht uiteindelijk een forecast met starttijd, eindtijd en prijs; Zonneplan levert dit in het forecast-attribuut van de tariefsensor. Zie ook de [Zonneplan-integratiebeschrijving](https://github.com/fsaris/home-assistant-zonneplan-one) voor de beschikbare forecastgegevens.

## Dashboard toevoegen

Het voorbeeld-dashboard staat in [`dashboards/ev-smart-charge-dashboard.yaml`](dashboards/ev-smart-charge-dashboard.yaml).

1. Ga naar `Instellingen → Dashboards`.
2. Maak een nieuw dashboard aan of open de YAML-configuratie van een bestaand dashboard.
3. Kopieer de inhoud van het YAML-bestand naar de dashboardconfiguratie.
4. Controleer na opslaan of de entiteiten van de integratie dezelfde object-ID's hebben.

Het sidebar-panel bevat laadplanning, sessiegegevens, dag-, maand- en jaaroverzichten, een setup wizard, verbindingstest, Telegraminstellingen en afzonderlijke Telegram-testknoppen. De pagina blijft staan tijdens sensorupdates: invoervelden, tabkeuze en knoppen worden niet opnieuw opgebouwd. Elke actie toont direct een bezig-, gelukt- of foutmelding en dubbele klikken worden geblokkeerd totdat de service klaar is. De panelresolver ondersteunt zowel de standaard entity-ID's als de bekende door Home Assistant geprefixte EV Smart Charge-ID's. De sensorverbindingen en gevoelige opties blijven ook beschikbaar via de native Home Assistant-integratie-instellingen.

## Testprocedure

Test eerst zonder de auto daadwerkelijk te laden:

1. Zet AI uit.
2. Open het sidebar-panel `EV Smart Charge`.
3. Klik op `🧪 Test flex`.
4. Klik op `🧪 Test plan`.
5. Controleer de actuele tariefforecast, gekozen prijsblokken, starttijd, eindtijd, kWh, kosten, ERE en netto.
6. Controleer de zonneforecast, het actuele zonnevermogen en de laadpaalstatus.
7. Klik op `Telegram test`.
8. Test daarna elk afzonderlijk berichttype.

Test vervolgens de veiligheidscontrole met de auto niet aangesloten. De actie `ev_smart_charge.start` moet dan worden geblokkeerd en de laadpaalswitch mag niet aan gaan.

Pas daarna test je met een aangesloten auto. Gebruik eerst een toekomstig plan en controleer of de Peblar pas op het geplande moment wordt ingeschakeld. De berichten mogen nooit de lokale veiligheidscontrole omzeilen.

`Test flex` en `Test plan` gebruiken dezelfde lokale planner als het echte flexibele plan. Ze schrijven alleen een simulatie-resultaat naar de testentiteiten; ze zetten de laadpaal niet aan, maken geen sessie aan en sturen geen Telegrambericht. Daardoor werken ze ook wanneer AI op `local`/uit staat.

Lokale ontwikkeltests kunnen worden uitgevoerd met:

```bash
python3 tests/test_planner.py
python3 -m compileall -q custom_components tests
```

De frontend kan zonder browserbuild worden gecontroleerd met een Node.js-modulecheck. Na een update moet Home Assistant opnieuw worden gestart en moet de browser één keer hard worden vernieuwd; de panel-URL bevat bewust een cacheversie.

## Wat is inbegrepen

De eerste integratie staat onder `custom_components/ev_smart_charge/` en bevat:

- configuratie via Home Assistant Config Flow;
- generieke koppeling van auto-, laadpaal- en tariefentiteiten;
- lokale planning zonder AI-afhankelijkheid;
- optionele OpenAI-kandidaatkeuze;
- lokale validatie en veiligheidscontrole;
- persistent plan en sessiehistorie;
- dag-, maand- en jaaraggregaten;
- Home Assistant-services voor plannen, simuleren, starten, stoppen en resetten;
- instelbare laadparameters als integratie-entiteiten in plaats van handmatige helpers;
- een eigen sidebar-panel voor bediening, instellingen en Telegramtests;
- zichtbare testplannen voor `Test flex` en `Test plan`, zonder laadpaalactivering;
- uitlezing van tariefforecast, zonneforecast, huidig zonnevermogen, auto-status en laadpaalstatus.
- Zonneplan-forecast parsing voor `start_date`, geneste prijsvelden en uur- of kwartierblokken.
- Een verduidelijkte testtoelichting wanneer geen geldig laadvenster beschikbaar is.
- automatische entity-suggesties voor verschillende automerken, laadpalen en energieproviders;
- een wizard om alle koppelingen te controleren en zonder schakelen te testen;
- een monitor-only veiligheidsmodus zodat Node-RED tijdelijk de actieve besturing kan blijven.

De Node-RED-export uit de persoonlijke installatie hoort niet bij deze installatie-instructie.

### Bekende MVP-beperkingen

- De tariefparser ondersteunt gangbare forecast-attributen, waaronder Zonneplan-uur- en kwartierblokken; andere providers kunnen kleine verschillen in hun forecaststructuur hebben.
- Sessieprijzen worden in deze eerste versie proportioneel uit het gekozen plan berekend. Exacte energie-toewijzing per werkelijk prijsblok volgt in een volgende versie.
- Telegramnotificaties gebruiken de bestaande Home Assistant Telegram-service. De service, chat-ID en berichttemplates zijn instelbaar.
- Het dashboard gebruikt alleen standaard Home Assistant-kaarten.
- De actuele FordPass/Peblar target-select wordt nog niet automatisch gewijzigd door de MVP.
- De simulatie- en testservices schakelen niets en slaan geen plan op.
- Provider-specifieke adapters en uitgebreide herstelpaden blijven uitbreidpunten voor volgende releases.

## Doel

De planner moet kunnen werken met verschillende automerken, laadpalen en energie-integraties. FordPass, Peblar en Zonneplan zijn voorbeelden van koppelingen, maar worden geen vaste onderdelen van de kernlogica.

De uiteindelijke Home Assistant-versie moet via een configuratiescherm instelbaar zijn. Gebruikers kiezen daar zelf de sensoren en switch die bij hun auto en laadpaal horen.

## Werking

```text
Sensoren uitlezen
        |
        v
Lokale planner berekent alle geldige laadplannen
        |
        v
Optioneel: OpenAI kiest uit de geldige kandidaten
        |
        v
Lokale validator controleert het gekozen plan
        |
        v
Lokale veiligheidscontrole
        |
        v
Laadpaal aan of uit
```

AI is optioneel. Zonder AI kiest de lokale planner zelf het goedkoopste geldige plan. Met AI krijgt OpenAI alleen vooraf berekende kandidaten en mag het alleen een bestaande kandidaat kiezen. OpenAI mag nooit rechtstreeks een laadpaal of andere elektrische verbruiker schakelen.

## Gegevens die nodig zijn

### Auto

Verplicht:

- State of charge (SoC)
- Aangeslotenstatus

Optioneel:

- Laadstatus
- Doelpercentage-select
- Odometer

### Laadpaal

Verplicht:

- Laadpaalstatus
- Aan/uit-besturing

Aanbevolen:

- Actueel laadvermogen
- Sessie-energie

### Energie

Verplicht:

- Actueel tarief of tariefforecast

Optioneel:

- Zonneforecast
- Actueel zonnevermogen

## Belangrijkste ontwerpprincipes

- Veiligheid wint altijd van prijsoptimalisatie.
- De laadpaal wordt nooit rechtstreeks door AI aangestuurd.
- De lokale planner kan zonder OpenAI werken.
- Exacte kosten worden lokaal berekend uit de beschikbare tariefblokken.
- Uur- en kwartiertarieven worden ondersteund.
- Een laadplan wordt gevalideerd voordat het wordt uitgevoerd.
- Handmatige stop, ontbrekende sensordata en een niet-aangesloten auto blokkeren het laden.
- Sessies en kosten worden persistent opgeslagen.
- Entity-ID's, laadvermogen, accucapaciteit, efficiëntie en ERE-vergoeding worden configureerbaar.
- Boilerlogica hoort niet bij de universele planner. Dat is alleen een optionele persoonlijke uitbreiding.

## Home Assistant-services

Beschikbare services:

```text
ev_smart_charge.create_plan
ev_smart_charge.start
ev_smart_charge.stop
ev_smart_charge.reset
ev_smart_charge.status
ev_smart_charge.simulate_plan
ev_smart_charge.test_flex
ev_smart_charge.test_plan
ev_smart_charge.update_setup
ev_smart_charge.test_connection
ev_smart_charge.telegram_test
ev_smart_charge.telegram_send
```

Beschikbare informatie-entiteiten:

```text
sensor.ev_smart_charge_status
sensor.ev_smart_charge_plan_start
sensor.ev_smart_charge_plan_end
sensor.ev_smart_charge_plan_cost
sensor.ev_smart_charge_plan_ere
sensor.ev_smart_charge_plan_net
sensor.ev_smart_charge_session_kwh
sensor.ev_smart_charge_session_cost
sensor.ev_smart_charge_today_kwh
sensor.ev_smart_charge_month_kwh
sensor.ev_smart_charge_year_kwh
sensor.ev_smart_charge_tariff_slots
sensor.ev_smart_charge_solar_forecast_kwh
sensor.ev_smart_charge_solar_now_w
sensor.ev_smart_charge_test_status
sensor.ev_smart_charge_test_windows
```

De gebruiker stelt de integratie in via een configuratie-flow en selecteert zelf de beschikbare Home Assistant-entiteiten. Daardoor kunnen verschillende automerken en laadpalen worden gebruikt zolang de benodigde waarden beschikbaar zijn.

## Node-RED

De huidige persoonlijke Node-RED-flow blijft voorlopig buiten deze repository. Een vereenvoudigde Node-RED-variant kan later worden toegevoegd als compatibiliteitslaag voor gebruikers die Node-RED en Home Assistant gebruiken.

De Node-RED-versie en de HACS-integratie moeten dezelfde onderdelen delen:

1. Generieke sensor-snapshot
2. Lokale planner
3. Optionele AI-keuze
4. Validator
5. Safety guard
6. Executor
7. Sessie- en kostenadministratie

## Roadmap

- [x] Generiek datamodel vastleggen
- [x] Lokale planner losmaken van FordPass en Peblar
- [x] Kandidatenmodel voor uur- en kwartiertarieven toevoegen
- [x] AI-keuze beperken tot bestaande kandidaten
- [x] Validator- en safety-contract vastleggen
- [x] Persistent sessie- en kostenmodel ontwerpen
- [ ] Vereenvoudigde Node-RED-compatibiliteitslaag maken
- [x] Home Assistant custom integration bouwen
- [x] Config flow voor auto-, laadpaal- en tariefsensoren toevoegen
- [x] HACS-publicatie voorbereiden
- [x] Standaard Lovelace-dashboard maken
- [x] Telegram-configuratie en testberichten toevoegen
- [x] Sidebar-panel voor dagelijkse bediening maken
- [x] Guided setup wizard met entity-discovery en verbindingstest maken
- [x] Monitor-only modus voor veilige migratie naast Node-RED toevoegen
- [x] Test flex en test plan vanuit het sidebar-panel toevoegen
- [x] Tarief- en zonneforecast zichtbaar maken
- [ ] Exacte kosten per werkelijk prijsblok toevoegen
- [ ] Uitgebreide Home Assistant integration tests toevoegen

Een optioneel YAML-dashboard staat in `dashboards/ev-smart-charge-dashboard.yaml`. De aanbevolen dagelijkse interface is het ingebouwde sidebar-panel `EV Smart Charge`.

## Bijdragen

Dit project is nog in de ontwerpfase. Ontwerpkeuzes, testscenario's en verbeteringen zijn welkom via GitHub Issues.

Deel nooit API-sleutels, Telegram-tokens, persoonlijke adressen, kentekens of volledige Home Assistant-state dumps in issues of pull requests.

## Licentie

De licentie wordt toegevoegd zodra de eerste publieke implementatie wordt gepubliceerd.
