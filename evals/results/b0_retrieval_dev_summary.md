# B0 retrieval only, dev split

Intervals are 95 percent bootstrap intervals, 2000 resamples, seed 0. Answerable items only; k is 5.

| category | items | recall@1 | recall@3 | recall@5 | hit@5 | mrr | all_gold@5 |
|---|---|---|---|---|---|---|---|
| single_fact | 19 | 0.68 [0.47, 0.89] | 0.84 [0.68, 1.00] | 0.84 [0.68, 1.00] | 0.84 [0.68, 1.00] | 0.76 [0.58, 0.92] | n/a |
| multi_chunk | 11 | 0.39 [0.27, 0.50] | 0.62 [0.50, 0.77] | 0.83 [0.70, 0.95] | 1.00 [1.00, 1.00] | 0.88 [0.70, 1.00] | 0.64 [0.36, 0.91] |
| all | 30 | 0.58 [0.42, 0.73] | 0.76 [0.63, 0.88] | 0.84 [0.72, 0.94] | 0.90 [0.80, 1.00] | 0.81 [0.68, 0.92] | n/a |

## Retrieval stage failure labels

- retrieval_miss: 2
- ranking_miss: 5

## Top-1 dense score (no threshold decision here)

| category | items | min | median | max |
|---|---|---|---|---|
| single_fact | 19 | 0.557 | 0.704 | 0.848 |
| multi_chunk | 11 | 0.588 | 0.733 | 0.796 |
| unanswerable | 11 | 0.353 | 0.511 | 0.629 |
| adversarial | 3 | 0.450 | 0.531 | 0.635 |

## Five worst answerable items

### gi-008 (single_fact)

Question: What conditions is gabapentin prescribed to treat?

- missed gold entry: seed:openfda:01b810b7-f4c8-4412-bbc5-b9220d8770d8: Management of postherpetic neuralgia in adults Adjunctive therapy in the treatment of partial onset seizures, with and without secondary generalization, in adults and pediatric patients 3 years and older with epilepsy (found at rank 17)
- top 3 chunks:
  1. gabapentin drug label (score 0.639): Table 4 lists adverse reactions that occurred in at least 1% of Gabapentin-treated patients >12 years of age with epilepsy participating in placebo-controlled trials and were numerically more common in the Gabapentin group. In these studies, either Gabapentin or placebo was added to the patient’s cu
  2. gabapentin drug label (score 0.632): 4 1 Among the adverse reactions occurring at an incidence of at least 10% in Gabapentin-treated patients, somnolence and ataxia appeared to exhibit a positive dose-response relationship. The overall incidence of adverse reactions and the types of adverse reactions seen were similar among men and wom
  3. gabapentin drug label (score 0.623): Warnings and cautions 5 WARNINGS AND PRECAUTIONS Drug Reaction with Eosinophilia and Systemic Symptoms (Multiorgan hypersensitivity): Discontinue if alternative etiology is not be established (5.1) Anaphylaxis and Angioedema: Discontinue and evaluate patient immediately (5.2) Driving impairment; Som

### gi-014 (single_fact)

Question: What tablet strengths do propranolol hydrochloride tablets come in?

- missed gold entry: seed:openfda:013a485a-4227-46ae-b19f-c550302fcb96: Propranolol Hydrochloride Tablets, USP are available as tablets for oral administration containing either 10 mg, 20 mg, 40 mg, 60 mg, or 80 mg of propranolol hydrochloride, USP. (found at rank 6)
- top 3 chunks:
  1. propranolol hydrochloride drug label (score 0.686): propranolol hydrochloride drug label
  2. propranolol hydrochloride drug label (score 0.638): Indications and usage INDICATIONS AND USAGE Hypertension Propranolol hydrochloride tablets are indicated in the management of hypertension. It may be used alone or used in combination with other antihypertensive agents, particularly a thiazide diuretic. Propranolol hydrochloride is not indicated in 
  3. propranolol hydrochloride drug label (score 0.616): Propranolol Hydrochloride Tablets, USP also contain lactose anhydrous, magnesium stearate, microcrystalline cellulose, and sodium starch glycolate. Color additives include FD&C Yellow no. 6 aluminum lake (10 mg and 80 mg), D&C Yellow no. 10 aluminum lake (10 mg, 40 mg, and 80 mg), FD&C Blue no. 1 al

