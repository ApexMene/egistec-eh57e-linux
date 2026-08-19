# Security

## What this driver is, and is not

This is a reverse-engineered driver for a sensor with no vendor support, written
and tested by one person on one machine. It authenticates. It has not been
audited, and the numbers below are the honest limit of what has been measured.

**Do not treat it as equivalent to a vendor fingerprint stack.**

### The false-acceptance rate is not known

The matcher has been measured on five fingers, three placements each: twenty
impostor comparisons in total, with no false accepts at the acceptance
threshold. Twenty comparisons cannot measure a rate. A false-acceptance rate of
1 in 1000 would be invisible in that experiment, and a rate that low is not
demonstrated.

For reference, the sensor images about **15 mm²** of skin at roughly 400 dpi.
Published work on sensor interoperability finds error rates climbing steeply
below 500 dpi and 500 × 500 pixels; this sensor is far below both. Small contact
area is a fundamental limit on how much can be distinguished, and no matcher
recovers information the sensor never captured.

### There is no anti-spoofing

The matcher compares ridge texture. It performs no liveness detection of any
kind. A sufficiently good physical replica of an enrolled fingertip is expected
to pass.

### Fingerprints are a username, not a password

This is true of all fingerprint authentication and worth restating: you leave
copies of your fingerprints on everything you touch, and you cannot change them
after a compromise.

### What this means in practice

Reasonable: unlocking a personal laptop as a convenience, in front of a password
you still know and still use.

Not reasonable: as the only factor protecting anything that matters; as a
second factor whose independence you are relying on; on a machine holding other
people's data; anywhere a threat model actually exists.

## Where enrolled data lives

Templates are stored by `fprintd`, not on the sensor, under
`/var/lib/fprint/<user>/egis057e/`, readable only by root. They are band-passed,
normalised images of the fingertip — not a hash, and not a one-way transform.
Anyone able to read them can reconstruct an approximation of the enrolled ridge
pattern. Treat that directory as sensitive.

The driver advertises no on-device storage, so nothing is retained in the sensor
between sessions.

## Reporting a vulnerability

Open a GitHub issue for anything that is not itself exploitable — a wrong
threshold, a missing bounds check, a way to make the driver accept an unenrolled
finger in ordinary use.

For something that would be harmful to publish before a fix, contact the
maintainer through their GitHub profile rather than opening a public issue.

Please include what you measured and how to reproduce it. As everywhere else in
this project, a security claim without a measurement cannot be acted on.
