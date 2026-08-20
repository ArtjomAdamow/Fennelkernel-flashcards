# Data Science & ML Fundamentals

<details>
  <summary><b> <sd

  Why does semi-supervised learning exist at all: what problem does it solve?</b></summary>
  
  Problem: labels are expensive (human time, expert knowledge: think doctors annotating X-rays), while unlabeled data is often abundant and cheap  
  Idea: learn from a small labeled set plus a large unlabeled set together  
  Result: much better models than the few labels alone would allow, at a fraction of the labeling cost
</details>

<details>
  <summary><b> <sd

  What is a Heuristic?</b></summary>
  
  Definition: a practical, experience-based shortcut that reduces effort  
  Trade-off: fast and usually good enough, but no guarantee of correctness or optimality  
  When used: when an exact algorithmic solution is impractical, unknown, or too expensive
</details>

<details>
  <summary><b> <sd

  What is Semi-supervised Learning? The image shows three datasets differing only in how many points are labeled. Which one is semi-supervised?</b></summary>
  
  Training data where only part of the examples are labeled, the rest unlabeled: Dataset C in the image (a mix of colored/labeled and gray/unlabeled points).
</details>

<details>
  <summary><b> <sd

  What is Reinforcement Learning? The image shows a dog performing a trick and getting a treat, with a burst of stars above it. What does this illustrate?</b></summary>
  
  Learning through feedback: an agent receives rewards or penalties for its actions instead of fixed labels. Just like the dog: no one told it the “correct” trick with an explicit label; it learns because the action was followed by a reward.
</details>

<details>
  <summary><b> <sd

  What's the difference between `git fetch` and `git pull`?</b></summary>
  
  `git fetch`: only downloads new remote commits; your working branch stays untouched; inspect first with `git log origin/main`  
  `git pull` = fetch + merge (or + rebase with `--rebase`): integrates the changes immediately  
  Rule of thumb: fetch to look first, pull to take the changes now
</details>

<details>
  <summary><b> <sd

  What does a Data Analyst do?</b></summary>
  
  Focuses on `EDA`, dashboards, KPIs and descriptive statistics to support business decisions.
</details>

<details>
  <summary><b> <sd

  What is a merge conflict, and how do you resolve it?</b></summary>
  
  What: two branches changed the same lines of the same file differently: Git can't pick automatically  
  How Git shows it: conflict markers `<<<<<<<` / `=======` / `>>>>>>>` in the file  
  Resolution: edit the file to the intended version, remove the markers, then `git add` + `git commit`  
  Pitfall: conflicts are normal teamwork, not an error — but never commit the markers themselves
</details>

<details>
  <summary><b> <sd

  What is a Pull Request (PR)? The image shows five stages of a collaborative Git workflow. Which stage is the PR itself?</b></summary>
  
  A request to merge a branch’s changes into another branch, typically after review and approval: Stage 3 in the image (“a pull request is opened, requesting review”).
</details>

<details>
  <summary><b> <sd

  What does `git stash` do, and when do you need it?</b></summary>
  
  What: parks all uncommitted changes on a stack and leaves a clean working directory  
  When: you must switch branches mid-work, but the work isn’t ready to commit  
  Back: `git stash pop` restores the parked changes  
  Pitfall: don’t confuse with `git reset --hard`, which destroys uncommitted changes
</details>

<details>
  <summary><b> <sd

  What's the difference between a Git repository and a remote?</b></summary>
  
  The repository is your project with its full history (local, via `git init` / `git clone`). A remote (e.g., `origin`) is a named reference to a copy of that repository hosted elsewhere, used to sync via `git push` / `git pull`.
</details>

<details>
  <summary><b> <sd

  What is the typical Data Science workflow (pipeline)?</b></summary>
  
  Magnifying glass: collect & explore the data  
  Gear: build/train a model  
  Bar chart: evaluate results, extract insights  
  Rocket: deploy the solution  
  In practice the pipeline is iterative: evaluation often sends you back to collecting more data or reworking the model.
</details>

<details>
  <summary><b> <sd

  What is an Algorithm (in the CS sense)?</b></summary>
  
  Definition: a finite set of unambiguous instructions, executed in a fixed order, that reaches a specific goal with a clear end condition  
  Key property: exact and repeatable: same input, same result  
  Contrast: a heuristic trades this guarantee for speed/simplicity
</details>

<details>
  <summary><b> <sd

  What does a Data Engineer do?</b></summary>
  
  Builds data pipelines, warehouses, `ETL` processes and infrastructure that other data roles rely on.
</details>

<details>
  <summary><b> <sd

  What does `git clone` do (vs. `git init`)?</b></summary>
  
  `git clone <url>`: downloads an existing repository with its complete history; the remote `origin` is configured automatically  
  `git init`: creates a brand-new empty repository with no history  
  Rule of thumb: new project → init; joining an existing project → clone
