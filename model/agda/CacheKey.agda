------------------------------------------------------------------------
-- CacheKey.agda
--
-- A small formal model of the two cache-key notions in play in
-- paperkit's mutation-testing grid (~68k cells, each a pair
-- (check, def-site)).
--
--   Notion A (host / Bazel):  key_A = hash of staged input CONTENT
--                             (transitive .pyc/.py closure + mutated
--                             module + project files).
--   Notion B (domain):        a cell (c , d) is a KNOWN NO-OP when
--                             d ∉ sens c.
--
-- The model is deliberately tiny: finite carriers, decidable
-- equality, list-as-set, no category theory.  Everything below is
-- either PROVED, or declared as a parameter of the `Model` module
-- telescope with a comment saying WHY it is an assumption and WHAT
-- breaks if it is false.  There are ZERO postulates: the file
-- typechecks under --safe, so every theorem below is universally
-- quantified over all instantiations of the assumptions.
--
-- Typechecks with Agda 2.8.0 + agda-stdlib:  agda CacheKey.agda
------------------------------------------------------------------------

{-# OPTIONS --safe #-}

module CacheKey where

open import Data.Nat using (ℕ; zero; suc; _+_; _*_; _≤_; z≤n; s≤s)
open import Data.Nat.Properties using (≤-refl; ≤-trans; +-mono-≤; n≤1+n)
open import Data.List using (List; []; _∷_; filter; length; _++_)
open import Data.List.Relation.Unary.Any using (Any; here; there)
open import Data.List.Membership.Propositional using (_∈_; _∉_)
open import Data.Product using (_×_; _,_; Σ; ∃; proj₁; proj₂; ∃-syntax)
open import Data.Sum using (_⊎_; inj₁; inj₂)
open import Data.Bool using (Bool; true; false)
open import Data.Empty using (⊥; ⊥-elim)
open import Data.Unit using (⊤; tt)
open import Relation.Nullary using (¬_; Dec; yes; no; does)
open import Relation.Nullary.Decidable using (⌊_⌋)
open import Relation.Binary.PropositionalEquality
  using (_≡_; refl; sym; trans; cong; _≢_)

------------------------------------------------------------------------
-- 1.  Carriers.  Finite, concrete, decidable.
--
-- We use small enumerations rather than an abstract `Fin n` so that
-- the COUNTEREXAMPLE TERMS in §5 are literally inhabitants one can
-- read off the page.  Nothing in §2-§4 depends on the cardinality.
------------------------------------------------------------------------

-- Modules of the engine (a check's import closure is drawn from these).
data Module : Set where
  gate cache bib layout : Module

-- Definition sites.  Each lives in exactly one module (see `owner`).
data DefSite : Set where
  gate-verdict   : DefSite   -- in `gate`
  gate-exit      : DefSite   -- in `gate`
  cache-key      : DefSite   -- in `cache`
  cache-logfmt   : DefSite   -- in `cache`, a logging-only definition
  bib-parse      : DefSite   -- in `bib`
  layout-widen   : DefSite   -- in `layout`

-- Checks (the things whose pass/fail we observe).
data Check : Set where
  claims-check   : Check
  render-check   : Check

_≟M_ : (m n : Module) → Dec (m ≡ n)
gate   ≟M gate   = yes refl
gate   ≟M cache  = no λ ()
gate   ≟M bib    = no λ ()
gate   ≟M layout = no λ ()
cache  ≟M gate   = no λ ()
cache  ≟M cache  = yes refl
cache  ≟M bib    = no λ ()
cache  ≟M layout = no λ ()
bib    ≟M gate   = no λ ()
bib    ≟M cache  = no λ ()
bib    ≟M bib    = yes refl
bib    ≟M layout = no λ ()
layout ≟M gate   = no λ ()
layout ≟M cache  = no λ ()
layout ≟M bib    = no λ ()
layout ≟M layout = yes refl

_≟D_ : (d e : DefSite) → Dec (d ≡ e)
gate-verdict ≟D gate-verdict = yes refl
gate-verdict ≟D gate-exit    = no λ ()
gate-verdict ≟D cache-key    = no λ ()
gate-verdict ≟D cache-logfmt = no λ ()
gate-verdict ≟D bib-parse    = no λ ()
gate-verdict ≟D layout-widen = no λ ()
gate-exit    ≟D gate-verdict = no λ ()
gate-exit    ≟D gate-exit    = yes refl
gate-exit    ≟D cache-key    = no λ ()
gate-exit    ≟D cache-logfmt = no λ ()
gate-exit    ≟D bib-parse    = no λ ()
gate-exit    ≟D layout-widen = no λ ()
cache-key    ≟D gate-verdict = no λ ()
cache-key    ≟D gate-exit    = no λ ()
cache-key    ≟D cache-key    = yes refl
cache-key    ≟D cache-logfmt = no λ ()
cache-key    ≟D bib-parse    = no λ ()
cache-key    ≟D layout-widen = no λ ()
cache-logfmt ≟D gate-verdict = no λ ()
cache-logfmt ≟D gate-exit    = no λ ()
cache-logfmt ≟D cache-key    = no λ ()
cache-logfmt ≟D cache-logfmt = yes refl
cache-logfmt ≟D bib-parse    = no λ ()
cache-logfmt ≟D layout-widen = no λ ()
bib-parse    ≟D gate-verdict = no λ ()
bib-parse    ≟D gate-exit    = no λ ()
bib-parse    ≟D cache-key    = no λ ()
bib-parse    ≟D cache-logfmt = no λ ()
bib-parse    ≟D bib-parse    = yes refl
bib-parse    ≟D layout-widen = no λ ()
layout-widen ≟D gate-verdict = no λ ()
layout-widen ≟D gate-exit    = no λ ()
layout-widen ≟D cache-key    = no λ ()
layout-widen ≟D cache-logfmt = no λ ()
layout-widen ≟D bib-parse    = no λ ()
layout-widen ≟D layout-widen = yes refl

------------------------------------------------------------------------
-- 2.  The three domain maps: closure, defsOf, sens.
--
-- `closure c` — the modules check c imports (transitively).  This is
--   exactly what the Bazel rule stages:
--     closure_pyc = depset(transitive=[t[PycInfo].pyc for t in closure])
--     closure_py  = depset(transitive=[t[PycInfo].py  for t in closure])
--     inputs = depset(mut + project + [sched], transitive=[pyc, py])
--
-- `defsOf m` — the def-sites the module m contains.
--
-- `sens c` — the def-sites where mutating actually flips c.  This is
--   MEASURED (the sweep), not declared.  §3 is entirely about what it
--   costs to treat a measured set as a specification.
------------------------------------------------------------------------

closure : Check → List Module
closure claims-check = gate ∷ cache ∷ bib ∷ []
closure render-check = layout ∷ cache ∷ []

defsOf : Module → List DefSite
defsOf gate   = gate-verdict ∷ gate-exit ∷ []
defsOf cache  = cache-key ∷ cache-logfmt ∷ []
defsOf bib    = bib-parse ∷ []
defsOf layout = layout-widen ∷ []

sens : Check → List DefSite
-- claims-check is sensitive to gate's verdict and exit paths and to
-- bib parsing, but NOT to cache-key (it runs uncached in the sweep)
-- and NOT to cache-logfmt (logging only — the canonical no-op).
sens claims-check = gate-verdict ∷ gate-exit ∷ bib-parse ∷ []
sens render-check = layout-widen ∷ []

-- The cell grid.  A cell is a (check , def-site) pair.
Cell : Set
Cell = Check × DefSite

------------------------------------------------------------------------
-- 3.  Behaviour, and what "flips" means.
--
-- `Flips c d` is the SEMANTIC fact: mutating def-site d makes check c
-- change verdict.  It is a relation we do not define — it is the
-- ground truth the sweep is trying to measure.  Modelling it as an
-- opaque parameter is the whole point: `sens` is an approximation OF
-- it, and the model's job is to say when the approximation is safe.
------------------------------------------------------------------------

-- `Flips`, `sens-complete`, `Bytes` and `Residue` are MODULE
-- PARAMETERS, not postulates.  This is strictly stronger than
-- postulating them: everything below is universally quantified over
-- every possible instantiation, the file passes --safe, and the
-- assumptions are visible in the module telescope rather than buried.
-- See the `Assumptions` telescope immediately below; the WHY for each
-- is stated there.

------------------------------------------------------------------------
-- 3a.  COMPLETENESS of `sens` — the load-bearing assumption.
--
-- Soundness of key_B is *exactly* the contrapositive of completeness.
-- We take completeness as a module PARAMETER and derive soundness from
-- it, so the dependency is visible in the proof term and in the
-- module telescope.
------------------------------------------------------------------------

------------------------------------------------------------------------
-- ASSUMPTIONS, as a module telescope.
--
-- Flips
--   WHY ASSUMED: the physical behaviour of running a check against a
--   mutated tree.  Not computable inside the model (it is the model's
--   *referent*); defining it would beg the question §7 asks.
--
-- sens-complete
--   WHY ASSUMED: says the measured sensitivity set names EVERY
--   def-site that could flip the check.  Unprovable inside the model
--   (`Flips` is opaque) and unprovable in the real system too — its
--   only warrant is an exhaustive sweep, an *empirical* claim resting
--   on the sweep's own coverage.
--   WHAT BREAKS IF FALSE: if some d with `Flips c d` is missing from
--   `sens c`, key_B skips a cell that would have flipped.  The skipped
--   cell is recorded as a no-op, so the sweep reports the check as
--   INSENSITIVE to d.  The failure is SILENT: a missed sensitivity is
--   a missed defect.
--
-- sens-tight   (the DUAL — see §3b)
--   WHY ASSUMED: says `sens` names ONLY def-sites that really flip.
--   Same epistemic status as completeness: `Flips` is opaque, so this
--   is measured, never derived.
--   WHAT BREAKS IF FALSE: every d ∈ sens c with ¬ (Flips c d) is a
--   cell that RUNS and provably could not have flipped — an AVOIDABLE
--   cell.  Under the operating criterion (>0 avoidable is a defect)
--   this is a defect of the same standing as a missed sensitivity, not
--   a lesser one.  The two failures differ in KIND, not in severity:
--   an under-large `sens` reports a wrong answer; an over-large `sens`
--   burns unmeasured resource to recompute a right answer it already
--   had.  NEITHER IS "SAFE".
--
-- Bytes / Residue / r₁ r₂ r₁≢r₂
--   WHY ASSUMED: irrelevant internal structure.  All we need of Bytes
--   is equality; all we need of Residue is that it has two distinct
--   inhabitants, which is what makes the §7b refutation bite.
------------------------------------------------------------------------

module Model
  (Flips         : Check → DefSite → Set)
  (sens-complete : ∀ (c : Check) (d : DefSite) → Flips c d → d ∈ sens c)
  (sens-tight    : ∀ (c : Check) (d : DefSite) → d ∈ sens c → Flips c d)
  (Bytes         : Set)
  (Residue       : Set)
  (r₁ r₂         : Residue)
  (r₁≢r₂         : r₁ ≢ r₂)
  where

  ------------------------------------------------------------------------
  -- THEOREM 1 (SOUNDNESS of key_B).
  --
  --   d ∉ sens c  →  ¬ (Flips c d)
  --
  -- i.e. a cell key_B calls a no-op genuinely cannot flip.
  ------------------------------------------------------------------------

  key_B-sound : ∀ (c : Check) (d : DefSite) → d ∉ sens c → ¬ (Flips c d)
  key_B-sound c d d∉ f = d∉ (sens-complete c d f)

  -- The converse direction does not follow from `sens-complete`
  -- alone; it is the separate assumption `sens-tight` (§3b).  It is
  -- NOT a "safe direction" that may be left unassumed: without it the
  -- avoidable-cell count of §6a is inexpressible, and an over-large
  -- `sens` silently reintroduces exactly the waste key_B exists to
  -- remove.  See R1/R2 in the revision notes at §9.

  ------------------------------------------------------------------------
  -- 4.  key_A: the content key.
  --
  -- We model the staged content of a cell abstractly: a cell's staged
  -- inputs are the contents of every module in the closure, plus the
  -- mutated module.  Two cells share a key iff those contents are
  -- byte-identical.  We model "content" as a function from Module to an
  -- opaque Bytes type, indexed by a "world" (a state of the tree).
  ------------------------------------------------------------------------

  -- A World is a snapshot of module contents.
  World : Set
  World = Module → Bytes

  -- The staged content of a cell, as the list of (module, bytes) the
  -- Bazel rule places in the sandbox.  We keep it as the list of bytes
  -- in closure order, which is what the depset hash sees.
  staged : World → Check → List Bytes
  staged w c = Data.List.map w (closure c)
    where open import Data.List using (map)

  -- key_A agreement: two worlds give a cell the same key iff every
  -- module in the closure has identical content in both.
  KeyA-same : World → World → Check → Set
  KeyA-same w w′ c = ∀ m → m ∈ closure c → w m ≡ w′ m

  -- key_A's decision: re-run cell (c , d) when the closure content moved.
  KeyA-rerun : World → World → Cell → Set
  KeyA-rerun w w′ (c , d) = ¬ (KeyA-same w w′ c)

  -- key_B's decision: skip cell (c , d) when d ∉ sens c, regardless of
  -- content.
  KeyB-skip : Cell → Set
  KeyB-skip (c , d) = d ∉ sens c

  ------------------------------------------------------------------------
  -- 5.  THEOREM 2 (REFINEMENT / OVER-INCLUSION).
  --
  -- We exhibit an inhabitant of the over-inclusion type: a def-site d
  -- living in a module m that IS in check c's closure, yet d ∉ sens c.
  -- Because m ∈ closure c, mutating d changes a staged input byte, so
  -- key_A re-runs; key_B knows the cell is a no-op.
  ------------------------------------------------------------------------

  -- The shape of an over-inclusion witness.
  record OverIncluded : Set where
    field
      chk    : Check
      mod    : Module
      site   : DefSite
      in-clo : mod ∈ closure chk       -- key_A stages mod for chk
      in-mod : site ∈ defsOf mod       -- mutating site perturbs mod's bytes
      off-s  : site ∉ sens chk         -- key_B: provable no-op

  -- THE COUNTEREXAMPLE TERM.  cache-logfmt is a logging-only definition
  -- in `cache`; `cache` is imported by claims-check; claims-check is not
  -- sensitive to it.
  over-inclusion : OverIncluded
  over-inclusion = record
    { chk    = claims-check
    ; mod    = cache
    ; site   = cache-logfmt
    ; in-clo = there (here refl)              -- cache ∈ gate ∷ cache ∷ bib ∷ []
    ; in-mod = there (here refl)              -- cache-logfmt ∈ defsOf cache
    ; off-s  = λ { (there (there (there ()))) }
    }

  -- A second, structurally different witness: cache-key itself.  Same
  -- module, different reason (claims-check runs uncached in the sweep).
  over-inclusion₂ : OverIncluded
  over-inclusion₂ = record
    { chk    = claims-check
    ; mod    = cache
    ; site   = cache-key
    ; in-clo = there (here refl)
    ; in-mod = here refl
    ; off-s  = λ { (there (there (there ()))) }
    }

  -- key_B is at least as coarse-grained-correct as key_A: anything key_B
  -- skips, it skips soundly (Theorem 1).  And it skips strictly more:
  -- the witness above is a cell key_A re-runs.  Formally:

  -- Given a world change that touches ONLY module m, and a cell whose
  -- closure contains m, key_A must re-run.
  touches-only : World → World → Module → Set
  touches-only w w′ m = (w m ≢ w′ m) × (∀ n → n ≢ m → w n ≡ w′ n)

  keyA-reruns-the-witness :
    ∀ (w w′ : World) →
    touches-only w w′ (OverIncluded.mod over-inclusion) →
    KeyA-rerun w w′ (OverIncluded.chk over-inclusion , OverIncluded.site over-inclusion)
  keyA-reruns-the-witness w w′ (m≢ , _) same =
    m≢ (same cache (there (here refl)))

  keyB-skips-the-witness :
    KeyB-skip (OverIncluded.chk over-inclusion , OverIncluded.site over-inclusion)
  keyB-skips-the-witness = OverIncluded.off-s over-inclusion

  -- STRICT REFINEMENT, as one statement: there is a cell and a world
  -- change where key_A re-runs and key_B soundly skips.
  strict-refinement :
    ∃[ cell ] ((∀ w w′ → touches-only w w′ cache → KeyA-rerun w w′ cell)
               × KeyB-skip cell)
  strict-refinement =
    (claims-check , cache-logfmt)
    , (λ w w′ (m≢ , _) same → m≢ (same cache (there (here refl))))
    , keyB-skips-the-witness

  ------------------------------------------------------------------------
  -- 6.  THEOREM 3 (THE QUANTITATIVE SHAPE).
  --
  -- One module m changes.  We count the cells each notion invalidates.
  ------------------------------------------------------------------------

  -- allChecks, and its EXHAUSTIVENESS certificate.
  --
  -- `allChecks` alone is just a list someone wrote; nothing ties it to
  -- the `Check` datatype.  `allChecks-covers` is the tie: it pattern
  -- matches on EVERY constructor of Check, so adding a constructor
  -- makes this definition a COVERAGE ERROR rather than silently
  -- leaving the new check out of every sum below.
  --
  -- (Verified by probe: with the previous inline
  --  `sumOverChecks f = f claims-check + f render-check`, adding a
  --  third check importing `cache` left `invA cache ≡ 4` typechecking
  --  GREEN when the honest answer was 6.  That is R4.)
  allChecks : List Check
  allChecks = claims-check ∷ render-check ∷ []

  allChecks-covers : ∀ (c : Check) → c ∈ allChecks
  allChecks-covers claims-check = here refl
  allChecks-covers render-check = there (here refl)

  -- decidable membership as a Bool, for counting
  _∈?M_ : (m : Module) → (ms : List Module) → Bool
  m ∈?M []       = false
  m ∈?M (n ∷ ns) with m ≟M n
  ... | yes _ = true
  ... | no  _ = m ∈?M ns

  _∈?D_ : (d : DefSite) → (ds : List DefSite) → Bool
  d ∈?D []       = false
  d ∈?D (e ∷ es) with d ≟D e
  ... | yes _ = true
  ... | no  _ = d ∈?D es

  -- How many of `ds` are in `sens c`.
  countSens : Check → List DefSite → ℕ
  countSens c []       = 0
  countSens c (d ∷ ds) with d ∈?D sens c
  ... | true  = suc (countSens c ds)
  ... | false = countSens c ds

  -- The number of def-sites of m that check c is sensitive to.
  sensIn : Check → Module → ℕ
  sensIn c m = countSens c (defsOf m)

  -- key_A: if m ∈ closure c, EVERY def-site of m yields a re-run
  -- (because every one of them perturbs a staged byte).
  invA1 : Check → Module → ℕ
  invA1 c m with m ∈?M closure c
  ... | true  = length (defsOf m)
  ... | false = 0

  invB1 : Check → Module → ℕ
  invB1 c m with m ∈?M closure c
  ... | true  = sensIn c m
  ... | false = 0

  -- Fold over `allChecks` — NOT an inline sum over hand-named
  -- constructors.  The set now has an owner (`allChecks`) whose
  -- exhaustiveness is certified by `allChecks-covers`.
  sumOver : List Check → (Check → ℕ) → ℕ
  sumOver []       f = 0
  sumOver (c ∷ cs) f = f c + sumOver cs f

  sumOverChecks : (Check → ℕ) → ℕ
  sumOverChecks f = sumOver allChecks f

  -- |{c : m ∈ closure c}| × |defsOf m|, summed the honest way (per check,
  -- since defsOf m is the same for each, this equals the product form in
  -- the prompt).
  invA : Module → ℕ
  invA m = sumOverChecks (λ c → invA1 c m)

  invB : Module → ℕ
  invB m = sumOverChecks (λ c → invB1 c m)

  -- THEOREM: key_B never invalidates more than key_A.  This is the
  -- symbolic content of the ratio invB/invA ≤ 1; we prove the ≤ rather
  -- than introducing rationals, which would not add information.
  invB1≤invA1 : ∀ c m → invB1 c m ≤ invA1 c m
  invB1≤invA1 c m with m ∈?M closure c
  ... | false = z≤n
  ... | true  = go (defsOf m)
    where
      go : (ds : List DefSite) → countSens c ds ≤ length ds
      go []       = z≤n
      go (d ∷ ds) with d ∈?D sens c
      ... | true  = s≤s (go ds)
      ... | false = ≤-trans (go ds) (n≤1+n (length ds))

  -- Proved by induction over the fold, so it does not name
  -- constructors either and cannot go stale when Check grows.
  sumOver-mono : ∀ (cs : List Check) (f g : Check → ℕ) →
                 (∀ c → f c ≤ g c) → sumOver cs f ≤ sumOver cs g
  sumOver-mono []       f g f≤g = z≤n
  sumOver-mono (c ∷ cs) f g f≤g = +-mono-≤ (f≤g c) (sumOver-mono cs f g f≤g)

  invB≤invA : ∀ m → invB m ≤ invA m
  invB≤invA m = sumOver-mono allChecks _ _ (λ c → invB1≤invA1 c m)

  -- And the inequality is STRICT for `cache` in this model: computed,
  -- not assumed.  (invA cache = 4 — two checks import cache, two
  -- def-sites each; invB cache = 0 — neither check is sensitive to
  -- either cache def-site.)
  invA-cache : invA cache ≡ 4
  invA-cache = refl

  invB-cache : invB cache ≡ 0
  invB-cache = refl

  -- The ratio is therefore 0/4 here.  IN GENERAL it is
  --
  --     invB m / invA m  =  Σ_{c : m ∈ closure c} |sens c ∩ defsOf m|
  --                       ─────────────────────────────────────────────
  --                         |{c : m ∈ closure c}| · |defsOf m|
  --
  -- Nothing in this file fixes those cardinalities; they are properties
  -- of the real engine.  TO INSTANTIATE, one must measure, per module m:
  --   (a) |defsOf m|            — static, from the AST mutator
  --   (b) |{c : m ∈ closure c}| — static, from the import graph
  --   (c) |sens c ∩ defsOf m|   — MEASURED, from a complete sweep
  -- Only (c) requires running anything.  We deliberately do not guess.

  ------------------------------------------------------------------------
  -- 7.  THEOREM 4 (THE CONFOUND).
  --
  -- Two reasons a hit rate is low:
  --   (i)  GENUINE     — inputs really changed and the result changed too
  --   (ii) OVER-INCLUSION — inputs changed, result did not
  --
  -- We model an observer that sees, per re-run cell, the cached verdict
  -- and the fresh verdict.
  ------------------------------------------------------------------------

  data Verdict : Set where
    pass fail : Verdict

  _≟V_ : (v u : Verdict) → Dec (v ≡ u)
  pass ≟V pass = yes refl
  pass ≟V fail = no λ ()
  fail ≟V pass = no λ ()
  fail ≟V fail = yes refl

  -- An observation about one re-run cell.
  record Rerun : Set where
    field
      cell   : Cell
      cached : Verdict     -- what the previous key said
      fresh  : Verdict     -- what re-running produced

  -- The two hypotheses, as predicates on a re-run.
  Genuine : Rerun → Set
  Genuine r = Rerun.cached r ≢ Rerun.fresh r

  OverIncl : Rerun → Set
  OverIncl r = Rerun.cached r ≡ Rerun.fresh r

  -- THEOREM 4a: the verdict comparison is DECIDABLE and the two
  -- hypotheses are exclusive and exhaustive on it.  So a single re-run
  -- IS classifiable by this observation.
  classify : (r : Rerun) → Genuine r ⊎ OverIncl r
  classify r with Rerun.cached r ≟V Rerun.fresh r
  ... | yes eq = inj₂ eq
  ... | no  ne = inj₁ ne

  exclusive : ∀ r → Genuine r → OverIncl r → ⊥
  exclusive r g o = g o

  ------------------------------------------------------------------------
  -- THEOREM 4b (the REFUTATION — the important half).
  --
  -- "same verdict ⇒ over-inclusion" is FALSE.  Verdict equality is a
  -- necessary but not sufficient distinguisher: a cell whose staged
  -- inputs genuinely changed in a way that MATTERS can still produce the
  -- same verdict, because the verdict is a 1-bit projection of the run.
  --
  -- We make this precise by giving the run a richer result than its
  -- verdict, and observing that verdict-equality does not entail
  -- result-equality.
  ------------------------------------------------------------------------

  -- A run's full result: the verdict plus everything else the cell's
  -- output depends on (timings, diagnostics, the identity of the failing
  -- assertion, the trace).  Modelled as verdict + a residue.
  record Result : Set where
    constructor mk
    field
      verdict : Verdict
      residue : Residue

  -- A re-run whose VERDICT is unchanged but whose RESULT changed.
  -- Its existence refutes "same verdict ⇒ the re-run was unnecessary".
  verdict-blind : Σ (Result × Result) (λ p →
                    (Result.verdict (proj₁ p) ≡ Result.verdict (proj₂ p))
                    × (proj₁ p ≢ proj₂ p))
  verdict-blind = (mk pass r₁ , mk pass r₂) , refl , λ eq → r₁≢r₂ (cong Result.residue eq)

  ------------------------------------------------------------------------
  -- THEOREM 4c: what DOES suffice.
  --
  -- The distinguishing observation is not verdict-equality but
  -- RESULT-equality (equality of everything the downstream consumer of
  -- the cell reads).  Given a notion of "what is consumed", `Observed`,
  -- and a projection `obs : Result → Observed`, a re-run was
  -- unnecessary exactly when obs(cached) ≡ obs(fresh).
  --
  -- This is provable, and it is nearly a tautology — which is the
  -- finding.  The empirical difficulty is entirely in knowing `obs`:
  -- one must know which fields of the result any consumer reads.
  ------------------------------------------------------------------------

  module Distinguisher
    (Observed : Set)
    (obs      : Result → Observed)
    (_≟O_     : (x y : Observed) → Dec (x ≡ y))
    where

    -- A re-run was NECESSARY iff the observed projection moved.
    Necessary : Result → Result → Set
    Necessary old new = obs old ≢ obs new

    Unnecessary : Result → Result → Set
    Unnecessary old new = obs old ≡ obs new

    decide : ∀ old new → Necessary old new ⊎ Unnecessary old new
    decide old new with obs old ≟O obs new
    ... | yes eq = inj₂ eq
    ... | no  ne = inj₁ ne

    -- SOUND: an unnecessary re-run is one whose output the consumer
    -- could not have told from the cached one.
    unnecessary-is-indistinguishable :
      ∀ old new → Unnecessary old new → obs old ≡ obs new
    unnecessary-is-indistinguishable _ _ eq = eq

    -- COMPLETE in the same breath: nothing else can be indistinguishable.
    indistinguishable-is-unnecessary :
      ∀ old new → obs old ≡ obs new → Unnecessary old new
    indistinguishable-is-unnecessary _ _ eq = eq

  -- Instantiating `obs = verdict` recovers Theorem 4a; `verdict-blind`
  -- above shows that instantiation is UNSOUND as a proxy for the full
  -- result whenever a consumer reads anything but the verdict.
  module VerdictOnly = Distinguisher Verdict Result.verdict _≟V_

  ------------------------------------------------------------------------
  -- 8.  WHAT IS NOT PROVED (obligations left open, deliberately).
  --
  -- O1.  `sens-complete` is ASSUMED (a module parameter).  In the real engine its warrant
  --      is a sweep's coverage, which is itself only as complete as the
  --      mutation operators.  A def-site no operator can perturb is
  --      invisible to the sweep AND to `sens`, so completeness is
  --      relative to the operator set.  Not modelled here.
  --
  -- O2.  We assume mutating d ∈ defsOf m changes m's bytes.  A mutation
  --      that is a no-op at the byte level (e.g. normalised away by the
  --      .pyc compiler) would leave key_A unchanged too.  We use this
  --      assumption only in `keyA-reruns-the-witness`, where it appears
  --      as the hypothesis `touches-only w w′ cache` — so it is a
  --      HYPOTHESIS of that theorem, not a hidden postulate.
  --
  -- O3.  The confound analysis assumes cells are DETERMINISTIC: the same
  --      staged inputs give the same Result.  If a check is
  --      nondeterministic, obs-equality no longer separates (i) from
  --      (ii) — a differing observation could be flakiness rather than
  --      genuine invalidation.  Determinism is NOT stated in this file;
  --      §7's theorems are conditional on it in the informal reading.
  --
  -- O4.  Nothing here proves key_B is IMPLEMENTABLE at acceptable cost:
  --      computing `sens` requires the full grid that key_B is meant to
  --      shrink.  The model says key_B is sound and finer; it says
  --      nothing about the bootstrap.
  ------------------------------------------------------------------------
