"""pr-check.yml 의 Reviewer step. claude -p 로 pr-correctness-reviewer 를 부르고 리뷰를 JSON 파일로만 남긴다.

PR 에 게시하지 않는다. claude 에는 gh 읽기 명령만 허용한다(gh api 와 쓰기 도구는 막는다).
환경변수: PR_NUMBER, REPO, OUT_DIR, GH_TOKEN(workflow 의 GITHUB_TOKEN). 작업 폴더는 pr_reviewer_h0 clone 이다.
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

AGENT = "pr-correctness-reviewer"
ALLOWED_TOOLS = ["Bash(gh pr diff:*)", "Bash(gh pr view:*)", "Bash(gh pr checks:*)"]
DISALLOWED_TOOLS = ["Bash(gh api:*)", "Edit", "Write", "Read"]
TIMEOUT_SEC = 900

REVIEW_SCHEMA = {
    "type": "object",
    "required": ["commit_id", "event", "body", "comments"],
    "properties": {
        "commit_id": {"type": "string"},
        "event": {"enum": ["COMMENT"]},
        "body": {"type": "string"},
        "comments": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["path", "line", "side", "body"],
                "properties": {
                    "path": {"type": "string"},
                    "line": {"type": "integer", "minimum": 1},
                    "side": {"enum": ["RIGHT"]},
                    "body": {"type": "string"},
                },
            },
        },
    },
}


def build_prompt(pr_number: str, repo: str) -> str:
    return (
        f"PR 번호 {pr_number}, 저장소 {repo} 를 리뷰하라.\n"
        "이번 실행은 PR 에 게시하지 않는다. 에이전트 지침의 '게시' 절차(gh api 호출)는 하지 말고 무시하라.\n"
        "대신 게시했을 내용을 지정된 JSON 스키마로 반환하라:\n"
        "- commit_id = `gh pr view <N> -R <repo> --json headRefOid` 의 값\n"
        '- event = "COMMENT"\n'
        "- body = 요약(전체 판단, `미검증`, 하단 `## diff 밖`)\n"
        '- comments = diff 의 바뀐 줄(RIGHT side) 인라인 코멘트 [{path, line, side: "RIGHT", body}]. 없으면 빈 배열\n'
        "코드, 브랜치, PR 상태는 수정하지 않는다.\n"
    )


def is_review(obj: object) -> bool:
    """게시할 리뷰의 모양(REVIEW_SCHEMA)을 갖췄는지 본다."""
    if not isinstance(obj, dict) or obj.get("event") != "COMMENT":
        return False
    if not isinstance(obj.get("commit_id"), str) or not isinstance(obj.get("body"), str):
        return False
    comments = obj.get("comments")
    if not isinstance(comments, list):
        return False
    return all(
        isinstance(c, dict) and isinstance(c.get("path"), str) and c.get("side") == "RIGHT"
        and isinstance(c.get("body"), str) and type(c.get("line")) is int and c["line"] >= 1
        for c in comments
    )


def extract_review(data: dict) -> dict | None:
    """structured_output 이 있으면 그것을, 없으면 본문(result)의 마지막 ```json 블록을 리뷰로 쓴다.

    --agent 와 --json-schema 를 같이 쓰면 structured_output 이 비고 JSON 이 본문에 실리는 경우가 있다.
    """
    structured = data.get("structured_output")
    if is_review(structured):
        return structured
    result = data.get("result")
    if not isinstance(result, str):
        return None
    decoder = json.JSONDecoder()
    for part in reversed(result.split("```json")[1:]):
        start = part.find("{")
        if start < 0:
            continue
        try:
            candidate, _ = decoder.raw_decode(part[start:])
        except json.JSONDecodeError:
            continue
        if is_review(candidate):
            return candidate
    return None


def main() -> int:
    pr_number = os.environ["PR_NUMBER"]
    repo = os.environ["REPO"]
    out_dir = Path(os.environ["OUT_DIR"])
    out_dir.mkdir(parents=True, exist_ok=True)

    # 어떤 리뷰어 버전으로 돌았는지 로그에 남긴다
    for git_args in (["rev-parse", "HEAD"], ["branch", "--show-current"], ["status", "--short"]):
        shown = subprocess.run(["git", *git_args], capture_output=True, text=True, check=False)
        print(f"[reviewer repo] git {' '.join(git_args)}: {shown.stdout.strip() or '-'}")

    # 이 실행에서는 hook 을 끈다(pr_reviewer_h0 의 Stop hook 이 pytest 를 돌리지 않게 한다)
    settings_path = out_dir / "claude-settings.json"
    settings_path.write_text(json.dumps({"disableAllHooks": True}), encoding="utf-8")

    claude = shutil.which("claude")
    if claude is None:
        print("claude 를 PATH 에서 찾을 수 없다", file=sys.stderr)
        return 1
    args = [
        claude, "-p", "--agent", AGENT,
        "--output-format", "json",
        "--json-schema", json.dumps(REVIEW_SCHEMA),
        "--settings", str(settings_path),
        "--allowedTools", *ALLOWED_TOOLS,
        "--disallowedTools", *DISALLOWED_TOOLS,
    ]
    try:
        # 프롬프트는 stdin 으로 넘긴다(Windows 명령줄 길이 제한)
        proc = subprocess.run(
            args, input=build_prompt(pr_number, repo), timeout=TIMEOUT_SEC, shell=False,
            capture_output=True, text=True, encoding="utf-8", errors="replace", check=False,
        )
    except subprocess.TimeoutExpired:
        print(f"claude 가 {TIMEOUT_SEC}초 안에 끝나지 않았다", file=sys.stderr)
        return 1

    (out_dir / "claude-raw.json").write_text(proc.stdout, encoding="utf-8")
    (out_dir / "claude-stderr.log").write_text(proc.stderr, encoding="utf-8")
    if proc.returncode != 0:
        print(f"claude 실패 (exit {proc.returncode}): {proc.stderr.strip()}", file=sys.stderr)
        return 1

    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError as e:
        print(f"claude 출력이 JSON 이 아니다: {e}", file=sys.stderr)
        return 1
    if not isinstance(data, dict) or data.get("is_error") or data.get("subtype") != "success":
        print(f"claude 결과가 성공이 아니다: {data.get('result') if isinstance(data, dict) else data}", file=sys.stderr)
        return 1
    # 거부된 호출은 실행되지 않았다. 실패로 두지 않고 기록만 남긴다(허용 목록이 막은 것이므로 게시·쓰기는 일어나지 않았다).
    denials = data.get("permission_denials") or []
    if denials:
        (out_dir / "denials.json").write_text(json.dumps(denials, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"::warning::허용하지 않은 도구 호출 {len(denials)}건이 거부되었다 (review/denials.json)")
    review = extract_review(data)
    if review is None:
        print("structured_output 도 본문의 ```json 블록도 리뷰 형식이 아니다", file=sys.stderr)
        return 1

    (out_dir / "review.json").write_text(json.dumps(review, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"리뷰 저장: {out_dir / 'review.json'} (인라인 {len(review.get('comments', []))}건, 게시 안 함)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
