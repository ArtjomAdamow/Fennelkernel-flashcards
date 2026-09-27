
# Github & Version Control Workflows
<details>
  <summary><b> <sd

  What do the `<<<<<<<`, `=======`, and `>>>>>>>` markers mean in a file after
  a `merge` conflict?</b></summary>
  
  They delimit the two competing versions inline: the section down to `=======` is your current `branch`'s version, and the section down to `>>>>>>>` is the incoming `branch`'s version. You edit the file to keep the correct combination, remove the markers, then `stage` and `commit` to finish the `merge`.
</details>

<details>
  <summary><b> <sd

  What is the difference between plain `git branch` and `git branch -a`?</b></summary>
  
  Plain `git branch` lists your local branches, with the current one marked by an
  asterisk. `git branch -a` lists both local branches and remote tracking
  branches.
</details>

<details>
  <summary><b> <sd

  What is a `.gitignore` file for?</b></summary>
  
  It lists filename and directory patterns that `git` should treat as untracked and
  never show in `git status` or accidentally `stage`, for example `node_modules/`,
  `.env`, or `__pycache__/`.
</details>

<details>
  <summary><b> <sd

  What is the standard `git` workflow order for recording a change to a file?</b></summary>
  
  Modify the file in your working directory, selectively `stage` the changes you
  want with `git add`, then `commit` the staged snapshot with `git commit` to store
  it permanently in the repository.
</details>

<details>
  <summary><b> <sd

  What causes a `merge` conflict?</b></summary>
  
  `Git` can't automatically reconcile two `branches` because both changed the
  same lines (or one edited a line the other deleted) since they diverged from a
  common point. You have to manually resolve the conflict before the `merge`
  can be completed.
</details>

<details>
  <summary><b> <sd

  What is a "detached `HEAD`" state?</b></summary>
  
  It's when `HEAD` points directly at a specific `commit` instead of at the tip of a
  `branch`. `Commits` made in this state don't belong to any `branch` and can
  become unreachable, eligible for eventual garbage collection, unless you
  create a new `branch` from that point before switching away.
</details>

<details>
  <summary><b> <sd

  What does `git config --global pull.ff only` actually change about `git pull`'s
  behavior?</b></summary>
  
  It makes `git pull` only succeed when it can fast forward, meaning your local
  `branch` has no divergent `commits` of its own. If histories have diverged, `pull`
  errors out instead of silently creating a `merge` `commit`, forcing you to
  consciously decide how to reconcile the branches yourself.
</details>

<details>
  <summary><b> <sd

  How do you unstage a file you've `git add`'ed, without discarding the edits
  themselves?</b></summary>
  
  `git restore --staged <file>` (the modern command), or the older equivalent `git`
  `reset HEAD <file>`. Both move the file back to `modified` without touching its
  actual content.
</details>

<details>
  <summary><b> <sd

  What steps sync a local feature `branch` that's fallen behind `main` after a
  teammate's `pull` request was `merged`?</b></summary>
  
  Switch to `main` (`git switch main`), `pull` the latest changes (`git pull`), switch
  back to your `branch` (`git switch <branch_name>`), then `merge` `main`'s new
  `commits` into your `branch` (`git merge main`), resolving any conflicts, before
  pushing again.
</details>

<details>
  <summary><b> <sd

  What is the difference between `git diff` and `git diff --staged`?</b></summary>
  
  Plain `git diff` compares your working directory to the staging area, showing
  unstaged edits. `git diff --staged` (equivalently `--cached`) compares the
  staging area to the last `commit`, showing exactly what would go into the next
  `commit`.
</details>

<details>
  <summary><b> <sd

  What is the difference between `git add` and `git commit`?</b></summary>
  
  `git add` moves changes from the working directory into the staging area
  (`index`): it says "this is what I want in the next snapshot". `git commit` takes
  whatever is currently staged and permanently records it as a new snapshot
  in the repository's history.
</details>

<details>
  <summary><b> <sd

  What uniquely identifies every `git commit`, and why does that matter for the
  integrity of the history?</b></summary>
  
  A `SHA` hash computed from the `commit`'s content, metadata (`author`,
  `message`, `timestamp`), and its parent `commit` reference(s). This chains
  `commits` together, so changing anything about a past `commit` changes its
  hash, and therefore every descendant `commit`'s hash too, making tampering
  with history detectable.
</details>

<details>
  <summary><b> <sd

  What does `git switch -c <branch>` do, and what is its older equivalent?</b></summary>
  
  The `-c` flag creates a brand new `branch` and switches you onto it in a single
  step. The older, equivalent two part `command` is `git checkout -b <branch>`.
</details>

<details>
  <summary><b> <sd

  What is the difference between `git fetch` and `git pull`?</b></summary>
  
  `git fetch` downloads new `commits` and `refs` from a `remote` but never touches
  your current working `branch`. `git pull` does that same `fetch` and then
  immediately `merges` (or `rebases`) those new `commits` into your current
  `branch`.
</details>

<details>
  <summary><b> <sd

  What typically has to happen before a `pull` request's `merge` option becomes
  available on GitHub?</b></summary>
  
  At least one requested `reviewer` needs to approve the changes (many
  projects require this before `merging` is even allowed). `Reviewers` can also
  explicitly request changes, which blocks `merging` until those concerns are
  addressed.
