# EV Smart Charge Planner

Een universele slimme laadplanner voor elektrische auto's en laadpalen.

Het project berekent wanneer een auto het beste kan laden op basis van dynamische energieprijzen, laadvermogen, benodigde energie, zonneforecast en een optionele deadline. De laadpaal wordt uitsluitend aangestuurd door lokale veiligheidscontroles.

> Status: eerste HACS-MVP in ontwikkeling. De persoonlijke Node-RED-flow wordt niet gepubliceerd.

## HACS-installatie

De repository is ingericht als een HACS custom integration. Voor installatie via HACS:

1. Open `HACS → Integraties`.
2. Kies het menu rechtsboven en selecteer `Aangepaste repositories`.
3. Voeg de URL van deze GitHub-repository toe.
4. Kies categorie `Integration`.
5. Installeer `EV Smart Charge Planner`.
6. Herstart Home Assistant.
7. Voeg de integratie toe via `Instellingen → Apparaten & diensten → Integratie toevoegen`.

Voor lokaal testen kan de map `custom_components/ev_smart_charge` rechtstreeks naar `/config/custom_components/` worden gekopieerd.

## Telegram instellen

De integratie gebruikt de bestaande Telegram-integratie van Home Assistant. Er wordt geen bot-token in deze integratie opgeslagen.

Open na installatie de opties van de integratie en vul in:

- `Telegramberichten inschakelen`: aan;
- `Telegram-service`: meestal `telegram_bot.send_message`;
- `Telegram chat-ID`: bijvoorbeeld `-5222938603`.

De integratie maakt daarna tekstentiteiten aan waarmee de templates vanuit het dashboard kunnen worden aangepast:

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

## HACS-MVP

De eerste integratie staat onder `custom_components/ev_smart_charge/` en bevat:

- configuratie via Home Assistant Config Flow;
- generieke koppeling van auto-, laadpaal- en tariefentiteiten;
- lokale planning zonder AI-afhankelijkheid;
- optionele OpenAI-kandidaatkeuze;
- lokale validatie en veiligheidscontrole;
- persistent plan en sessiehistorie;
- dag-, maand- en jaaraggregaten;
- Home Assistant-services voor plannen, simuleren, starten, stoppen en resetten;
- instelbare laadparameters als integratie-entiteiten in plaats van handmatige helpers.

De MVP is nog niet klaar voor een productie-installatie. De exacte per-prijsblok kostenadministratie, uitgebreide herstelpaden en een kant-en-klaar Lovelace-dashboard worden in volgende stappen toegevoegd.

### Installeren tijdens ontwikkeling

1. Kopieer of clone deze repository.
2. Plaats de map `custom_components/ev_smart_charge` in `/config/custom_components/`.
3. Herstart Home Assistant.
4. Ga naar `Instellingen → Apparaten & diensten → Integratie toevoegen`.
5. Zoek naar `EV Smart Charge Planner`.

De Node-RED-export uit de persoonlijke installatie hoort niet bij deze installatie-instructie.

### Bekende MVP-beperkingen

- De tariefparser ondersteunt gangbare forecast-attributen; de exacte Zonneplan-attribuutstructuur moet nog met een echte Home Assistant-export worden gevalideerd.
- Sessieprijzen worden in deze eerste versie proportioneel uit het gekozen plan berekend. Exacte energie-toewijzing per werkelijk prijsblok volgt in een volgende versie.
- Telegram-notificaties gebruiken de bestaande Home Assistant Telegram-service. De service, chat-ID en berichttemplates zijn instelbaar.
- De actuele FordPass/Peblar target-select wordt nog niet automatisch gewijzigd door de MVP.
- De integratie is lokaal gecompileerd en met pure planner-scenario's getest. Een volledige Home Assistant-testomgeving is nog nodig voor de eerste alpha-release.

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

## Geplande Home Assistant-integratie

De uiteindelijke integratie wordt beschikbaar gemaakt via HACS en moet zonder Node-RED kunnen werken.

Geplande services:

```text
ev_smart_charge.create_plan
ev_smart_charge.start
ev_smart_charge.stop
ev_smart_charge.reset
ev_smart_charge.status
ev_smart_charge.simulate
```

Geplande informatie-entiteiten:

```text
sensor.ev_plan_status
sensor.ev_plan_start
sensor.ev_plan_end
sensor.ev_plan_cost
sensor.ev_plan_ere
sensor.ev_plan_net_cost
sensor.ev_session_energy
sensor.ev_session_cost
sensor.ev_month_energy
sensor.ev_month_cost
sensor.ev_month_savings
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

- [ ] Generiek datamodel vastleggen
- [ ] Lokale planner losmaken van FordPass en Peblar
- [ ] Kandidatenmodel voor uur- en kwartiertarieven toevoegen
- [ ] AI-keuze beperken tot bestaande kandidaten
- [ ] Validator- en safety-contract vastleggen
- [ ] Persistent sessie- en kostenmodel ontwerpen
- [ ] Vereenvoudigde Node-RED-compatibiliteitslaag maken
- [ ] Home Assistant custom integration bouwen
- [ ] Config flow voor auto-, laadpaal- en tariefsensoren toevoegen
- [ ] HACS-publicatie voorbereiden
- [ ] Optionele dashboardkaart maken

Een eerste standaard Lovelace-dashboard staat in `dashboards/ev-smart-charge-dashboard.yaml`. Dit bestand kan via de YAML-editor van Home Assistant worden gekopieerd. Het gebruikt alleen standaard Home Assistant-kaarten; een aparte custom dashboardkaart komt pas later.

## Bijdragen

Dit project is nog in de ontwerpfase. Ontwerpkeuzes, testscenario's en verbeteringen zijn welkom via GitHub Issues.

Deel nooit API-sleutels, Telegram-tokens, persoonlijke adressen, kentekens of volledige Home Assistant-state dumps in issues of pull requests.

## Licentie

De licentie wordt toegevoegd zodra de eerste publieke implementatie wordt gepubliceerd.
