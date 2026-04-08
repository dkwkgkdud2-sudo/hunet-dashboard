#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
휴넷 하이브리드러닝운영팀 - 교육운영 대시보드 자동 생성기
GitHub Actions에서 실행되어 Jira 데이터를 가져와 HTML을 생성합니다.
"""

import requests
import base64
import os
from datetime import datetime

# GitHub Actions secrets에서 읽어옴
JIRA_DOMAIN = "ihunet.atlassian.net"
JIRA_EMAIL = os.environ.get("JIRA_EMAIL", "")
JIRA_TOKEN = os.environ.get("JIRA_TOKEN", "")
ASSIGNEE_ID = "712020:fe080e9d-2ca8-4503-aecf-1038752788c7"
OUTPUT_FILE = "휴넷_교육운영_대시보드.html"


def get_headers():
    credentials = base64.b64encode(f"{JIRA_EMAIL}:{JIRA_TOKEN}".encode()).decode()
    return {"Authorization": f"Basic {credentials}", "Accept": "application/json"}


def fetch_issues():
    # URL에서 확인된 정확한 조건: 프로젝트 LZIJ + 담당자 + 운영중 상태
    jql = f'project = LZIJ AND assignee = "{ASSIGNEE_ID}" AND status = 운영중 ORDER BY updated DESC'
    fields = ["summary", "status", "priority", "updated", "duedate", "description", "comment", "labels"]

    headers = get_headers()
    headers["Content-Type"] = "application/json"

    # POST 방식으로 호출 (한글 JQL 처리에 안정적)
    payload = {"jql": jql, "maxResults": 100, "fields": fields}

    print(f"🔍 Jira 검색 중... JQL: {jql}")

    # 신규 API 엔드포인트 사용 (Atlassian 마이그레이션 정책 반영)
    url = f"https://{JIRA_DOMAIN}/rest/api/3/search/jql"
    resp = requests.post(url, headers=headers, json=payload, timeout=30)
    print(f"API 응답: {resp.status_code}")

    if not resp.ok:
        print(f"오류 내용: {resp.text[:500]}")
        resp.raise_for_status()

    issues = resp.json().get("issues", [])
    print(f"✅ 운영중 프로젝트 {len(issues)}건 조회 완료")
    return issues


def parse_adf(node):
    if not node:
        return ""
    if isinstance(node, dict):
        if node.get("type") == "text":
            return node.get("text", "")
        return " ".join(parse_adf(c) for c in node.get("content", []))
    return ""


def get_dday(due_str):
    if not due_str:
        return None
    try:
        due = datetime.strptime(due_str, "%Y-%m-%d").date()
        return (due - datetime.now().date()).days
    except:
        return None


def dday_badge(dday):
    if dday is None:
        return ""
    if dday < 0:
        return f'<span class="dday dday-over">D+{abs(dday)}</span>'
    if dday == 0:
        return '<span class="dday dday-today">D-Day!</span>'
    if dday <= 7:
        return f'<span class="dday dday-soon">D-{dday}</span>'
    return f'<span class="dday dday-normal">D-{dday}</span>'


def generate_insights(issue):
    f = issue["fields"]
    insights = []
    dday = get_dday(f.get("duedate"))
    comments = f.get("comment", {}).get("comments", [])

    if dday is not None and 0 <= dday <= 3:
        insights.append(f"마감 {'오늘' if dday == 0 else str(dday) + '일 전'}입니다. 강사/고객사 최종 확인 및 현장 준비사항을 점검해보세요.")
    if dday is not None and dday < 0:
        insights.append(f"마감일이 {abs(dday)}일 지났습니다. 사후 처리 및 결과보고서 준비가 필요합니다.")
    if dday is not None and 7 <= dday <= 14:
        insights.append("교육 2주 전입니다. 사전 안내자료, 참석자 명단, 장소 확인 등을 점검할 시기예요.")
    if comments:
        last_date = datetime.strptime(comments[-1]["created"][:10], "%Y-%m-%d").date()
        days_since = (datetime.now().date() - last_date).days
        if days_since >= 3:
            insights.append(f"마지막 소통이 {days_since}일 전입니다. 강사 또는 고객사에 진행 상황 확인 메일을 보내보는 건 어떨까요?")
    if not comments:
        insights.append("아직 소통 기록이 없습니다. 강사/고객사 첫 연락 및 오리엔테이션 일정 공유를 준비해보세요.")

    return insights


def build_html(issues):
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    if not issues:
        tabs_html = '<button class="tab-btn active">데이터 없음</button>'
        contents_html = '<div class="tab-content active"><p class="empty-text">운영중 프로젝트가 없습니다.</p></div>'
    else:
        tabs_html = ""
        contents_html = ""
        for i, issue in enumerate(issues):
            f = issue["fields"]
            dday = get_dday(f.get("duedate"))
            badge = dday_badge(dday)
            active = "active" if i == 0 else ""
            short = f["summary"][:18] + "…" if len(f["summary"]) > 18 else f["summary"]

            tabs_html += f'<button class="tab-btn {active}" onclick="showTab({i})" title="{f["summary"]}">{short} {badge}</button>\n'

            # 댓글
            comments = f.get("comment", {}).get("comments", [])
            recent = list(reversed(comments[-3:]))
            if recent:
                comments_html = "".join(f"""
                <div class="comment-item">
                    <div class="comment-meta">
                        <span class="comment-author">👤 {c.get('author',{}).get('displayName','알 수 없음')}</span>
                        <span class="comment-date">{c.get('created','')[:10]}</span>
                    </div>
                    <p class="comment-body">{parse_adf(c.get('body',''))[:200]}</p>
                </div>""" for c in recent)
            else:
                comments_html = '<p class="empty-text">소통 기록 없음</p>'

            # 라벨
            labels_html = "".join(f'<span class="label">{l}</span>' for l in f.get("labels", []))

            # 설명
            desc = parse_adf(f.get("description"))[:400] or "내용 없음"

            # 인사이트
            insights = generate_insights(issue)
            if insights:
                insight_html = "<ul class='insight-list'>" + "".join(f"<li>{ins}</li>" for ins in insights) + "</ul>"
            else:
                insight_html = '<p class="insight-content" style="color:#bbb">현재 특이 사항 없음</p>'

            due = f.get("duedate") or "미설정"
            updated = (f.get("updated") or "")[:10]

            contents_html += f"""
            <div class="tab-content {active}" id="tab-{i}">
                <div class="project-header">
                    <div class="project-title-row">
                        <h2 class="project-title">{f['summary']}</h2>
                        <a href="https://{JIRA_DOMAIN}/browse/{issue['key']}" target="_blank" class="jira-link">🔗 Jira 보기</a>
                    </div>
                    <div class="project-meta">
                        <span class="meta-item">📌 {issue['key']}</span>
                        <span class="meta-item">🔄 업데이트: {updated}</span>
                        <span class="meta-item">📅 마감: {due} {badge}</span>
                        <span class="meta-item">💬 댓글 {len(comments)}건</span>
                    </div>
                    {f'<div class="labels">{labels_html}</div>' if labels_html else ''}
                </div>
                <div class="content-grid">
                    <div class="card">
                        <div class="card-title">📋 업무 개요</div>
                        <p class="description-text">{desc}</p>
                    </div>
                    <div class="card">
                        <div class="card-title">💬 최근 소통 (Jira 댓글)</div>
                        {comments_html}
                    </div>
                    <div class="card full-width">
                        <div class="card-title">📧 메일 소통 현황 <span class="badge badge-pending">연동 예정</span></div>
                        <div class="mail-placeholder">
                            <div class="mail-icon">📧</div>
                            <p>메일 API 연동 후 강사 · 고객사 최신 소통 내용이 자동으로 표시됩니다</p>
                        </div>
                    </div>
                    <div class="card full-width ops-insight">
                        <div class="card-title">💡 오늘의 운영 포인트 <span class="badge badge-daily">일 1회</span></div>
                        {insight_html}
                    </div>
                </div>
            </div>"""

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>휴넷 교육운영 대시보드</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:'Segoe UI',-apple-system,'Noto Sans KR',sans-serif;background:#f0f2f5;color:#333}}
.header{{background:linear-gradient(135deg,#1e3a5f,#2d6a9f);color:white;padding:18px 30px;display:flex;align-items:center;justify-content:space-between;box-shadow:0 2px 10px rgba(0,0,0,.2)}}
.header-left h1{{font-size:19px;font-weight:700}}
.header-left p{{font-size:12px;opacity:.75;margin-top:3px}}
.last-updated{{background:rgba(255,255,255,.15);padding:5px 12px;border-radius:20px;font-size:11px}}
.tab-nav{{background:white;padding:0 20px;display:flex;overflow-x:auto;border-bottom:2px solid #e5e7eb;box-shadow:0 1px 3px rgba(0,0,0,.05)}}
.tab-btn{{padding:13px 18px;border:none;background:none;cursor:pointer;font-size:13px;color:#666;white-space:nowrap;border-bottom:3px solid transparent;margin-bottom:-2px;transition:all .2s;display:flex;align-items:center;gap:6px}}
.tab-btn:hover{{color:#2d6a9f;background:#f8f9ff}}
.tab-btn.active{{color:#1e3a5f;font-weight:600;border-bottom-color:#2d6a9f}}
.dday{{display:inline-block;padding:2px 6px;border-radius:10px;font-size:10px;font-weight:700}}
.dday-over{{background:#fee2e2;color:#dc2626}}
.dday-today{{background:#fef3c7;color:#d97706}}
.dday-soon{{background:#fef3c7;color:#d97706}}
.dday-normal{{background:#dbeafe;color:#2563eb}}
.tab-content{{display:none;padding:22px 28px}}
.tab-content.active{{display:block}}
.project-header{{background:white;border-radius:12px;padding:20px 24px;margin-bottom:18px;box-shadow:0 1px 4px rgba(0,0,0,.08);border-left:4px solid #2d6a9f}}
.project-title-row{{display:flex;align-items:center;justify-content:space-between;margin-bottom:10px}}
.project-title{{font-size:17px;font-weight:700;color:#1e3a5f}}
.jira-link{{color:#2d6a9f;text-decoration:none;font-size:12px;padding:4px 10px;border:1px solid #2d6a9f;border-radius:6px;transition:all .2s}}
.jira-link:hover{{background:#2d6a9f;color:white}}
.project-meta{{display:flex;gap:14px;flex-wrap:wrap}}
.meta-item{{font-size:12px;color:#555}}
.labels{{margin-top:8px;display:flex;gap:6px;flex-wrap:wrap}}
.label{{background:#e0f0ff;color:#1e6fb0;padding:2px 8px;border-radius:10px;font-size:11px}}
.content-grid{{display:grid;grid-template-columns:1fr 1fr;gap:16px}}
.card{{background:white;border-radius:12px;padding:18px 20px;box-shadow:0 1px 4px rgba(0,0,0,.08)}}
.card.full-width{{grid-column:1/-1}}
.card-title{{font-size:13px;font-weight:600;color:#1e3a5f;margin-bottom:14px;display:flex;align-items:center;gap:6px;padding-bottom:10px;border-bottom:1px solid #f0f2f5}}
.description-text{{font-size:13px;line-height:1.7;color:#555}}
.comment-item{{border-left:3px solid #dbeafe;padding:8px 12px;margin-bottom:10px;background:#f8fbff;border-radius:0 8px 8px 0}}
.comment-meta{{display:flex;align-items:center;gap:8px;margin-bottom:4px}}
.comment-author{{font-size:12px;font-weight:600;color:#2d6a9f}}
.comment-date{{font-size:11px;color:#999}}
.comment-body{{font-size:12px;color:#555;line-height:1.5}}
.empty-text{{font-size:13px;color:#bbb;text-align:center;padding:24px}}
.mail-placeholder{{text-align:center;padding:28px;color:#aaa;border:2px dashed #e5e7eb;border-radius:10px}}
.mail-icon{{font-size:34px;margin-bottom:10px}}
.mail-placeholder p{{font-size:13px}}
.ops-insight{{border-top:3px solid #f59e0b}}
.insight-list{{list-style:none;margin-top:10px}}
.insight-list li{{padding:8px 12px;margin-bottom:6px;background:#fffbeb;border-radius:8px;font-size:12px;color:#78350f;display:flex;align-items:flex-start;gap:8px}}
.insight-list li::before{{content:"💡";flex-shrink:0}}
.insight-content{{font-size:13px;line-height:1.8;color:#555}}
.badge{{padding:2px 8px;border-radius:10px;font-size:10px;font-weight:600;margin-left:6px}}
.badge-pending{{background:#fef3c7;color:#92400e}}
.badge-daily{{background:#d1fae5;color:#065f46}}
@media(max-width:768px){{.content-grid{{grid-template-columns:1fr}}.tab-content{{padding:14px}}}}
</style>
</head>
<body>
<div class="header">
    <div class="header-left">
        <h1>🎓 휴넷 교육운영 대시보드</h1>
        <p>하이브리드러닝운영팀 · 담당자: 김하영 PM</p>
    </div>
    <div class="last-updated">🔄 마지막 업데이트: {now}</div>
</div>
<div class="tab-nav">{tabs_html}</div>
<div>{contents_html}</div>
<script>
function showTab(i){{
    document.querySelectorAll('.tab-btn').forEach((b,idx)=>b.classList.toggle('active',idx===i));
    document.querySelectorAll('.tab-content').forEach((c,idx)=>c.classList.toggle('active',idx===i));
}}
</script>
</body>
</html>"""


if __name__ == "__main__":
    print("🏫 휴넷 교육운영 대시보드 생성 시작")
    issues = fetch_issues()
    html = build_html(issues)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"✅ {OUTPUT_FILE} 생성 완료!")
