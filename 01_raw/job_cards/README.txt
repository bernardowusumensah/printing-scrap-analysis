JOB CARD PRACTICE DATA (simulated - not real company data)

A fictional cup-printing department with 4 dry offset printers, 13 weeks
(Mon 2026-07-06 to Sat 2026-10-03; a few jobs finish on the following Monday).
Plant runs Mon-Sat, 3 shifts: 1 = 06:00-14:00, 2 = 14:00-22:00, 3 = 22:00-06:00.
Night shift rows use the date the shift STARTED.

Files
  job_cards.csv        one row per job card (top of card + Setup box)
  job_card_shifts.csv  one row per filled-in Production line (per shift)
  work_centers.csv     the 4 printers
  materials.csv        products, customers (coded) and pallet sizes

Joins
  job_card_shifts.order  -> job_cards.order
  job_cards.work_center  -> work_centers.work_center
  job_cards.material     -> materials.material

Useful facts
  Each printer has one running counter. counter_end - counter_start should equal
  total_printed + run_scrap (shifts) or setup_scrap (setup).
  Scrap is counted in cups, not kg.

Your brief: which printers, products, shifts and job types create the most scrap,
and what would you fix first? Profile and clean before you analyze: the data was
"typed up from paper", so some entries have mistakes.
