<!-- One PR = one research packet under research/<name>/. See docs/OPEN_TASKS.md. -->

## Task
Program + window(s) targeted (e.g. Pump `pump_quote` 12 windows):

Base checkpoint (lalalune commit + checkpoint dir):

## Measured result (required)
Metric script + command used:

```
matched before: __ / ___   raw before: ___
matched after:  __ / ___   raw after:  ___
windows gained: ______   windows/raw lost: NONE
```

Paste the metric output (or link the measure JSON in the packet).

## Deployed evidence (for any behavior-affecting change)
Address(es) + error variant in the deployed binary that justify the change:

## Checklist
- [ ] Packet at `research/<name>/` with: patch, build recipe, measure JSON, RESULT.md, SHA256SUMS
- [ ] Built natively from source — deployed `.so` is NOT a build input
- [ ] No regression in the matched set or the raw set
- [ ] No file/line-hardcoding macro; no removed/added checks; no changed error codes vs deployed
- [ ] No captured `.so` committed; no secrets
- [ ] Attribution to lalalune/pumpfun-source (MIT) kept
