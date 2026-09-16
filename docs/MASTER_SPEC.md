# PROMPT 00 — MASTER CONTRACT
# AL_TRADING_AL — REAL-MARKET MULTI-ASSET PAPER TRADING

Pracujesz na istniejącym repozytorium `Al_Trading_Al`.

Ten dokument jest KONTRAKTEM projektu. Nie wykonuj całego programu prac z tego prompta naraz.
Kolejne zadania będą przekazywane osobnymi promptami fazowymi.

## CEL KOŃCOWY

System ma być prawdziwym multi-market paper trading engine dla:
- BTCUSDT
- ETHUSDT
- SOLUSDT
- BNBUSDT
- XRPUSDT
- EURUSD
- GOLD futures proxy używany obecnie przez projekt
- WTI futures proxy używany obecnie przez projekt
- AAPL

Obsługiwane klasy:
- CRYPTO
- FOREX
- STOCKS
- METALS/FUTURES PROXY
- ENERGY/FUTURES PROXY

Architektura ma umożliwiać późniejsze dodawanie kolejnych aktywów bez kopiowania całego TradingEngine.

## FUNDAMENTALNA ZASADA PAPER TRADINGU

Wirtualny jest kapitał.
Rynek NIE jest wirtualny.

PAPER LIVE ma korzystać z:
- prawdziwych notowań,
- prawdziwych timestampów providerów,
- prawdziwego market status,
- prawdziwych bid/ask, jeśli provider je dostarcza,
- realnego spreadu, jeśli można go uzyskać,
- rzeczywistych sesji rynku,
- realnych reguł instrumentu,
- prawdziwych kursów walutowych,
- realistycznego modelu wykonania.

Nie generuj sztucznych cen w PAPER LIVE.
Mock/synthetic market data są dopuszczalne wyłącznie w testach.

PaperBroker symuluje zlecenie na podstawie prawdziwego rynku, ale nie wysyła prawdziwego zlecenia i nie używa prawdziwych pieniędzy.

## PLN JAKO WALUTA UŻYTKOWNIKA

Waluta bazowa portfolio paper: PLN.

Użytkownik ma przede wszystkim widzieć:
- cash PLN,
- equity PLN,
- realized PnL PLN,
- unrealized PnL PLN,
- daily PnL PLN,
- total PnL PLN,
- exposure PLN,
- fees PLN,
- spread cost PLN,
- slippage PLN,
- drawdown PLN i %.

Wartości natywne instrumentu pozostają zapisane dla audytu.

Nie stosuj:
- 1 USD = 1 PLN,
- bezwarunkowego 1 USDT = 1 USD.

Brak wiarygodnego FX oznacza status jakości, a nie wymyśloną konwersję.

## REALIZED / UNREALIZED FX

REALIZED:
- fx_pair,
- fx_path,
- fx_rate,
- fx_provider,
- fx_timestamp,
- pnl_pln zapisane na stałe,
- nie przeliczaj ponownie historycznego realized PnL.

UNREALIZED:
- przeliczaj według aktualnego dostępnego FX,
- pokazuj jakość i wiek FX.

Statusy:
- FX_FRESH
- FX_STALE
- FX_UNAVAILABLE

## DWA PROFILE EGZEKUCJI

ExecutionProfile.LEGACY_V1:
- tylko backtest/regresja,
- zachowanie zgodne z historyczną wersją,
- legacy fill logic,
- nie używać w PAPER LIVE.

ExecutionProfile.REALISTIC_V2:
- real bid/ask, gdy dostępny,
- rzeczywisty lub jawnie modelowany spread,
- slippage,
- STOP_GAP,
- sessions,
- EXIT_PENDING,
- realistic execution.

Nie wymagaj, aby REALISTIC_V2 dawał ten sam PnL co LEGACY_V1.

Frozen BTC w LEGACY_V1:
- BUY RSI = 33.8
- SELL RSI = 68.5
- RSI = classic
- MIN_DIFF = 1.0
- SL = 5%
- RR = 2.0
- TIME = 241 świec przy 1m
- FEE = 0.0004
- INITIAL BALANCE = 1000.0

Nie zmieniaj tych parametrów podczas hardeningu.

## EXECUTION QUALITY

Runtime per asset:
- REAL_BOOK
- DERIVED_SPREAD
- SIMULATED_SPREAD
- UNTRADEABLE

REAL_BOOK:
real bid/ask i realny spread.

DERIVED_SPREAD:
brak realnego booka, ale realna cena + empirycznie uzasadniony model spreadu.

SIMULATED_SPREAD:
fallback z konfiguracji, niższa wiarygodność.

UNTRADEABLE:
za mało danych do wiarygodnej egzekucji.

Nie mieszaj wyników różnych jakości bez jawnej informacji.

## TRYBY PAPER

realistic_paper:
- wymaga odpowiedniej świeżości danych,
- delayed feed blokuje nowe wejścia,
- tylko REALISTIC_V2.

research_paper:
- może dopuścić delayed lub niższą jakość egzekucji,
- wszystko musi być oznaczone,
- wynik nie może udawać pełnego realistic paper.

## PAPER READINESS

Raportuj:
DATA_QUALITY:
- REALTIME_BOOK
- REALTIME_LAST
- DELAYED
- UNRELIABLE

EXECUTION_QUALITY:
- REAL_BOOK
- DERIVED_SPREAD
- SIMULATED_SPREAD
- UNTRADEABLE

FX_QUALITY:
- LIVE
- DAILY_REFERENCE
- STALE_PRONE
- UNAVAILABLE

SESSION_QUALITY:
- EXCHANGE_CALENDAR
- APPROXIMATED
- UNKNOWN

INSTRUMENT_CLARITY:
- CONFIRMED
- PROXY
- UNKNOWN

PAPER_READINESS:
- FULL
- LIMITED
- RESEARCH_ONLY
- NOT_READY

PAPER_READINESS wynika z najsłabszego krytycznego elementu.

## INSTRUMENTY

