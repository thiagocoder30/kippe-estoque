#!/usr/bin/env bash
#
# ============================================================
# KIPPE PLATFORM
# Institutional Installation Framework
# ------------------------------------------------------------
# Module  : git.sh
# Version : 1.0.0
# Status  : Stable
# ============================================================

[[ -n "${KIPPE_GIT_LOADED:-}" ]] && return 0 2>/dev/null || true
readonly KIPPE_GIT_LOADED=1

kippe::git_root() {

    git rev-parse --show-toplevel

}

kippe::git_branch() {

    git branch --show-current

}

kippe::git_commit_hash() {

    git rev-parse --short HEAD

}

kippe::git_has_changes() {

    [[ -n "$(git status --porcelain)" ]]

}

kippe::git_stage_all() {

    git add -A

}

kippe::git_commit() {

    local message="$1"

    if ! kippe::git_has_changes; then
        kippe::warn "Nothing to commit."
        return 0
    fi

    kippe::git_stage_all

    git commit -m "${message}"

}

kippe::git_push() {

    local remote="${1:-origin}"
    local branch

    branch="$(kippe::git_branch)"

    git push "${remote}" "${branch}"

}

kippe::git_pull() {

    local remote="${1:-origin}"
    local branch

    branch="$(kippe::git_branch)"

    git pull --rebase "${remote}" "${branch}"

}

kippe::git_status() {

    git status --short

}

kippe::git_tag() {

    local tag="$1"

    git tag "${tag}"

}

kippe::git_info() {

    cat <<EOF
Repository : $(basename "$(kippe::git_root)")
Branch     : $(kippe::git_branch)
Commit     : $(kippe::git_commit_hash)
EOF

}
