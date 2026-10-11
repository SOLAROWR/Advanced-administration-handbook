#!/usr/bin/env bash
# 사용법: build_docx.sh <작업폴더> <출력.docx> [보고서.md ...]
# 보고서를 생략하면 작업폴더의 reports/·theses/ 파일을 워크플로우 순서로 묶는다.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
WORK="${1:?작업폴더를 지정하세요}"
OUT="${2:?출력 파일명을 지정하세요}"
shift 2

files=()
if [ "$#" -gt 0 ]; then
  files=("$@")
else
  for stage in sector screen earnings-analysis earnings-preview initiate-coverage thesis catalysts earnings morning-note; do
    if [ "$stage" = thesis ]; then
      for f in "$WORK"/theses/*.md; do [ -e "$f" ] && files+=("$f"); done
    else
      for f in "$WORK"/reports/*_"$stage"_*.md "$WORK"/reports/*_"$stage".md; do [ -e "$f" ] && files+=("$f"); done
    fi
  done
fi
[ "${#files[@]}" -gt 0 ] || { echo "묶을 보고서가 없습니다" >&2; exit 1; }

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
MD="$TMP/all.md"
PB=$'\n\n```{=openxml}\n<w:p><w:r><w:br w:type="page"/></w:r></w:p>\n```\n\n'

{
  echo '---'
  echo 'title: "주식자동화 — 1인 투자 하우스 리서치 보고서 모음"'
  echo "subtitle: \"작성일 $(date +%Y-%m-%d)\""
  echo '---'
  echo
  echo '# 이 문서에 대하여'
  echo
  echo '| 순서 | 보고서 |'
  echo '|---|---|'
  i=1
  for f in "${files[@]}"; do
    title="$(grep -m1 '^# ' "$f" | sed 's/^# //')"
    echo "| $i | $title |"
    i=$((i+1))
  done
  echo
  echo '> ⚠️ 본 자료는 정보 정리용이며 투자 권유가 아닙니다. 최종 투자 판단과 책임은 본인에게 있습니다.'
  for f in "${files[@]}"; do
    printf '%s' "$PB"
    # "- (A)" 같은 줄이 알파벳 번호 목록으로 바뀌지 않게 괄호를 이스케이프
    sed -E 's/^- \(([A-Z])\)/- \\(\1\\)/' "$f"
    echo
  done
} > "$MD"

pandoc "$MD" -o "$OUT" --reference-doc="$HERE/../assets/reference.docx" --lua-filter="$HERE/table_widths.lua"
echo "완료: $OUT (${#files[@]}개 보고서)"