Jeżeli repo używa `GC=F` i `CL=F`, nie nazywaj ich spot XAUUSD/WTI.

Użyj nazw wskazujących proxy, np.:
- GOLD_FUT_CONT
- WTI_FUT_CONT

instrument_type:
`continuous_future_proxy`

Continuous futures proxy:
- może zawierać rollover discontinuities,
- nie jest bezpośrednio handlowalnym kontraktem,
- pozostaje EXPERIMENTAL,
- dashboard ma pokazywać PROXY.

## SHORT SELLING

AssetConfig ma semantycznie zawierać:
- allow_long
- allow_short
- short_mechanism
- short_financing_model

Mechanizmy:
- MARGIN
- FUTURES
- CFD
- BORROW
- SYNTHETIC
- NONE

Nie zakładaj, że SELL zawsze oznacza możliwy realny short.

BTCUSDT spot nie jest realnym shortem bez margin/futures.
AAPL short wymaga borrow.

Jeżeli short jest syntetyczny:
- SYNTHETIC_SHORT
- FINANCING_NOT_MODELLED

Jeżeli short niedostępny:
REJECTED / SHORT_NOT_SUPPORTED.

## AI

AI simulation_units są wyłącznie wewnętrznym wynikiem AI.

Nie mogą zmieniać paper cash.

Historia AI minimum per:
asset_id + strategy_id.

## REPRODUCE BEFORE FIX

Dla każdego podejrzanego błędu:
1. napisz test reprodukujący,
2. uruchom na obecnym kodzie,
3. czerwony → bug potwierdzony → napraw,
4. zielony → nie zmieniaj zachowania,
5. zapisz wynik w raporcie.

## CZAS

Core:
- tylko timezone-aware UTC,
- bez naiwnych datetime,
- bez bezpośredniego datetime.now()/time.time() w core,
- używaj Clock,
- durations przez time.monotonic().

Wykrywaj CLOCK_DRIFT_SUSPECTED.

## IDEMPOTENCJA

Każdy order:
client_order_id przed execution.

Krytyczne identyfikatory:
UNIQUE.

Ponowne przetworzenie tej samej świecy:
nie może tworzyć drugiego orderu.

## GLOBALNY HALT

HALT:
- blokuje nowe wejścia,
- nie wyłącza zarządzania otwartymi pozycjami,
- przetrwa restart,
- zdjęcie tylko jawnie,
- wszystko logowane.

Auto-HALT minimum przy:
- reconciliation mismatch,
- krytycznym DB error,
- przekroczeniu globalnego daily loss.

## API SECURITY

Mutujące endpointy:
- API key z env,
- bezpieczne porównanie,
- CORS z configu bez "*",
- brak key → fail closed,
- rate limiting,
- `.env.example` bez sekretów.

## TESTY

Offline:
- deterministyczne,
- zero network,
- Clock injection,
- stałe random seeds,
- fixtures w repo.

Network:
- oddzielne.

Golden benchmark:
- zmiana tylko jawnie i osobnym commitem.

Nie zmieniaj istniejących asercji bez akceptacji.

## DOKUMENTY

Utrzymuj:
- docs/MASTER_SPEC.md
- docs/PAPER_READINESS.md
- TODO_HARDENING.md
- docs/adr/

ADR minimum:
- FX source,
- FX weekend policy,
- slippage model,
- synthetic shorts,
- GOLD/WTI proxy,
- ledger schema,
- execution profiles.

## ZASADA PRACY

Jedna faza = jedna sesja = mały zakres = testy = raport.

Na początku każdej fazy:
1. przeczytaj docs/MASTER_SPEC.md,
2. przeczytaj ostatni raport,
3. sprawdź git status,
4. nie zakładaj clean repo,
5. nie usuwaj cudzych zmian.

Raport fazy:
- SUMMARY
- BUGS/ISSUES VERIFIED
- BUGS FIXED
- CLAIMS THAT DID NOT REPRODUCE
- CHANGED FILES
- NEW FILES
- TESTS ADDED
- TEST RESULT
- LEGACY BTC REGRESSION RESULT
- REALISTIC RESULT
- PAPER_READINESS CHANGES
- SPEC ASSUMPTIONS THAT WERE FALSE
- NEW TECHNICAL DEBT
- CYCLE DURATION IMPACT
- ROLLBACK PLAN
- HARD STOP REQUIRED BEFORE NEXT PHASE

## HARD STOP

Wymaga jawnej akceptacji użytkownika:
- zmiana semantyki execution,
- migracja JSON → SQLite,
- zmiana księgowania/PLN istniejących danych,
- usuwanie plików/dashboardów/skryptów,
- usunięcie/nadpisanie data/live_state,
- usunięcie bazy,
- zmiana frozen strategy params,
- zmiana istniejących assertions,
- dodanie nowej dependency.

Przed HARD STOP pokaż:
- plan,
- pliki,
- dane,
- backup,
- rollback,
- wpływ na zachowanie.

Potem STOP.

## ZAKAZY

Nie:
- przepisuj projektu od zera,
- rób dużego rewrite,
- optymalizuj strategii podczas hardeningu,
- udawaj realtime przy delayed feed,
- handluj na stale data,
- udawaj XAUUSD jeśli źródłem jest GC=F,
- udawaj spot WTI jeśli źródłem jest CL=F,
- zakładaj handlowalność continuous future proxy,
- zakładaj realność każdego shorta,
- używaj 1 USD = 1 PLN,
- mieszaj AI simulation units z cash,
- mieszaj LEGACY_V1 z REALISTIC_V2,
- agreguj różnych EXECUTION_QUALITY bez etykiety,
- twórz giant commitów,
- ignoruj błędów przez `except: pass`,
- obchodź failed tests,
- commituj .env,
- commituj .venv,
- włączaj real-money trading.

Najpierw ustal, co rzeczywiście potrafią providery i instrumenty.
Potem projektuj system.

---

# ANEKS DO MASTER PROMPTU — AL_TRADING_AL

Ten dokument dopisuje się na końcu MASTER PROMPTU.