</details>

<details>
  <summary><b> <sd

  How do you correctly interpret a probabilistic prediction like “70% chance of rain”?</b></summary>
  
  Meaning: among many situations with these starting conditions, ~70% end in rain  
  Not: rain during 70% of the day, or over 70% of the area, or a guarantee  
  Why it matters: ML models output probabilities — they quantify uncertainty, not promises
</details>

<details>
  <summary><b> <sd

  What is Supervised Learning?</b></summary>
  
  Training with data that includes known target values (labels), e.g., predicting house prices from features.  
  Like the student in the image: labels are handed out explicitly by the teacher; the learner must infer the rule mapping features to labels.
</details>

<details>
  <summary><b> <sd

  What belongs in a `.gitignore` file (data science project)?</b></summary>
  
  Everything that is secret, machine-specific, or regenerable:  
  secrets: `.env`, API keys  
  environments: `.venv/`, conda envs  
  caches: `__pycache__/`, `.ipynb_checkpoints/`  
  (often) large data files  
  Pitfall: a secret pushed once is public forever — `.gitignore` it before the first commit
</details>

<details>
  <summary><b> <sd

  Which system is deterministic, which probabilistic?</b></summary>
  
  System A: deterministic (same input → same output)  
  System B: probabilistic (same input → different outputs with probabilities)
</details>

<details>
  <summary><b> <sd

  Which result is the merge, which is the rebase?</b></summary>
  
  Result A: merge (extra commit joining histories)  
  Result B: rebase (linear history; feature commits moved after latest main commit)  
  Rebase rewrites your local commits (new hashes): avoid on shared commits
</details>

<details>
  <summary><b> <sd

  Which type (A–D) is Supervised, Unsupervised, Semi-supervised, Reinforcement?</b></summary>
  
  Type C = Supervised  
  Type D = Unsupervised  
  Type A = Semi-supervised  
  Type B = Reinforcement  
  They differ mainly in how much labeled data exists and whether learning uses feedback.
</details>

<details>
  <summary><b> <sd

  What is Unsupervised Learning?</b></summary>
  
  Training with data that has no labels: the model finds structure on its own, e.g., clustering customers.  
  Like the kids in the image: no one told them the groups; similarity alone formed clusters.
</details>

<details>
  <summary><b> <sd

  What’s the golden rule for choosing between an algorithm and ML?</b></summary>
  
  Use ML only when simpler, exact alternatives are exhausted.  
  If a rule-based solution already works reliably, use that.  
  ML is for problems without reliable fixed rules.
</details>

<details>
  <summary><b> <sd

  What are common sources of bias in ML?</b></summary>
  
  Source A: who is (and isn’t) represented in the training data  
  Source B: which outcome the objective is designed to optimize  
  Bias can arise from data or design choices, even without intent.
</details>

<details>
  <summary><b> <sd

  Which stage is the staging area?</b></summary>
  
  Stage 2: you reach it via `git add` and leave it via `git commit`.  
  It’s where changes are marked for inclusion in the next commit.
</details>

<details>
  <summary><b> <sd

  What are the four core components of a reinforcement learning setup?</b></summary>
  
  Agent: the learner  
  Environment: the world  
  Action: what the agent can do  
  Reward: feedback after each action  
  The agent learns a policy that maximizes accumulated reward.
</details>

<details>
  <summary><b> <sd

  What does `git commit` do?</b></summary>
  
  Permanently saves the currently staged snapshot into the local repository history  
  Scope: only staged changes (`git add` first!)  
  Good practice: small commits with clear messages
</details>

<details>
  <summary><b> <sd

  Why is version control essential for data science?</b></summary>
  
  Reproducibility: restore any past state exactly  
  Collaboration: branches + pull requests instead of file ping‑pong  
  Safe experimentation: risky ideas live on branches
</details>

<details>
  <summary><b> <sd

  What’s the difference between structured and unstructured data?</b></summary>
  
  Structured: fixed rows/columns — CSV, SQL, spreadsheets  
  Unstructured: free text, images, audio, video — needs NLP or deep learning  
  The structure determines which methods apply
</details>

<details>
  <summary><b> <sd

  What’s the difference between Classification and Regression?</b></summary>
  
  Classification: predicts a category  
  Regression: predicts a continuous number  
  Deciding factor: the type of the target variable
</details>

<details>
  <summary><b> <sd

  What is “Weak AI”?</b></summary>
  
  AI built to solve one specific task well — nearly all real-world AI.  
  Like the robot in the image: focused entirely on its one task; everything else out of reach.  
  Contrast: “Strong AI” = hypothetical general intelligence.
</details>

