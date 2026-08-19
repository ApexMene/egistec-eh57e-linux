# Contributing

This project reverse engineers an undocumented fingerprint sensor and matches on
its output. Both halves have a house rule that matters more than style:

> **Every claim is attached to a measurement.**

If you change a threshold, a filter, a search radius or an algorithm, the pull
request has to say what you measured, on what data, and what the numbers were
before and after. "It feels more reliable" is not reviewable, and on biometrics
it is not safe either. Three methods recommended by the literature were tried
here and lost to a simpler baseline — the only reason we know that is that they
were measured.

Negative results are welcome and are kept. If you try something and it does not
work, that is a contribution: open a pull request that adds the measurement and
the conclusion to `CHANGELOG.md`.

## Reporting a device

If you have an Egis sensor that is not `1c7a:057e`, open an issue with the
**Device report** template. Useful even if nothing works yet: the USB id, the
`lsusb -v` output, and what the device does when sent the `EGIS` commands
documented in the README tells us whether it is the same family.

Before concluding that a command sequence works, run the echo test described in
`research/protocol/probe6-echo-test.py`. Some Egis firmwares validate only the
`EGIS` prefix and echo the parameters back, so an init sequence can report
"24/24 OK" while the device has executed nothing at all. This is the single
easiest way to waste a week.

## Working on the driver

The driver lives in `driver/` and is copied into a libfprint checkout to build.
See the README for the build steps.

Two constraints are easy to trip over:

- A `FpDevice` instance must stay under 65535 bytes. Large buffers go on the
  heap. The failure appears at runtime, from `g_type_register_static_simple`,
  not at compile time.
- A `FpDevice` subclass must set `dev_class->features`. `FpImageDevice` fills
  this in for you; a plain `FpDevice` does not, and the assertion fires on the
  first construction.

Use `tools/matching/matchtest.c` to check that a change to the matcher gives the
same numbers as the Python prototype. It includes `egis057e.c` directly, because
the maths functions are `static` and that is the only way to test the code that
actually runs rather than a copy that can drift.

## Working on the matcher

`tools/analysis/matching_protocol.py` defines the measurement protocol: enrol
placements 1 and 2 of each finger, verify with placement 3. Keep it. The third
placement never enters enrolment, otherwise the experiment measures how well
something resembles itself, which is always excellent and always meaningless.

Report both genuine **and** impostor scores. Every change that raised genuine
scores in this project also raised impostor scores, usually by more. A change
that only reports the genuine side is not evidence of anything.

When comparing two methods, hold everything else fixed. The mosaicking study in
`tools/analysis/mosaic.py` initially looked like it lost because of fusion, when
part of the effect was simply a larger search radius; the control that separated
the two is what made the conclusion trustworthy.

## Captures and privacy

**Fingerprint captures are not committed.** `data/` and `scratch/` are ignored,
and they must stay that way. If you contribute a measurement, contribute the
script and the numbers, not the biometric data.

## Style

- C follows libfprint's style, which is GNOME's.
- Comments explain *why*, and cite the measurement where there is one.
- Commit messages are in English and explain the reasoning, not just the diff.
- Python targets the standard library plus `numpy`; `matplotlib` only for figures.