Część A **nadpisuje** wskazane sekcje oryginału — przy konflikcie obowiązuje Część A.
Część B dodaje nowe wymagania (sekcje 134+).

---

# CZĘŚĆ A — POPRAWKI I ROZSTRZYGNIĘCIA SPRZECZNOŚCI

## A1. FAZA 0.5 — PROVIDER CAPABILITY MATRIX (przed FAZĄ 3, obowiązkowa)

Sekcje 15–23 i 32–33 zakładają dostępność danych, których obecne providery mogą nie
dostarczać. Zanim napiszesz jakikolwiek kod egzekucji, ustal **empirycznie** — przez
faktyczne odpytanie providera, nie z pamięci — co jest dostępne.

Dla każdego z 9 assetów wypełnij:

```text
asset_id
provider
provider_symbol
endpoint użyty do sprawdzenia

bid dostępny            YES / NO
ask dostępny            YES / NO
book depth dostępna     YES / NO
last dostępny           YES / NO
volume dostępny         YES / NO

opóźnienie feedu        REALTIME / DELAYED_<N>MIN / UNKNOWN
źródło informacji o opóźnieniu

streaming dostępny      YES / NO / UNKNOWN
metadata instrumentu    YES / NO
tick size ze źródła     YES / NO
quantity rules ze źródła YES / NO

limity rate
warunki użycia / oficjalność API
```

Wynik zapisz w `docs/PROVIDER_CAPABILITY.md`.

**Znane punkty wyjścia do weryfikacji (potwierdź, nie przyjmuj na wiarę):**

- `data-api.binance.vision` — klines są używane. Sprawdź, czy dostępne są też
  `/api/v3/ticker/bookTicker` (bid/ask), `/api/v3/depth` i `/api/v3/exchangeInfo`
  (tick size, step size, min notional). Jeżeli tak, crypto może mieć realny bid/ask
  i realne reguły instrumentu ze źródła, nie z ręcznie wpisanego configu.
- Yahoo `query1.finance.yahoo.com/v8/finance/chart` — to nieoficjalny endpoint.
  Zweryfikuj, czy zwraca bid/ask (prawdopodobnie nie) i jakie jest opóźnienie dla akcji.
  Sprawdź też pole `exchangeDataDelayedBy` w odpowiedzi.

Ta matryca jest **wejściem** do A2 i A3. Bez niej nie zaczynaj FAZY 3.

---

## A2. EXECUTION QUALITY — rozstrzygnięcie sprzeczności §19 / §32 / §33

Sekcja 19 każe domyślnie odrzucać zlecenia na delayed feedzie. Sekcja 32–33 wymaga
realnego bid/ask. Jeżeli matryca z A1 potwierdzi, że Yahoo nie daje bid/ask i jest
opóźniony, literalne zastosowanie §19 **wyłączy XAU, WTI, EURUSD i AAPL**.

To nie jest akceptowalne rozwiązanie i nie jest intencją promptu.

Wprowadź jawny, zapisywany przy każdej transakcji poziom jakości egzekucji:

```text
EXECUTION_QUALITY:

REAL_BOOK
    realny bid/ask ze źródła
    spread z realnego booka
    najwyższa wiarygodność

DERIVED_SPREAD
    brak bid/ask, ale realny last + realny, zmierzony historycznie spread
    spread modelowany, nie zmyślony
    wiarygodność średnia

SIMULATED_SPREAD
    brak bid/ask i brak wiarygodnego modelu spreadu
    spread z configu
    wiarygodność niska — wynik NIE jest porównywalny z REAL_BOOK

UNTRADEABLE
    brak danych pozwalających na sensowną wycenę wykonania
```

Zasady:

1. `EXECUTION_QUALITY` to pole **per asset, wyliczane w runtime**, nie stała w configu.
   Spadek jakości (np. utrata streamu) musi być widoczny natychmiast.
2. Handel na `DELAYED` feedzie jest dozwolony **wyłącznie** w trybie `research_paper`,
   z obowiązkową etykietą w UI, w benchmarku i w rekordzie transakcji.
   W trybie `realistic_paper` obowiązuje §19 bez wyjątków.
3. Każdy raport, benchmark i ekran dashboardu **musi** pokazywać `EXECUTION_QUALITY`
   obok wyniku. Zysk osiągnięty na `SIMULATED_SPREAD` nie może być prezentowany
   tak samo jak zysk na `REAL_BOOK`.
4. Nie agreguj wyników o różnej jakości egzekucji w jedną liczbę bez adnotacji.

---

## A3. PROFILE EGZEKUCJI — rozstrzygnięcie sprzeczności §7 vs FAZA 5/6

Sekcja 7 traktuje każdą zmianę wyniku BTC na frozen datasecie jako regresję.
Fazy 5 i 6 wymagają bid/ask, spreadu, slippage i STOP_GAP.

Te wymagania **nie mogą** być jednocześnie spełnione: realistyczna egzekucja z definicji
zmieni entry, exit i PnL. Prompt jest tu wewnętrznie sprzeczny.

Rozstrzygnięcie:

```text
ExecutionProfile.LEGACY_V1
    fill dokładnie po SL/TP
    spread = 0
    slippage = 0
    wejście po close świecy sygnałowej
    zachowanie bit-for-bit zgodne z tagiem v1.0.0

ExecutionProfile.REALISTIC_V2
    bid/ask jeśli dostępne
    spread realny lub modelowany
    slippage
    STOP_GAP
    market closed / EXIT_PENDING
```

Zasady:

1. Test regresji BTC (§7) uruchamiaj **wyłącznie** na `LEGACY_V1`. Ten profil jest
   zamrożony na zawsze i służy jako punkt odniesienia historyczny.
2. `REALISTIC_V2` raportuj **osobno**, jako nowy benchmark z własnym `config_hash`.
   Różnica LEGACY vs REALISTIC to cenna informacja — pokazuje, ile z dotychczasowego
   wyniku BTC było artefaktem optymistycznej egzekucji. **Zaraportuj tę liczbę jawnie.**