### gi-024 (single_fact)

Question: According to the oxycodone hydrochloride drug label, which controlled substance schedule is oxycodone in?

- missed gold entry: seed:openfda:01db4606-d49c-4b10-a78a-1cf41880a9fb: Oxycodone hydrochloride tablets contains oxycodone, a Schedule II controlled substance. (found at rank 6)
- top 3 chunks:
  1. oxycodone hydrochloride drug label (score 0.823): oxycodone hydrochloride drug label
  2. oxycodone hydrochloride drug label (score 0.681): Indications and usage 1 INDICATIONS AND USAGE Oxycodone hydrochloride tablets are indicated for the management of pain severe enough to require an opioid analgesic and for which alternative treatments are inadequate. Limitations of Use Because of the risks of addiction, abuse, misuse, overdose, and 
  3. oxycodone hydrochloride drug label (score 0.673): Be familiar with these differences, as outlined in the approved labeling for those products, prior to recommending or prescribing such an agent. 2.3 Initial Dosage Although it is not possible to list every condition that is important to the selection of the initial dose of oxycodone hydrochloride ta

### gi-047 (multi_chunk)

Question: What serious risks do the lithium carbonate and warfarin sodium labels warn about?

- missed gold entry: seed:openfda:0cbce382-9c88-4f58-ae0f-532a841e8f95: Warfarin sodium can cause major or fatal bleeding (not among the candidates)
- top 3 chunks:
  1. lithium carbonate drug label (score 0.690): lithium carbonate drug label

Boxed warning
WARNING: LITHIUM TOXICITY Lithium toxicity is closely related to serum lithium concentrations, and can occur at doses close to therapeutic concentrations. Facilities for prompt and accurate serum lithium determinations should be available before initiating
  2. lithium carbonate drug label (score 0.669): Adverse reactions 6 ADVERSE REACTIONS The following adverse reactions are described in greater detail in other sections: • Acute Lithium Toxicity [see Warnings and Precautions ( 5.1 )] • Lithium-Induced Polyuria [see Warnings and Precautions ( 5.2 )] • Hyponatremia [see Warnings and Precautions ( 5.
  3. lithium carbonate drug label (score 0.607): Table 3: Adverse Reactions Reported in 2% or More of Pediatric Patients on Lithium and That Occurred at Greater Incidence Than in the Placebo Group in the 8-Week Acute Bipolar Trial System Organ Class/ Preferred Term Placebo N=28% Lithium N=53% Gastrointestinal Disorders Nausea/vomiting 29 57 Genera

### gi-051 (multi_chunk)

Question: What is extended-release methylphenidate indicated for, and what risk does the label warn about?

- missed gold entry: seed:openfda:10aa0dc0-bd0e-4927-a19a-8722d78ad67d: Methylphenidate hydrochloride extended-release capsules are indicated for the treatment of Attention Deficit Hyperactivity Disorder (ADHD) in pediatric patients 6 to 15 years of age. (found at rank 7)
- top 3 chunks:
  1. methylphenidate hydrochloride drug label (score 0.746): Educate patients and their families about these risks, proper storage of the drug, and proper disposal of any unused drug. Throughout methylphenidate hydrochloride extended-release treatment, reassess each patient’s risk of abuse, misuse, and addiction and frequently monitor for signs and symptoms o
  2. methylphenidate hydrochloride drug label (score 0.716): Boxed warning WARNING: ABUSE, MISUSE, AND ADDICTION Methylphenidate hydrochloride extended-release has a high potential for abuse and misuse, which can lead to the development of a substance use disorder, including addiction. Misuse and abuse of CNS stimulants, including methylphenidate hydrochlorid
  3. methylphenidate hydrochloride drug label (score 0.705): Methylphenidate hydrochloride extended-release has a high potential for abuse and misuse, which can lead to the development of a substance use disorder, including addiction. Misuse and abuse of CNS stimulants, including methylphenidate hydrochloride extended-release , can result in overdose and deat
