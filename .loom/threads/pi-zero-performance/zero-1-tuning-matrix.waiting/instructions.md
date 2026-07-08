# zero-1-tuning-matrix

**.waiting — needs a real Zero 2 W.** Run zero-0's matrix on hardware, commit
Zero-safe defaults.

- [ ] Baseline with current defaults under the reference patch (record which).
- [ ] Run the matrix (`-p` 512→1024, `-n` 2→3, 44.1k vs 22.05k); pick defaults
      with honest headroom, commit to start.sh/bopos.config with the report in
      this stitch dir.
- [ ] Confirm nice-level/-rt observations from zero-0 on target; apply what
      measures well.

**Bob confirmed (2026-07-08): a dev Pi is ssh-reachable during development** —
an agent may drive the kit over ssh once zero-0 is tied. Confirm the host
in-session (check `~/.ssh/config`; the kite-choir-brains bopos-dev skill
documents the Pi tmux workflow) — never flash/reimage/apt-upgrade without
asking. This stitch waits only on zero-0 existing, not on Bob.