3. Nie „naprawiaj" spadku wyniku w `REALISTIC_V2` przez zmianę parametrów strategii.
   Jeżeli strategia przestaje być rentowna po uwzględnieniu realnych kosztów, to jest
   wynik badania, nie błąd do zamaskowania.
4. `LEGACY_V1` nie jest dostępny w paper-live. Tylko backtest/regresja.

---

## A4. SHORT SELLING — brakujące ograniczenie instrumentu

Prompt nigdzie tego nie porusza, a zamrożona strategia otwiera pozycje `SELL`.

Fakty do uwzględnienia:

- BTCUSDT na **spocie** nie da się shortować. Short wymaga margin/futures.
  Obecny silnik otwiera `SELL` na danych spotowych — to pozycja syntetyczna,
  nieosiągalna na rynku, z którego pochodzą ceny.
- Short na AAPL wymaga pożyczki akcji (borrow fee, możliwy recall).
- Short na XAU/WTI zależy od tego, czym faktycznie jest instrument (§50, §51).

Wymagania:

1. Dodaj do `AssetConfig`:

```text
allow_long: bool
allow_short: bool
short_mechanism: str | None    # MARGIN / FUTURES / CFD / BORROW / SYNTHETIC / NONE
short_financing_model: str | None
```

2. Jeżeli `allow_short = False`, sygnał SELL bez otwartej pozycji długiej →
   `REJECTED / SHORT_NOT_SUPPORTED`. To jest nowy powód odrzucenia do listy z §78.
3. Jeżeli pozostawiasz shorty jako syntetyczne (żeby nie zerwać ciągłości z frozen BTC),
   oznacz je **wszędzie**: w rekordzie transakcji, w benchmarku i w dashboardzie, jako
   `SYNTHETIC_SHORT / FINANCING_NOT_MODELLED`. Nie prezentuj takiego wyniku jako
   osiągalnego na prawdziwym rynku.
4. To jest dokładnie ta klasa problemu, którą §130 tępi w innych miejscach.
   Nie pomijaj jej dlatego, że dotyczy zamrożonej strategii.

---

## A5. KONFLIKT Z ISTNIEJĄCYM KODEM — sweep zysku AI do PLN

Sekcja 73 zakazuje, by `simulation_units` zasilały paper cash.

Obecny `docs/AI_PAPER.md` opisuje mechanizm przeciwny: zysk konta AI ponad bazę 1000
jednostek jest przelewany do `user_portfolio.json` i prezentowany jako wynik w PLN.

Wymagania:

1. Usuń ten mechanizm w FAZIE 1, nie później.
2. Zmigruj `user_portfolio.json`: pozycje pochodzące ze sweepu oznacz jako
   `ADJUSTMENT / LEGACY_AI_SWEEP` i wyzeruj ich wpływ na saldo, zachowując ślad audytowy.
3. Zaktualizuj `docs/AI_PAPER.md` — dokumentacja opisująca usunięty mechanizm jest
   gorsza niż jej brak.
4. Dodaj test: żaden zapis z modułu AI nie zmienia `cash` portfela paper.

---

## A6. NAJPIERW REPRODUKCJA, POTEM NAPRAWA

Prompt w kilku miejscach stwierdza istnienie błędu (§67 backtest state leakage,
§71 AI ranking bug). **Nie zakładaj, że te błędy istnieją.**

Dla każdego zarzutu z tego promptu:

```text
1. napisz test reprodukujący
2. uruchom go na obecnym kodzie
3a. test czerwony → błąd potwierdzony → napraw, test zostaje
3b. test zielony  → błędu nie ma → zapisz to w raporcie fazy, NIE "naprawiaj"
```

Cicha „naprawa" nieistniejącego błędu jest zmianą zachowania bez uzasadnienia
i w tym projekcie liczy się jako regresja.

---

## A7. BRAMKI — nadpisanie §125 i §128

Sekcja 125 każe pracować autonomicznie bez pytania o zgodę. Dla większości faz to słuszne.
Ale część operacji jest nieodwracalna albo zmienia semantykę wyników.

**HARD STOP — wymagana jawna akceptacja człowieka przed rozpoczęciem:**

```text
FAZA 5   zmiana modelu egzekucji
FAZA 6   wprowadzenie PLN jako waluty raportowej
FAZA 8   migracja JSON → SQLite
FAZA 12  usuwanie plików, dashboardów, skryptów
```

**HARD STOP — zawsze, niezależnie od fazy:**

```text
usunięcie lub nadpisanie danych w data/live_state/
usunięcie pliku bazy
zmiana zamrożonych parametrów strategii
zmiana asercji istniejącego testu
dodanie nowej zależności zewnętrznej
```

Przed każdym HARD STOP przedstaw plan, listę plików i sposób wycofania zmiany.

W pozostałych przypadkach §125 obowiązuje — pracuj dalej bez pytania.

---

## A8. ROZMIAR PROMPTU — sposób pracy

133 sekcje i 13 faz w jednym kontekście to zbyt dużo, żeby utrzymać spójność przez całą
pracę. Ryzyko: dryf, gigantyczne nieprzeglądalne commity, ciche pomijanie wymagań.

Wymagania:

1. Zapisz ten prompt wraz z aneksem jako `docs/MASTER_SPEC.md`, wersjonowany w gicie.
2. Pracuj **jedna faza = jedna sesja = jedna gałąź**. Na początku każdej sesji wczytaj
   `MASTER_SPEC.md` i raport z poprzedniej fazy.
3. Jeżeli w trakcie pracy rzeczywistość przeczy specyfikacji (np. provider nie ma pola
   wymaganego przez §17), **zaktualizuj `MASTER_SPEC.md` osobnym commitem** z uzasadnieniem.
   Specyfikacja, która kłamie o systemie, jest gorsza niż jej brak.
4. Na końcu każdej fazy zaktualizuj `docs/PAPER_READINESS.md` (§132).

---

