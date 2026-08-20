"""
Constants shared between train_cmac.py (stand-alone CMAC warm-up) and
main.py (live throwing).

These MUST stay in sync between the two scripts: main.py's live sample_window()
calls and train_cmac.py's warmup() calls need to agree on timing, or the CMAC
ends up seeing input spacing / prediction horizons at inference time that
differ from what it was trained on (see the notes in cmac_warmup.warmup).
"""

N_CENTERS = 9
TIME_OF_FLIGHT = 3.0    # seconds -- fixed estimate of ball flight time, tune on the robot
WARMUP_DURATION = 300.0  # seconds of prediction-only CMAC warm-up before throwing.
                          # Bumped up from 120s: aggregate warm-up MSE was already low there,
                          # but that was dominated by the well-covered middle of the target's
                          # range -- the windows that specifically look like "3s before a real
                          # peak/trough" are a minority of what any one pass sees, so they need
                          # many more revisits (more full cycles) to actually converge, even
                          # though the position *range* itself was already covered early on.
POLL_INTERVAL = 1.2     # seconds between buffered target samples during warm-up
                         # (independent of TIME_OF_FLIGHT -- see cmac_warmup.warmup)
                         # Also sets how far apart x1,x2,x3 are, i.e. how much of the
                         # target's motion the CMAC actually "sees" per prediction --
                         # too small (e.g. 0.5s) and a window near a peak/trough carries
                         # almost no velocity/direction info, so predictions near turning
                         # points collapse toward an averaged, ambiguous guess. Bumped up
                         # from 0.5s for that reason -- retune if predictions are still
                         # worst specifically near the target's direction reversals.
                         # Set to 1.2s (== 60/50) to match the target's actual 50 BPM
                         # step rate -- see notebooks/test_cmac_pingpong.ipynb, which found
                         # that sampling at the target's real movement rhythm (instead of an
                         # unrelated rate like the old 1.0s) is what let the CMAC learn a
                         # clean, consistent x1,x2,x3 -> x_true mapping in the first place.
MSE_WINDOW = 20          # number of predictions compared first-vs-last in report_learning
