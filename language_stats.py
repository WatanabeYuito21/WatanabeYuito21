#!/usr/bin/env python3
"""
GitHub言語統計を取得してREADMEを更新するスクリプト
"""
import requests
import json
from collections import defaultdict
import sys
import os


def get_language_stats(username, token=None):
    """
    GitHubユーザーの全リポジトリから言語統計を取得

    Args:
        username: GitHubユーザー名
        token: GitHub Personal Access Token (オプション)

    Returns:
        dict: 言語名をキーとしたバイト数の辞書
    """
    headers = {}
    if token:
        headers['Authorization'] = f'token {token}'

    # ユーザーのリポジトリ一覧を取得
    repos_url = f'https://api.github.com/users/{username}/repos'
    params = {'per_page': 100, 'type': 'owner'}

    all_repos = []
    page = 1

    while True:
        params['page'] = page
        response = requests.get(repos_url, headers=headers, params=params)

        if response.status_code != 200:
            print(f"エラー: GitHubリポジトリ一覧の取得に失敗しました (status: {response.status_code})")
            print(f"レスポンス: {response.text}")
            return None

        repos = response.json()
        if not repos:
            break

        all_repos.extend(repos)
        page += 1

    # 各リポジトリの言語統計を集計
    language_bytes = defaultdict(int)

    for repo in all_repos:
        if repo['fork']:  # フォークしたリポジトリは除外
            continue

        languages_url = repo['languages_url']
        response = requests.get(languages_url, headers=headers)

        if response.status_code == 200:
            languages = response.json()
            for lang, bytes_count in languages.items():
                language_bytes[lang] += bytes_count

    return dict(language_bytes)


def calculate_percentages(language_bytes):
    """
    言語のバイト数から割合を計算

    Args:
        language_bytes: 言語名をキーとしたバイト数の辞書

    Returns:
        list: (言語名, 割合, バイト数)のタプルのリスト（割合の降順）
    """
    if not language_bytes:
        return []

    total_bytes = sum(language_bytes.values())

    percentages = [
        (lang, (bytes_count / total_bytes) * 100, bytes_count)
        for lang, bytes_count in language_bytes.items()
    ]

    # 割合の降順でソート
    percentages.sort(key=lambda x: x[1], reverse=True)

    return percentages


def format_stats_markdown(percentages):
    """
    統計データをMarkdown形式にフォーマット

    Args:
        percentages: calculate_percentages()の返り値

    Returns:
        str: Markdown形式の統計データ
    """
    if not percentages:
        return "統計データがありません。"

    markdown = "| 言語 | 使用割合 | コード量 |\n"
    markdown += "|------|----------|----------|\n"

    for lang, percent, bytes_count in percentages:
        # バイト数を読みやすい単位に変換
        if bytes_count >= 1024 * 1024:
            size_str = f"{bytes_count / (1024 * 1024):.2f} MB"
        elif bytes_count >= 1024:
            size_str = f"{bytes_count / 1024:.2f} KB"
        else:
            size_str = f"{bytes_count} bytes"

        # プログレスバーを作成
        bar_length = 20
        filled_length = int(bar_length * percent / 100)
        bar = '█' * filled_length + '░' * (bar_length - filled_length)

        markdown += f"| {lang} | {percent:.2f}% {bar} | {size_str} |\n"

    return markdown


def update_readme(stats_markdown, readme_path='README.md'):
    """
    README.mdに言語統計を追加または更新

    Args:
        stats_markdown: フォーマットされた統計データ
        readme_path: READMEファイルのパス
    """
    # README.mdを読み込み
    try:
        with open(readme_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        content = "# GitHub Profile\n\n"

    # 統計セクションのマーカー
    start_marker = "<!-- LANGUAGE_STATS_START -->"
    end_marker = "<!-- LANGUAGE_STATS_END -->"

    stats_section = f"{start_marker}\n## 📊 使用言語統計\n\n{stats_markdown}\n\n{end_marker}"

    # 既存の統計セクションを置き換え、なければ追加
    if start_marker in content and end_marker in content:
        import re
        pattern = f"{re.escape(start_marker)}.*?{re.escape(end_marker)}"
        content = re.sub(pattern, stats_section, content, flags=re.DOTALL)
    else:
        # コメントブロックの後に追加
        if '-->' in content:
            parts = content.rsplit('-->', 1)
            content = parts[0] + '-->\n\n' + stats_section + parts[1]
        else:
            content += '\n\n' + stats_section

    # README.mdに書き込み
    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"✓ {readme_path}を更新しました")


def main():
    # 環境変数またはコマンドライン引数からユーザー名を取得
    username = os.environ.get('GITHUB_USERNAME') or (sys.argv[1] if len(sys.argv) > 1 else 'WatanabeYuito21')
    token = os.environ.get('GITHUB_TOKEN')  # オプション: レート制限を回避するため

    print(f"GitHubユーザー: {username}")
    print("言語統計を取得中...")

    # 言語統計を取得
    language_bytes = get_language_stats(username, token)

    if language_bytes is None:
        sys.exit(1)

    if not language_bytes:
        print("言語データが見つかりませんでした。")
        sys.exit(0)

    # 割合を計算
    percentages = calculate_percentages(language_bytes)

    # 結果を表示
    print("\n使用言語統計:")
    print("=" * 50)
    for lang, percent, bytes_count in percentages:
        print(f"{lang:20} {percent:6.2f}%")

    # Markdownをフォーマット
    stats_markdown = format_stats_markdown(percentages)

    # README.mdを更新
    update_readme(stats_markdown)

    print("\n完了しました！")


if __name__ == '__main__':
    main()