## A9. RELACJA DO `CODEX_TASKS.md`

Jeżeli w repozytorium istnieje wcześniejsza rozpiska zadań (`CODEX_TASKS.md`),
nie realizuj obu dokumentów równolegle.

Mapowanie:

```text
CODEX_TASKS P0-1 (precyzja per instrument)   → FAZA 2 (AssetRegistry)
CODEX_TASKS P0-2 (auth API)                  → FAZA 10, ale wykonaj WCZEŚNIEJ (patrz §145)
CODEX_TASKS P0-3 (fsync, lock)               → FAZA 1
CODEX_TASKS P0-4 (jeden model egzekucji)     → FAZA 5
CODEX_TASKS P1-1 (requirements)              → FAZA 0
CODEX_TASKS P1-2 (jedno źródło configu)      → FAZA 2 (§12)
CODEX_TASKS P1-3 (RiskGuard)                 → FAZA 7
CODEX_TASKS P1-4 (migracje stanu)            → FAZA 8
CODEX_TASKS P1-5 (equity_curve)              → FAZA 1
CODEX_TASKS P1-6 (walidacja świec)           → FAZA 3 (§27)
CODEX_TASKS P1-7 (retry Yahoo)               → FAZA 3 (§23)
CODEX_TASKS P1-8 (testy backendu)            → FAZA 11
CODEX_TASKS P1-9 (logging)                   → FAZA 0
CODEX_TASKS P1-10 (CI)                       → FAZA 11, ale minimalny workflow w FAZIE 0
CODEX_TASKS P2-*                             → FAZA 12
```

Po zmapowaniu oznacz `CODEX_TASKS.md` jako `SUPERSEDED BY MASTER_SPEC.md` i nie utrzymuj
dwóch list zadań.

---

## A10. NAZEWNICTWO XAU I WTI

Prompt raz mówi o `XAU / XAUUSD / GOLD` (§2) i sugeruje spot (§50), a repozytorium używa
`GC=F` i `CL=F`, czyli **ciągłych kontraktów futures**, nie spotu.

Wymagania:

1. Nie nazywaj instrumentu `XAUUSD`, jeżeli danymi jest `GC=F`. Użyj jawnego
   `asset_id` odzwierciedlającego rzeczywistość, np. `GOLD_FUT_CONT` / `WTI_FUT_CONT`,
   z `instrument_type = "continuous_future_proxy"`.
2. Ciągły kontrakt futures ma **nieciągłości na rolowaniu**, których nie da się handlować.
   Backtest na takiej serii zawyża wyniki. Oznacz to jako `KNOWN_LIMITATION` i nie
   nadawaj tym assetom statusu wyższego niż `EXPERIMENTAL` bez rozwiązania problemu.
3. W dashboardzie pokaż użytkownikowi, że to proxy, nie spot.

---

## A11. ZALEŻNOŚĆ OD NIEOFICJALNEGO API

Endpoint Yahoo `v8/finance/chart` nie jest publicznym, wspieranym API. Może zmienić
format, zacząć wymagać cookie/crumb albo blokować ruch bez ostrzeżenia. Na tym stoi
prawie połowa rynków w tym systemie.

Wymagania:

1. Oznacz go w `PROVIDER_CAPABILITY.md` jako `UNOFFICIAL / DEGRADED_BY_DESIGN`.
2. Warstwa `MarketDataProvider` (§15) musi pozwalać na podmianę providera dla tych
   assetów **bez dotykania trading core** — to jeden z głównych powodów, dla których
   ta abstrakcja w ogóle powstaje. Zweryfikuj to testem z dwoma providerami dla
   tego samego assetu.
3. Do `TODO_HARDENING.md` dopisz zadanie rozpoznania oficjalnego źródła dla
   FX / metali / energii / akcji.

---

# CZĘŚĆ B — NOWE SEKCJE

## 134. POLITYKA FX — KONKRETY

Sekcje 4–6 wymagają realnego FX, ale nie wskazują źródła ani nie rozwiązują problemu
weekendu. To musi być rozstrzygnięte, zanim powstanie `CurrencyConverter`.

Problem strukturalny: **crypto handluje 24/7, rynek walutowy nie.** Przy literalnym
zastosowaniu §6 każda sobota i niedziela oznaczałaby `PLN: UNAVAILABLE` dla całego
portfela. To bezużyteczne.

Polityka:

```text
REALIZED PnL (księgowanie, nieodwracalne)
    kurs z momentu zamknięcia transakcji
    zapisany na stałe wraz z fx_timestamp i fx_provider
    nigdy nie przeliczany ponownie

UNREALIZED PnL / MTM (prezentacja)
    FX_FRESH        wiek kursu < max_fx_age        → pokaż PLN normalnie
    FX_STALE        wiek > max_fx_age, < 96h       → pokaż PLN z etykietą FX_STALE
                                                      i jawnym wiekiem kursu
    FX_UNAVAILABLE  wiek > 96h lub brak kursu      → PLN: UNAVAILABLE (§6)
```

Wymagania:

1. Wskaż i udokumentuj konkretne źródło kursów. Dla polskiego użytkownika naturalnym
   punktem odniesienia dla księgowania jest NBP (tabela A, kurs średni) — ale NBP
   **nie publikuje kursów intraday ani weekendowych**, więc do MTM potrzebne jest
   drugie źródło. Zweryfikuj dostępność obu i opisz w `docs/FX_POLICY.md`.
2. `max_fx_age` konfigurowalny, osobny dla dni roboczych i weekendu.
3. Kurs USDT→PLN: zdecyduj jawnie, czy idziesz ścieżką `USDT→USD→PLN` z realnym
   kursem USDT/USD (depeg bywa realny), czy przyjmujesz `USDT ≈ USD` jako
   udokumentowane uproszczenie. Nie zostawiaj tego domyślnie.
