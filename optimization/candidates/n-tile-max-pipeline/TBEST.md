# Current official baseline versus TBest

Baseline submission: `6ad33b78193e507d8ea310c4`, official score 19.45.
Source: `evidence/formal/dual-aiv-fixed-6ad33b78/evidence.json`.
TBest is best_time from that same stored official response, not a fresh query.
Order below is baseline official testcase order; shapes are unknown.
Times are microseconds. TBest need not be from one runnable submission.

| Point | Testcase ID | FIFO | Dual AIV | Delta | Change | TBest | Dual/TBest |
|---:|---|---:|---:|---:|---:|---:|---:|
| 1 | `6a9a9ec4bf41025d6014adc3` | 21.08 | 18.41 | -2.67 | -12.67% | 2.06 | 8.94x |
| 2 | `6a9a9ec4bf41025d6014adc7` | 9.30 | 9.36 | +0.06 | +0.65% | 1.67 | 5.60x |
| 3 | `6a9a9ec4bf41025d6014adcb` | 15.52 | 12.36 | -3.16 | -20.36% | 2.11 | 5.86x |
| 4 | `6a9a9ec4bf41025d6014adcf` | 25.96 | 20.75 | -5.21 | -20.07% | 7.55 | 2.75x |
| 5 | `6a9a9ec4bf41025d6014add3` | 19.02 | 17.66 | -1.36 | -7.15% | 8.28 | 2.13x |
| 6 | `6a9a9ec4bf41025d6014add7` | 59.59 | 38.90 | -20.69 | -34.72% | 12.02 | 3.24x |
| 7 | `6a9a9ec4bf41025d6014addb` | 90.07 | 61.65 | -28.42 | -31.55% | 14.68 | 4.20x |
| 8 | `6a9a9ec4bf41025d6014addf` | 224.02 | 136.64 | -87.38 | -39.01% | 15.80 | 8.65x |
| 9 | `6a9a9ec4bf41025d6014ade3` | 189.66 | 103.41 | -86.25 | -45.48% | 19.27 | 5.37x |
| 10 | `6a9a9ec4bf41025d6014ade7` | 431.58 | 266.85 | -164.73 | -38.17% | 35.63 | 7.49x |
| 11 | `6a9a9ec4bf41025d6014adeb` | 482.63 | 327.58 | -155.05 | -32.13% | 52.73 | 6.21x |
| 12 | `6a9a9ec4bf41025d6014adef` | 987.95 | 661.18 | -326.77 | -33.08% | 64.52 | 10.25x |
| 13 | `6a9a9ec4bf41025d6014adf3` | 1434.54 | 873.24 | -561.30 | -39.13% | 76.73 | 11.38x |
| 14 | `6a9a9ec4bf41025d6014adf7` | 3329.91 | 1931.74 | -1398.17 | -41.99% | 173.37 | 11.14x |
| 15 | `6a9a9ec4bf41025d6014adfb` | 7438.21 | 4600.98 | -2837.23 | -38.14% | 340.89 | 13.50x |

No inferred aggregate score, shape assignment, or stage bottleneck.
New submissions without attributable score must be compared by testcase ID
against this verified baseline; timings alone cannot trigger promotion.
