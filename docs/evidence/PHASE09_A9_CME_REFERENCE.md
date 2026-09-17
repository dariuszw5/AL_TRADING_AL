# Phase 09 A.9 - CME Contract Reference Note

Verified externally on 2026-09-17 against official CME Group material.

## Gold futures

App canonical ID:

```text
GOLD_FUT_CONT
```

Provider proxy symbol:

```text
GC=F
```

CME reference product:

```text
GC
```

Official contract unit:

```text
100 troy ounces
```

Official price quotation:

```text
U.S. dollars and cents per troy ounce
```

Primary reference:

https://www.cmegroup.com/markets/metals/precious/gold-futures.html

CME contract-specification fact card also documents:

```text
Contract Size: 100 troy ounces
```

## WTI crude oil futures

App canonical ID:

```text
WTI_FUT_CONT
```

Provider proxy symbol:

```text
CL=F
```

CME reference product:

```text
CL
```

Official contract unit:

```text
1,000 barrels
```

Official minimum tick:

```text
$0.01 per barrel
```

Official standard-contract tick value:

```text
$10 per contract
```

Reference:

https://www.cmegroup.com/education/articles-and-reports/micro-wti-crude-oil-futures-faq

## Accounting decision

The exchange reference units are documented, but NOT activated as the
app runtime `pnl_multiplier`.

Reason:

1. Yahoo GC=F / CL=F are continuous futures proxies in the application.
2. Current runtime quantity sizing is generic price-unit sizing.
3. Current fee model is not contract-aware.
4. Rollover semantics remain unresolved.

Therefore:

```text
GOLD_FUT_CONT runtime pnl_multiplier = None
WTI_FUT_CONT  runtime pnl_multiplier = None
```

until futures quantity/execution semantics are explicitly redesigned.