4. Zapisz **ścieżkę konwersji**, nie tylko wynik: `fx_path = "USDT→USD→PLN"`.
5. Koszt wymiany walutowej: jeżeli go nie modelujesz, zapisz to jako
   `KNOWN_LIMITATION: FX_CONVERSION_COST_NOT_MODELLED`. Nie udawaj, że wymiana
   PLN→USD jest darmowa i natychmiastowa.

---

## 135. DYSCYPLINA CZASU

1. Cały core operuje na `datetime` **aware, UTC**. Naiwne `datetime` zabronione —
   dodaj lintera albo test, który to wymusza.
2. Zakaz `datetime.now()` / `time.time()` bezpośrednio w core. Wyłącznie przez
   wstrzykiwany `Clock` — to warunek determinizmu testów (§144).
3. Do pomiaru czasu trwania używaj `time.monotonic()`, nie wall-clock.
4. Wiek danych liczony z `provider_timestamp` (§24), nie z lokalnego zegara — ale
   dodaj wykrywanie dryfu zegara lokalnego: jeżeli `provider_timestamp` jest
   systematycznie w przyszłości względem lokalnego, zgłoś `CLOCK_DRIFT_SUSPECTED`.
   Zły zegar VM-a potrafi wyglądać jak stale data i odwrotnie.
5. Wszystkie timestampy w bazie: UTC, w jednym formacie, jawnie udokumentowanym
   (epoch ms albo ISO8601 — wybierz jeden i trzymaj się go).

---

## 136. IDEMPOTENCJA I IDENTYFIKATORY

1. Każdy order dostaje `client_order_id` (UUID) generowany **przed** próbą wykonania.
2. Tabele `orders`, `executions`, `trades`, `portfolio_transactions` mają `UNIQUE`
   na odpowiednim identyfikatorze. Duplikat → błąd, nie cichy drugi wpis.
3. Ponowne przetworzenie tej samej świecy (po restarcie, po retry) **nie może**
   wygenerować drugiej transakcji. Dodaj test: ten sam cykl uruchomiony dwa razy
   daje jeden order.
4. `last_processed_candle_timestamp` (§84) commituj w **tej samej transakcji bazodanowej**
   co skutki cyklu. Osobny commit = okno na podwójne przetworzenie.

---

## 137. INVARIANT LEDGERA I REKONCYLIACJA

Sekcja 75 mówi, że balance ma być wyprowadzalny z ledgera. Potrzebny jest mechanizm,
który to **egzekwuje**, nie tylko zaleca.

1. Invariant: `suma(portfolio_transactions.amount_pln) == cash_balance_pln`.
   Sprawdzany po każdym cyklu zapisu.
2. Niezgodność → `RECONCILIATION_MISMATCH` w `system_events` + **automatyczny HALT**
   nowych wejść. Zarządzanie otwartymi pozycjami działa dalej.
3. Drugi invariant: `suma(realized_pnl z trades) == suma(REALIZED_PNL z ledgera)`.
4. Dzienny raport rekoncyliacji w `docs/` albo przez `/api/v1/system/reconciliation`.
5. Test: ręczne wstrzyknięcie rozjazdu → wykrycie + halt.

---

## 138. SQLITE — WYMAGANIA OPERACYJNE

Sekcje 74–77 opisują schemat, ale nie sposób bezpiecznej eksploatacji.

1. `PRAGMA journal_mode=WAL`, `PRAGMA busy_timeout=5000`,
   `PRAGMA foreign_keys=ON`, `PRAGMA synchronous=FULL` dla zapisów finansowych.
2. **Jeden pisarz.** `run_paper_live` pisze, API czyta. Wymuś to na poziomie połączenia
   (read-only dla API) — nie polegaj na konwencji.
3. Tabela `schema_version` + wersjonowane, idempotentne migracje. Migracja w dół
   niewymagana, ale migracja w górę musi być testowana na realnym pliku.
4. **Backup przed każdą migracją**, automatyczny, z timestampem. Test odtworzenia.
5. Polityka retencji: `equity_snapshots` i `system_events` rosną w nieskończoność.
   Zdefiniuj rolowanie (np. pełna rozdzielczość 30 dni, potem agregat dzienny).
6. `VACUUM` jako świadoma, rzadka operacja konserwacyjna, nigdy w pętli live.

---

## 139. KILL SWITCH

System handlujący bez awaryjnego zatrzymania jest niedokończony.

1. Globalny HALT przez: plik-sygnał, endpoint `POST /api/v1/system/halt` (z auth z §145)
   oraz automatycznie przy `RECONCILIATION_MISMATCH`, `DATABASE_ERROR` i przekroczeniu
   globalnego dziennego limitu straty.
2. HALT **przetrwa restart** — stan w bazie, nie w pamięci.
3. HALT blokuje **nowe wejścia**. Zarządzanie otwartymi pozycjami (SL, TP, TIME_EXIT)
   działa dalej — inaczej awaria zostawia niezabezpieczone pozycje.
4. Zdjęcie HALT wyłącznie jawną akcją, z wpisem w `system_events` (kto, kiedy, powód).
5. Widoczny na pierwszym ekranie dashboardu, nie ukryty w sekcji health.

---

## 140. WALIDACJA KONFIGURACJI NA STARCIE

1. Cały `AssetRegistry` walidowany schematem (pydantic) przy starcie. Fail-fast.
2. Reguły spójności sprawdzane jawnie, np.:
   - `tick_size` zgodny z `price_precision`
   - `minimum_notional` osiągalny przy `minimum_quantity` i realnej cenie
   - `quote_currency` ma zdefiniowaną ścieżkę konwersji do PLN
   - asset z `allow_short=True` ma zdefiniowany `short_mechanism`
   - asset ze statusem `VALIDATED` ma wskazany raport walidacyjny
3. `config_hash` liczony ze znormalizowanego rejestru, zapisywany przy każdym
   benchmarku i w `system_events` przy starcie.
4. Niespójny rejestr → aplikacja **nie startuje**. Nie startuj w trybie „częściowo działa".

---

## 141. OBSERWOWALNOŚĆ

