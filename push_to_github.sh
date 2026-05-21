#!/bin/bash
set -e

cd "$(dirname "$0")"

if [ -z "$GITHUB_TOKEN" ]; then
  echo "GITHUB_TOKEN environment variable yo'q!"
  exit 1
fi

REPO_URL="https://${GITHUB_TOKEN}@github.com/telegrambotkrmv/Hahaha.git"

git config user.email "bot@railway.app"
git config user.name "TelegramBot"

if ! git log --oneline -1 > /dev/null 2>&1; then
  git add .
  git commit -m "Initial commit: Telegram video downloader bot"
fi

git remote remove origin 2>/dev/null || true
git remote add origin "$REPO_URL"

git push -u origin main --force

echo "GitHub ga muvaffaqiyatli push qilindi!"