</details>

<details>
  <summary><b> <sd

  What happens when you run `git init` inside a project folder?</b></summary>
  
  It turns the folder into a `git` repository by creating a hidden `.git` subdirectory
  that stores the `commit` history, `refs`, and `config`. No files are tracked yet until
  you explicitly `git add` them.
</details>

<details>
  <summary><b> <sd

  What's the practical difference between `merge` and `rebase` when integrating
  one `branch`'s changes into another?</b></summary>
  
  `Merge` creates a new `commit` that joins two histories together, preserving
  both `branches`' `commits` exactly as they happened. `Rebase` replays your
  `branch`'s `commits` one by one on top of the other `branch`'s latest tip,
  producing new `commit` hashes and a linear history with no `merge` `commit`.
</details>

<details>
  <summary><b> <sd

  After `pushing` a brand new local `branch` for the first time, what flag links it to
  a matching `remote` `branch`, and why does that matter?</b></summary>
  
  `git push --set-upstream origin <branch_name>` (or the shorter `-u origin
  <branch_name>`). It links your local `branch` to the corresponding `remote`
  `branch`, so subsequent `git push` and `git pull` `commands` on that `branch`
  already know which `remote` and `branch` to sync with, without you specifying
  it every time.
</details>

<details>
  <summary><b> <sd

  What are the three stages a change moves through in `git`'s basic model:
  `modified`, `staged`, and `committed`?</b></summary>
  
  `Modified` means the file was edited in the working directory but not yet
  marked for the next `commit`. `Staged` means it was marked (via `git add`) to go
  into the next `commit`. `Committed` means it's safely stored as a permanent
  snapshot in the local `.git` database.
</details>

<details>
  <summary><b> <sd

  What problem does `git stash` solve?</b></summary>
  
  It temporarily shelves your uncommitted changes (working directory and
  optionally staged changes) so you get a clean working tree, useful for
  switching `branches` or `pulling` without `committing` half finished work. Later,
  `git stash pop` or `git stash apply` reapplies those changes.
</details>

<details>
  <summary><b> <sd

  Why prefer `git revert` over `git reset` when undoing a `commit` that others have
  already `pulled`?</b></summary>
  
  `git revert` adds a brand new `commit` that undoes the changes of an earlier
  `commit`, preserving history exactly as it happened. `git reset` moves the
  `branch` pointer, optionally discarding `commits`, which effectively rewrites
  history and causes trouble for anyone who already `pulled` the `commits` it
  removes.
</details>

<details>
  <summary><b> <sd

  Why is `git` described as a distributed version control system, and why does
  that matter in practice?</b></summary>
  
  Every `clone` contains a full copy of the project's entire history, not just the
  latest snapshot. That means you can `commit`, `branch`, and view `logs`
  completely offline; syncing with a `remote` (via `push` or `pull`) is a separate,
  deliberate step, not something baked into every operation like it is in older
  centralized systems.
</details>

<details>
  <summary><b> <sd

  When can `git` perform a fast forward `merge` instead of creating a `merge`
  `commit`?</b></summary>
  
  When the `branch` you're `merging` into hasn't diverged, meaning its tip is a
  direct ancestor of the `branch` being `merged` in. Since there's nothing to
  reconcile, `git` can simply move the `branch` pointer forward with no new
  `commit` needed.
</details>

<details>
  <summary><b> <sd

  What does a `git tag` typically mark, and how is it different from a `branch`?</b></summary>
  
  A `tag` marks a specific `commit` as significant, such as a `release` like `v1.0.0`.
  Unlike a `branch`, a `tag` is a fixed pointer, it doesn't move forward
  automatically as new `commits` get added on top.
</details>

<details>
  <summary><b> <sd

  What is a `pull` request (`PR`), and is it a core `git` feature or something else?</b></summary>
  
  A `pull` request proposes `merging` one `branch`'s changes into another and
  opens the changes up for discussion, `review`, and approval before anything is
  actually `merged`. It's a feature of hosting platforms like GitHub and GitLab; `git`
  itself has no built in concept of a "`pull` request" at all.
</details>

<details>
  <summary><b> <sd

  What are the four global `git config` `commands` typically used to set up `git` for
  the first time?</b></summary>
  
  `git config --global user.name "Your Name"`; `git config --global user.email
  "your.email@example.com"`; `git config --global pull.ff only` (only allow fast
  forward `pulls`); `git config --global init.defaultBranch main` (name new `repos'`
  initial `branch` `main`). Use `git config --list` to see every currently active setting.
</details>

<details>
  <summary><b> <sd

  What does `git status` tell you, and why is it worth running after every
  `command` while you're still learning `git`?</b></summary>
  
  It reports the current state of your working directory and staging area (which
  files are untracked, `modified`, or `staged`), and it also suggests the exact
  follow up `commands` you'd need to `stage`, `unstage`, `track`, or `untrack` a file.
</details>

<details>
  <summary><b> <sd

  What does `git commit --amend` do, and what's the caution around it?</b></summary>
  
  It replaces the most recent `commit` with a new one, letting you fold in
  currently `staged` changes and/or edit the `commit` `message`, instead of
  creating a separate follow