1. Logi strukturalne (JSON) z polami: `timestamp`, `level`, `asset_id`, `phase`,
   `event_type`, `correlation_id`. Jeden `correlation_id` na cykl — pozwala prześledzić
   ścieżkę od quote do wpisu w ledgerze.
2. `GET /api/v1/system/metrics` — format tekstowy Prometheusa. Minimum:
   - czas trwania cyklu (histogram)
   - opóźnienie providera per asset
   - wiek quote per asset
   - wiek FX
   - liczba odrzuconych zleceń wg powodu
   - liczba błędów providera wg typu
   - equity PLN, exposure PLN
3. Nie buduj własnego dashboardu metryk. Wystaw dane, reszta to osobna decyzja.

---

## 142. BUDŻET CZASU CYKLU

Przy 9 assetach i providerach o różnej latencji cykl może przekroczyć interwał świecy.
Wtedy system zaczyna działać na starych danych, nie wiedząc o tym.

1. Zdefiniuj `max_cycle_duration` (proponowany punkt wyjścia: 20 s przy interwale 60 s).
2. Pobieranie danych równolegle, z limitem workerów i **twardym timeoutem per asset**.
   Asset, który nie zdążył, dostaje `PROVIDER_TIMEOUT` i jest pomijany w tym cyklu —
   nie blokuje pozostałych (§86).
3. Cykle nie mogą się nakładać. Lock; jeżeli poprzedni cykl trwa, pomiń start
   i zapisz `CYCLE_OVERRUN`.
4. Przekroczenie 50% budżetu → ostrzeżenie. Przekroczenie 100% → `system_event` + alert.
5. Zmierz to na realnych danych **przed** FAZĄ 5 i zapisz wynik. Dokładanie logiki
   do cyklu, który już się nie mieści, to marnowanie pracy.

---

## 143. KALENDARZE RYNKOWE

Sekcja 39 wymaga sesji, świąt i DST, ale nie wskazuje źródła. To najczęstsze miejsce,
w którym takie systemy po cichu się mylą.

1. Jedno źródło prawdy: biblioteka kalendarzy giełdowych albo wersjonowany plik JSON
   w repo. Nie zaszywaj dat w kodzie.
2. Pokryj: dni wolne, **wcześniejsze zamknięcia** (half days), przerwy sesyjne,
   przejścia DST (różne daty w USA i w Europie — to realny błąd w EURUSD i AAPL),
   otwarcie i zamknięcie tygodnia na FX.
3. Testy na konkretnych, wpisanych na sztywno datach: 3 lata wstecz i 1 rok w przód.
   Minimum: Thanksgiving (half day dzień po), 24 grudnia, niedzielne otwarcie FX,
   weekend DST w marcu i w listopadzie.
4. Kalendarz wygasł (brak danych na przyszłość) → `MARKET_STATUS = UNKNOWN`,
   nie „zakładam że otwarte".

---

## 144. DETERMINIZM TESTÓW

1. Wstrzykiwany `Clock` we wszystkich testach — zero zależności od realnego czasu.
2. Wszystkie testy offline deterministyczne. Test, który czasem przechodzi,
   traktuj jak test czerwony.
3. Ustalone ziarna dla wszystkiego losowego (np. model slippage).
4. Benchmarki jako **golden files**: wynik zapisany w repo, test porównuje.
   Zmiana golden file = jawny commit z uzasadnieniem, widoczny w review.
   To realizuje §7 w sposób automatyczny zamiast deklaratywnego.
5. Fixtures danych rynkowych w repo (małe, zanonimizowane wycinki), nie pobierane z sieci.

---

## 145. BEZPIECZEŃSTWO API — PRZED FAZĄ 10

Sekcja 92 planuje API v1 dopiero w FAZIE 10, ale obecny backend **już teraz** wystawia
endpointy POST modyfikujące stan portfela, przy `allow_origins=["*"]` i bez autoryzacji.
Czekanie do FAZY 10 zostawia to otwarte przez cały hardening.

Wykonaj w FAZIE 0 lub 1:

1. Klucz API ze zmiennej środowiskowej, sprawdzany przez `secrets.compare_digest`
   na **wszystkich** metodach mutujących.
2. `allow_origins` z konfiguracji, bez `"*"`.
3. Brak skonfigurowanego klucza → endpointy mutujące zwracają 503, nie działają otwarte.
4. `.env.example` ze wszystkimi zmiennymi, bez sekretów.
5. Popraw `read_only: true` w odpowiedzi `/` — obecnie jest nieprawdziwe.
6. Rate limit na endpointy mutujące.

---

## 146. RETENCJA I ROZMIAR DANYCH

Każdy strumień, który rośnie w nieskończoność, musi mieć zdefiniowaną politykę:

```text
logi aplikacji          rotacja, limit rozmiaru i liczby plików
equity_snapshots        pełna rozdzielczość N dni → agregat dzienny
system_events           retencja czasowa, krytyczne zdarzenia bez limitu
ai_decisions            ostatnie N per asset
executions / trades     bez limitu (dane finansowe)
plik stanu JSON         limit długości krzywej equity
market data cache       TTL
```

Test: symulacja 90 dni pracy nie powoduje nieograniczonego wzrostu żadnego artefaktu
poza tabelami finansowymi.

---

## 147. KOPIE ZAPASOWE I WYCOFANIE

1. Backup `trading.db` przed każdą migracją i przed każdym HARD STOP z §A7.
2. Udokumentowana procedura odtworzenia w `deploy/RECOVERY.md`.
3. **Przetestowane** odtworzenie, nie tylko opisane. Backup, którego nikt nie odtworzył,
   nie jest backupem.
4. Każda faza ma opisany sposób wycofania (rewert commita + ewentualna migracja w dół
   lub odtworzenie z backupu).

---

## 148. FEATURE FLAGS

Nowe modele (egzekucja, FX, PLN, SQLite) wprowadzaj za flagami konfiguracyjnymi.

1. Możliwość powrotu do poprzedniego zachowania **bez rewertu commita**.
2. Flagi zapisywane w `config_hash` i w metadanych benchmarku — inaczej nie da się
   odtworzyć, w jakim trybie powstał wynik.
3. Flagi tymczasowe usuwaj po ustabilizowaniu fazy. Nie zostawiaj martwych gałęzi kodu.

---

## 149. CONTRACT TESTY Z OPENAPI

Sekcja 93 wymaga contract testów. Konkretnie:

1. FastAPI generuje schemat OpenAPI — zapisz go jako artefakt w repo.
2. Test wykrywający **breaking change** w schemacie: usunięte pole, zmieniony typ,
   zmieniony kod odpowiedzi.
3. Testy Fluttera parsują realne przykładowe odpowiedzi (fixtures generowane z API),
   nie ręcznie napisane mapy.
4. Rozważ generowanie modeli Darta ze schematu zamiast ręcznego utrzymywania —
   ale tylko jeżeli nie wprowadza to ciężkiego toolchainu. Ręczne modele
   z testem kontraktowym też są akceptowalne.

---

## 150. DECYZJE ARCHITEKTONICZNE (ADR)

Załóż `docs/adr/` i zapisuj krótkie (jedna strona) decyzje dla wyborów, które trudno
odwrócić:

```text
wybór źródła FX
polityka weekendowa FX
model slippage
traktowanie syntetycznych shortów
instrument dla XAU i WTI
schemat bazy ledgera
podział profili egzekucji
```

Format: kontekst, rozważane opcje, decyzja, konsekwencje, data.

Bez tego za pół roku nikt nie odtworzy, dlaczego coś wygląda tak, a nie inaczej —
i ktoś to „naprawi" w złą stronę.

---

## 151. PAPER READY — STOPNIOWANIE ZAMIAST TAK/NIE

Sekcja 132 wymaga raportu per rynek, ale `PAPER READY` jako flaga binarna jest zbyt
gruba. Zastąp:

```text
DATA_QUALITY         REALTIME_BOOK / REALTIME_LAST / DELAYED / UNRELIABLE
EXECUTION_QUALITY    REAL_BOOK / DERIVED_SPREAD / SIMULATED_SPREAD / UNTRADEABLE
FX_QUALITY           LIVE / DAILY_REFERENCE / STALE_PRONE / UNAVAILABLE
SESSION_QUALITY      EXCHANGE_CALENDAR / APPROXIMATED / UNKNOWN
INSTRUMENT_CLARITY   CONFIRMED / PROXY / UNKNOWN

PAPER_READINESS      FULL / LIMITED / RESEARCH_ONLY / NOT_READY
```

`PAPER_READINESS` wynika z najsłabszego z powyższych, nie ze średniej.

Realistyczne oczekiwanie: BTC i pozostałe crypto mogą osiągnąć `FULL`.
AAPL, XAU, WTI i EURUSD na obecnych źródłach prawdopodobnie zatrzymają się
na `LIMITED` albo `RESEARCH_ONLY`. **To jest poprawny wynik, nie porażka.**
Nie naciągaj statusu, żeby tabela ładnie wyglądała.

---

## 152. CZEGO NIE ROBIĆ — UZUPEŁNIENIE §130

Dodatkowo nie:

```text
nie dodawaj zależności zewnętrznej bez uzasadnienia i akceptacji

nie buduj correlation engine, matching engine ani OMS
    — §65 i §35 wyraźnie tego nie wymagają na tym etapie

nie otwieraj shortów na instrumentach, które ich nie wspierają, bez jawnej etykiety

nie prezentuj wyniku z SIMULATED_SPREAD razem z wynikiem z REAL_BOOK bez adnotacji

nie zakładaj, że continuous futures proxy da się handlować

nie używaj naiwnych datetime

nie wołaj datetime.now() w core

nie commituj processed timestamp przed zapisem skutków cyklu

nie "naprawiaj" błędu, którego nie potwierdziłeś testem reprodukującym

nie zmieniaj golden file benchmarku bez osobnego commita z uzasadnieniem

nie zostawiaj włączonych tymczasowych feature flags po zakończeniu fazy

nie migruj bazy bez backupu

nie zdejmuj HALT automatycznie

nie prezentuj PLN policzonego po kursie sprzed tygodnia bez etykiety wieku

nie nadawaj statusu VALIDATED bez raportu walidacyjnego w repo
```

---

## 153. RAPORT FAZY — UZUPEŁNIENIE §127

Do listy z §127 dodaj:

```text
ZAŁOŻENIA SPECYFIKACJI, KTÓRE OKAZAŁY SIĘ NIEPRAWDZIWE
    (i jak zaktualizowano MASTER_SPEC.md)

ZARZUTY Z PROMPTU, KTÓRE NIE POTWIERDZIŁY SIĘ TESTEM

DŁUG TECHNICZNY DODANY ŚWIADOMIE W TEJ FAZIE

WPŁYW NA CZAS TRWANIA CYKLU

ZMIANY W PAPER_READINESS PER ASSET

CZY WYMAGANY JEST HARD STOP PRZED NASTĘPNĄ FAZĄ
```

---

## 154. PIERWSZE TRZY KROKI

Zanim zaczniesz FAZĘ 0 z §125, wykonaj w tej kolejności:

```text
1. Przeczytaj MASTER_SPEC.md wraz z tym aneksem w całości.

2. Wypisz WSZYSTKIE sprzeczności i niewykonalne wymagania, jakie dostrzegasz —
   także te, których nie ma w Części A.
   Nie zaczynaj kodować przed przedstawieniem tej listy.

3. Wykonaj FAZĘ 0.5 (A1) — capability matrix providerów.
   Dopiero jej wynik przesądza, które wymagania sekcji 15–35 są w ogóle wykonalne
   na obecnych źródłach danych.
```

Jeżeli po kroku 2 uznasz, że jakieś wymaganie tego promptu jest błędne — **powiedz to**.
Specyfikacja napisana przed poznaniem systemu nie jest nieomylna, a milczące obejście
wymagania jest gorsze niż jego zakwestionowanie.
